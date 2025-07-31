from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from appointments.models import UserProfile, Organization
from decimal import Decimal
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Add sample doctors with enhanced data for the doctors map'

    def handle(self, *args, **options):
        self.stdout.write('Adding sample doctors with enhanced data...')
        
        # Get existing organizations
        organizations = Organization.objects.all()
        if not organizations.exists():
            self.stdout.write(self.style.ERROR('No organizations found. Please run add_sample_data first.'))
            return
        
        # Sample doctor data with enhanced information
        doctors_data = [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@healthcare.com',
                'specialization': 'Cardiology',
                'experience_years': 15,
                'rating': 4.8,
                'consultation_fee': 150.00,
                'bio': 'Experienced cardiologist with expertise in interventional cardiology and heart disease prevention.',
                'languages': ['English', 'Spanish'],
                'certifications': ['Board Certified Cardiologist', 'Fellowship in Interventional Cardiology'],
                'on_duty': True
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@healthcare.com',
                'specialization': 'Pediatrics',
                'experience_years': 12,
                'rating': 4.9,
                'consultation_fee': 120.00,
                'bio': 'Dedicated pediatrician with a passion for children\'s health and development.',
                'languages': ['English', 'French'],
                'certifications': ['Board Certified Pediatrician', 'Child Development Specialist'],
                'on_duty': True
            },
            {
                'first_name': 'Michael',
                'last_name': 'Chen',
                'email': 'michael.chen@healthcare.com',
                'specialization': 'Orthopedics',
                'experience_years': 18,
                'rating': 4.7,
                'consultation_fee': 180.00,
                'bio': 'Specialist in sports medicine and joint replacement surgery.',
                'languages': ['English', 'Mandarin'],
                'certifications': ['Board Certified Orthopedic Surgeon', 'Sports Medicine Fellowship'],
                'on_duty': False
            },
            {
                'first_name': 'Emily',
                'last_name': 'Davis',
                'email': 'emily.davis@healthcare.com',
                'specialization': 'Dermatology',
                'experience_years': 10,
                'rating': 4.6,
                'consultation_fee': 140.00,
                'bio': 'Expert in medical and cosmetic dermatology with focus on skin cancer prevention.',
                'languages': ['English', 'German'],
                'certifications': ['Board Certified Dermatologist', 'Cosmetic Dermatology Fellowship'],
                'on_duty': True
            },
            {
                'first_name': 'David',
                'last_name': 'Wilson',
                'email': 'david.wilson@healthcare.com',
                'specialization': 'Neurology',
                'experience_years': 20,
                'rating': 4.9,
                'consultation_fee': 200.00,
                'bio': 'Neurologist specializing in stroke treatment and neurological disorders.',
                'languages': ['English', 'Portuguese'],
                'certifications': ['Board Certified Neurologist', 'Stroke Specialist'],
                'on_duty': True
            },
            {
                'first_name': 'Lisa',
                'last_name': 'Brown',
                'email': 'lisa.brown@healthcare.com',
                'specialization': 'Psychiatry',
                'experience_years': 14,
                'rating': 4.5,
                'consultation_fee': 160.00,
                'bio': 'Psychiatrist with expertise in anxiety, depression, and mood disorders.',
                'languages': ['English', 'Italian'],
                'certifications': ['Board Certified Psychiatrist', 'Child and Adolescent Psychiatry'],
                'on_duty': False
            },
            {
                'first_name': 'Robert',
                'last_name': 'Taylor',
                'email': 'robert.taylor@healthcare.com',
                'specialization': 'General Surgery',
                'experience_years': 16,
                'rating': 4.8,
                'consultation_fee': 175.00,
                'bio': 'General surgeon with extensive experience in minimally invasive procedures.',
                'languages': ['English', 'Spanish'],
                'certifications': ['Board Certified General Surgeon', 'Minimally Invasive Surgery'],
                'on_duty': True
            },
            {
                'first_name': 'Jennifer',
                'last_name': 'Garcia',
                'email': 'jennifer.garcia@healthcare.com',
                'specialization': 'Obstetrics & Gynecology',
                'experience_years': 13,
                'rating': 4.7,
                'consultation_fee': 145.00,
                'bio': 'OB/GYN specialist providing comprehensive women\'s healthcare services.',
                'languages': ['English', 'Spanish'],
                'certifications': ['Board Certified OB/GYN', 'High-Risk Pregnancy Specialist'],
                'on_duty': True
            },
            {
                'first_name': 'James',
                'last_name': 'Miller',
                'email': 'james.miller@healthcare.com',
                'specialization': 'Emergency Medicine',
                'experience_years': 11,
                'rating': 4.4,
                'consultation_fee': 130.00,
                'bio': 'Emergency medicine physician with experience in trauma and critical care.',
                'languages': ['English', 'Arabic'],
                'certifications': ['Board Certified Emergency Medicine', 'Trauma Specialist'],
                'on_duty': True
            },
            {
                'first_name': 'Maria',
                'last_name': 'Rodriguez',
                'email': 'maria.rodriguez@healthcare.com',
                'specialization': 'Family Medicine',
                'experience_years': 9,
                'rating': 4.6,
                'consultation_fee': 110.00,
                'bio': 'Family medicine physician providing comprehensive primary care for all ages.',
                'languages': ['English', 'Spanish', 'Portuguese'],
                'certifications': ['Board Certified Family Medicine', 'Primary Care Specialist'],
                'on_duty': True
            }
        ]
        
        doctors_created = 0
        
        for i, doctor_data in enumerate(doctors_data):
            # Create user
            username = f"doctor_{doctor_data['first_name'].lower()}_{doctor_data['last_name'].lower()}"
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'Doctor {doctor_data["first_name"]} {doctor_data["last_name"]} already exists, skipping...')
                continue
            
            user = User.objects.create_user(
                username=username,
                email=doctor_data['email'],
                password='doctor123',
                first_name=doctor_data['first_name'],
                last_name=doctor_data['last_name']
            )
            
            # Assign to a random organization
            organization = random.choice(organizations)
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role='doctor',
                organization=organization,
                specialization=doctor_data['specialization'],
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                on_duty=doctor_data['on_duty'],
                experience_years=doctor_data['experience_years'],
                rating=Decimal(str(doctor_data['rating'])),
                consultation_fee=Decimal(str(doctor_data['consultation_fee'])),
                bio=doctor_data['bio'],
                languages=doctor_data['languages'],
                certifications=doctor_data['certifications'],
                next_available=datetime.now() + timedelta(days=random.randint(1, 7)) if doctor_data['on_duty'] else None,
                total_appointments=random.randint(50, 500)
            )
            
            doctors_created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created Dr. {doctor_data["first_name"]} {doctor_data["last_name"]} - {doctor_data["specialization"]} at {organization.name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {doctors_created} doctors with enhanced data!'
            )
        )
        
        # Display summary
        total_doctors = UserProfile.objects.filter(role='doctor').count()
        on_duty_doctors = UserProfile.objects.filter(role='doctor', on_duty=True).count()
        
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'- Total doctors: {total_doctors}')
        self.stdout.write(f'- On duty: {on_duty_doctors}')
        self.stdout.write(f'- Available for map: {UserProfile.objects.filter(role="doctor", organization__latitude__isnull=False).exclude(organization__latitude=0).count()}') 