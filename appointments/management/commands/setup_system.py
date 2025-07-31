from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from appointments.models import Organization, UserProfile
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Setup the PulseCal system with initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@pulsecal.com',
            help='Admin email address'
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123456',
            help='Admin password'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up PulseCal system...'))

        # Create default site
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': 'localhost:8000',
                'name': 'PulseCal System'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created default site'))

        # Create default organization
        org, created = Organization.objects.get_or_create(
            name='Default Clinic',
            defaults={
                'org_type': 'clinic',
                'address': '123 Main Street, City, State 12345',
                'contact_info': '+1-555-123-4567',
                'city': 'City',
                'state': 'State',
                'postal_code': '12345',
                'country': 'USA',
                'phone': '+1-555-123-4567',
                'email': 'info@defaultclinic.com',
                'is_24_hours': False,
                'is_location_verified': False,
                'operating_hours': {}
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created default organization'))

        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': options['admin_email'],
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password(options['admin_password'])
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create admin profile
        admin_profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'receptionist',
                'organization': org,
                'phone': '+1-555-123-4567'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created admin profile'))

        # Create sample doctor
        doctor_user, created = User.objects.get_or_create(
            username='doctor1',
            defaults={
                'email': 'doctor1@pulsecal.com',
                'first_name': 'John',
                'last_name': 'Smith',
                'is_staff': False
            }
        )
        if created:
            doctor_user.set_password('doctor123')
            doctor_user.save()
            self.stdout.write(self.style.SUCCESS('Created sample doctor'))

        # Create doctor profile
        doctor_profile, created = UserProfile.objects.get_or_create(
            user=doctor_user,
            defaults={
                'role': 'doctor',
                'organization': org,
                'specialization': 'General Medicine',
                'phone': '+1-555-123-4568'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created doctor profile'))

        # Create sample patient
        patient_user, created = User.objects.get_or_create(
            username='patient1',
            defaults={
                'email': 'patient1@pulsecal.com',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'is_staff': False
            }
        )
        if created:
            patient_user.set_password('patient123')
            patient_user.save()
            self.stdout.write(self.style.SUCCESS('Created sample patient'))

        # Create patient profile
        patient_profile, created = UserProfile.objects.get_or_create(
            user=patient_user,
            defaults={
                'role': 'patient',
                'organization': org,
                'phone': '+1-555-123-4569'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created patient profile'))

        # Create logs directory
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        self.stdout.write(self.style.SUCCESS('Created logs directory'))

        # Run migrations
        self.stdout.write('Running migrations...')
        call_command('migrate', verbosity=0)

        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', verbosity=0)

        self.stdout.write(
            self.style.SUCCESS(
                '\nPulseCal system setup complete!\n'
                'Default credentials:\n'
                f'Admin: admin / {options["admin_password"]}\n'
                'Doctor: doctor1 / doctor123\n'
                'Patient: patient1 / patient123\n'
                '\nVisit http://localhost:8000 to access the system.'
            )
        ) 