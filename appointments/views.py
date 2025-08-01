import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.conf import settings
from django.urls import reverse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.contrib.auth.decorators import user_passes_test
from django.utils.html import escape
from notifications.signals import notify

from .models import (
    Appointment, Organization, ChatRoom, ChatMessage, UserProfile, AuditLog, 
    DoctorOrganizationJoinRequest, MedicalRecord, Prescription, Insurance, 
    Payment, EmergencyContact, MedicationReminder, TelemedicineSession
)
from .forms import (
    AppointmentForm, MinimalPatientCreationForm, DoctorDutyForm, OrganizationForm, 
    PatientDataExportForm, UserProfileForm, RegistrationForm, AppointmentExportForm, 
    AppointmentImportForm, PatientImportForm, MedicalRecordForm, PrescriptionForm,
    InsuranceForm, PaymentForm, EmergencyContactForm, MedicationReminderForm, TelemedicineSessionForm
)
from .utils import send_notification, send_appointment_update, create_or_get_chat_room, save_chat_message, broadcast_appointment_ws_update

User = get_user_model()

# Google Calendar OAuth2 setup
GOOGLE_CLIENT_SECRETS_FILE = os.path.join(settings.BASE_DIR, 'client_secret.json')
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
GOOGLE_REDIRECT_URI = 'http://localhost:8000/oauth2callback/'

def home(request):
    return render(request, 'appointments/home.html', {'appointments': []})

def register(request):
    """Redirect to Allauth signup page for registration."""
    from django.shortcuts import redirect
    return redirect('account_signup')

def dashboard(request):
    """User dashboard view (robust, auto-create profile, safe for all roles)"""
    from django.utils import timezone
    if not request.user.is_authenticated:
        return redirect('account_login')

    # Auto-create UserProfile if missing
    try:
        user_profile = request.user.profile
    except AttributeError:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user, defaults={'role': 'patient'})

    # Filter params
    filter_date = request.GET.get('date')
    filter_status = request.GET.get('status')

    # Default context values
    appointments = []
    total_appointments = pending_appointments = accepted_appointments = declined_appointments = 0
    completed_appointments = 0
    waiting_patients = in_consultation = done_patients = 0
    total_revenue = None
    appts_last_7 = appts_last_30 = 0
    completion_rate = 0
    duty_form = None
    current_appointment = next_appointment = None
    available_slots = []
    unread_notifications = 0
    error_message = None
    # Always define these to avoid UnboundLocalError
    joinable_organizations = []
    join_requests = []
    current_org = None
    org_join_status = {}

    # Doctor dashboard
    if user_profile.role == 'doctor':
        appointments = Appointment.objects.filter(doctor=request.user).order_by('appointment_date')
        # Apply filters
        if filter_date:
            appointments = appointments.filter(appointment_date__date=filter_date)
        if filter_status:
            appointments = appointments.filter(status=filter_status)
        # On-duty toggle
        if request.method == 'POST' and 'toggle_duty' in request.POST:
            duty_form = DoctorDutyForm(request.POST, instance=user_profile)
            if duty_form.is_valid():
                duty_form.save()
                messages.success(request, f"On Duty status updated: {'On Duty' if user_profile.on_duty else 'Off Duty'}.")
                return redirect('appointments:dashboard')
        else:
            duty_form = DoctorDutyForm(instance=user_profile)
        now = timezone.now()
        current_appointment = appointments.filter(appointment_date__lte=now, appointment_date__gte=now-timedelta(hours=1)).first()
        next_appointment = appointments.filter(appointment_date__gt=now).order_by('appointment_date').first()
        available_slots = []
        if user_profile.on_duty:
            today = now.date()
            for i in range(7):
                date = today + timedelta(days=i)
                for hour in range(9, 17):
                    slot_time = timezone.make_aware(datetime.combine(date, datetime.min.time().replace(hour=hour)))
                    if slot_time > now:
                        available_slots.append(slot_time)
            booked_slots = appointments.filter(appointment_date__gte=now).values_list('appointment_date', flat=True)
            available_slots = [slot for slot in available_slots if slot not in booked_slots]
        waiting_patients = appointments.filter(patient_status='waiting').count()
        in_consultation = appointments.filter(patient_status='in_consultation').count()
        done_patients = appointments.filter(patient_status='done').count()
        total_appointments = appointments.count()
        pending_appointments = appointments.filter(status='pending').count()
        accepted_appointments = appointments.filter(status='confirmed').count()
        declined_appointments = appointments.filter(status='declined').count()
        completed_appointments = appointments.filter(status='completed').count()
        total_revenue = appointments.filter(status='completed').aggregate(Sum('fee'))['fee__sum'] or 0
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        appts_last_7 = appointments.filter(appointment_date__gte=last_7_days).count()
        appts_last_30 = appointments.filter(appointment_date__gte=last_30_days).count()
        completion_rate = (completed_appointments / total_appointments * 100) if total_appointments else 0
        # Add join org logic
        from .models import Organization, DoctorOrganizationJoinRequest
        current_org = user_profile.organization
        join_requests = DoctorOrganizationJoinRequest.objects.filter(doctor=request.user)
        # Only show clinics/hospitals, not solo_doctor orgs
        joinable_organizations = Organization.objects.exclude(members__user=request.user).filter(org_type__in=['clinic', 'hospital'])
        # Handle join request submission
        if request.method == 'POST' and 'join_org_id' in request.POST:
            org_id = request.POST.get('join_org_id')
            if org_id and not join_requests.filter(organization_id=org_id, status='pending').exists():
                DoctorOrganizationJoinRequest.objects.create(doctor=request.user, organization_id=org_id)
                messages.success(request, 'Join request sent to organization.')
                return redirect('appointments:dashboard')
        # Add join request status to organizations
        org_join_status = {}
        for org in joinable_organizations:
            req = join_requests.filter(organization=org).order_by('-created_at').first()
            org_join_status[org.id] = req.status if req else None
    # Patient dashboard fallback
    elif user_profile.role == 'patient':
        # Appointment is already imported at the top of the file
        appointments = Appointment.objects.filter(patient=request.user).order_by('appointment_date')
        if filter_date:
            appointments = appointments.filter(appointment_date__date=filter_date)
        if filter_status:
            appointments = appointments.filter(status=filter_status)
        total_appointments = appointments.count()
        pending_appointments = appointments.filter(status='pending').count()
        accepted_appointments = appointments.filter(status='confirmed').count()
        declined_appointments = appointments.filter(status='declined').count()
        completed_appointments = appointments.filter(status='completed').count()
        joinable_organizations = []
        join_requests = []
        current_org = None
    else:
        error_message = "You do not have access to the dashboard. Please contact the administrator."
        joinable_organizations = []
        join_requests = []
        current_org = None

    # Get unread notifications count
    if request.user.is_authenticated:
        try:
            unread_notifications = request.user.notifications.unread().count()
        except Exception:
            unread_notifications = 0

    available_patient_statuses = [
        {'value': 'waiting', 'label': 'Waiting'},
        {'value': 'in_consultation', 'label': 'In Consultation'},
        {'value': 'done', 'label': 'Done'},
    ]
    if user_profile.role in ['doctor', 'receptionist']:
        if request.method == 'POST' and 'update_patient_status' in request.POST:
            appt_id = request.POST.get('appt_id')
            new_status = request.POST.get('new_status')
            try:
                appt = Appointment.objects.get(id=appt_id)
                if new_status in dict(Appointment.PATIENT_STATUS_CHOICES):
                    appt.patient_status = new_status
                    appt.save()
                    # Send notification to patient
                    send_notification(
                        appt.patient,
                        title='Appointment Status Updated',
                        message=f'Your appointment status is now: {appt.get_patient_status_display()}',
                        notification_type='appointment_update',
                        data={'appointment_id': appt.id}
                    )
                    messages.success(request, 'Patient status updated.')
            except Appointment.DoesNotExist:
                messages.error(request, 'Appointment not found.')
            return redirect('appointments:dashboard')

    context = {
        'appointments': appointments,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'accepted_appointments': accepted_appointments,
        'declined_appointments': declined_appointments,
        'completed_appointments': completed_appointments,
        'waiting_patients': waiting_patients,
        'in_consultation': in_consultation,
        'done_patients': done_patients,
        'total_revenue': total_revenue,
        'appts_last_7': appts_last_7,
        'appts_last_30': appts_last_30,
        'completion_rate': completion_rate,
        'duty_form': duty_form,
        'current_appointment': current_appointment,
        'next_appointment': next_appointment,
        'available_slots': available_slots,
        'unread_notifications': unread_notifications,
        'error_message': error_message,
        'filter_date': filter_date,
        'filter_status': filter_status,
        'joinable_organizations': joinable_organizations,
        'join_requests': join_requests,
        'current_org': current_org,
        'available_patient_statuses': available_patient_statuses,
        'org_join_status': org_join_status,
    }
    return render(request, 'appointments/dashboard.html', context)

@login_required
def patient_dashboard(request):
    """Patient-specific dashboard with enhanced features"""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
        appointments = Appointment.objects.filter(patient=request.user).order_by('appointment_date')
        today = datetime.now().date()
        today_appointments = appointments.filter(appointment_date__date=today)
        upcoming_appointments = appointments.filter(
            appointment_date__date__gt=today,
            status='confirmed'
        )[:5]
        queue_appointments = appointments.filter(
            patient_status__in=['waiting', 'in_consultation'],
            appointment_date__date=today
        )
        total_appointments = appointments.count()
        pending_appointments = appointments.filter(status='pending').count()
        completed_appointments = appointments.filter(status='completed').count()
        # Doctor info for grid
        from django.utils import timezone
        now = timezone.now()
        doctors = User.objects.filter(profile__role='doctor')
        doctor_infos = []
        for doctor in doctors:
            profile = doctor.profile
            doc_appts = Appointment.objects.filter(doctor=doctor).order_by('appointment_date')
            current_appointment = doc_appts.filter(appointment_date__lte=now, appointment_date__gte=now-timedelta(hours=1)).first()
            next_appointment = doc_appts.filter(appointment_date__gt=now).order_by('appointment_date').first()
            doctor_infos.append({
                'doctor': doctor,
                'profile': profile,
                'current_appointment': current_appointment,
                'next_appointment': next_appointment,
                'is_available': profile.on_duty and not current_appointment
            })
        context = {
            'appointments': appointments,
            'today_appointments': today_appointments,
            'upcoming_appointments': upcoming_appointments,
            'queue_appointments': queue_appointments,
            'total_appointments': total_appointments,
            'pending_appointments': pending_appointments,
            'completed_appointments': completed_appointments,
            'doctor_infos': doctor_infos,
        }
    else:
        context = {'error_message': 'Access denied. Patient dashboard only.'}
    return render(request, 'appointments/patient_dashboard.html', context)

def browse_doctors(request):
    """Browse available doctors with filtering and org search"""
    doctors = User.objects.filter(profile__role='doctor').select_related('profile', 'profile__organization')
    # Filtering
    search_query = request.GET.get('search', '')
    specialization = request.GET.get('specialization')
    org_name = request.GET.get('org_name', '')
    city = request.GET.get('city')
    available_today = request.GET.get('available_today')
    if search_query:
        doctors = doctors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(profile__specialization__icontains=search_query)
        )
    if specialization:
        doctors = doctors.filter(profile__specialization__icontains=specialization)
    if org_name:
        doctors = doctors.filter(profile__organization__name__icontains=org_name)
    if city:
        doctors = doctors.filter(profile__organization__city__icontains=city)
    if available_today:
        doctors = doctors.filter(profile__on_duty=True)
    # Build doctor_infos with real-time available slots
    from django.utils import timezone
    now = timezone.now()
    doctor_infos = []
    for doctor in doctors:
        profile = doctor.profile
        org = profile.organization
        # Real-time available slots (today, 9-17, not booked)
        available_slots = []
        if profile.on_duty and org:
            today = now.date()
            for i in range(7):
                date = today + timedelta(days=i)
                for hour in range(9, 17):
                    slot_time = timezone.make_aware(datetime.combine(date, datetime.min.time().replace(hour=hour)))
                    if slot_time > now:
                        # Check if slot is available
                        exists = Appointment.objects.filter(
                            doctor=doctor,
                            appointment_date=slot_time,
                            status__in=['pending', 'confirmed']
                        ).exists()
                        if not exists:
                            available_slots.append(slot_time)
        doctor_infos.append({
            'doctor': doctor,
            'profile': profile,
            'organization': org,
            'on_duty': profile.on_duty,
            'available_slots': available_slots[:8],  # show up to 8 slots
        })
    context = {
        'doctor_infos': doctor_infos,
        'specializations': UserProfile.objects.filter(role='doctor').values_list('specialization', flat=True).distinct(),
        'cities': Organization.objects.values_list('city', flat=True).distinct(),
        'search_query': search_query,
        'specialization_filter': specialization,
        'org_name': org_name,
    }
    return render(request, 'appointments/browse_doctors.html', context)

def doctor_detail(request, doctor_id):
    """Detailed doctor profile with appointment booking"""
    doctor = get_object_or_404(User, id=doctor_id, profile__role='doctor')
    profile = doctor.profile
    
    # Get available time slots
    today = timezone.now().date()
    available_slots = []
    if profile.on_duty:
        for hour in range(9, 17):  # 9 AM to 5 PM
            slot_time = timezone.make_aware(datetime.combine(today, datetime.min.time().replace(hour=hour)))
            if slot_time > timezone.now():
                # Check if slot is available
                existing_appointment = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=slot_time,
                    status__in=['pending', 'confirmed']
                ).first()
                if not existing_appointment:
                    available_slots.append(slot_time)
    
    # Get doctor's recent appointments
    recent_appointments = Appointment.objects.filter(
        doctor=doctor,
        status='completed'
    ).order_by('-appointment_date')[:5]
    
    context = {
        'doctor': doctor,
        'profile': profile,
        'available_slots': available_slots,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'appointments/doctor_detail.html', context)

def schedule_appointment(request):
    """Schedule a new appointment"""
    from django.contrib.auth.models import User
    from .models import Organization
    doctor_id = request.GET.get('doctor')
    org_id = request.GET.get('organization')
    doctors = User.objects.filter(profile__role='doctor')
    selected_doctor = None
    selected_org = None
    if doctor_id:
        try:
            selected_doctor = User.objects.get(id=doctor_id)
        except User.DoesNotExist:
            selected_doctor = None
    if org_id:
        try:
            selected_org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            selected_org = None
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user
            if selected_org:
                appointment.organization = selected_org
            appointment.save()
            # Send notification to doctor
            send_notification(
                appointment.doctor.id,
                'appointment_update',
                'New Appointment Request',
                f'New appointment request from {appointment.patient.get_full_name()}',
                {'appointment_id': appointment.id}
            )
            # Log audit event for appointment creation
            from .utils import log_appointment_audit, broadcast_appointment_ws_update
            log_appointment_audit(
                request=request,
                action='appointment_created',
                appointment=appointment,
                details=f'Appointment created by {request.user.get_full_name()} with Dr. {appointment.doctor.get_full_name()} for {appointment.appointment_date.strftime("%Y-%m-%d %H:%M")}'
            )
            # WebSocket broadcast
            broadcast_appointment_ws_update(appointment, event_type='booked')
            messages.success(request, 'Appointment scheduled successfully!')
            return redirect('appointments:patient_dashboard')
    else:
        form = AppointmentForm()
        # Pre-select doctor if provided
        if selected_doctor:
            form.fields['doctor'].initial = selected_doctor.id
    return render(request, 'appointments/schedule.html', {
        'form': form,
        'doctors': doctors,
        'selected_doctor': selected_doctor,
        'selected_org': selected_org,
    })

def reschedule_appointment(request, appointment_id):
    """Reschedule an existing appointment with enhanced functionality"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to reschedule appointments.')
        return redirect('account_login')
    
    # Only patients can reschedule their own appointments
    if request.user.profile.role != 'patient' or appointment.patient != request.user:
        messages.error(request, 'You can only reschedule your own appointments.')
        return redirect('appointments:dashboard')
    
    # Check if appointment can be rescheduled (not too close to appointment time)
    time_until_appointment = appointment.appointment_date - timezone.now()
    if time_until_appointment.total_seconds() < 3600:  # Less than 1 hour
        messages.error(request, 'Appointments cannot be rescheduled within 1 hour of the scheduled time.')
        return redirect('appointments:patient_dashboard')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            old_date = appointment.appointment_date
            appointment = form.save()
            
            # Send notification to doctor about reschedule
            send_notification(
                appointment.doctor.id,
                'appointment_update',
                'Appointment Rescheduled',
                f'Appointment with {appointment.patient.get_full_name()} has been rescheduled from {old_date.strftime("%Y-%m-%d %H:%M")} to {appointment.appointment_date.strftime("%Y-%m-%d %H:%M")}',
                {'appointment_id': appointment.id}
            )
            
            # Clear cache for real-time updates
            cache_key = f"queue_status_{appointment.patient.id}"
            cache.delete(cache_key)
            cache_key_api = f"queue_status_api_{appointment.patient.id}"
            cache.delete(cache_key_api)
            
            # Log the reschedule action
            from .utils import log_appointment_audit
            log_appointment_audit(
                request=request,
                action='appointment_updated',
                appointment=appointment,
                details=f'Appointment rescheduled by {request.user.get_full_name()} from {old_date.strftime("%Y-%m-%d %H:%M")} to {appointment.appointment_date.strftime("%Y-%m-%d %H:%M")}'
            )
            
            # WebSocket broadcast
            from .utils import broadcast_appointment_ws_update
            broadcast_appointment_ws_update(appointment, event_type='rescheduled')
            
            messages.success(request, 'Appointment rescheduled successfully!')
            return redirect('appointments:patient_dashboard')
    else:
        form = AppointmentForm(instance=appointment)
    
    return render(request, 'appointments/reschedule.html', {
        'form': form,
        'appointment': appointment
    })

@login_required
def cancel_appointment(request, appointment_id):
    """Cancel an appointment with proper validation and notifications"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if request.user.profile.role == 'patient':
        if appointment.patient != request.user:
            messages.error(request, 'You can only cancel your own appointments.')
            return redirect('appointments:patient_dashboard')
    elif request.user.profile.role in ['doctor', 'receptionist']:
        if appointment.doctor != request.user and request.user.profile.role == 'doctor':
            messages.error(request, 'You can only cancel appointments with you.')
            return redirect('appointments:dashboard')
    else:
        messages.error(request, 'You do not have permission to cancel appointments.')
        return redirect('appointments:dashboard')
    
    # Check if appointment can be cancelled
    time_until_appointment = appointment.appointment_date - timezone.now()
    if time_until_appointment.total_seconds() < 1800:  # Less than 30 minutes
        messages.error(request, 'Appointments cannot be cancelled within 30 minutes of the scheduled time.')
        return redirect('appointments:patient_dashboard')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        
        # Update appointment status
        old_status = appointment.status
        appointment.status = 'cancelled'
        appointment.notes = f"Cancelled by {request.user.get_full_name()}. Reason: {reason}"
        appointment.save()
        
        # Send notifications
        if request.user.profile.role == 'patient':
            # Notify doctor
            send_notification(
                appointment.doctor.id,
                'appointment_update',
                'Appointment Cancelled',
                f'Appointment with {appointment.patient.get_full_name()} has been cancelled. Reason: {reason}',
                {'appointment_id': appointment.id}
            )
        else:
            # Notify patient
            send_notification(
                appointment.patient.id,
                'appointment_update',
                'Appointment Cancelled',
                f'Your appointment with Dr. {appointment.doctor.get_full_name()} has been cancelled. Reason: {reason}',
                {'appointment_id': appointment.id}
            )
        
        # Clear cache for real-time updates
        cache_key = f"queue_status_{appointment.patient.id}"
        cache.delete(cache_key)
        cache_key_api = f"queue_status_api_{appointment.patient.id}"
        cache.delete(cache_key_api)
        
        # Log the cancellation
        from .utils import log_appointment_audit
        log_appointment_audit(
            request=request,
            action='appointment_cancelled',
            appointment=appointment,
            details=f'Appointment cancelled by {request.user.get_full_name()}. Reason: {reason}'
        )
        
        # WebSocket broadcast
        from .utils import broadcast_appointment_ws_update
        broadcast_appointment_ws_update(appointment, event_type='cancelled')
        
        messages.success(request, 'Appointment cancelled successfully!')
        return redirect('appointments:patient_dashboard' if request.user.profile.role == 'patient' else 'appointments:dashboard')
    
    return render(request, 'appointments/cancel_appointment.html', {
        'appointment': appointment
    })

@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    user = request.user
    if not (user.is_authenticated and (appointment.patient == user or appointment.doctor == user)):
        raise Http404()
    return HttpResponse(f'Appointment detail for {appointment.pk}')

@receiver(post_save, sender=Appointment)
def appointment_updated(sender, instance, created, **kwargs):
    """Clear cache when appointment is updated"""
    if not created:  # Only for updates, not new appointments
        # Clear queue status cache for the patient
        cache_key = f"queue_status_{instance.patient.id}"
        cache.delete(cache_key)
        cache_key_api = f"queue_status_api_{instance.patient.id}"
        cache.delete(cache_key_api)
        
        # Clear queue status cache for the doctor
        cache_key = f"queue_status_doctor_{instance.doctor.id}"
        cache.delete(cache_key)

@receiver(post_delete, sender=Appointment)
def appointment_deleted(sender, instance, **kwargs):
    """Clear cache when appointment is deleted"""
    # Clear queue status cache for the patient
    cache_key = f"queue_status_{instance.patient.id}"
    cache.delete(cache_key)
    cache_key_api = f"queue_status_api_{instance.patient.id}"
    cache.delete(cache_key_api)
    
    # Clear queue status cache for the doctor
    cache_key = f"queue_status_doctor_{instance.doctor.id}"
    cache.delete(cache_key)

def queue_status(request):
    """Track queue status for patient's appointments with real-time updates"""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
        today = datetime.now().date()
        
        # Try to get from cache first
        cache_key = f"queue_status_{request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            queue_appointments = Appointment.objects.filter(
                patient=request.user,
                appointment_date__date=today,
                patient_status__in=['waiting', 'in_consultation']
            ).order_by('appointment_date')
            
            # Calculate queue position and wait times with more accurate logic
            for appointment in queue_appointments:
                if appointment.patient_status == 'waiting':
                    # Calculate position in queue for this specific doctor
                    position = Appointment.objects.filter(
                        doctor=appointment.doctor,
                        appointment_date__date=today,
                        appointment_date__lt=appointment.appointment_date,
                        patient_status='waiting'
                    ).count()
                    appointment.queue_position = position + 1
                    
                    # Calculate estimated wait time based on average consultation time
                    avg_consultation_time = 20  # minutes
                    appointment.estimated_wait = position * avg_consultation_time
                    
                    # Add time until appointment
                    time_until = appointment.appointment_date - timezone.now()
                    appointment.minutes_until = int(time_until.total_seconds() / 60)
                else:
                    appointment.queue_position = 0
                    appointment.estimated_wait = 0
                    appointment.minutes_until = 0
            
            # Cache the data for 30 seconds
            cache.set(cache_key, queue_appointments, 30)
        else:
            queue_appointments = cached_data
    else:
        queue_appointments = []
    
    context = {
        'queue_appointments': queue_appointments,
        'total_in_queue': queue_appointments.count(),
        'estimated_total_wait': sum(app.estimated_wait for app in queue_appointments if app.patient_status == 'waiting'),
    }
    return render(request, 'appointments/queue_status.html', context)

def reminders(request):
    """Patient reminders page"""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        today_appointments = Appointment.objects.filter(
            patient=request.user,
            appointment_date__date=today,
            status='confirmed'
        )
        tomorrow_appointments = Appointment.objects.filter(
            patient=request.user,
            appointment_date__date=tomorrow,
            status='confirmed'
        )
        upcoming_appointments = Appointment.objects.filter(
            patient=request.user,
            appointment_date__date__gt=today,
            appointment_date__date__lte=today + timedelta(days=7),
            status='confirmed'
        )
        # SMS logic removed. Use notifications for all alerts.
    else:
        today_appointments = tomorrow_appointments = upcoming_appointments = []
    context = {
        'today_appointments': today_appointments,
        'tomorrow_appointments': tomorrow_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'appointments/reminders.html', context)

def manage_appointments(request):
    """Doctor/Receptionist appointment management with filtering and bulk actions"""
    user_profile = request.user.profile
    filter_date = request.GET.get('date')
    filter_status = request.GET.get('status')
    if user_profile.role == 'doctor':
        appointments = Appointment.objects.filter(doctor=request.user)
    elif user_profile.role == 'receptionist':
        appointments = Appointment.objects.filter(organization=user_profile.organization)
    else:
        appointments = Appointment.objects.none()
    if filter_date:
        appointments = appointments.filter(appointment_date__date=filter_date)
    if filter_status:
        appointments = appointments.filter(status=filter_status)

    # Bulk actions
    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        try:
            with transaction.atomic():
                if action == 'accept_all_pending' and user_profile.role in ['doctor', 'receptionist']:
                    updated = appointments.filter(status='pending').update(status='confirmed')
                    messages.success(request, f"Confirmed {updated} pending appointments.")
                elif action == 'mark_all_waiting' and user_profile.role in ['doctor', 'receptionist']:
                    updated = appointments.filter(patient_status='waiting').update(patient_status='in_consultation')
                    messages.success(request, f"Marked {updated} patients as in consultation.")
                else:
                    messages.error(request, "Invalid or unauthorized bulk action.")
        except Exception as e:
            messages.error(request, f"Bulk action failed: {str(e)}")
        return redirect('appointments:manage')

    waiting_patients = appointments.filter(patient_status='waiting').count()
    in_consultation = appointments.filter(patient_status='in_consultation').count()
    completed = appointments.filter(patient_status='done').count()
    context = {
        'appointments': appointments,
        'waiting_patients': waiting_patients,
        'in_consultation': in_consultation,
        'completed': completed,
        'filter_date': filter_date,
        'filter_status': filter_status,
    }
    return render(request, 'appointments/manage_appointments.html', context)

def calendar_view(request):
    """Calendar view"""
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_profile = request.user.profile
        if user_profile.role == 'doctor':
            appointments = Appointment.objects.filter(doctor=request.user, organization=user_profile.organization)
        elif user_profile.role == 'receptionist':
            appointments = Appointment.objects.filter(organization=user_profile.organization)
        else:
            appointments = Appointment.objects.filter(patient=request.user)
        calendar_data = []
        for appointment in appointments:
            calendar_data.append({
                'id': appointment.id,
                'title': f"{appointment.patient.get_full_name() if user_profile.role in ['doctor', 'receptionist'] else appointment.doctor.get_full_name()}",
                'start': appointment.appointment_date.isoformat(),
                'end': (appointment.appointment_date + timedelta(hours=1)).isoformat(),
                'status': appointment.status,
                'patient_status': appointment.patient_status
            })
    else:
        calendar_data = []
    return render(request, 'appointments/calendar.html', {
        'calendar_data': json.dumps(calendar_data)
    })

def update_appointment_status(request, appointment_id):
    """Update appointment status (AJAX)"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.role == 'doctor' and appointment.doctor != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        if request.user.profile.role == 'patient' and appointment.patient != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        status = request.POST.get('status')
        patient_status = request.POST.get('patient_status')
        status_changed = False
        patient_status_changed = False
        if status and status in dict(Appointment.STATUS_CHOICES):
            appointment.status = status
            status_changed = True
            # If status is confirmed, always set patient_status to confirmed
            if status == 'confirmed':
                appointment.patient_status = 'confirmed'
        elif patient_status and patient_status in dict(Appointment.PATIENT_STATUS_CHOICES):
            appointment.patient_status = patient_status
            patient_status_changed = True
        appointment.save()
        
        # Log audit event for appointment status update
        from .utils import log_appointment_audit
        log_appointment_audit(
            request=request,
            action='appointment_updated',
            appointment=appointment,
            details=f'Appointment status updated by {request.user.get_full_name()}: status={appointment.status}, patient_status={appointment.patient_status}'
        )
        
        # Send WebSocket notification
        if appointment.organization:
            send_appointment_update(
                appointment.organization.id,
                appointment.id,
                appointment.status,
                appointment.patient_status
            )
        
        # Send notifications for status changes
        if status_changed:
            send_notification(
                appointment.patient.id,
                'appointment_update',
                'Appointment Status Updated',
                f'Your appointment status has been updated to {appointment.status}',
                {'appointment_id': appointment.id, 'status': appointment.status}
            )
        if patient_status_changed:
            # Notify both patient and doctor for workflow changes
            if appointment.patient_status == 'waiting':
                send_notification(
                    appointment.patient.id,
                    'appointment_update',
                    'You are now waiting for your appointment',
                    f'Your appointment is now marked as waiting.',
                    {'appointment_id': appointment.id, 'patient_status': 'waiting'}
                )
                send_notification(
                    appointment.doctor.id,
                    'appointment_update',
                    'Patient is waiting',
                    f'Patient {appointment.patient.get_full_name()} is now waiting.',
                    {'appointment_id': appointment.id, 'patient_status': 'waiting'}
                )
            elif appointment.patient_status == 'in_consultation':
                send_notification(
                    appointment.patient.id,
                    'appointment_update',
                    'You are now in consultation',
                    f'Your appointment is now in consultation.',
                    {'appointment_id': appointment.id, 'patient_status': 'in_consultation'}
                )
                send_notification(
                    appointment.doctor.id,
                    'appointment_update',
                    'Patient in consultation',
                    f'Patient {appointment.patient.get_full_name()} is now in consultation.',
                    {'appointment_id': appointment.id, 'patient_status': 'in_consultation'}
                )
            elif appointment.patient_status == 'done':
                send_notification(
                    appointment.patient.id,
                    'appointment_update',
                    'Appointment Completed',
                    f'Your appointment has been marked as done.',
                    {'appointment_id': appointment.id, 'patient_status': 'done'}
                )
                send_notification(
                    appointment.doctor.id,
                    'appointment_update',
                    'Appointment Completed',
                    f'Appointment with {appointment.patient.get_full_name()} has been marked as done.',
                    {'appointment_id': appointment.id, 'patient_status': 'done'}
                )
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Authentication required'}, status=403)

def api_appointments(request):
    """API endpoint for calendar data"""
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_profile = request.user.profile
        if user_profile.role == 'doctor':
            appointments = Appointment.objects.filter(doctor=request.user, organization=user_profile.organization)
        elif user_profile.role == 'receptionist':
            appointments = Appointment.objects.filter(organization=user_profile.organization)
        else:
            appointments = Appointment.objects.filter(patient=request.user)
        
        calendar_data = []
        for appointment in appointments:
            calendar_data.append({
                'id': appointment.id,
                'title': f"{appointment.patient.get_full_name() if user_profile.role in ['doctor', 'receptionist'] else appointment.doctor.get_full_name()}",
                'start': appointment.appointment_date.isoformat(),
                'end': (appointment.appointment_date + timedelta(hours=1)).isoformat(),
                'status': appointment.status,
                'patient_status': appointment.patient_status
            })
        return JsonResponse(calendar_data, safe=False)
    else:
        return JsonResponse({'error': 'Authentication required'}, status=403)

def google_calendar_init(request):
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    request.session['google_oauth_state'] = state
    return redirect(authorization_url)

def google_calendar_redirect(request):
    state = request.session.get('google_oauth_state')
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        state=state,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    # Store credentials in session (for demo; use DB for production)
    request.session['google_credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    return redirect(reverse('appointments:google_calendar_sync'))

def google_calendar_sync(request):
    creds_data = request.session.get('google_credentials')
    if not creds_data:
        return redirect(reverse('appointments:google_calendar_init'))
    creds = Credentials(
        creds_data['token'],
        refresh_token=creds_data['refresh_token'],
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )
    service = build('calendar', 'v3', credentials=creds)
    # Example: push all user's appointments to Google Calendar
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.role == 'doctor':
            appointments = Appointment.objects.filter(doctor=request.user)
        else:
            appointments = Appointment.objects.filter(patient=request.user)
        for appt in appointments:
            event = {
                'summary': f'Appointment with {appt.patient.get_full_name() if request.user.profile.role == "doctor" else appt.doctor.get_full_name()}',
                'start': {'dateTime': appt.appointment_date.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': (appt.appointment_date + timedelta(hours=1)).isoformat(), 'timeZone': 'UTC'},
                'description': appt.notes or '',
            }
            service.events().insert(calendarId='primary', body=event).execute()
        return HttpResponse('Appointments synced to your Google Calendar!')
    return HttpResponse('No appointments to sync.')

def about_page(request):
    return render(request, 'appointments/about.html')

def reception_dashboard(request):
    search_query = request.GET.get('search', '')
    selected_patient_id = request.GET.get('selected_patient')
    user_profile = request.user.profile if request.user.is_authenticated and hasattr(request.user, 'profile') else None
    # Receptionists see only their org's patients; others see all
    if user_profile and user_profile.role == 'receptionist':
        patients = User.objects.filter(profile__role='patient', profile__organization=user_profile.organization)
        doctors = User.objects.filter(profile__role='doctor', profile__organization=user_profile.organization)
    else:
        patients = User.objects.filter(profile__role='patient')
        doctors = User.objects.filter(profile__role='doctor')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    # Doctor info for grid
    from django.utils import timezone
    now = timezone.now()
    doctor_infos = []
    for doctor in doctors:
        profile = doctor.profile
        appointments = Appointment.objects.filter(doctor=doctor).order_by('appointment_date')
        current_appointment = appointments.filter(appointment_date__lte=now, appointment_date__gte=now-timedelta(hours=1)).first()
        next_appointment = appointments.filter(appointment_date__gt=now).order_by('appointment_date').first()
        available_slots = []
        if profile.on_duty:
            today = now.date()
            for i in range(7):
                date = today + timedelta(days=i)
                for hour in range(9, 17):
                    slot_time = timezone.make_aware(datetime.combine(date, datetime.min.time().replace(hour=hour)))
                    if slot_time > now:
                        available_slots.append(slot_time)
            booked_slots = appointments.filter(appointment_date__gte=now).values_list('appointment_date', flat=True)
            available_slots = [slot for slot in available_slots if slot not in booked_slots]
        doctor_infos.append({
            'doctor': doctor,
            'on_duty': profile.on_duty,
            'current_appointment': current_appointment,
            'next_appointment': next_appointment,
            'available_slots': available_slots[:5],
        })
    if request.method == 'POST':
        if 'create_patient' in request.POST:
            patient_form = MinimalPatientCreationForm(request.POST)
            if patient_form.is_valid():
                user = patient_form.save(commit=False)
                user.set_password(patient_form.cleaned_data['password'])
                user.save()
                # Create UserProfile for patient
                phone = patient_form.cleaned_data.get('phone', '')
                org = user_profile.organization if user_profile and user_profile.role == 'receptionist' else None
                UserProfile.objects.create(user=user, role='patient', phone=phone, organization=org)
                messages.success(request, 'New patient added successfully!')
                return redirect(f"{reverse('appointments:reception_dashboard')}?selected_patient={user.id}")
            else:
                form = AppointmentForm()
        else:
            form = AppointmentForm(request.POST)
            patient_id = request.POST.get('patient')
            if form.is_valid() and patient_id:
                appointment = form.save(commit=False)
                appointment.patient = User.objects.get(id=patient_id)
                appointment.save()
                
                # Log audit event for appointment creation by receptionist
                from .utils import log_appointment_audit
                log_appointment_audit(
                    request=request,
                    action='appointment_created',
                    appointment=appointment,
                    details=f'Appointment created by receptionist {request.user.get_full_name()} for patient {appointment.patient.get_full_name()} with Dr. {appointment.doctor.get_full_name()} for {appointment.appointment_date.strftime("%Y-%m-%d %H:%M")}'
                )
                
                messages.success(request, 'Appointment booked successfully!')
                return redirect('appointments:reception_dashboard')
    else:
        form = AppointmentForm()
        patient_form = MinimalPatientCreationForm()
    context = {
        'form': form,
        'patients': patients,
        'search_query': search_query,
        'selected_patient_id': selected_patient_id,
        'patient_form': patient_form,
        'doctor_infos': doctor_infos,
    }
    return render(request, 'appointments/reception_dashboard.html', context)

def create_organization(request):
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save()
            messages.success(request, f'Organization {org.name} created successfully!')
            return redirect('create_organization')
    else:
        form = OrganizationForm()
    return render(request, 'appointments/create_organization.html', {'form': form})

@login_required
def export_patients(request):
    if request.method == 'POST':
        form = PatientDataExportForm(request.POST)
        if form.is_valid():
            org = form.cleaned_data['organization']
            patients = User.objects.filter(profile__role='patient', profile__organization=org)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="organization_{org.id}_patients.csv"'
            writer = csv.writer(response)
            writer.writerow(['Username', 'Full Name', 'Phone', 'Created At'])
            for patient in patients:
                writer.writerow([patient.username, patient.get_full_name(), patient.profile.phone, patient.profile.created_at])
            return response
    else:
        form = PatientDataExportForm()
    return render(request, 'appointments/export_patients.html', {'form': form})

# New views for WebSocket and real-time features

@login_required
def notifications_view(request):
    """View for displaying user notifications"""
    notifications = request.user.notifications.unread() | request.user.notifications.read()
    notifications = notifications.order_by('-timestamp')
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            try:
                notification = request.user.notifications.get(id=notification_id)
                notification.mark_as_read()
                return JsonResponse({'success': True})
            except Exception:
                return JsonResponse({'success': False, 'error': 'Notification not found'})
    return render(request, 'appointments/notifications.html', {
        'notifications': notifications,
        'unread_count': request.user.notifications.unread().count()
    })

@login_required
def chat_view(request, room_name=None):
    """View for chat functionality"""
    if not room_name:
        # Create or get a chat room for the user
        room = create_or_get_chat_room([request.user])
        room_name = room.name
    
    room = get_object_or_404(ChatRoom, name=room_name)
    messages = ChatMessage.objects.filter(room=room).order_by('created_at')
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            save_chat_message(room, request.user, message_text)
            # Send via WebSocket
            from .utils import send_chat_message
            send_chat_message(room_name, request.user.id, request.user.get_full_name(), message_text)
            return JsonResponse({'success': True})
    
    return render(request, 'appointments/chat.html', {
        'room': room,
        'messages': messages,
        'room_name': room_name
    })

@login_required
def chat_rooms_view(request):
    """View for listing available chat rooms"""
    user_rooms = ChatRoom.objects.filter(participants=request.user, is_active=True)
    
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        participants = request.POST.getlist('participants')
        
        if room_name and participants:
            participant_users = User.objects.filter(id__in=participants)
            room = create_or_get_chat_room([request.user] + list(participant_users))
            return redirect('appointments:chat', room_name=room.name)
    
    # Get available users for creating new rooms
    if hasattr(request.user, 'profile') and request.user.profile.organization:
        available_users = User.objects.filter(
            profile__organization=request.user.profile.organization
        ).exclude(id=request.user.id)
    else:
        available_users = User.objects.exclude(id=request.user.id)
    
    return render(request, 'appointments/chat_rooms.html', {
        'user_rooms': user_rooms,
        'available_users': available_users
    })

@login_required
def update_appointment_status_websocket(request, appointment_id):
    """Update appointment status with WebSocket notification"""
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        new_status = request.POST.get('status')
        new_patient_status = request.POST.get('patient_status')
        
        if new_status:
            appointment.status = new_status
        if new_patient_status:
            appointment.patient_status = new_patient_status
        
        appointment.save()
        
        # Send WebSocket notification
        if appointment.organization:
            send_appointment_update(
                appointment.organization.id,
                appointment.id,
                appointment.status,
                appointment.patient_status
            )
        
        # Send notification to patient
        send_notification(
            appointment.patient.id,
            'appointment_update',
            'Appointment Status Updated',
            f'Your appointment status has been updated to {appointment.status}',
            {'appointment_id': appointment.id, 'status': appointment.status}
        )
        
        return JsonResponse({
            'success': True,
            'status': appointment.status,
            'patient_status': appointment.patient_status
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def send_notification_api(request):
    """API endpoint for sending notifications"""
    if request.method == 'POST':
        data = json.loads(request.body)
        recipient_id = data.get('recipient_id')
        notification_type = data.get('notification_type')
        title = data.get('title')
        message = data.get('message')
        if recipient_id and notification_type and title and message:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                recipient = User.objects.get(id=recipient_id)
                notify.send(request.user, recipient=recipient, verb=notification_type, description=title, data={'message': message, **(data.get('data') or {})})
                return JsonResponse({'success': True})
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Notification not found'})

@login_required
def get_unread_notifications_count(request):
    """Get count of unread notifications"""
    count = request.user.notifications.unread().count()
    return JsonResponse({'count': count})

@login_required
def profile_view(request):
    """Display the current user's profile (doctor or patient)"""
    user_profile = request.user.profile
    return render(request, 'appointments/profile.html', {'profile': user_profile})

@login_required
@require_http_methods(["GET", "POST"])
def edit_profile_view(request):
    """Edit the current user's profile (doctor or patient)"""
    user_profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('appointments:profile')
    else:
        form = UserProfileForm(instance=user_profile)
    return render(request, 'appointments/edit_profile.html', {'form': form, 'profile': user_profile})

@staff_member_required
def admin_analytics(request):
    from datetime import timedelta, datetime
    today = timezone.now().date()
    # --- FILTERS ---
    org_id = request.GET.get('organization')
    doctor_id = request.GET.get('doctor')
    specialization = request.GET.get('specialization')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    # Build base queryset
    appt_qs = Appointment.objects.all()
    if org_id:
        appt_qs = appt_qs.filter(organization_id=org_id)
    if doctor_id:
        appt_qs = appt_qs.filter(doctor_id=doctor_id)
    if specialization:
        appt_qs = appt_qs.filter(doctor__profile__specialization=specialization)
    if date_start:
        try:
            date_start_dt = datetime.strptime(date_start, '%Y-%m-%d')
            appt_qs = appt_qs.filter(appointment_date__date__gte=date_start_dt)
        except Exception:
            pass
    if date_end:
        try:
            date_end_dt = datetime.strptime(date_end, '%Y-%m-%d')
            appt_qs = appt_qs.filter(appointment_date__date__lte=date_end_dt)
        except Exception:
            pass

    # --- Analytics ---
    # Appointments trend (last 30 days or filtered range)
    if date_start and date_end:
        try:
            start = datetime.strptime(date_start, '%Y-%m-%d').date()
            end = datetime.strptime(date_end, '%Y-%m-%d').date()
            days = [start + timedelta(days=i) for i in range((end-start).days+1)]
        except Exception:
            days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    else:
        days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    day_labels = [d.strftime('%b %d') for d in days]
    appt_counts = [appt_qs.filter(appointment_date__date=d).count() for d in days]

    total = appt_qs.count()
    no_show = appt_qs.filter(status='no_show').count()
    no_show_rate = (no_show / total * 100) if total else 0

    # Peak booking times (by hour)
    hour_labels = [f'{h}:00' for h in range(8, 20)]
    hour_counts = [appt_qs.filter(appointment_date__hour=h).count() for h in range(8, 20)]

    # User role distribution (all users, not filtered)
    User = get_user_model()
    roles = ['doctor', 'patient', 'receptionist']
    role_counts = [User.objects.filter(profile__role=role).count() for role in roles]

    # --- Active doctors per organization ---
    orgs = Organization.objects.all()
    active_doctors_per_org = []
    for org in orgs:
        active_count = UserProfile.objects.filter(organization=org, role='doctor', on_duty=True).count()
        total_count = UserProfile.objects.filter(organization=org, role='doctor').count()
        active_doctors_per_org.append({
            'org': org,
            'active': active_count,
            'total': total_count
        })

    # --- Filter dropdown options ---
    org_options = Organization.objects.all()
    doctor_options = User.objects.filter(profile__role='doctor')
    specialization_options = UserProfile.objects.filter(role='doctor').exclude(specialization__isnull=True).exclude(specialization='').values_list('specialization', flat=True).distinct()

    context = {
        'day_labels': json.dumps(day_labels),
        'appt_counts': json.dumps(appt_counts),
        'no_show_rate': no_show_rate,
        'hour_labels': json.dumps(hour_labels),
        'hour_counts': json.dumps(hour_counts),
        'role_labels': json.dumps([r.title() for r in roles]),
        'role_counts': json.dumps(role_counts),
        'org_options': org_options,
        'doctor_options': doctor_options,
        'specialization_options': specialization_options,
        'active_doctors_per_org': active_doctors_per_org,
        'selected_org': int(org_id) if org_id else '',
        'selected_doctor': int(doctor_id) if doctor_id else '',
        'selected_specialization': specialization or '',
        'date_start': date_start or '',
        'date_end': date_end or '',
    }
    return render(request, 'appointments/admin_analytics.html', context)

@staff_member_required
def export_appointments(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Patient', 'Doctor', 'Date', 'Status'])
    for appt in Appointment.objects.all():
        writer.writerow([
            appt.id,
            appt.patient.get_full_name() if appt.patient else '',
            appt.doctor.get_full_name() if appt.doctor else '',
            appt.appointment_date,
            appt.status
        ])
    return response

@staff_member_required
def export_users(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Email', 'Role', 'Is Active'])
    User = get_user_model()
    for user in User.objects.all():
        writer.writerow([
            user.id,
            user.username,
            user.email,
            getattr(user.profile, 'role', ''),
            user.is_active
        ])
    return response

@staff_member_required
@csrf_exempt
def import_patients(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        preview = []
        errors = []
        for row in reader:
            # Basic validation: check required fields
            if not row.get('username') or not row.get('email'):
                errors.append(f"Missing username or email in row: {row}")
                continue
            preview.append(row)
        if errors:
            messages.error(request, '\n'.join(errors))
        else:
            # Save to DB (example: create users as patients)
            User = get_user_model()
            for row in preview:
                if not User.objects.filter(username=row['username']).exists():
                    user = User.objects.create_user(
                        username=row['username'],
                        email=row['email'],
                        password=row.get('password', User.objects.make_random_password())
                    )
                    profile = getattr(user, 'profile', None)
                    if profile:
                        profile.role = 'patient'
                        profile.save()
            messages.success(request, f"Imported {len(preview)} patients.")
            return HttpResponseRedirect(reverse('appointments:admin_analytics'))
        return render(request, 'appointments/import_patients.html', {'preview': preview, 'errors': errors})
    return render(request, 'appointments/import_patients.html')

@staff_member_required
def manage_roles(request):
    User = get_user_model()
    users = User.objects.all().select_related('profile')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        user = User.objects.get(id=user_id)
        if hasattr(user, 'profile'):
            user.profile.role = new_role
            user.profile.save()
        user.is_active = is_active
        user.save()
        messages.success(request, f"Updated user {user.username}.")
        return redirect('appointments:manage_roles')
    return render(request, 'appointments/manage_roles.html', {'users': users, 'roles': ['doctor', 'patient', 'receptionist']})

def log_audit(user, action, details=''):
    AuditLog.objects.create(user=user if user.is_authenticated else None, action=action, details=details)

@staff_member_required
def audit_logs(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request, 'appointments/audit_logs.html', {'logs': logs})

@login_required
def maps_view(request):
    """Display all registered organizations and doctors on Google Maps"""
    from django.conf import settings
    
    # Get all organizations with location data
    organizations = Organization.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(latitude=0, longitude=0)
    
    # Get all doctors with their organization locations
    doctors = UserProfile.objects.filter(
        role='doctor',
        organization__isnull=False,
        organization__latitude__isnull=False,
        organization__longitude__isnull=False
    ).exclude(
        organization__latitude=0,
        organization__longitude=0
    ).select_related('user', 'organization')
    
    # Prepare data for the map
    map_data = {
        'organizations': [],
        'doctors': [],
        'api_key': settings.GOOGLE_MAPS_API_KEY
    }
    
    # Add organizations
    for org in organizations:
        map_data['organizations'].append({
            'id': org.id,
            'name': org.name,
            'type': org.get_org_type_display(),
            'address': org.address or '',
            'phone': org.phone or '',
            'email': org.email or '',
            'website': org.website or '',
            'latitude': float(org.latitude),
            'longitude': float(org.longitude),
            'is_24_hours': org.is_24_hours,
            'specialization': 'General Clinic' if org.org_type == 'clinic' else 'Hospital'
        })
    
    # Add doctors
    for doctor in doctors:
        org = doctor.organization
        map_data['doctors'].append({
            'id': doctor.user.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization or 'General Medicine',
            'organization': org.name,
            'address': org.address or '',
            'phone': doctor.phone or org.phone or '',
            'email': doctor.user.email,
            'latitude': float(org.latitude),
            'longitude': float(org.longitude),
            'on_duty': doctor.on_duty,
            'org_type': org.get_org_type_display()
        })
    
    return render(request, 'appointments/maps.html', map_data)

@login_required
def organization_detail_map(request, org_id):
    """Display a specific organization on the map"""
    from django.conf import settings
    
    organization = get_object_or_404(Organization, id=org_id)
    
    if not organization.latitude or not organization.longitude:
        messages.warning(request, "This organization doesn't have location data.")
        return redirect('appointments:maps')
    
    # Get doctors at this organization
    doctors = UserProfile.objects.filter(
        role='doctor',
        organization=organization
    ).select_related('user')
    
    map_data = {
        'organization': {
            'id': organization.id,
            'name': organization.name,
            'type': organization.get_org_type_display(),
            'address': organization.address or '',
            'phone': organization.phone or '',
            'email': organization.email or '',
            'website': organization.website or '',
            'latitude': float(organization.latitude),
            'longitude': float(organization.longitude),
            'is_24_hours': organization.is_24_hours,
            'operating_hours': organization.operating_hours or {}
        },
        'doctors': [{
            'id': doctor.user.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization or 'General Medicine',
            'phone': doctor.phone or '',
            'email': doctor.user.email,
            'on_duty': doctor.on_duty
        } for doctor in doctors],
        'api_key': settings.GOOGLE_MAPS_API_KEY
    }
    
    return render(request, 'appointments/organization_map.html', map_data)

@csrf_exempt
def api_locations(request):
    """API endpoint to get all locations for maps"""
    if request.method == 'GET':
        from django.conf import settings
        
        # Get all organizations with location data
        organizations = Organization.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).exclude(latitude=0, longitude=0)
        
        # Get all doctors with their organization locations
        doctors = UserProfile.objects.filter(
            role='doctor',
            organization__isnull=False,
            organization__latitude__isnull=False,
            organization__longitude__isnull=False
        ).exclude(
            organization__latitude=0,
            organization__longitude=0
        ).select_related('user', 'organization')
        
        # Prepare response data
        response_data = {
            'organizations': [],
            'doctors': [],
            'api_key': settings.GOOGLE_MAPS_API_KEY
        }
        
        # Add organizations
        for org in organizations:
            response_data['organizations'].append({
                'id': org.id,
                'name': org.name,
                'type': org.get_org_type_display(),
                'address': org.address or '',
                'phone': org.phone or '',
                'email': org.email or '',
                'website': org.website or '',
                'latitude': float(org.latitude),
                'longitude': float(org.longitude),
                'is_24_hours': org.is_24_hours,
                'specialization': 'General Clinic' if org.org_type == 'clinic' else 'Hospital'
            })
        
        # Add doctors
        for doctor in doctors:
            org = doctor.organization
            response_data['doctors'].append({
                'id': doctor.user.id,
                'name': f"Dr. {doctor.user.get_full_name()}",
                'specialization': doctor.specialization or 'General Medicine',
                'organization': org.name,
                'address': org.address or '',
                'phone': doctor.phone or org.phone or '',
                'email': doctor.user.email,
                'latitude': float(org.latitude),
                'longitude': float(org.longitude),
                'on_duty': doctor.on_duty,
                'org_type': org.get_org_type_display()
            })
        
        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def doctors_map(request):
    """Enhanced interactive doctors map with filtering and search"""
    from django.conf import settings
    
    # Get filter parameters
    specialization = request.GET.get('specialization', '')
    organization_type = request.GET.get('org_type', '')
    on_duty_only = request.GET.get('on_duty', '') == 'true'
    search_query = request.GET.get('search', '')
    
    # Base queryset for doctors
    doctors = UserProfile.objects.filter(
        role='doctor',
        organization__isnull=False,
        organization__latitude__isnull=False,
        organization__longitude__isnull=False
    ).exclude(
        organization__latitude=0,
        organization__longitude=0
    ).select_related('user', 'organization')
    
    # Apply filters
    if specialization:
        doctors = doctors.filter(specialization__icontains=specialization)
    
    if organization_type:
        doctors = doctors.filter(organization__org_type=organization_type)
    
    if on_duty_only:
        doctors = doctors.filter(on_duty=True)
    
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialization__icontains=search_query) |
            Q(organization__name__icontains=search_query)
        )
    
    # Get organizations for doctors
    organizations = Organization.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(latitude=0, longitude=0)
    
    # Get unique specializations for filter dropdown
    specializations = UserProfile.objects.filter(
        role='doctor',
        specialization__isnull=False
    ).exclude(specialization='').values_list('specialization', flat=True).distinct()
    
    # Prepare map data
    map_data = {
        'doctors': [],
        'organizations': [],
        'specializations': list(specializations),
        'filters': {
            'specialization': specialization,
            'org_type': organization_type,
            'on_duty': on_duty_only,
            'search': search_query
        },
        'api_key': settings.GOOGLE_MAPS_API_KEY
    }
    
    # Add doctors with enhanced data
    for doctor in doctors:
        org = doctor.organization
        map_data['doctors'].append({
            'id': doctor.user.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization or 'General Medicine',
            'organization': org.name,
            'organization_type': org.get_org_type_display(),
            'address': org.address or '',
            'phone': doctor.phone or org.phone or '',
            'email': doctor.user.email,
            'latitude': float(org.latitude),
            'longitude': float(org.longitude),
            'on_duty': doctor.on_duty,
            'experience_years': doctor.experience_years or 0,
            'rating': getattr(doctor, 'rating', 4.5),
            'consultation_fee': getattr(doctor, 'consultation_fee', 0),
            'avatar_url': doctor.avatar.url if doctor.avatar else '',
            'bio': doctor.bio or '',
            'languages': doctor.languages or [],
            'certifications': doctor.certifications or []
        })
    
    # Add organizations
    for org in organizations:
        map_data['organizations'].append({
            'id': org.id,
            'name': org.name,
            'type': org.get_org_type_display(),
            'address': org.address or '',
            'phone': org.phone or '',
            'email': org.email or '',
            'website': org.website or '',
            'latitude': float(org.latitude),
            'longitude': float(org.longitude),
            'is_24_hours': org.is_24_hours,
            'specialization': 'General Clinic' if org.org_type == 'clinic' else 'Hospital'
        })
    
    return render(request, 'appointments/doctors_map.html', map_data)

@login_required
def api_doctors_map(request):
    """API endpoint for doctors map with real-time filtering"""
    from django.conf import settings
    from django.db.models import Q
    
    # Get filter parameters
    specialization = request.GET.get('specialization', '')
    organization_type = request.GET.get('org_type', '')
    on_duty_only = request.GET.get('on_duty', '') == 'true'
    search_query = request.GET.get('search', '')
    min_rating = request.GET.get('min_rating', '')
    max_fee = request.GET.get('max_fee', '')
    
    # Base queryset
    doctors = UserProfile.objects.filter(
        role='doctor',
        organization__isnull=False,
        organization__latitude__isnull=False,
        organization__longitude__isnull=False
    ).exclude(
        organization__latitude=0,
        organization__longitude=0
    ).select_related('user', 'organization')
    
    # Apply filters
    if specialization:
        doctors = doctors.filter(specialization__icontains=specialization)
    
    if organization_type:
        doctors = doctors.filter(organization__org_type=organization_type)
    
    if on_duty_only:
        doctors = doctors.filter(on_duty=True)
    
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialization__icontains=search_query) |
            Q(organization__name__icontains=search_query)
        )
    
    if min_rating:
        doctors = doctors.filter(rating__gte=float(min_rating))
    
    if max_fee:
        doctors = doctors.filter(consultation_fee__lte=float(max_fee))
    
    # Prepare response data
    response_data = {
        'doctors': [],
        'total_count': doctors.count(),
        'filters_applied': {
            'specialization': specialization,
            'org_type': organization_type,
            'on_duty': on_duty_only,
            'search': search_query,
            'min_rating': min_rating,
            'max_fee': max_fee
        }
    }
    
    # Add doctors with detailed information
    for doctor in doctors:
        org = doctor.organization
        response_data['doctors'].append({
            'id': doctor.user.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization or 'General Medicine',
            'organization': org.name,
            'organization_type': org.get_org_type_display(),
            'address': org.address or '',
            'phone': doctor.phone or org.phone or '',
            'email': doctor.user.email,
            'latitude': float(org.latitude),
            'longitude': float(org.longitude),
            'on_duty': doctor.on_duty,
            'experience_years': doctor.experience_years or 0,
            'rating': getattr(doctor, 'rating', 4.5),
            'consultation_fee': getattr(doctor, 'consultation_fee', 0),
            'avatar_url': doctor.avatar.url if doctor.avatar else '',
            'bio': doctor.bio or '',
            'languages': doctor.languages or [],
            'certifications': doctor.certifications or [],
            'next_available': getattr(doctor, 'next_available', None),
            'total_appointments': getattr(doctor, 'total_appointments', 0)
        })
    
    return JsonResponse(response_data)

@login_required
def doctor_map_detail(request, doctor_id):
    """Detailed view of a specific doctor on the map"""
    from django.conf import settings
    
    doctor = get_object_or_404(UserProfile, user_id=doctor_id, role='doctor')
    
    if not doctor.organization or not doctor.organization.latitude:
        messages.warning(request, "This doctor doesn't have location data.")
        return redirect('appointments:doctors_map')
    
    # Get similar doctors in the same area
    similar_doctors = UserProfile.objects.filter(
        role='doctor',
        organization__latitude__isnull=False,
        organization__longitude__isnull=False,
        specialization=doctor.specialization
    ).exclude(user_id=doctor_id)[:5]
    
    # Get upcoming appointments for this doctor
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor,
        status='accepted',
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')[:5]
    
    map_data = {
        'doctor': {
            'id': doctor.user.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization or 'General Medicine',
            'organization': doctor.organization.name,
            'organization_type': doctor.organization.get_org_type_display(),
            'address': doctor.organization.address or '',
            'phone': doctor.phone or doctor.organization.phone or '',
            'email': doctor.user.email,
            'latitude': float(doctor.organization.latitude),
            'longitude': float(doctor.organization.longitude),
            'on_duty': doctor.on_duty,
            'experience_years': doctor.experience_years or 0,
            'rating': getattr(doctor, 'rating', 4.5),
            'consultation_fee': getattr(doctor, 'consultation_fee', 0),
            'avatar_url': doctor.avatar.url if doctor.avatar else '',
            'bio': doctor.bio or '',
            'languages': doctor.languages or [],
            'certifications': doctor.certifications or []
        },
        'similar_doctors': [{
            'id': d.user.id,
            'name': f"Dr. {d.user.get_full_name()}",
            'specialization': d.specialization,
            'organization': d.organization.name,
            'rating': getattr(d, 'rating', 4.5),
            'on_duty': d.on_duty
        } for d in similar_doctors],
        'upcoming_appointments': [{
            'id': apt.id,
            'patient_name': apt.patient.user.get_full_name(),
            'scheduled_time': apt.scheduled_time.strftime('%Y-%m-%d %H:%M'),
            'status': apt.status
        } for apt in upcoming_appointments],
        'api_key': settings.GOOGLE_MAPS_API_KEY
    }
    
    return render(request, 'appointments/doctor_map_detail.html', map_data)

@login_required
def export_appointments_enhanced(request):
    """Enhanced appointment export with multiple formats and filtering"""
    if not request.user.profile.role in ['doctor', 'receptionist', 'admin']:
        messages.error(request, "You don't have permission to export appointments.")
        return redirect('appointments:dashboard')
    
    if request.method == 'POST':
        form = AppointmentExportForm(request.POST)
        if form.is_valid():
            # Get filtered appointments
            appointments = Appointment.objects.all()
            
            # Apply filters
            if form.cleaned_data.get('organization'):
                appointments = appointments.filter(organization=form.cleaned_data['organization'])
            if form.cleaned_data.get('doctor'):
                appointments = appointments.filter(doctor=form.cleaned_data['doctor'])
            if form.cleaned_data.get('status'):
                appointments = appointments.filter(status=form.cleaned_data['status'])
            if form.cleaned_data.get('date_from'):
                appointments = appointments.filter(appointment_date__date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data.get('date_to'):
                appointments = appointments.filter(appointment_date__date__lte=form.cleaned_data['date_to'])
            
            # Role-based filtering
            if request.user.profile.role == 'doctor':
                appointments = appointments.filter(doctor=request.user)
            elif request.user.profile.role == 'receptionist':
                appointments = appointments.filter(organization=request.user.profile.organization)
            
            export_format = form.cleaned_data.get('export_format', 'csv')
            
            if export_format == 'csv':
                return export_appointments_csv(appointments)
            elif export_format == 'excel':
                return export_appointments_excel(appointments)
            elif export_format == 'pdf':
                return export_appointments_pdf(appointments)
    else:
        form = AppointmentExportForm()
    
    return render(request, 'appointments/export_appointments_enhanced.html', {'form': form})

def export_appointments_csv(appointments):
    """Export appointments to CSV format"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="appointments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Patient Name', 'Patient Email', 'Patient Phone', 'Doctor Name', 
        'Organization', 'Appointment Date', 'Status', 'Patient Status', 
        'Appointment Type', 'Fee', 'Notes', 'Created At'
    ])
    
    for appt in appointments:
        writer.writerow([
            appt.id,
            appt.patient.get_full_name() if appt.patient else '',
            appt.patient.email if appt.patient else '',
            appt.patient.profile.phone if appt.patient and hasattr(appt.patient, 'profile') else '',
            appt.doctor.get_full_name() if appt.doctor else '',
            appt.organization.name if appt.organization else '',
            appt.appointment_date.strftime('%Y-%m-%d %H:%M'),
            appt.status,
            appt.patient_status,
            appt.appointment_type,
            appt.fee,
            appt.notes or '',
            appt.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response

def export_appointments_excel(appointments):
    """Export appointments to Excel format"""
    # Create DataFrame
    data = []
    for appt in appointments:
        data.append({
            'ID': appt.id,
            'Patient Name': appt.patient.get_full_name() if appt.patient else '',
            'Patient Email': appt.patient.email if appt.patient else '',
            'Patient Phone': appt.patient.profile.phone if appt.patient and hasattr(appt.patient, 'profile') else '',
            'Doctor Name': appt.doctor.get_full_name() if appt.doctor else '',
            'Organization': appt.organization.name if appt.organization else '',
            'Appointment Date': appt.appointment_date.strftime('%Y-%m-%d %H:%M'),
            'Status': appt.status,
            'Patient Status': appt.patient_status,
            'Appointment Type': appt.appointment_type,
            'Fee': float(appt.fee),
            'Notes': appt.notes or '',
            'Created At': appt.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Appointments', index=False)
    
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="appointments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response

def export_appointments_pdf(appointments):
    """Export appointments to PDF format"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="appointments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    # Create PDF
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph("Appointments Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Appointments', str(appointments.count())],
        ['Pending', str(appointments.filter(status='pending').count())],
        ['Accepted', str(appointments.filter(status='accepted').count())],
        ['Completed', str(appointments.filter(status='completed').count())],
        ['Declined', str(appointments.filter(status='declined').count())],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Appointments table
    if appointments.exists():
        table_data = [['Patient', 'Doctor', 'Date', 'Status', 'Fee']]
        
        for appt in appointments[:50]:  # Limit to 50 for PDF
            table_data.append([
                appt.patient.get_full_name() if appt.patient else 'N/A',
                appt.doctor.get_full_name() if appt.doctor else 'N/A',
                appt.appointment_date.strftime('%Y-%m-%d %H:%M'),
                appt.status.title(),
                f"${appt.fee}"
            ])
        
        appointments_table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.2*inch, 1*inch, 0.8*inch])
        appointments_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(appointments_table)
    
    doc.build(elements)
    return response

@login_required
def import_appointments_enhanced(request):
    """Enhanced appointment import with preview and validation"""
    if not request.user.profile.role in ['receptionist', 'admin']:
        messages.error(request, "You don't have permission to import appointments.")
        return redirect('appointments:dashboard')
    
    if request.method == 'POST':
        form = AppointmentImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            organization = form.cleaned_data['organization']
            import_mode = form.cleaned_data['import_mode']
            
            try:
                # Read file based on extension
                file_extension = os.path.splitext(file.name)[1].lower()
                
                if file_extension == '.csv':
                    # Read CSV
                    decoded_file = file.read().decode('utf-8')
                    df = pd.read_csv(StringIO(decoded_file))
                else:
                    # Read Excel
                    df = pd.read_excel(file)
                
                # Validate and process data
                preview_data = []
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Validate required fields
                        if pd.isna(row.get('patient_email', '')) or pd.isna(row.get('doctor_email', '')):
                            errors.append(f"Row {index + 1}: Missing patient_email or doctor_email")
                            continue
                        
                        # Check if patient and doctor exist
                        try:
                            patient = User.objects.get(email=row['patient_email'])
                            doctor = User.objects.get(email=row['doctor_email'])
                        except User.DoesNotExist:
                            errors.append(f"Row {index + 1}: Patient or doctor not found")
                            continue
                        
                        # Parse appointment date
                        try:
                            appointment_date = pd.to_datetime(row.get('appointment_date', ''))
                        except:
                            errors.append(f"Row {index + 1}: Invalid appointment date")
                            continue
                        
                        preview_data.append({
                            'patient_name': patient.get_full_name(),
                            'doctor_name': doctor.get_full_name(),
                            'appointment_date': appointment_date.strftime('%Y-%m-%d %H:%M'),
                            'status': row.get('status', 'pending'),
                            'fee': row.get('fee', 0),
                            'notes': row.get('notes', ''),
                            'patient': patient,
                            'doctor': doctor,
                            'appointment_date_obj': appointment_date
                        })
                        
                    except Exception as e:
                        errors.append(f"Row {index + 1}: {str(e)}")
                
                if import_mode == 'import' and not errors:
                    # Import data
                    imported_count = 0
                    for data in preview_data:
                        try:
                            appointment = Appointment.objects.create(
                                patient=data['patient'],
                                doctor=data['doctor'],
                                appointment_date=data['appointment_date_obj'],
                                status=data['status'],
                                fee=data['fee'],
                                notes=data['notes'],
                                organization=organization
                            )
                            imported_count += 1
                        except Exception as e:
                            errors.append(f"Failed to create appointment: {str(e)}")
                    
                    if imported_count > 0:
                        # Log audit event for bulk appointment import
                        from .utils import log_audit_event
                        log_audit_event(
                            user=request.user,
                            action='data_imported',
                            details=f'Imported {imported_count} appointments from file {file.name}',
                            object_type='appointment',
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')
                        )
                        
                        messages.success(request, f"Successfully imported {imported_count} appointments.")
                        return redirect('appointments:manage')
                
                return render(request, 'appointments/import_appointments_enhanced.html', {
                    'form': form,
                    'preview_data': preview_data,
                    'errors': errors,
                    'import_mode': import_mode
                })
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = AppointmentImportForm()
    
    return render(request, 'appointments/import_appointments_enhanced.html', {'form': form})

@login_required
def import_patients_enhanced(request):
    """Enhanced patient import with preview and validation"""
    if not request.user.profile.role in ['receptionist', 'admin']:
        messages.error(request, "You don't have permission to import patients.")
        return redirect('appointments:dashboard')
    
    if request.method == 'POST':
        form = PatientImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            organization = form.cleaned_data['organization']
            import_mode = form.cleaned_data['import_mode']
            
            try:
                # Read file based on extension
                file_extension = os.path.splitext(file.name)[1].lower()
                
                if file_extension == '.csv':
                    # Read CSV
                    decoded_file = file.read().decode('utf-8')
                    df = pd.read_csv(StringIO(decoded_file))
                else:
                    # Read Excel
                    df = pd.read_excel(file)
                
                # Validate and process data
                preview_data = []
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Validate required fields
                        if pd.isna(row.get('email', '')) or pd.isna(row.get('first_name', '')):
                            errors.append(f"Row {index + 1}: Missing email or first_name")
                            continue
                        
                        # Check if user already exists
                        if User.objects.filter(email=row['email']).exists():
                            errors.append(f"Row {index + 1}: User with email {row['email']} already exists")
                            continue
                        
                        preview_data.append({
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                            'email': row['email'],
                            'phone': row.get('phone', ''),
                            'username': row.get('username', row['email'].split('@')[0])
                        })
                        
                    except Exception as e:
                        errors.append(f"Row {index + 1}: {str(e)}")
                
                if import_mode == 'import' and not errors:
                    # Import data
                    imported_count = 0
                    for data in preview_data:
                        try:
                            # Create user
                            user = User.objects.create_user(
                                username=data['username'],
                                email=data['email'],
                                first_name=data['first_name'],
                                last_name=data['last_name'],
                                password=User.objects.make_random_password()
                            )
                            
                            # Create profile
                            profile = UserProfile.objects.create(
                                user=user,
                                role='patient',
                                organization=organization,
                                phone=data['phone']
                            )
                            
                            imported_count += 1
                        except Exception as e:
                            errors.append(f"Failed to create user: {str(e)}")
                    
                    if imported_count > 0:
                        # Log audit event for bulk patient import
                        from .utils import log_audit_event
                        log_audit_event(
                            user=request.user,
                            action='data_imported',
                            details=f'Imported {imported_count} patients from file {file.name}',
                            object_type='user',
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')
                        )
                        
                        messages.success(request, f"Successfully imported {imported_count} patients.")
                        return redirect('appointments:export_patients')
                
                return render(request, 'appointments/import_patients_enhanced.html', {
                    'form': form,
                    'preview_data': preview_data,
                    'errors': errors,
                    'import_mode': import_mode
                })
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = PatientImportForm()
    
    return render(request, 'appointments/import_patients_enhanced.html', {'form': form})

@login_required
def auto_export_appointments(request):
    """Automatically export appointments for a clinic to a file"""
    if not request.user.profile.role in ['doctor', 'receptionist', 'admin']:
        messages.error(request, "You don't have permission to auto-export appointments.")
        return redirect('appointments:dashboard')
    
    # Get appointments for the user's organization
    if request.user.profile.role == 'doctor':
        appointments = Appointment.objects.filter(doctor=request.user)
    elif request.user.profile.role == 'receptionist':
        appointments = Appointment.objects.filter(organization=request.user.profile.organization)
    else:
        appointments = Appointment.objects.all()
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"appointments_auto_export_{timestamp}.csv"
    
    # Create CSV content
    csv_content = StringIO()
    writer = csv.writer(csv_content)
    writer.writerow([
        'ID', 'Patient Name', 'Patient Email', 'Doctor Name', 'Appointment Date', 
        'Status', 'Patient Status', 'Fee', 'Notes'
    ])
    
    for appt in appointments:
        writer.writerow([
            appt.id,
            appt.patient.get_full_name() if appt.patient else '',
            appt.patient.email if appt.patient else '',
            appt.doctor.get_full_name() if appt.doctor else '',
            appt.appointment_date.strftime('%Y-%m-%d %H:%M'),
            appt.status,
            appt.patient_status,
            appt.fee,
            appt.notes or ''
        ])
    
    # Save to storage
    file_path = f"exports/{filename}"
    default_storage.save(file_path, ContentFile(csv_content.getvalue()))
    
    messages.success(request, f"Appointments automatically exported to {filename}")
    return redirect('appointments:dashboard')

@login_required
def nearby_clinics(request):
    """Find nearby clinics based on user location"""
    if request.method == 'POST':
        # Get user's location from form
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        radius = request.POST.get('radius', 10)  # Default 10km radius
        
        if latitude and longitude:
            # Store user location in session
            request.session['user_latitude'] = latitude
            request.session['user_longitude'] = longitude
            
            # Get nearby clinics
            clinics = get_nearby_clinics(float(latitude), float(longitude), float(radius))
            return JsonResponse({'clinics': clinics})
    
    # Get clinics with location data
    clinics = Organization.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(latitude='').exclude(longitude='')
    
    return render(request, 'appointments/nearby_clinics.html', {
        'clinics': clinics,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

def get_nearby_clinics(lat, lng, radius_km=10):
    """Calculate nearby clinics using distance formula"""
    from math import radians, cos, sin, asin, sqrt
    
    clinics = Organization.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(latitude='').exclude(longitude='')
    
    nearby_clinics = []
    
    for clinic in clinics:
        try:
            clinic_lat = float(clinic.latitude)
            clinic_lng = float(clinic.longitude)
            
            # Calculate distance using Haversine formula
            distance = calculate_distance(lat, lng, clinic_lat, clinic_lng)
            
            if distance <= radius_km:
                nearby_clinics.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'address': clinic.address,
                    'latitude': clinic.latitude,
                    'longitude': clinic.longitude,
                    'distance': round(distance, 2),
                    'org_type': clinic.get_org_type_display(),
                    'phone': clinic.phone,
                    'is_24_hours': clinic.is_24_hours,
                    'doctors_count': clinic.members.filter(role='doctor').count()
                })
        except (ValueError, TypeError):
            continue
    
    # Sort by distance
    nearby_clinics.sort(key=lambda x: x['distance'])
    return nearby_clinics

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    from math import radians, cos, sin, asin, sqrt
    
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

@login_required
def appointment_directions(request, appointment_id):
    """Get directions to appointment location"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if not appointment.organization or not appointment.organization.latitude:
        messages.error(request, "Location information not available for this appointment.")
        return redirect('appointments:dashboard')
    
    # Get user's current location from session or request
    user_lat = request.session.get('user_latitude')
    user_lng = request.session.get('user_longitude')
    
    clinic_data = {
        'name': appointment.organization.name,
        'address': appointment.organization.address,
        'latitude': appointment.organization.latitude,
        'longitude': appointment.organization.longitude,
        'phone': appointment.organization.phone,
        'appointment_date': appointment.appointment_date,
        'doctor_name': appointment.doctor.get_full_name(),
        'user_lat': user_lat,
        'user_lng': user_lng
    }
    
    return render(request, 'appointments/appointment_directions.html', {
        'appointment': appointment,
        'clinic_data': clinic_data,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

@login_required
def clinic_details_map(request, clinic_id):
    """Show detailed clinic information on map"""
    clinic = get_object_or_404(Organization, id=clinic_id)
    
    # Get doctors at this clinic
    doctors = UserProfile.objects.filter(
        organization=clinic,
        role='doctor'
    ).select_related('user')
    
    # Get upcoming appointments for this clinic
    upcoming_appointments = Appointment.objects.filter(
        organization=clinic,
        appointment_date__gte=timezone.now()
    ).order_by('appointment_date')[:10]
    
    return render(request, 'appointments/clinic_details_map.html', {
        'clinic': clinic,
        'doctors': doctors,
        'upcoming_appointments': upcoming_appointments
    })

@login_required
def search_clinics(request):
    from .models import Organization, UserProfile
    query = request.GET.get('q', '')
    orgs = Organization.objects.all()
    if query:
        orgs = orgs.filter(name__icontains=query)
    # For each org, get member doctors who are on duty
    orgs_with_doctors = []
    for org in orgs:
        doctors = UserProfile.objects.filter(organization=org, role='doctor', on_duty=True)
        orgs_with_doctors.append({'org': org, 'doctors': doctors})
    context = {
        'orgs_with_doctors': orgs_with_doctors,
        'query': query,
    }
    return render(request, 'appointments/search_clinics.html', context)

@login_required
def get_user_location(request):
    """Get user's current location via JavaScript"""
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if latitude and longitude:
            request.session['user_latitude'] = latitude
            request.session['user_longitude'] = longitude
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

@login_required
def clinic_appointments_map(request, clinic_id):
    """Show all appointments for a clinic on a map"""
    clinic = get_object_or_404(Organization, id=clinic_id)
    
    # Get all appointments for this clinic
    appointments = Appointment.objects.filter(
        organization=clinic,
        appointment_date__gte=timezone.now()
    ).select_related('patient', 'doctor').order_by('appointment_date')
    
    # Group appointments by date
    appointments_by_date = {}
    for appointment in appointments:
        date_key = appointment.appointment_date.strftime('%Y-%m-%d')
        if date_key not in appointments_by_date:
            appointments_by_date[date_key] = []
        appointments_by_date[date_key].append(appointment)
    
    return render(request, 'appointments/clinic_appointments_map.html', {
        'clinic': clinic,
        'appointments_by_date': appointments_by_date
    })

@csrf_exempt
def queue_status_api(request):
    """API endpoint for real-time queue status updates"""
    if request.method == 'GET' and request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
            today = datetime.now().date()
            
            # Try to get from cache first
            cache_key = f"queue_status_api_{request.user.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data is None:
                queue_appointments = Appointment.objects.filter(
                    patient=request.user,
                    appointment_date__date=today,
                    patient_status__in=['waiting', 'in_consultation']
                ).order_by('appointment_date')
                
                appointments_data = []
                for appointment in queue_appointments:
                    if appointment.patient_status == 'waiting':
                        position = Appointment.objects.filter(
                            doctor=appointment.doctor,
                            appointment_date__date=today,
                            appointment_date__lt=appointment.appointment_date,
                            patient_status='waiting'
                        ).count()
                        estimated_wait = position * 20
                    else:
                        position = 0
                        estimated_wait = 0
                    
                    appointments_data.append({
                        'id': appointment.id,
                        'doctor_name': appointment.doctor.get_full_name(),
                        'doctor_specialization': appointment.doctor.profile.specialization,
                        'appointment_time': appointment.appointment_date.strftime('%I:%M %p'),
                        'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
                        'status': appointment.get_patient_status_display(),
                        'status_class': appointment.patient_status.replace('_', '-'),
                        'queue_position': position + 1,
                        'estimated_wait': estimated_wait,
                        'minutes_until': int((appointment.appointment_date - timezone.now()).total_seconds() / 60),
                    })
                
                # Cache the data for 15 seconds (shorter than page cache for more responsive updates)
                cache.set(cache_key, appointments_data, 15)
            else:
                appointments_data = cached_data
            
            return JsonResponse({
                'appointments': appointments_data,
                'total_in_queue': len(appointments_data),
                'estimated_total_wait': sum(app['estimated_wait'] for app in appointments_data if app['status'] == 'Waiting'),
                'timestamp': timezone.now().isoformat(),
                'cache_hit': cached_data is not None,
            })
    
    return JsonResponse({'error': 'Unauthorized'}, status=401)

def privacy_policy(request):
    """Privacy Policy page"""
    return render(request, 'appointments/privacy_policy.html')

def terms_of_service(request):
    """Terms of Service page"""
    return render(request, 'appointments/terms_of_service.html')

def copyright_page(request):
    """Copyright page"""
    return render(request, 'appointments/copyright.html')

def refund_policy(request):
    """Refund Policy page"""
    return render(request, 'appointments/refund_policy.html')

def terms_conditions(request):
    """Terms and Conditions page"""
    return render(request, 'appointments/terms_conditions.html')

def custom_register(request):
    from django.contrib.auth import login, authenticate
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            reg_type = form.cleaned_data['registration_type']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            # Create org if needed
            org = None
            if reg_type in ['clinic', 'hospital', 'doctor_solo', 'solo_doctor']:
                org_type = form.cleaned_data['org_type']
                org_name = form.cleaned_data['org_name']
                org_address = form.cleaned_data['org_address']
                org = Organization.objects.create(
                    org_type=org_type if org_type else ('solo_doctor' if reg_type in ['doctor_solo', 'solo_doctor'] else reg_type),
                    name=org_name,
                    address=org_address,
                    admin=user
                )
            # Create user profile
            if reg_type in ['clinic', 'hospital', 'doctor_solo', 'solo_doctor']:
                role = 'admin' if reg_type in ['clinic', 'hospital'] else 'doctor'
            else:
                role = reg_type
            profile = UserProfile.objects.create(
                user=user,
                role=role,
                organization=org if org else None
            )
            # Authenticate and login with backend specification
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user:
                login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('appointments:dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'appointments/custom_register.html', {'form': form})

@login_required
def manage_org_join_requests(request):
    user_profile = request.user.profile
    if user_profile.role not in ['receptionist', 'admin'] or not user_profile.organization:
        return redirect('appointments:dashboard')
    org = user_profile.organization
    from .models import DoctorOrganizationJoinRequest, UserProfile
    join_requests = DoctorOrganizationJoinRequest.objects.filter(organization=org, status='pending')
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        if req_id and action in ['approve', 'deny']:
            join_req = DoctorOrganizationJoinRequest.objects.get(id=req_id, organization=org)
            join_req.status = 'approved' if action == 'approve' else 'denied'
            join_req.reviewed_at = timezone.now()
            join_req.reviewed_by = request.user
            join_req.save()
            from .utils import log_audit_event
            if action == 'approve':
                # Set doctor's organization
                doctor_profile = UserProfile.objects.get(user=join_req.doctor)
                doctor_profile.organization = org
                doctor_profile.save()
                log_audit_event(
                    user=request.user,
                    action='doctor_approved',
                    details=f"Approved doctor {join_req.doctor.get_full_name()} for org {org.name}",
                    object_type='doctor_org_join',
                    object_id=join_req.id
                )
            else:
                log_audit_event(
                    user=request.user,
                    action='doctor_denied',
                    details=f"Denied doctor {join_req.doctor.get_full_name()} for org {org.name}",
                    object_type='doctor_org_join',
                    object_id=join_req.id
                )
            messages.success(request, f"Request {'approved' if action == 'approve' else 'denied'}.")
            return redirect('appointments:manage_org_join_requests')
    # List current member doctors
    member_doctors = UserProfile.objects.filter(organization=org, role='doctor')
    context = {
        'join_requests': join_requests,
        'member_doctors': member_doctors,
        'org': org,
    }
    return render(request, 'appointments/manage_org_join_requests.html', context)

def home(request):
    return render(request, 'appointments/home.html', {'appointments': []})

def appointment_list(request):
    return HttpResponse('Appointment list placeholder')

def appointment_create(request):
    from django.utils.html import escape
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        # Always refresh doctor queryset to include all doctors
        form.fields['doctor'].queryset = User.objects.filter(profile__role='doctor')
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = form.cleaned_data['patient']
            appointment.doctor = form.cleaned_data['doctor']
            appointment.organization = form.cleaned_data.get('organization')
            # Escape notes to prevent XSS
            appointment.notes = escape(form.cleaned_data.get('notes', ''))
            appointment.save()
            # Redirect after successful creation (Post/Redirect/Get)
            return redirect('appointments:appointment_list')
        else:
            print('AppointmentForm errors:', form.errors)
    else:
        form = AppointmentForm()
        # Always refresh doctor queryset to include all doctors
        form.fields['doctor'].queryset = User.objects.filter(profile__role='doctor')
    return render(request, 'appointments/appointment_create.html', {'form': form})

def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    user = request.user
    if not (user.is_authenticated and (appointment.patient == user or appointment.doctor == user)):
        raise Http404()
    return HttpResponse(f'Appointment detail for {appointment.pk}')

def search_appointments(request):
    return HttpResponse('Search results')

# Enhanced Features Views

@login_required
def medical_records_view(request):
    """View for managing medical records"""
    if request.user.profile.role not in ['doctor', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            if request.user.profile.role == 'doctor':
                record.doctor = request.user
                record.patient = request.POST.get('patient')
            else:
                record.patient = request.user
            record.save()
            messages.success(request, "Medical record created successfully.")
            return redirect('medical_records')
    else:
        form = MedicalRecordForm()
    
    # Get records based on user role
    if request.user.profile.role == 'doctor':
        records = MedicalRecord.objects.filter(doctor=request.user).order_by('-date_recorded')
        patients = User.objects.filter(profile__role='patient')
    else:
        records = MedicalRecord.objects.filter(patient=request.user).order_by('-date_recorded')
        patients = None
    
    context = {
        'records': records,
        'form': form,
        'patients': patients,
    }
    return render(request, 'appointments/medical_records.html', context)

@login_required
def prescription_view(request):
    """View for managing prescriptions"""
    if request.user.profile.role not in ['doctor', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            prescription = form.save(commit=False)
            if request.user.profile.role == 'doctor':
                prescription.doctor = request.user
                prescription.patient = request.POST.get('patient')
                prescription.appointment = request.POST.get('appointment')
            else:
                prescription.patient = request.user
            prescription.save()
            messages.success(request, "Prescription created successfully.")
            return redirect('prescriptions')
    else:
        form = PrescriptionForm()
    
    # Get prescriptions based on user role
    if request.user.profile.role == 'doctor':
        prescriptions = Prescription.objects.filter(doctor=request.user).order_by('-prescribed_date')
        patients = User.objects.filter(profile__role='patient')
        appointments = Appointment.objects.filter(doctor=request.user, status='completed')
    else:
        prescriptions = Prescription.objects.filter(patient=request.user).order_by('-prescribed_date')
        patients = None
        appointments = None
    
    context = {
        'prescriptions': prescriptions,
        'form': form,
        'patients': patients,
        'appointments': appointments,
    }
    return render(request, 'appointments/prescriptions.html', context)

@login_required
def insurance_view(request):
    """View for managing insurance information"""
    if request.user.profile.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = InsuranceForm(request.POST)
        if form.is_valid():
            insurance = form.save(commit=False)
            insurance.patient = request.user
            insurance.save()
            messages.success(request, "Insurance information saved successfully.")
            return redirect('insurance')
    else:
        form = InsuranceForm()
    
    insurances = Insurance.objects.filter(patient=request.user).order_by('-effective_date')
    
    context = {
        'insurances': insurances,
        'form': form,
    }
    return render(request, 'appointments/insurance.html', context)

@login_required
def payment_view(request):
    """View for managing payments"""
    if request.user.profile.role not in ['doctor', 'patient', 'receptionist']:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, patient=request.user if request.user.profile.role == 'patient' else None)
        if form.is_valid():
            payment = form.save(commit=False)
            if request.user.profile.role == 'patient':
                payment.patient = request.user
                payment.doctor = request.POST.get('doctor')
                payment.organization = request.POST.get('organization')
            else:
                payment.patient = request.POST.get('patient')
                payment.doctor = request.user
                payment.organization = request.user.profile.organization
            payment.save()
            messages.success(request, "Payment processed successfully.")
            return redirect('payments')
    else:
        form = PaymentForm(patient=request.user if request.user.profile.role == 'patient' else None)
    
    # Get payments based on user role
    if request.user.profile.role == 'patient':
        payments = Payment.objects.filter(patient=request.user).order_by('-payment_date')
        doctors = User.objects.filter(profile__role='doctor')
        organizations = Organization.objects.all()
    elif request.user.profile.role == 'doctor':
        payments = Payment.objects.filter(doctor=request.user).order_by('-payment_date')
        patients = User.objects.filter(profile__role='patient')
        organizations = [request.user.profile.organization] if request.user.profile.organization else []
    else:  # receptionist
        payments = Payment.objects.filter(organization=request.user.profile.organization).order_by('-payment_date')
        patients = User.objects.filter(profile__role='patient')
        doctors = User.objects.filter(profile__role='doctor')
        organizations = [request.user.profile.organization] if request.user.profile.organization else []
    
    context = {
        'payments': payments,
        'form': form,
        'patients': patients if 'patients' in locals() else None,
        'doctors': doctors if 'doctors' in locals() else None,
        'organizations': organizations if 'organizations' in locals() else None,
    }
    return render(request, 'appointments/payments.html', context)

@login_required
def emergency_contacts_view(request):
    """View for managing emergency contacts"""
    if request.user.profile.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmergencyContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.patient = request.user
            contact.save()
            messages.success(request, "Emergency contact saved successfully.")
            return redirect('emergency_contacts')
    else:
        form = EmergencyContactForm()
    
    contacts = EmergencyContact.objects.filter(patient=request.user).order_by('-is_primary', 'name')
    
    context = {
        'contacts': contacts,
        'form': form,
    }
    return render(request, 'appointments/emergency_contacts.html', context)

@login_required
def medication_reminders_view(request):
    """View for managing medication reminders"""
    if request.user.profile.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = MedicationReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.patient = request.user
            reminder.prescription = request.POST.get('prescription')
            reminder.save()
            messages.success(request, "Medication reminder created successfully.")
            return redirect('medication_reminders')
    else:
        form = MedicationReminderForm()
    
    reminders = MedicationReminder.objects.filter(patient=request.user).order_by('next_reminder')
    prescriptions = Prescription.objects.filter(patient=request.user, status='active')
    
    context = {
        'reminders': reminders,
        'form': form,
        'prescriptions': prescriptions,
    }
    return render(request, 'appointments/medication_reminders.html', context)

@login_required
def telemedicine_sessions_view(request):
    """View for managing telemedicine sessions"""
    if request.user.profile.role not in ['doctor', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TelemedicineSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.appointment = request.POST.get('appointment')
            session.save()
            messages.success(request, "Telemedicine session created successfully.")
            return redirect('telemedicine_sessions')
    else:
        form = TelemedicineSessionForm()
    
    # Get sessions based on user role
    if request.user.profile.role == 'doctor':
        sessions = TelemedicineSession.objects.filter(appointment__doctor=request.user).order_by('-scheduled_start')
        appointments = Appointment.objects.filter(doctor=request.user, is_virtual=True)
    else:
        sessions = TelemedicineSession.objects.filter(appointment__patient=request.user).order_by('-scheduled_start')
        appointments = Appointment.objects.filter(patient=request.user, is_virtual=True)
    
    context = {
        'sessions': sessions,
        'form': form,
        'appointments': appointments,
    }
    return render(request, 'appointments/telemedicine_sessions.html', context)

@login_required
def start_telemedicine_session(request, session_id):
    """Start a telemedicine session"""
    session = get_object_or_404(TelemedicineSession, id=session_id)
    
    # Check if user has permission to access this session
    if request.user not in [session.appointment.doctor, session.appointment.patient]:
        messages.error(request, "Access denied.")
        return redirect('telemedicine_sessions')
    
    # Update session status
    session.status = 'in_progress'
    session.actual_start = timezone.now()
    session.save()
    
    context = {
        'session': session,
        'meeting_link': session.meeting_link,
        'meeting_password': session.meeting_password,
    }
    return render(request, 'appointments/telemedicine_session_room.html', context)

@login_required
def end_telemedicine_session(request, session_id):
    """End a telemedicine session"""
    session = get_object_or_404(TelemedicineSession, id=session_id)
    
    # Check if user has permission to end this session
    if request.user not in [session.appointment.doctor, session.appointment.patient]:
        messages.error(request, "Access denied.")
        return redirect('telemedicine_sessions')
    
    # Update session status
    session.status = 'completed'
    session.actual_end = timezone.now()
    if session.actual_start:
        duration = session.actual_end - session.actual_start
        session.duration_minutes = int(duration.total_seconds() / 60)
    session.save()
    
    messages.success(request, "Telemedicine session ended successfully.")
    return redirect('telemedicine_sessions')

@login_required
def health_analytics_view(request):
    """View for health analytics and insights"""
    if request.user.profile.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    # Get patient's health data
    appointments = Appointment.objects.filter(patient=request.user)
    prescriptions = Prescription.objects.filter(patient=request.user)
    medical_records = MedicalRecord.objects.filter(patient=request.user)
    payments = Payment.objects.filter(patient=request.user)
    
    # Calculate analytics
    total_appointments = appointments.count()
    completed_appointments = appointments.filter(status='completed').count()
    active_prescriptions = prescriptions.filter(status='active').count()
    total_spent = payments.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Recent activity
    recent_appointments = appointments.order_by('-appointment_date')[:5]
    recent_prescriptions = prescriptions.order_by('-prescribed_date')[:5]
    recent_records = medical_records.order_by('-date_recorded')[:5]
    
    context = {
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'active_prescriptions': active_prescriptions,
        'total_spent': total_spent,
        'recent_appointments': recent_appointments,
        'recent_prescriptions': recent_prescriptions,
        'recent_records': recent_records,
    }
    return render(request, 'appointments/health_analytics.html', context)
