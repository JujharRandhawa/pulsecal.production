import os
import logging
from django.conf import settings
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.utils import timezone
from notifications.signals import notify
from .models import ChatMessage, ChatRoom
from datetime import datetime

logger = logging.getLogger(__name__)

# Twilio SMS logic removed. Use notifications for all alerts.

def send_notification(user_id, notification_type, title, message, data=None):
    """
    Send a notification to a specific user via WebSocket and django-notifications-hq
    """
    try:
        user = User.objects.get(id=user_id)
        notify.send(
            sender=None,
            recipient=user,
            verb=notification_type,
            description=title,
            data={'message': message, **(data or {})}
        )
        # Send via WebSocket
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'notification_message',
                    'notification_type': notification_type,
                    'message': message,
                    'data': data or {},
                    'timestamp': timezone.now().isoformat(),
                }
            )
            logger.info(f"Notification sent to user {user_id}: {title}")
        except Exception as e:
            logger.error(f"WebSocket notification failed for user {user_id}: {e}")
        return True
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification")
        return False
    except Exception as e:
        logger.error(f"Notification creation failed: {e}")
        return False

def send_appointment_update(organization_id, appointment_id, status, patient_status=None):
    """
    Send appointment update to all users in an organization with error handling
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'appointments_org_{organization_id}',
            {
                'type': 'appointment_update',
                'appointment_id': appointment_id,
                'status': status,
                'patient_status': patient_status,
                'timestamp': timezone.now().isoformat(),
            }
        )
        logger.info(f"Appointment update sent for org {organization_id}, appointment {appointment_id}")
    except Exception as e:
        logger.error(f"Appointment update WebSocket failed: {e}")

def send_chat_message(room_name, user_id, username, message):
    """
    Send a chat message to a specific room with validation
    """
    if not message or not message.strip():
        logger.warning("Empty chat message attempted")
        return False
    
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room_name}',
            {
                'type': 'chat_message',
                'message': message.strip(),
                'user_id': user_id,
                'username': username,
                'timestamp': timezone.now().isoformat(),
            }
        )
        logger.info(f"Chat message sent to room {room_name} by {username}")
        return True
    except Exception as e:
        logger.error(f"Chat message WebSocket failed: {e}")
        return False

def create_or_get_chat_room(participants):
    """
    Create or get an existing chat room for participants with validation
    """
    if not participants:
        logger.warning("No participants provided for chat room creation")
        return None
    
    try:
        # Sort participant IDs for consistent room naming
        participant_ids = sorted([p.id if hasattr(p, 'id') else p for p in participants])
        room_name = f"room_{'_'.join(map(str, participant_ids))}"

        room, created = ChatRoom.objects.get_or_create(
            name=room_name,
            defaults={'is_active': True}
        )

        if created:
            room.participants.set(participants)
            logger.info(f"Created new chat room: {room_name}")

        return room
    except Exception as e:
        logger.error(f"Chat room creation failed: {e}")
        return None

def save_chat_message(room, sender, message):
    """
    Save a chat message to the database with validation
    """
    if not message or not message.strip():
        logger.warning("Empty chat message attempted to save")
        return None
    
    try:
        chat_message = ChatMessage.objects.create(
            room=room,
            sender=sender,
            message=message.strip()
        )
        logger.info(f"Chat message saved: {chat_message.id}")
        return chat_message
    except Exception as e:
        logger.error(f"Chat message save failed: {e}")
        return None

def log_audit_event(user, action, details='', object_type=None, object_id=None, ip_address=None, user_agent=None, level='info'):
    """
    Log audit events with enhanced tracking
    """
    try:
        from .models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=action,
            details=details,
            object_type=object_type,
            object_id=object_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if level == 'warning':
            logger.warning(f"Audit: {user} - {action} - {details}")
        elif level == 'error':
            logger.error(f"Audit: {user} - {action} - {details}")
        else:
            logger.info(f"Audit: {user} - {action} - {details}")
            
    except Exception as e:
        logger.error(f"Audit logging failed: {e}")

def log_appointment_audit(request, action, appointment, details=''):
    """
    Log appointment-specific audit events
    """
    try:
        # Get IP address from request
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else None
        
        log_audit_event(
            user=request.user if request and request.user.is_authenticated else None,
            action=action,
            details=details,
            object_type='appointment',
            object_id=appointment.id if appointment else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
    except Exception as e:
        logger.error(f"Appointment audit logging failed: {e}")

def validate_phone_number(phone):
    """
    Validate phone number format
    """
    import re
    phone_regex = re.compile(r'^\+?1?\d{9,15}$')
    return bool(phone_regex.match(phone)) if phone else False

def sanitize_message(message):
    """
    Sanitize chat messages to prevent XSS
    """
    import html
    return html.escape(message.strip())

def get_user_display_name(user):
    """
    Get user's display name safely
    """
    if user.is_authenticated:
        full_name = user.get_full_name()
        return full_name if full_name else user.username
    return "Anonymous" 

def broadcast_appointment_ws_update(appointment, event_type='update'):
    """
    Broadcast appointment update to doctor, patient, and all receptionists in the organization via WebSocket.
    event_type: 'update', 'booked', 'cancelled', etc.
    """
    from .models import UserProfile
    channel_layer = get_channel_layer()
    # Doctor
    if appointment.doctor:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{appointment.doctor.id}',
            {
                'type': 'notification_message',
                'notification_type': 'appointment_update',
                'message': f'Appointment {event_type} for you.',
                'data': {'appointment_id': appointment.id, 'event_type': event_type},
                'timestamp': timezone.now().isoformat(),
            }
        )
    # Patient
    if appointment.patient:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{appointment.patient.id}',
            {
                'type': 'notification_message',
                'notification_type': 'appointment_update',
                'message': f'Appointment {event_type} for you.',
                'data': {'appointment_id': appointment.id, 'event_type': event_type},
                'timestamp': timezone.now().isoformat(),
            }
        )
    # Receptionists in the org
    if appointment.organization:
        receptionists = UserProfile.objects.filter(organization=appointment.organization, role='receptionist')
        for rec in receptionists:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{rec.user.id}',
                {
                    'type': 'notification_message',
                    'notification_type': 'appointment_update',
                    'message': f'Appointment {event_type} in your organization.',
                    'data': {'appointment_id': appointment.id, 'event_type': event_type},
                    'timestamp': timezone.now().isoformat(),
                }
            ) 