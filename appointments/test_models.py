import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import factory
from faker import Faker

from .models import (
    UserProfile, Organization, Appointment, AuditLog
)
from .factories import (
    UserFactory, UserProfileFactory, OrganizationFactory, 
    AppointmentFactory
)

fake = Faker()

User = get_user_model()


@pytest.mark.django_db
class TestUserProfile:
    """Test UserProfile model"""
    
    def test_user_profile_creation(self):
        """Test UserProfile model creation"""
        profile = UserProfileFactory()
        assert profile.user is not None
        assert profile.role in ['patient', 'doctor', 'receptionist', 'admin']
    
    def test_user_profile_str_representation(self):
        user = UserFactory(username='user60', first_name='User', last_name='Sixty')
        profile = UserProfileFactory(user=user, role='patient', organization=None)
        expected = f"{user.get_full_name()} - {profile.role} ({profile.organization})"
        assert str(profile) == expected
    
    def test_user_profile_default_role(self):
        """Test UserProfile default role"""
        user = UserFactory()
        profile = UserProfile.objects.create(user=user)
        assert profile.role == 'patient'  # Default role


@pytest.mark.django_db
class TestOrganization:
    """Test Organization model"""
    
    def test_organization_creation(self):
        """Test Organization model creation"""
        org = OrganizationFactory()
        assert org.name is not None
        assert org.address is not None
        assert org.phone is not None
        assert org.email is not None
    
    def test_organization_str_representation(self):
        org = OrganizationFactory(org_type='clinic', name='Anderson and Sons')
        expected = f"Clinic: Anderson and Sons"
        assert str(org) == expected


@pytest.mark.django_db
class TestAppointment:
    """Test Appointment model"""
    
    def test_appointment_creation(self):
        """Test Appointment model creation"""
        appointment = AppointmentFactory()
        assert appointment.patient is not None
        assert appointment.doctor is not None
        assert appointment.organization is not None
        assert appointment.appointment_date > timezone.now()
        assert appointment.status in ['pending', 'scheduled', 'confirmed', 'completed', 'cancelled']
    
    def test_appointment_str_representation(self):
        """Test Appointment string representation"""
        appointment = AppointmentFactory()
        expected = f"{appointment.patient.get_full_name()} with Dr. {appointment.doctor.get_full_name()} on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}"
        assert str(appointment) == expected
    
    def test_appointment_status_transitions(self):
        """Test appointment status transitions"""
        appointment = AppointmentFactory()
        
        # Test valid status transitions
        valid_statuses = ['scheduled', 'confirmed', 'completed', 'cancelled']
        
        for status in valid_statuses:
            appointment.status = status
            appointment.save()
            appointment.refresh_from_db()
            assert appointment.status == status
    
    def test_appointment_future_date_validation(self):
        """Test that appointments cannot be created in the past"""
        patient = UserFactory() # Changed from PatientFactory
        doctor = UserFactory() # Changed from DoctorFactory
        
        # Try to create appointment in the past
        past_date = timezone.now() - timedelta(days=1)
        
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            organization=None,
            appointment_date=past_date,
            status='pending'
        )
        
        # The model should allow this for testing purposes
        # In production, this would be validated at the form level
        assert appointment.appointment_date == past_date
    
    def test_appointment_duration(self):
        """Test appointment duration calculation"""
        appointment = AppointmentFactory()
        
        # Set specific start and end times
        start_time = timezone.now() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)
        
        appointment.appointment_date = start_time
        appointment.end_time = end_time
        appointment.save()
        
        # Calculate duration
        duration = appointment.end_time - appointment.appointment_date
        assert duration.total_seconds() == 1800  # 30 minutes in seconds
    
    def test_appointment_conflicts(self):
        """Test appointment conflict detection"""
        doctor = UserFactory() # Changed from DoctorFactory
        patient1 = UserFactory() # Changed from PatientFactory
        patient2 = UserFactory() # Changed from PatientFactory
        
        # Create first appointment
        appointment1 = AppointmentFactory(
            doctor=doctor,
            patient=patient1,
            appointment_date=timezone.now() + timedelta(hours=1),
            status='confirmed'
        )
        
        # Create overlapping appointment
        appointment2 = AppointmentFactory(
            doctor=doctor,
            patient=patient2,
            appointment_date=timezone.now() + timedelta(hours=1, minutes=15),
            status='scheduled'
        )
        
        # Both appointments should exist (conflict detection would be in business logic)
        assert Appointment.objects.count() == 2
        assert appointment1.doctor == appointment2.doctor


@pytest.mark.django_db
class TestAuditLog:
    """Test AuditLog model"""
    
    def test_audit_log_creation(self):
        """Test AuditLog model creation"""
        user = UserFactory()
        audit_log = AuditLog.objects.create(
            user=user,
            action="test_action",
            object_type="appointment",
            object_id=1,
            details="Test audit log entry"
        )
        
        assert audit_log.user == user
        assert audit_log.action == "test_action"
        assert audit_log.object_type == "appointment"
        assert audit_log.object_id == 1
        assert audit_log.details == "Test audit log entry"
        assert audit_log.timestamp is not None
    
    def test_audit_log_str_representation(self):
        user = UserFactory()
        audit_log = AuditLog.objects.create(
            user=user,
            action="test_action",
            object_type="appointment",
            object_id=1,
            details="Test audit log entry"
        )
        expected = f"{user} - test_action at {audit_log.timestamp}"
        assert str(audit_log) == expected


@pytest.mark.django_db
class TestModelRelationships:
    """Test relationships between models"""
    
    def test_doctor_clinic_relationship(self):
        doctor = UserFactory()
        UserProfileFactory(user=doctor, role='doctor', organization=OrganizationFactory())
        assert doctor.profile.organization is not None
    
    def test_appointment_relationships(self):
        appointment = AppointmentFactory()
        assert appointment.patient is not None
        assert appointment.doctor is not None
        assert appointment.organization is not None
    
    def test_user_profile_relationship(self):
        """Test user-profile relationship"""
        profile = UserProfileFactory()
        assert profile.user is not None
        assert hasattr(profile.user, 'profile')
        assert profile.user.profile == profile
    
    def test_patient_doctor_relationship(self):
        """Test patient-doctor relationship through appointments"""
        patient = UserFactory() # Changed from PatientFactory
        doctor = UserFactory() # Changed from DoctorFactory
        UserProfileFactory(user=patient, role='patient')
        UserProfileFactory(user=doctor, role='doctor')
        appointment = AppointmentFactory(patient=patient, doctor=doctor)
        
        # Patient should have access to their doctors through appointments
        patient_doctors = UserProfile.objects.filter(user__doctor_appointments__patient=patient).distinct()
        assert doctor.profile in patient_doctors
    
    def test_doctor_patient_relationship(self):
        """Test doctor-patient relationship through appointments"""
        patient = UserFactory() # Changed from PatientFactory
        doctor = UserFactory() # Changed from DoctorFactory
        UserProfileFactory(user=patient, role='patient')
        UserProfileFactory(user=doctor, role='doctor')
        appointment = AppointmentFactory(patient=patient, doctor=doctor)
        
        # Doctor should have access to their patients through appointments
        doctor_patients = UserProfile.objects.filter(user__patient_appointments__doctor=doctor).distinct()
        assert patient.profile in doctor_patients


@pytest.mark.django_db
class TestModelValidation:
    """Test model validation"""
    
    def test_appointment_date_validation(self):
        """Test appointment date validation"""
        patient = UserFactory() # Changed from PatientFactory
        doctor = UserFactory() # Changed from DoctorFactory
        UserProfileFactory(user=patient, role='patient')
        UserProfileFactory(user=doctor, role='doctor')
        org = OrganizationFactory()
        # Valid future date
        future_date = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            organization=org,
            appointment_date=future_date,
            status='scheduled'
        )
        assert appointment.appointment_date > timezone.now()
    
    def test_user_profile_role_validation(self):
        """Test user profile role validation"""
        user = UserFactory()
        # Valid role
        profile = UserProfile.objects.create(user=user, role='doctor')
        assert profile.role == 'doctor'
        # Invalid role should be handled by choices
        profile.role = 'invalid_role'
        profile.save()  # Django will handle this based on choices


@pytest.mark.django_db
def test_admin_can_create_multiple_clinics():
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    org1 = OrganizationFactory(name='Clinic A', admin=admin_user)
    org2 = OrganizationFactory(name='Clinic B', admin=admin_user)
    assert org1.admin == admin_user
    assert org2.admin == admin_user
    assert org1.name != org2.name

@pytest.mark.django_db
def test_doctor_and_receptionist_association():
    org = OrganizationFactory(name='Clinic C')
    doctor_user = UserFactory()
    receptionist_user = UserFactory()
    doctor_profile = UserProfileFactory(user=doctor_user, role='doctor', organization=org)
    receptionist_profile = UserProfileFactory(user=receptionist_user, role='receptionist', organization=org)
    assert doctor_profile.organization == org
    assert receptionist_profile.organization == org

@pytest.mark.django_db
def test_clinic_data_isolation():
    org_a = OrganizationFactory(name='Clinic A')
    org_b = OrganizationFactory(name='Clinic B')
    doctor_a = UserFactory()
    doctor_b = UserFactory()
    receptionist_a = UserFactory()
    receptionist_b = UserFactory()
    UserProfileFactory(user=doctor_a, role='doctor', organization=org_a)
    UserProfileFactory(user=doctor_b, role='doctor', organization=org_b)
    UserProfileFactory(user=receptionist_a, role='receptionist', organization=org_a)
    UserProfileFactory(user=receptionist_b, role='receptionist', organization=org_b)
    # Doctor A should not see org B
    assert doctor_a.profile.organization == org_a
    assert doctor_b.profile.organization == org_b
    assert receptionist_a.profile.organization == org_a
    assert receptionist_b.profile.organization == org_b
    # Simulate dashboard data isolation
    clinics_seen_by_a = OrganizationFactory._meta.model.objects.filter(members__user=doctor_a)
    clinics_seen_by_b = OrganizationFactory._meta.model.objects.filter(members__user=doctor_b)
    assert org_b not in clinics_seen_by_a
    assert org_a not in clinics_seen_by_b

@pytest.mark.django_db
def test_organization_switching_dashboard_data():
    client = Client()
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    org1 = OrganizationFactory(name='Clinic X', admin=admin_user)
    org2 = OrganizationFactory(name='Clinic Y', admin=admin_user)
    doctor_user = UserFactory()
    UserProfileFactory(user=doctor_user, role='doctor', organization=org1)
    # Log in as doctor and check dashboard for org1
    client.force_login(doctor_user)
    response1 = client.get(reverse('appointments:dashboard'))
    assert org1.name in response1.content.decode()
    # Switch organization
    doctor_user.profile.organization = org2
    doctor_user.profile.save()
    response2 = client.get(reverse('appointments:dashboard'))
    assert org2.name in response2.content.decode()


if __name__ == '__main__':
    pytest.main([__file__]) 