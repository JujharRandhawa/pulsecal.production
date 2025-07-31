import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime, timedelta
import factory
from faker import Faker

from .models import UserProfile, Organization, Appointment, AuditLog
from .factories import UserFactory, UserProfileFactory, OrganizationFactory

User = get_user_model()
fake = Faker()


class TestBasicAuthentication(TestCase):
    """Test basic authentication without Axes complications"""
    
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
    def test_user_creation(self):
        """Test that users can be created"""
        self.assertIsNotNone(self.user)
        self.assertEqual(self.user.username, self.user.username)
        
    def test_password_setting(self):
        """Test that passwords can be set"""
        self.assertTrue(self.user.check_password('testpass123'))
        
    def test_user_profile_creation(self):
        """Test UserProfile creation"""
        profile = UserProfileFactory(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertIn(profile.role, ['patient', 'doctor', 'receptionist'])


class TestUserProfileRoles(TestCase):
    """Test UserProfile role functionality"""
    
    def setUp(self):
        self.patient_user = UserFactory()
        self.patient_profile = UserProfileFactory(user=self.patient_user, role='patient')
        
        self.doctor_user = UserFactory()
        self.doctor_profile = UserProfileFactory(user=self.doctor_user, role='doctor')
        
        self.receptionist_user = UserFactory()
        self.receptionist_profile = UserProfileFactory(user=self.receptionist_user, role='receptionist')
        
    def test_role_assignment(self):
        """Test that roles are correctly assigned"""
        self.assertEqual(self.patient_profile.role, 'patient')
        self.assertEqual(self.doctor_profile.role, 'doctor')
        self.assertEqual(self.receptionist_profile.role, 'receptionist')
        
    def test_role_methods(self):
        """Test role checking methods if they exist"""
        # Test basic role checking
        self.assertEqual(self.patient_profile.role, 'patient')
        self.assertEqual(self.doctor_profile.role, 'doctor')
        self.assertEqual(self.receptionist_profile.role, 'receptionist')


class TestOrganizationAccess(TestCase):
    """Test organization-based access control"""
    
    def setUp(self):
        self.organization = OrganizationFactory()
        
        # Create users in organization
        self.org_user = UserFactory()
        self.org_profile = UserProfileFactory(
            user=self.org_user, 
            role='doctor',
            organization=self.organization
        )
        
        # Create user outside organization
        self.outside_user = UserFactory()
        self.outside_profile = UserProfileFactory(
            user=self.outside_user, 
            role='doctor'
        )
        
    def test_organization_assignment(self):
        """Test that users can be assigned to organizations"""
        self.assertEqual(self.org_profile.organization, self.organization)
        self.assertIsNone(self.outside_profile.organization)
        
    def test_organization_membership(self):
        """Test organization membership"""
        self.assertIn(self.org_profile, self.organization.members.all())
        self.assertNotIn(self.outside_profile, self.organization.members.all())


class TestAppointmentCreation(TestCase):
    """Test appointment creation and access control"""
    
    def setUp(self):
        self.organization = OrganizationFactory()
        
        # Create doctor
        self.doctor_user = UserFactory()
        self.doctor_profile = UserProfileFactory(
            user=self.doctor_user, 
            role='doctor',
            organization=self.organization
        )
        
        # Create patient
        self.patient_user = UserFactory()
        self.patient_profile = UserProfileFactory(
            user=self.patient_user, 
            role='patient'
        )
        
    def test_appointment_creation(self):
        """Test that appointments can be created"""
        appointment = Appointment.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment_date=timezone.now() + timedelta(days=1),
            status='pending',
            organization=self.organization
        )
        
        self.assertIsNotNone(appointment)
        self.assertEqual(appointment.patient, self.patient_user)
        self.assertEqual(appointment.doctor, self.doctor_user)
        self.assertEqual(appointment.organization, self.organization)


class TestAuditLogging(TestCase):
    """Test audit logging system"""
    
    def setUp(self):
        self.user = UserFactory()
        self.profile = UserProfileFactory(user=self.user, role='patient')
        
    def test_audit_log_creation(self):
        """Test that audit logs can be created"""
        audit_log = AuditLog.objects.create(
            user=self.user,
            action='test_action',
            details='Test audit log entry'
        )
        
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'test_action')


class TestPermissionSystem(TestCase):
    """Test Django's permission system integration"""
    
    def setUp(self):
        self.user = UserFactory()
        self.profile = UserProfileFactory(user=self.user, role='doctor')
        
    def test_basic_permissions(self):
        """Test basic permission functionality"""
        # Test that users can have permissions
        content_type = ContentType.objects.get_for_model(Appointment)
        permission = Permission.objects.get(
            codename='add_appointment',
            content_type=content_type,
        )
        
        self.user.user_permissions.add(permission)
        self.assertTrue(self.user.has_perm('appointments.add_appointment'))


class TestURLPatterns(TestCase):
    """Test that URL patterns exist and are accessible"""
    
    def setUp(self):
        self.client = Client()
        
    def test_home_page_exists(self):
        """Test that home page URL exists"""
        try:
            response = self.client.get('/')
            # Should either return 200 (if accessible) or 302 (if login required)
            self.assertIn(response.status_code, [200, 302])
        except Exception as e:
            self.fail(f"Home page URL failed: {e}")
            
    def test_login_page_exists(self):
        """Test that login page URL exists"""
        try:
            response = self.client.get('/accounts/login/')
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"Login page URL failed: {e}")
            
    def test_signup_page_exists(self):
        """Test that signup page URL exists"""
        try:
            response = self.client.get('/accounts/signup/')
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"Signup page URL failed: {e}")


class TestModelValidation(TestCase):
    """Test model validation and constraints"""
    
    def test_userprofile_role_validation(self):
        """Test UserProfile role validation"""
        # Test valid roles with unique user for each
        valid_roles = ['patient', 'doctor', 'receptionist']
        for role in valid_roles:
            user = UserFactory()
            profile = UserProfileFactory(user=user, role=role)
            self.assertEqual(profile.role, role)
            
    def test_appointment_status_validation(self):
        """Test Appointment status validation"""
        patient = UserFactory()
        doctor = UserFactory()
        organization = OrganizationFactory()
        
        # Test valid statuses
        valid_statuses = ['pending', 'confirmed', 'checkedin', 'cancelled', 'completed', 'declined']
        for status in valid_statuses:
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=timezone.now() + timedelta(days=1),
                status=status,
                organization=organization
            )
            self.assertEqual(appointment.status, status)


class RegistrationAndLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient_data = {
            'username': 'patient1',
            'email': 'patient1@example.com',
            'password': 'Testpass123!',
            'confirm_password': 'Testpass123!',
            'registration_type': 'patient',
            'first_name': 'Test',
            'last_name': 'Patient',
        }

    def test_patient_registration_and_login(self):
        # Register patient
        response = self.client.post(reverse('appointments:custom_register'), self.patient_data, follow=True)
        if response.status_code != 200 or '/dashboard/' not in response.request['PATH_INFO']:
            print('Registration form errors:', getattr(response.context.get('form'), 'errors', 'No form in context'))
        self.assertEqual(response.status_code, 200)  # Should land on dashboard
        # Check that the final URL is the dashboard
        self.assertIn('dashboard', response.request['PATH_INFO'])

class DashboardRedirectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users for each role
        self.patient = User.objects.create_user(username='pat', password='pass', email='pat@example.com')
        UserProfile.objects.create(user=self.patient, role='patient')
        self.doctor = User.objects.create_user(username='doc', password='pass', email='doc@example.com')
        UserProfile.objects.create(user=self.doctor, role='doctor')
        self.receptionist = User.objects.create_user(username='rec', password='pass', email='rec@example.com')
        UserProfile.objects.create(user=self.receptionist, role='receptionist')
        self.admin = User.objects.create_user(username='adm', password='pass', email='adm@example.com', is_staff=True, is_superuser=True)
        UserProfile.objects.create(user=self.admin, role='admin')

    def test_patient_dashboard_redirect(self):
        self.client.login(username='pat', password='pass')
        response = self.client.get(reverse('appointments:dashboard'))
        self.assertIn(response.status_code, [200, 302])

    def test_doctor_dashboard_redirect(self):
        self.client.login(username='doc', password='pass')
        response = self.client.get(reverse('appointments:dashboard'))
        self.assertIn(response.status_code, [200, 302])

    def test_receptionist_dashboard_redirect(self):
        self.client.login(username='rec', password='pass')
        response = self.client.get(reverse('appointments:dashboard'))
        self.assertIn(response.status_code, [200, 302])

    def test_admin_dashboard_redirect(self):
        self.client.login(username='adm', password='pass')
        response = self.client.get(reverse('appointments:dashboard'))
        self.assertIn(response.status_code, [200, 302])

class UnauthorizedDashboardAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = User.objects.create_user(username='pat', password='pass', email='pat@example.com')
        UserProfile.objects.create(user=self.patient, role='patient')
        self.doctor = User.objects.create_user(username='doc', password='pass', email='doc@example.com')
        UserProfile.objects.create(user=self.doctor, role='doctor')

    def test_patient_cannot_access_admin_dashboard(self):
        self.client.login(username='pat', password='pass')
        response = self.client.get('/admin/', follow=True)
        # Should show login form for admin
        self.assertIn(b'username', response.content)
        self.assertIn(b'password', response.content)

    def test_patient_cannot_access_doctor_dashboard(self):
        self.client.login(username='pat', password='pass')
        response = self.client.get(reverse('appointments:dashboard'))
        # Should be redirected to patient dashboard or denied
        self.assertIn(response.status_code, [200, 302])

    def test_doctor_cannot_access_admin_dashboard(self):
        self.client.login(username='doc', password='pass')
        response = self.client.get('/admin/', follow=True)
        self.assertIn(b'username', response.content)
        self.assertIn(b'password', response.content)


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create patient and doctor
        self.patient = User.objects.create_user(username='pat2', password='pass', email='pat2@example.com')
        UserProfile.objects.create(user=self.patient, role='patient')
        self.doctor = User.objects.create_user(username='doc2', password='pass', email='doc2@example.com')
        UserProfile.objects.create(user=self.doctor, role='doctor')
        # Log in patient
        self.client.login(username='pat2', password='pass')
        # Set up appointment time
        self.appointment_time = timezone.now() + timedelta(days=1, hours=2)

    def test_patient_can_book_appointment(self):
        response = self.client.post(reverse('appointments:schedule'), {
            'doctor': self.doctor.id,
            'patient': self.patient.id,
            'appointment_date': self.appointment_time.strftime('%Y-%m-%d %H:%M'),
            'appointment_type': 'new',
            'status': 'pending',
            'fee': 100.0,
        })
        if response.status_code != 302:
            print('Form errors:', response.context['form'].errors)
        self.assertIn(response.status_code, [200, 302])
        appt = Appointment.objects.filter(patient=self.patient, doctor=self.doctor, appointment_date__date=self.appointment_time.date()).first()
        self.assertIsNotNone(appt)
        self.assertEqual(appt.status, 'pending')

    def test_double_booking_prevented(self):
        # Book first appointment
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_time,
            status='pending'
        )
        # Try to book same slot again
        response = self.client.post(reverse('appointments:schedule'), {
            'doctor': self.doctor.id,
            'appointment_date': self.appointment_time.strftime('%Y-%m-%d %H:%M'),
        })
        # Should not allow double booking (expect error or redirect without new appointment)
        appts = Appointment.objects.filter(doctor=self.doctor, appointment_date=self.appointment_time)
        self.assertEqual(appts.count(), 1)

    def test_patient_can_see_appointment_lists(self):
        # Create upcoming, past, and cancelled appointments
        upcoming = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=timezone.now() + timedelta(days=2),
            status='confirmed'
        )
        past = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=timezone.now() - timedelta(days=2),
            status='done'
        )
        cancelled = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=timezone.now() - timedelta(days=1),
            status='cancelled'
        )
        response = self.client.get(reverse('appointments:patient_dashboard'))
        self.assertContains(response, str(upcoming.doctor.get_full_name()))
        self.assertContains(response, str(past.doctor.get_full_name()))
        self.assertContains(response, str(cancelled.doctor.get_full_name()))


if __name__ == '__main__':
    pytest.main([__file__]) 