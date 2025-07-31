from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Appointment, UserProfile
from notifications.signals import notify
# from .utils import send_sms  # Removed Twilio

logger = logging.getLogger(__name__)

@shared_task
def send_appointment_reminder(appointment_id):
    """Send appointment reminder to patient"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        patient = appointment.patient
        doctor = appointment.doctor
        
        # Send email reminder
        subject = f"Appointment Reminder - {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}"
        message = f"""
        Dear {patient.get_full_name()},
        
        This is a reminder for your appointment with Dr. {doctor.get_full_name()} 
        on {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}.
        
        Please arrive 10 minutes before your scheduled time.
        
        If you need to reschedule or cancel, please contact the clinic.
        
        Best regards,
        PulseCal Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
        
        # SMS logic removed. Use notifications for all alerts.
        logger.info(f"Appointment reminder sent for appointment {appointment_id}")
    except Exception as e:
        logger.error(f"Failed to send appointment reminder: {e}")

@shared_task
def send_appointment_confirmation(appointment_id):
    """Send appointment confirmation to patient"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        patient = appointment.patient
        doctor = appointment.doctor
        
        subject = f"Appointment Confirmed - {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}"
        message = f"""
        Dear {patient.get_full_name()},
        
        Your appointment with Dr. {doctor.get_full_name()} has been confirmed for 
        {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}.
        
        Appointment Details:
        - Date: {appointment.appointment_date.strftime('%B %d, %Y')}
        - Time: {appointment.appointment_date.strftime('%I:%M %p')}
        - Doctor: Dr. {doctor.get_full_name()}
        - Fee: ${appointment.fee}
        
        Please arrive 10 minutes before your scheduled time.
        
        Best regards,
        PulseCal Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
        
        logger.info(f"Appointment confirmation sent for appointment {appointment_id}")
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as e:
        logger.error(f"Error sending appointment confirmation: {str(e)}")

@shared_task
def send_appointment_cancellation(appointment_id):
    """Send appointment cancellation notification"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        patient = appointment.patient
        doctor = appointment.doctor
        
        subject = f"Appointment Cancelled - {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}"
        message = f"""
        Dear {patient.get_full_name()},
        
        Your appointment with Dr. {doctor.get_full_name()} scheduled for 
        {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')} has been cancelled.
        
        If you have any questions, please contact the clinic.
        
        Best regards,
        PulseCal Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
        
        logger.info(f"Appointment cancellation sent for appointment {appointment_id}")
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as e:
        logger.error(f"Error sending appointment cancellation: {str(e)}")

@shared_task
def cleanup_old_notifications():
    """Clean up notifications older than 30 days"""
    try:
        from notifications.models import Notification
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = Notification.objects.filter(
            timestamp__lt=cutoff_date,
            unread=False
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {str(e)}")

@shared_task
def send_daily_appointment_summary():
    """Send daily appointment summary to doctors"""
    try:
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Get all doctors
        doctors = UserProfile.objects.filter(role='doctor')
        
        for doctor_profile in doctors:
            doctor = doctor_profile.user
            appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__date=tomorrow,
                status='confirmed'
            ).order_by('appointment_date')
            
            if appointments.exists():
                subject = f"Tomorrow's Appointments - {tomorrow.strftime('%B %d, %Y')}"
                message = f"""
                Dear Dr. {doctor.get_full_name()},
                
                Here are your appointments for tomorrow ({tomorrow.strftime('%B %d, %Y')}):
                
                """
                
                for appointment in appointments:
                    message += f"""
                - {appointment.appointment_date.strftime('%I:%M %p')} - {appointment.patient.get_full_name()}
                  Type: {appointment.get_appointment_type_display()}
                  Fee: ${appointment.fee}
                """
                
                message += """
                
                Best regards,
                PulseCal Team
                """
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[doctor.email],
                    fail_silently=False,
                )
        
        logger.info("Daily appointment summaries sent to doctors")
        
    except Exception as e:
        logger.error(f"Error sending daily appointment summaries: {str(e)}")

@shared_task
def update_doctor_availability():
    """Update doctor availability status based on current time"""
    try:
        now = timezone.now()
        
        # Get doctors who are on duty
        on_duty_doctors = UserProfile.objects.filter(role='doctor', on_duty=True)
        
        for doctor_profile in on_duty_doctors:
            # Check if doctor has appointments within the next 2 hours
            upcoming_appointments = Appointment.objects.filter(
                doctor=doctor_profile.user,
                appointment_date__gte=now,
                appointment_date__lte=now + timedelta(hours=2),
                status='confirmed'
            )
            
            # Update next available time
            if upcoming_appointments.exists():
                last_appointment = upcoming_appointments.order_by('-appointment_date').first()
                doctor_profile.next_available = last_appointment.appointment_date + timedelta(minutes=30)
            else:
                doctor_profile.next_available = now
            
            doctor_profile.save()
        
        logger.info("Doctor availability updated")
        
    except Exception as e:
        logger.error(f"Error updating doctor availability: {str(e)}") 