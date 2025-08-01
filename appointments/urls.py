from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.home, name='home'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointment/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patient-dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('browse-doctors/', views.browse_doctors, name='browse_doctors'),
    path('doctor/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('schedule/', views.schedule_appointment, name='schedule'),
    path('reschedule/<int:appointment_id>/', views.reschedule_appointment, name='reschedule'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel'),
    path('appointment/<int:appointment_id>/directions/', views.appointment_directions, name='appointment_directions'),
    path('queue-status/', views.queue_status, name='queue_status'),
    path('queue-status-api/', views.queue_status_api, name='queue_status_api'),
    path('reminders/', views.reminders, name='reminders'),
    path('manage/', views.manage_appointments, name='manage'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/appointments/', views.api_appointments, name='api_appointments'),
    path('update-status/<int:appointment_id>/', views.update_appointment_status, name='update_status'),
    path('google-calendar/init/', views.google_calendar_init, name='google_calendar_init'),
    path('oauth2callback/', views.google_calendar_redirect, name='google_calendar_redirect'),
    path('google-calendar/sync/', views.google_calendar_sync, name='google_calendar_sync'),
    path('about/', views.about_page, name='about'),
    path('reception-dashboard/', views.reception_dashboard, name='reception_dashboard'),
    path('organizations/create/', views.create_organization, name='create_organization'),
    path('patients/export/', views.export_patients, name='export_patients'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    
    # Legal pages
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('copyright/', views.copyright_page, name='copyright'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('terms-conditions/', views.terms_conditions, name='terms_conditions'),
    
    # WebSocket and real-time features
    path('notifications/', views.notifications_view, name='notifications'),
    path('chat/', views.chat_rooms_view, name='chat_rooms'),
    path('chat/<str:room_name>/', views.chat_view, name='chat'),
    path('update-status-websocket/<int:appointment_id>/', views.update_appointment_status_websocket, name='update_status_websocket'),
    path('api/send-notification/', views.send_notification_api, name='send_notification_api'),
    path('api/mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('api/unread-notifications-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('manage-analytics/', views.admin_analytics, name='admin_analytics'),
    path('export-appointments/', views.export_appointments, name='export_appointments'),
    path('export-users/', views.export_users, name='export_users'),
    path('import-patients/', views.import_patients, name='import_patients'),
    path('manage-roles/', views.manage_roles, name='manage_roles'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    
    # Enhanced import/export functionality
    path('export/appointments/enhanced/', views.export_appointments_enhanced, name='export_appointments_enhanced'),
    path('import/appointments/enhanced/', views.import_appointments_enhanced, name='import_appointments_enhanced'),
    path('import/patients/enhanced/', views.import_patients_enhanced, name='import_patients_enhanced'),
    path('auto-export/appointments/', views.auto_export_appointments, name='auto_export_appointments'),
    
    # Location-based features
    path('nearby-clinics/', views.nearby_clinics, name='nearby_clinics'),
    path('search-clinics/', views.search_clinics, name='search_clinics'),
    path('clinic/<int:clinic_id>/details/', views.clinic_details_map, name='clinic_details_map'),
    path('clinic/<int:clinic_id>/appointments/', views.clinic_appointments_map, name='clinic_appointments_map'),
    path('api/user-location/', views.get_user_location, name='get_user_location'),
    
    # Maps and location features
    path('maps/', views.maps_view, name='maps'),
    path('organization/<int:org_id>/map/', views.organization_detail_map, name='organization_map'),
    path('api/locations/', views.api_locations, name='api_locations'),
    
    # Enhanced doctors map features
    path('doctors-map/', views.doctors_map, name='doctors_map'),
    path('api/doctors-map/', views.api_doctors_map, name='api_doctors_map'),
    path('doctor/<int:doctor_id>/map/', views.doctor_map_detail, name='doctor_map_detail'),
    path('register/', views.custom_register, name='custom_register'),
    path('organization/join-requests/', views.manage_org_join_requests, name='manage_org_join_requests'),
    path('search-appointments/', views.search_appointments, name='search_appointments'),
    
    # Enhanced Features - Medical Records
    path('medical-records/', views.medical_records_view, name='medical_records'),
    
    # Enhanced Features - Prescriptions
    path('prescriptions/', views.prescription_view, name='prescriptions'),
    
    # Enhanced Features - Insurance
    path('insurance/', views.insurance_view, name='insurance'),
    
    # Enhanced Features - Payments
    path('payments/', views.payment_view, name='payments'),
    
    # Enhanced Features - Emergency Contacts
    path('emergency-contacts/', views.emergency_contacts_view, name='emergency_contacts'),
    
    # Enhanced Features - Medication Reminders
    path('medication-reminders/', views.medication_reminders_view, name='medication_reminders'),
    
    # Enhanced Features - Telemedicine Sessions
    path('telemedicine-sessions/', views.telemedicine_sessions_view, name='telemedicine_sessions'),
    path('telemedicine-sessions/<int:session_id>/start/', views.start_telemedicine_session, name='start_telemedicine_session'),
    path('telemedicine-sessions/<int:session_id>/end/', views.end_telemedicine_session, name='end_telemedicine_session'),
    
    # Enhanced Features - Health Analytics
    path('health-analytics/', views.health_analytics_view, name='health_analytics'),
] 