import factory
from django.contrib.auth import get_user_model
from faker import Faker
from decimal import Decimal
import random
from .models import (
    UserProfile, Organization, Appointment, AuditLog
)
import datetime

User = get_user_model()
fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())


class UserProfileFactory(factory.django.DjangoModelFactory):
    """Factory for creating UserProfile instances"""
    class Meta:
        model = UserProfile
    
    user = factory.SubFactory(UserFactory)
    role = factory.Iterator(['patient', 'doctor', 'receptionist'])
    organization = None  # Only set if explicitly provided
    specialization = factory.LazyFunction(lambda: fake.job()[:100])
    phone = factory.LazyFunction(lambda: fake.phone_number()[:20])
    on_duty = factory.LazyFunction(lambda: fake.boolean())
    experience_years = factory.LazyFunction(lambda: fake.random_int(min=0, max=30))
    rating = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(1.0, 5.0), 2))))
    consultation_fee = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(0, 500), 2))))
    bio = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    languages = factory.LazyFunction(lambda: [fake.language_name()[:20] for _ in range(fake.random_int(min=1, max=3))])
    certifications = factory.LazyFunction(lambda: [fake.job()[:50] for _ in range(fake.random_int(min=0, max=3))])


class OrganizationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Organization instances"""
    class Meta:
        model = Organization
    
    org_type = factory.Iterator(['clinic', 'hospital'])
    name = factory.LazyFunction(lambda: fake.company())
    address = factory.LazyFunction(lambda: fake.address())
    contact_info = factory.LazyFunction(lambda: fake.phone_number())
    city = factory.LazyFunction(lambda: fake.city())
    country = factory.LazyFunction(lambda: fake.country())
    email = factory.LazyFunction(lambda: fake.email())
    is_24_hours = factory.LazyFunction(lambda: fake.boolean())
    is_location_verified = factory.LazyFunction(lambda: fake.boolean())
    latitude = factory.LazyFunction(lambda: fake.latitude())
    longitude = factory.LazyFunction(lambda: fake.longitude())
    operating_hours = factory.LazyFunction(lambda: {
        'monday': {'open': '09:00', 'close': '17:00'},
        'tuesday': {'open': '09:00', 'close': '17:00'},
        'wednesday': {'open': '09:00', 'close': '17:00'},
        'thursday': {'open': '09:00', 'close': '17:00'},
        'friday': {'open': '09:00', 'close': '17:00'},
        'saturday': {'open': '09:00', 'close': '13:00'},
        'sunday': {'open': 'closed', 'close': 'closed'}
    })
    phone = factory.LazyFunction(lambda: fake.phone_number())
    postal_code = factory.LazyFunction(lambda: fake.postcode())
    state = factory.LazyFunction(lambda: fake.state())
    website = factory.LazyFunction(lambda: fake.url())


class AppointmentFactory(factory.django.DjangoModelFactory):
    """Factory for creating Appointment instances"""
    class Meta:
        model = Appointment
    
    patient = factory.SubFactory(UserFactory)
    doctor = factory.SubFactory(UserFactory)
    appointment_date = factory.LazyFunction(lambda: fake.future_datetime())
    status = factory.Iterator(['pending', 'confirmed', 'checkedin', 'cancelled', 'completed'])
    patient_status = factory.Iterator(['waiting', 'in_consultation', 'done'])
    notes = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    fee = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(0, 500), 2))))
    appointment_type = factory.Iterator(['new', 'followup', 'emergency', 'virtual'])
    reception_notes = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    patient_notes = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    organization = factory.SubFactory(OrganizationFactory)


# AuditLogFactory removed. Use django-notifications-hq in tests if needed.


# Specialized factories for specific test scenarios
class ConfirmedAppointmentFactory(AppointmentFactory):
    """Factory for creating confirmed appointments"""
    status = 'confirmed'


class CompletedAppointmentFactory(AppointmentFactory):
    """Factory for creating completed appointments"""
    status = 'completed'
    appointment_date = factory.LazyFunction(
        lambda: fake.past_datetime(start_date='-30d', end_date='-1d')
    )


class CancelledAppointmentFactory(AppointmentFactory):
    """Factory for creating cancelled appointments"""
    status = 'cancelled'


# EmergencyNotificationFactory removed. Use django-notifications-hq in tests if needed.


# ReadNotificationFactory removed. Use django-notifications-hq in tests if needed.


# AdminUserFactory removed. Use django-notifications-hq in tests if needed.


# DoctorUserFactory removed. Use django-notifications-hq in tests if needed.


# PatientUserFactory removed. Use django-notifications-hq in tests if needed.


# ReceptionistUserFactory removed. Use django-notifications-hq in tests if needed.


# Factory for creating complete appointment scenarios
class CompleteAppointmentScenarioFactory:
    """Factory for creating complete appointment scenarios with all related objects"""
    
    @classmethod
    def create_scenario(cls, **kwargs):
        """Create a complete appointment scenario"""
        # Create organization
        organization = OrganizationFactory()
        
        # Create doctor (as UserProfile)
        doctor = UserProfileFactory(organization=organization, role='doctor')
        
        # Create patient (as UserProfile)
        patient = UserProfileFactory(organization=organization, role='patient')
        
        # Create appointment
        appointment = AppointmentFactory(
            patient=patient,
            doctor=doctor,
            clinic=organization, # Changed from clinic
            **kwargs
        )
        
        # Create notification
        # NotificationFactory removed. Use django-notifications-hq in tests if needed.
        
        # Create audit log
        audit_log = AuditLogFactory(
            user=patient.user,
            action='appointment_created',
            object_type='appointment',
            object_id=appointment.id,
            details=f"Appointment created for {patient.user.username} with {doctor.user.username}"
        )
        
        return {
            'organization': organization,
            'doctor': doctor,
            'patient': patient,
            'appointment': appointment,
            'notification': None, # NotificationFactory removed. Use django-notifications-hq in tests if needed.
            'audit_log': audit_log
        }


# Factory for creating multiple appointments for testing
class MultipleAppointmentsFactory:
    """Factory for creating multiple appointments for load testing"""
    
    @classmethod
    def create_multiple_appointments(cls, count=10, **kwargs):
        """Create multiple appointments"""
        appointments = []
        
        for i in range(count):
            appointment = AppointmentFactory(**kwargs)
            appointments.append(appointment)
        
        return appointments
    
    @classmethod
    def create_appointments_for_doctor(cls, doctor, count=5, **kwargs):
        """Create multiple appointments for a specific doctor"""
        appointments = []
        
        for i in range(count):
            appointment = AppointmentFactory(doctor=doctor, **kwargs)
            appointments.append(appointment)
        
        return appointments
    
    @classmethod
    def create_appointments_for_patient(cls, patient, count=3, **kwargs):
        """Create multiple appointments for a specific patient"""
        appointments = []
        
        for i in range(count):
            appointment = AppointmentFactory(patient=patient, **kwargs)
            appointments.append(appointment)
        
        return appointments


# Factory for creating test data for specific time periods
class TimeBasedAppointmentFactory:
    """Factory for creating appointments in specific time periods"""
    
    @classmethod
    def create_today_appointments(cls, count=5, **kwargs):
        """Create appointments for today"""
        from django.utils import timezone
        from datetime import timedelta
        
        appointments = []
        today = timezone.now().date()
        
        for i in range(count):
            hour = 9 + (i * 2)  # 9 AM, 11 AM, 1 PM, etc.
            appointment_time = timezone.make_aware(
                datetime.combine(today, datetime.min.time().replace(hour=hour))
            )
            appointment = AppointmentFactory(
                appointment_date=appointment_time,
                **kwargs
            )
            appointments.append(appointment)
        
        return appointments
    
    @classmethod
    def create_this_week_appointments(cls, count=10, **kwargs):
        """Create appointments for this week"""
        from django.utils import timezone
        from datetime import timedelta
        
        appointments = []
        today = timezone.now().date()
        
        for i in range(count):
            day_offset = i % 7  # Spread across the week
            appointment_date = today + timedelta(days=day_offset)
            hour = 9 + (i % 8)  # 9 AM to 5 PM
            
            appointment_time = timezone.make_aware(
                datetime.combine(appointment_date, datetime.min.time().replace(hour=hour))
            )
            appointment = AppointmentFactory(
                appointment_date=appointment_time,
                **kwargs
            )
            appointments.append(appointment)
        
        return appointments
    
    @classmethod
    def create_past_appointments(cls, count=5, days_back=30, **kwargs):
        """Create appointments in the past"""
        from django.utils import timezone
        from datetime import timedelta
        
        appointments = []
        
        for i in range(count):
            days_ago = fake.random_int(min=1, max=days_back)
            appointment_date = timezone.now() - timedelta(days=days_ago)
            appointment = AppointmentFactory(
                appointment_date=appointment_date,
                status='completed',
                **kwargs
            )
            appointments.append(appointment)
        
        return appointments 


class DoctorOrganizationJoinRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'appointments.DoctorOrganizationJoinRequest'
    doctor = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    status = 'pending'
    created_at = factory.LazyFunction(lambda: fake.past_datetime(start_date='-5d'))
    reviewed_at = None
    reviewed_by = None 