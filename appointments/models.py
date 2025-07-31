from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid

class Organization(models.Model):
    ORG_TYPE_CHOICES = [
        ('clinic', 'Clinic'),
        ('hospital', 'Hospital'),
        ('solo_doctor', 'Solo Doctor'),
    ]
    org_type = models.CharField(max_length=15, choices=ORG_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    contact_info = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    google_places_id = models.CharField(max_length=255, blank=True, null=True)
    is_24_hours = models.BooleanField(default=False)
    is_location_verified = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    operating_hours = models.JSONField(default=dict)
    phone = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_organizations')

    def __str__(self):
        return f"{self.get_org_type_display()}: {self.name}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    specialization = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    on_duty = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    experience_years = models.PositiveIntegerField(default=0, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.50, blank=True, null=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    languages = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    next_available = models.DateTimeField(blank=True, null=True)
    total_appointments = models.PositiveIntegerField(default=0, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role} ({self.organization})"
    
    def is_patient(self):
        return self.role == 'patient'
    def is_doctor(self):
        return self.role == 'doctor'
    def is_receptionist(self):
        return self.role == 'receptionist'
    def is_admin(self):
        return self.role == 'admin'
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checkedin', 'Checked-in'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
    ]
    
    PATIENT_STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_consultation', 'In Consultation'),
        ('done', 'Done'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('new', 'New'),
        ('followup', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('virtual', 'Virtual'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    patient_status = models.CharField(max_length=20, choices=PATIENT_STATUS_CHOICES, default='waiting')
    notes = models.TextField(blank=True, null=True)
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='new')
    reception_notes = models.TextField(blank=True, null=True)
    patient_notes = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    is_virtual = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True, null=True)
    meeting_password = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.get_full_name()} - {self.appointment_date}"
    
    class Meta:
        ordering = ['-appointment_date']
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
    
    def save(self, *args, **kwargs):
        if self.appointment_type == 'virtual':
            self.is_virtual = True
        super().save(*args, **kwargs)

# New Models for Enhanced Features

class MedicalRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('allergy', 'Allergy'),
        ('condition', 'Medical Condition'),
        ('medication', 'Current Medication'),
        ('surgery', 'Surgery'),
        ('vaccination', 'Vaccination'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('note', 'Medical Note'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_records')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_recorded = models.DateField()
    date_occurred = models.DateField(blank=True, null=True)
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_medical_records')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    attachments = models.JSONField(default=list, blank=True)  # URLs to uploaded files
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.get_record_type_display()}: {self.title}"
    
    class Meta:
        ordering = ['-date_recorded']
        verbose_name = "Medical Record"
        verbose_name_plural = "Medical Records"

class Prescription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('discontinued', 'Discontinued'),
        ('expired', 'Expired'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_medications')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)  # e.g., "7 days", "1 month"
    instructions = models.TextField()
    quantity = models.PositiveIntegerField()
    refills = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    prescribed_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_controlled_substance = models.BooleanField(default=False)
    side_effects = models.TextField(blank=True, null=True)
    contraindications = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.medication_name}"
    
    class Meta:
        ordering = ['-prescribed_date']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"

class Insurance(models.Model):
    INSURANCE_TYPE_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
        ('employer', 'Employer'),
        ('medicare', 'Medicare'),
        ('medicaid', 'Medicaid'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insurance_policies')
    insurance_type = models.CharField(max_length=20, choices=INSURANCE_TYPE_CHOICES)
    provider_name = models.CharField(max_length=255)
    policy_number = models.CharField(max_length=100)
    group_number = models.CharField(max_length=100, blank=True, null=True)
    subscriber_name = models.CharField(max_length=255)
    relationship_to_patient = models.CharField(max_length=50, choices=[
        ('self', 'Self'),
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('other', 'Other'),
    ])
    effective_date = models.DateField()
    expiration_date = models.DateField()
    copay_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    deductible_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.provider_name}"
    
    class Meta:
        verbose_name = "Insurance"
        verbose_name_plural = "Insurance Policies"

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('appointment', 'Appointment Fee'),
        ('prescription', 'Prescription'),
        ('consultation', 'Consultation'),
        ('procedure', 'Procedure'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('insurance', 'Insurance'),
        ('bank_transfer', 'Bank Transfer'),
        ('digital_wallet', 'Digital Wallet'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments', blank=True, null=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_payments')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payments')
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateTimeField(blank=True, null=True)
    
    insurance = models.ForeignKey(Insurance, on_delete=models.SET_NULL, blank=True, null=True)
    insurance_coverage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    patient_responsibility = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    notes = models.TextField(blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - ${self.amount} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

class EmergencyContact(models.Model):
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    can_make_medical_decisions = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.name} ({self.get_relationship_display()})"
    
    class Meta:
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

class MedicationReminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='reminders')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medication_reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    time_of_day = models.TimeField()
    days_of_week = models.JSONField(default=list)  # [1,2,3,4,5,6,7] for days of week
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(blank=True, null=True)
    next_reminder = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.prescription.medication_name}"
    
    class Meta:
        verbose_name = "Medication Reminder"
        verbose_name_plural = "Medication Reminders"

class TelemedicineSession(models.Model):
    SESSION_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='telemedicine_session')
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    meeting_link = models.URLField()
    meeting_password = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default='scheduled')
    scheduled_start = models.DateTimeField()
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recording_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.appointment.patient.get_full_name()} - {self.session_id}"
    
    class Meta:
        verbose_name = "Telemedicine Session"
        verbose_name_plural = "Telemedicine Sessions"

class ChatRoom(models.Model):
    name = models.CharField(max_length=255)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Chat Room"
        verbose_name_plural = "Chat Rooms"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.message[:50]}"
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('appointment_created', 'Appointment Created'),
        ('appointment_updated', 'Appointment Updated'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('appointment_completed', 'Appointment Completed'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('user_registered', 'User Registered'),
        ('profile_updated', 'Profile Updated'),
        ('data_exported', 'Data Exported'),
        ('data_imported', 'Data Imported'),
        ('system_action', 'System Action'),
        ('prescription_created', 'Prescription Created'),
        ('payment_processed', 'Payment Processed'),
        ('medical_record_updated', 'Medical Record Updated'),
        ('telemedicine_session_started', 'Telemedicine Session Started'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=128, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    object_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'appointment', 'user'
    object_id = models.PositiveIntegerField(blank=True, null=True)  # ID of the related object
    user_agent = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

class DoctorOrganizationJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_join_requests')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='org_join_reviews')
    
    class Meta:
        unique_together = ('doctor', 'organization')
        verbose_name = 'Doctor Organization Join Request'
        verbose_name_plural = 'Doctor Organization Join Requests'
    
    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.organization.name} - {self.get_status_display()}"
