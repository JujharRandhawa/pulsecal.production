#!/usr/bin/env python
"""
Sample data creation script for PulseCal
This script creates sample organizations, users, and appointments for testing.
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
django.setup()

from django.contrib.auth.models import User
from appointments.models import Organization, UserProfile, Appointment
from django.utils import timezone

def create_sample_data():
    print("Creating sample data for PulseCal...")
    
    # Create organizations with location data
    organizations_data = [
        {
            'name': 'City General Hospital',
            'org_type': 'hospital',
            'address': '123 Main Street, Downtown, NY 10001',
            'city': 'New York',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '10001',
            'phone': '+1-555-0101',
            'email': 'info@citygeneral.com',
            'website': 'https://citygeneral.com',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'is_24_hours': True,
            'is_location_verified': True,
            'operating_hours': {
                'monday': {'open': '08:00', 'close': '20:00'},
                'tuesday': {'open': '08:00', 'close': '20:00'},
                'wednesday': {'open': '08:00', 'close': '20:00'},
                'thursday': {'open': '08:00', 'close': '20:00'},
                'friday': {'open': '08:00', 'close': '18:00'},
                'saturday': {'open': '09:00', 'close': '17:00'},
                'sunday': {'open': '10:00', 'close': '16:00'}
            }
        },
        {
            'name': 'Downtown Medical Clinic',
            'org_type': 'clinic',
            'address': '456 Broadway, Manhattan, NY 10013',
            'city': 'New York',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '10013',
            'phone': '+1-555-0102',
            'email': 'contact@downtownclinic.com',
            'website': 'https://downtownclinic.com',
            'latitude': 40.7589,
            'longitude': -73.9851,
            'is_24_hours': False,
            'is_location_verified': True,
            'operating_hours': {
                'monday': {'open': '09:00', 'close': '17:00'},
                'tuesday': {'open': '09:00', 'close': '17:00'},
                'wednesday': {'open': '09:00', 'close': '17:00'},
                'thursday': {'open': '09:00', 'close': '17:00'},
                'friday': {'open': '09:00', 'close': '16:00'},
                'saturday': {'open': '10:00', 'close': '14:00'},
                'sunday': {'open': 'closed', 'close': 'closed'}
            }
        },
        {
            'name': 'Brooklyn Health Center',
            'org_type': 'clinic',
            'address': '789 Atlantic Ave, Brooklyn, NY 11238',
            'city': 'Brooklyn',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '11238',
            'phone': '+1-555-0103',
            'email': 'info@brooklynhealth.com',
            'website': 'https://brooklynhealth.com',
            'latitude': 40.6782,
            'longitude': -73.9442,
            'is_24_hours': False,
            'is_location_verified': True,
            'operating_hours': {
                'monday': {'open': '08:30', 'close': '18:30'},
                'tuesday': {'open': '08:30', 'close': '18:30'},
                'wednesday': {'open': '08:30', 'close': '18:30'},
                'thursday': {'open': '08:30', 'close': '18:30'},
                'friday': {'open': '08:30', 'close': '17:30'},
                'saturday': {'open': '09:00', 'close': '15:00'},
                'sunday': {'open': 'closed', 'close': 'closed'}
            }
        },
        {
            'name': 'Queens Emergency Clinic',
            'org_type': 'clinic',
            'address': '321 Queens Blvd, Queens, NY 11101',
            'city': 'Queens',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '11101',
            'phone': '+1-555-0104',
            'email': 'emergency@queensclinic.com',
            'website': 'https://queensclinic.com',
            'latitude': 40.7505,
            'longitude': -73.9934,
            'is_24_hours': True,
            'is_location_verified': True,
            'operating_hours': {
                'monday': {'open': '00:00', 'close': '23:59'},
                'tuesday': {'open': '00:00', 'close': '23:59'},
                'wednesday': {'open': '00:00', 'close': '23:59'},
                'thursday': {'open': '00:00', 'close': '23:59'},
                'friday': {'open': '00:00', 'close': '23:59'},
                'saturday': {'open': '00:00', 'close': '23:59'},
                'sunday': {'open': '00:00', 'close': '23:59'}
            }
        },
        {
            'name': 'Manhattan Specialty Hospital',
            'org_type': 'hospital',
            'address': '555 Park Avenue, Manhattan, NY 10022',
            'city': 'New York',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '10022',
            'phone': '+1-555-0105',
            'email': 'specialty@manhattanhospital.com',
            'website': 'https://manhattanhospital.com',
            'latitude': 40.7587,
            'longitude': -73.9787,
            'is_24_hours': True,
            'is_location_verified': True,
            'operating_hours': {
                'monday': {'open': '00:00', 'close': '23:59'},
                'tuesday': {'open': '00:00', 'close': '23:59'},
                'wednesday': {'open': '00:00', 'close': '23:59'},
                'thursday': {'open': '00:00', 'close': '23:59'},
                'friday': {'open': '00:00', 'close': '23:59'},
                'saturday': {'open': '00:00', 'close': '23:59'},
                'sunday': {'open': '00:00', 'close': '23:59'}
            }
        }
    ]
    
    organizations = []
    for org_data in organizations_data:
        org, created = Organization.objects.get_or_create(
            name=org_data['name'],
            defaults=org_data
        )
        organizations.append(org)
        if created:
            print(f"Created organization: {org.name}")
        else:
            print(f"Organization already exists: {org.name}")
    
    # Create users with different roles
    users_data = [
        # Doctors
        {
            'username': 'dr.smith',
            'email': 'dr.smith@citygeneral.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'role': 'doctor',
            'organization': organizations[0],  # City General Hospital
            'specialization': 'Cardiology',
            'phone': '+1-555-0201',
            'experience_years': 15,
            'rating': 4.8,
            'consultation_fee': 150.00,
            'bio': 'Experienced cardiologist with expertise in interventional cardiology.',
            'languages': ['English', 'Spanish'],
            'certifications': ['Board Certified Cardiologist', 'Fellowship in Interventional Cardiology']
        },
        {
            'username': 'dr.johnson',
            'email': 'dr.johnson@downtownclinic.com',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'role': 'doctor',
            'organization': organizations[1],  # Downtown Medical Clinic
            'specialization': 'Pediatrics',
            'phone': '+1-555-0202',
            'experience_years': 12,
            'rating': 4.9,
            'consultation_fee': 120.00,
            'bio': 'Pediatrician specializing in child development and preventive care.',
            'languages': ['English', 'French'],
            'certifications': ['Board Certified Pediatrician', 'Child Development Specialist']
        },
        {
            'username': 'dr.williams',
            'email': 'dr.williams@brooklynhealth.com',
            'first_name': 'Michael',
            'last_name': 'Williams',
            'role': 'doctor',
            'organization': organizations[2],  # Brooklyn Health Center
            'specialization': 'Orthopedics',
            'phone': '+1-555-0203',
            'experience_years': 18,
            'rating': 4.7,
            'consultation_fee': 180.00,
            'bio': 'Orthopedic surgeon with expertise in sports medicine and joint replacement.',
            'languages': ['English', 'German'],
            'certifications': ['Board Certified Orthopedic Surgeon', 'Sports Medicine Fellowship']
        },
        {
            'username': 'dr.brown',
            'email': 'dr.brown@queensclinic.com',
            'first_name': 'Emily',
            'last_name': 'Brown',
            'role': 'doctor',
            'organization': organizations[3],  # Queens Emergency Clinic
            'specialization': 'Emergency Medicine',
            'phone': '+1-555-0204',
            'experience_years': 10,
            'rating': 4.6,
            'consultation_fee': 200.00,
            'bio': 'Emergency medicine specialist with trauma care expertise.',
            'languages': ['English', 'Spanish', 'Portuguese'],
            'certifications': ['Board Certified Emergency Medicine', 'Trauma Care Specialist']
        },
        {
            'username': 'dr.davis',
            'email': 'dr.davis@manhattanhospital.com',
            'first_name': 'David',
            'last_name': 'Davis',
            'role': 'doctor',
            'organization': organizations[4],  # Manhattan Specialty Hospital
            'specialization': 'Neurology',
            'phone': '+1-555-0205',
            'experience_years': 20,
            'rating': 4.9,
            'consultation_fee': 250.00,
            'bio': 'Neurologist specializing in stroke treatment and neurological disorders.',
            'languages': ['English', 'Italian'],
            'certifications': ['Board Certified Neurologist', 'Stroke Specialist']
        },
        # Receptionists
        {
            'username': 'receptionist1',
            'email': 'reception@citygeneral.com',
            'first_name': 'Lisa',
            'last_name': 'Anderson',
            'role': 'receptionist',
            'organization': organizations[0],
            'phone': '+1-555-0301'
        },
        {
            'username': 'receptionist2',
            'email': 'reception@downtownclinic.com',
            'first_name': 'Mark',
            'last_name': 'Thompson',
            'role': 'receptionist',
            'organization': organizations[1],
            'phone': '+1-555-0302'
        },
        # Patients
        {
            'username': 'patient1',
            'email': 'john.doe@email.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'patient',
            'phone': '+1-555-0401'
        },
        {
            'username': 'patient2',
            'email': 'jane.smith@email.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'role': 'patient',
            'phone': '+1-555-0402'
        },
        {
            'username': 'patient3',
            'email': 'robert.wilson@email.com',
            'first_name': 'Robert',
            'last_name': 'Wilson',
            'role': 'patient',
            'phone': '+1-555-0403'
        },
        {
            'username': 'patient4',
            'email': 'maria.garcia@email.com',
            'first_name': 'Maria',
            'last_name': 'Garcia',
            'role': 'patient',
            'phone': '+1-555-0404'
        },
        {
            'username': 'patient5',
            'email': 'james.lee@email.com',
            'first_name': 'James',
            'last_name': 'Lee',
            'role': 'patient',
            'phone': '+1-555-0405'
        }
    ]
    
    users = []
    for user_data in users_data:
        # Create user if doesn't exist
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name']
            }
        )
        
        if created:
            user.set_password('password123')
            user.save()
            print(f"Created user: {user.get_full_name()}")
        else:
            print(f"User already exists: {user.get_full_name()}")
        
        # Create or update profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': user_data['role'],
                'organization': user_data.get('organization'),
                'specialization': user_data.get('specialization'),
                'phone': user_data.get('phone'),
                'experience_years': user_data.get('experience_years', 0),
                'rating': user_data.get('rating', 4.5),
                'consultation_fee': user_data.get('consultation_fee', 0.00),
                'bio': user_data.get('bio', ''),
                'languages': user_data.get('languages', []),
                'certifications': user_data.get('certifications', [])
            }
        )
        
        if profile_created:
            print(f"Created profile for: {user.get_full_name()}")
        else:
            # Update existing profile with new data
            for key, value in user_data.items():
                if key != 'username' and hasattr(profile, key):
                    setattr(profile, key, value)
            profile.save()
            print(f"Updated profile for: {user.get_full_name()}")
        
        users.append(user)
    
    # Create appointments
    appointment_types = ['new', 'followup', 'emergency', 'virtual']
    statuses = ['pending', 'confirmed', 'checkedin', 'completed']
    patient_statuses = ['waiting', 'in_consultation', 'done']
    
    # Get doctors and patients
    doctors = [user for user in users if user.profile.role == 'doctor']
    patients = [user for user in users if user.profile.role == 'patient']
    
    if doctors and patients:
        # Create appointments for the next 30 days
        base_date = timezone.now()
        appointments_created = 0
        
        for i in range(50):  # Create 50 sample appointments
            # Random date within next 30 days
            days_offset = random.randint(0, 30)
            appointment_date = base_date + timedelta(days=days_offset)
            
            # Random time between 9 AM and 5 PM
            hour = random.randint(9, 17)
            minute = random.choice([0, 15, 30, 45])
            appointment_date = appointment_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Random doctor and patient
            doctor = random.choice(doctors)
            patient = random.choice(patients)
            
            # Random appointment details
            appointment_type = random.choice(appointment_types)
            status = random.choice(statuses)
            patient_status = random.choice(patient_statuses) if status in ['confirmed', 'checkedin'] else 'waiting'
            
            # Create appointment
            appointment, created = Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                defaults={
                    'status': status,
                    'patient_status': patient_status,
                    'appointment_type': appointment_type,
                    'fee': random.randint(100, 300),
                    'notes': f'Sample appointment {i+1}',
                    'organization': doctor.profile.organization
                }
            )
            
            if created:
                appointments_created += 1
        
        print(f"Created {appointments_created} appointments")
    
    print("\nSample data creation completed!")
    print("\nLogin credentials:")
    print("Admin: admin / admin123")
    print("Doctors: dr.smith, dr.johnson, dr.williams, dr.brown, dr.davis / password123")
    print("Patients: patient1, patient2, patient3, patient4, patient5 / password123")
    print("Receptionists: receptionist1, receptionist2 / password123")

if __name__ == '__main__':
    create_sample_data() 