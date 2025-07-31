from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    UserProfile, Appointment, Organization, MedicalRecord, Prescription,
    Insurance, Payment, EmergencyContact, MedicationReminder, TelemedicineSession
)
import os
from django.conf import settings

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['org_type', 'name', 'address', 'contact_info']
        widgets = {
            'org_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter organization name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter full address'}),
            'contact_info': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone or email'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name.strip()) < 2:
            raise forms.ValidationError("Organization name must be at least 2 characters long.")
        return name.strip()

class UserProfileForm(forms.ModelForm):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    class Meta:
        model = UserProfile
        fields = ['role', 'organization', 'specialization', 'phone', 'avatar']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cardiology, Pediatrics'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-555-123-4567'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone_regex = RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
            try:
                phone_regex(phone)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid phone number.")
        return phone
    
    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (5MB limit)
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file size must be under 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if avatar.content_type not in allowed_types:
                raise forms.ValidationError("Please upload a valid image file (JPEG, PNG, or GIF).")
        
        return avatar

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['appointment_type', 'status', 'doctor', 'patient', 'appointment_date', 'notes', 'fee']
        widgets = {
            'appointment_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'appointment_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any specific concerns or information...'}),
            'fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show doctors in the dropdown
        self.fields['doctor'].queryset = User.objects.filter(profile__role='doctor')
        
        # Set minimum date to today
        today = timezone.now().date()
        min_datetime = datetime.combine(today, datetime.min.time())
        self.fields['appointment_date'].widget.attrs['min'] = min_datetime.strftime('%Y-%m-%dT%H:%M')
    
    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
            # Robust naive datetime handling
            if appointment_date.tzinfo is None:
                if getattr(settings, 'USE_TZ', False):
                    # Django interprets naive as UTC if USE_TZ
                    appointment_date = timezone.make_aware(appointment_date, timezone.utc)
                    appointment_date = appointment_date.astimezone(ist)
                else:
                    appointment_date = ist.localize(appointment_date)
            else:
                appointment_date = appointment_date.astimezone(ist)
            now_ist = timezone.now().astimezone(ist)
            if appointment_date < now_ist:
                raise forms.ValidationError("Appointment cannot be scheduled in the past.")
            self.cleaned_data['appointment_date'] = appointment_date
            return appointment_date
        return appointment_date
    
    def clean_fee(self):
        fee = self.cleaned_data.get('fee')
        if fee is not None and fee < 0:
            raise forms.ValidationError("Fee cannot be negative.")
        return fee

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        doctor = cleaned_data.get('doctor')
        instance_pk = self.instance.pk if self.instance and self.instance.pk else None
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        if appointment_date and doctor:
            # Always localize naive datetimes to IST
            if appointment_date.tzinfo is None:
                appointment_date = ist.localize(appointment_date)
                cleaned_data['appointment_date'] = appointment_date
            # Overlap logic (30 min window)
            start = appointment_date
            end = appointment_date + timedelta(minutes=30)
            overlapping = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__lt=end,
                appointment_date__gte=start - timedelta(minutes=29),
            )
            if instance_pk:
                overlapping = overlapping.exclude(pk=instance_pk)
            if overlapping.exists():
                raise forms.ValidationError("This time slot is not available for the selected doctor (overlapping appointment exists).")
        return cleaned_data

class MinimalPatientCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Please confirm your password."
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'}),
        validators=[phone_regex]
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class DoctorDutyForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['on_duty']
        widgets = {
            'on_duty': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PatientDataExportForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label="All Organizations"
    )
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        help_text="Export data from this date (optional)"
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        help_text="Export data until this date (optional)"
    )
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel (XLSX)'),
            ('pdf', 'PDF Report')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='csv',
        help_text="Choose export format"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

class AppointmentExportForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label="All Organizations"
    )
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='doctor'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label="All Doctors"
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Appointment.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        help_text="Export appointments from this date (optional)"
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        help_text="Export appointments until this date (optional)"
    )
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel (XLSX)'),
            ('pdf', 'PDF Report')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='csv',
        help_text="Choose export format"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

class AppointmentImportForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx,.xls'}),
        help_text="Upload CSV or Excel file with appointment data"
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="Select organization for imported appointments"
    )
    import_mode = forms.ChoiceField(
        choices=[
            ('preview', 'Preview Only'),
            ('import', 'Import Data')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='preview',
        help_text="Choose import mode"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB.")
            
            # Check file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError("Please upload a valid file (CSV, XLSX, or XLS).")
        
        return file

class PatientImportForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx,.xls'}),
        help_text="Upload CSV or Excel file with patient data"
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="Select organization for imported patients"
    )
    import_mode = forms.ChoiceField(
        choices=[
            ('preview', 'Preview Only'),
            ('import', 'Import Data')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='preview',
        help_text="Choose import mode"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB.")
            
            # Check file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError("Please upload a valid file (CSV, XLSX, or XLS).")
        
        return file 

class RegistrationForm(forms.Form):
    REG_TYPE_CHOICES = [
        ("patient", "Patient"),
        ("doctor_solo", "Solo Doctor"),
        ("clinic", "Clinic"),
        ("hospital", "Hospital"),
    ]
    registration_type = forms.ChoiceField(
        choices=REG_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Register as"
    )
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Organization fields (conditionally required)
    org_type = forms.ChoiceField(
        choices=Organization.ORG_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    org_name = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    org_address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def clean(self):
        cleaned_data = super().clean()
        reg_type = cleaned_data.get('registration_type')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        org_type = cleaned_data.get('org_type')
        org_name = cleaned_data.get('org_name')
        org_address = cleaned_data.get('org_address')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        # If registering as an organization, require org fields
        if reg_type in ['clinic', 'hospital', 'doctor_solo', 'solo_doctor']:
            if not org_type:
                raise forms.ValidationError("Please select an organization type.")
            if not org_name or len(org_name.strip()) < 2:
                raise forms.ValidationError("Organization name must be at least 2 characters long.")
            if not org_address or len(org_address.strip()) < 5:
                raise forms.ValidationError("Please provide a valid organization address.")
        return cleaned_data 

from django.contrib.auth import get_user_model

User = get_user_model()

class PatientForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    date_of_birth = forms.DateField()
    emergency_contact = forms.CharField(max_length=20) 

class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['record_type', 'title', 'description', 'date_recorded', 'date_occurred', 'severity', 'is_active']
        widgets = {
            'record_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter record title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description...'}),
            'date_recorded': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_occurred': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_date_occurred(self):
        date_occurred = self.cleaned_data.get('date_occurred')
        date_recorded = self.cleaned_data.get('date_recorded')
        
        if date_occurred and date_recorded and date_occurred > date_recorded:
            raise forms.ValidationError("Date occurred cannot be after date recorded.")
        
        return date_occurred

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = [
            'medication_name', 'dosage', 'frequency', 'duration', 'instructions',
            'quantity', 'refills', 'start_date', 'end_date', 'is_controlled_substance',
            'side_effects', 'contraindications'
        ]
        widgets = {
            'medication_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medication name'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500mg'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Twice daily'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7 days'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Special instructions...'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'refills': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_controlled_substance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'side_effects': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Known side effects...'}),
            'contraindications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Contraindications...'}),
        }
    
    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")
        
        return end_date

class InsuranceForm(forms.ModelForm):
    class Meta:
        model = Insurance
        fields = [
            'insurance_type', 'provider_name', 'policy_number', 'group_number',
            'subscriber_name', 'relationship_to_patient', 'effective_date',
            'expiration_date', 'copay_amount', 'deductible_amount', 'notes'
        ]
        widgets = {
            'insurance_type': forms.Select(attrs={'class': 'form-select'}),
            'provider_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Insurance provider name'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Policy number'}),
            'group_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group number (optional)'}),
            'subscriber_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subscriber name'}),
            'relationship_to_patient': forms.Select(attrs={'class': 'form-select'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'copay_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'deductible_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional notes...'}),
        }
    
    def clean_expiration_date(self):
        effective_date = self.cleaned_data.get('effective_date')
        expiration_date = self.cleaned_data.get('expiration_date')
        
        if effective_date and expiration_date and expiration_date <= effective_date:
            raise forms.ValidationError("Expiration date must be after effective date.")
        
        return expiration_date

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'payment_type', 'amount', 'payment_method', 'insurance',
            'insurance_coverage', 'patient_responsibility', 'notes'
        ]
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'insurance': forms.Select(attrs={'class': 'form-select'}),
            'insurance_coverage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'patient_responsibility': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['insurance'].queryset = Insurance.objects.filter(patient=patient, is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        insurance_coverage = cleaned_data.get('insurance_coverage', 0)
        patient_responsibility = cleaned_data.get('patient_responsibility', 0)
        
        if amount and insurance_coverage and patient_responsibility:
            total = insurance_coverage + patient_responsibility
            if abs(total - amount) > 0.01:  # Allow for small rounding differences
                raise forms.ValidationError("Insurance coverage + patient responsibility must equal total amount.")
        
        return cleaned_data

class EmergencyContactForm(forms.ModelForm):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    class Meta:
        model = EmergencyContact
        fields = ['name', 'relationship', 'phone', 'email', 'address', 'is_primary', 'can_make_medical_decisions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'relationship': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-555-123-4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address (optional)'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_make_medical_decisions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            try:
                self.phone_regex(phone)
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid phone number.")
        return phone

class MedicationReminderForm(forms.ModelForm):
    class Meta:
        model = MedicationReminder
        fields = ['reminder_type', 'time_of_day', 'days_of_week', 'is_active']
        widgets = {
            'reminder_type': forms.Select(attrs={'class': 'form-select'}),
            'time_of_day': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom widget for days of week
        self.fields['days_of_week'] = forms.MultipleChoiceField(
            choices=[
                (1, 'Monday'),
                (2, 'Tuesday'),
                (3, 'Wednesday'),
                (4, 'Thursday'),
                (5, 'Friday'),
                (6, 'Saturday'),
                (7, 'Sunday'),
            ],
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False
        )

class TelemedicineSessionForm(forms.ModelForm):
    class Meta:
        model = TelemedicineSession
        fields = ['meeting_link', 'meeting_password', 'scheduled_start', 'notes']
        widgets = {
            'meeting_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Meeting URL'}),
            'meeting_password': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meeting password (optional)'}),
            'scheduled_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Session notes...'}),
        }
    
    def clean_scheduled_start(self):
        scheduled_start = self.cleaned_data.get('scheduled_start')
        if scheduled_start and scheduled_start < timezone.now():
            raise forms.ValidationError("Scheduled start time cannot be in the past.")
        return scheduled_start 