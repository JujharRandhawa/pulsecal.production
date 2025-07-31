from django.contrib import admin
from .models import (
    UserProfile, Appointment, Organization, ChatRoom, ChatMessage, 
    AuditLog, DoctorOrganizationJoinRequest, MedicalRecord, Prescription,
    Insurance, Payment, EmergencyContact, MedicationReminder, TelemedicineSession
)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'org_type', 'city', 'state', 'is_24_hours', 'is_location_verified']
    list_filter = ['org_type', 'is_24_hours', 'is_location_verified']
    search_fields = ['name', 'address', 'city', 'state']
    ordering = ['name']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'specialization', 'phone', 'created_at', 'on_duty']
    list_filter = ['role', 'created_at', 'on_duty']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'specialization']
    ordering = ['-created_at']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'appointment_date', 'status', 'patient_status', 'fee', 'is_virtual']
    list_filter = ['status', 'patient_status', 'appointment_date', 'created_at', 'is_virtual', 'appointment_type']
    search_fields = ['patient__username', 'doctor__username', 'notes']
    ordering = ['-appointment_date']
    date_hierarchy = 'appointment_date'

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'record_type', 'title', 'date_recorded', 'severity', 'is_active']
    list_filter = ['record_type', 'severity', 'is_active', 'date_recorded']
    search_fields = ['patient__username', 'title', 'description']
    ordering = ['-date_recorded']
    date_hierarchy = 'date_recorded'

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'medication_name', 'status', 'prescribed_date', 'is_controlled_substance']
    list_filter = ['status', 'is_controlled_substance', 'prescribed_date']
    search_fields = ['patient__username', 'doctor__username', 'medication_name']
    ordering = ['-prescribed_date']
    date_hierarchy = 'prescribed_date'

@admin.register(Insurance)
class InsuranceAdmin(admin.ModelAdmin):
    list_display = ['patient', 'insurance_type', 'provider_name', 'policy_number', 'is_active', 'effective_date']
    list_filter = ['insurance_type', 'is_active', 'effective_date', 'expiration_date']
    search_fields = ['patient__username', 'provider_name', 'policy_number']
    ordering = ['-effective_date']
    date_hierarchy = 'effective_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'payment_type', 'amount', 'status', 'payment_method', 'payment_date']
    list_filter = ['payment_type', 'status', 'payment_method', 'payment_date']
    search_fields = ['patient__username', 'doctor__username', 'transaction_id']
    ordering = ['-payment_date']
    date_hierarchy = 'payment_date'

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['patient', 'name', 'relationship', 'phone', 'is_primary', 'can_make_medical_decisions']
    list_filter = ['relationship', 'is_primary', 'can_make_medical_decisions']
    search_fields = ['patient__username', 'name', 'phone']
    ordering = ['patient__username', 'name']

@admin.register(MedicationReminder)
class MedicationReminderAdmin(admin.ModelAdmin):
    list_display = ['patient', 'prescription', 'reminder_type', 'time_of_day', 'is_active', 'next_reminder']
    list_filter = ['reminder_type', 'is_active']
    search_fields = ['patient__username', 'prescription__medication_name']
    ordering = ['-next_reminder']

@admin.register(TelemedicineSession)
class TelemedicineSessionAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'session_id', 'status', 'scheduled_start', 'actual_start', 'duration_minutes']
    list_filter = ['status', 'scheduled_start']
    search_fields = ['appointment__patient__username', 'session_id']
    ordering = ['-scheduled_start']
    date_hierarchy = 'scheduled_start'

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'room', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'message']
    ordering = ['-created_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp', 'object_type', 'object_id']
    list_filter = ['action', 'timestamp', 'object_type']
    search_fields = ['user__username', 'action', 'details']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

@admin.register(DoctorOrganizationJoinRequest)
class DoctorOrganizationJoinRequestAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'organization', 'status', 'created_at', 'reviewed_at']
    list_filter = ['status', 'created_at', 'reviewed_at']
    search_fields = ['doctor__username', 'organization__name']
    ordering = ['-created_at']
