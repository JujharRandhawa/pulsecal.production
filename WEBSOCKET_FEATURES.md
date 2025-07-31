# WebSocket and Real-time Features

This document describes the WebSocket functionality and real-time features added to the PulseCal appointment system.

## Features Added

### 1. Real-time Appointment Updates
- **WebSocket Consumer**: `AppointmentConsumer` handles real-time appointment status updates
- **URL Pattern**: `ws/appointments/{room_name}/`
- **Functionality**: 
  - Updates appointment status in real-time across all connected clients
  - Sends notifications when appointment status changes
  - Updates patient status (waiting, in consultation, done)

### 2. Real-time Notifications
- **WebSocket Consumer**: `NotificationConsumer` handles user-specific notifications
- **URL Pattern**: `ws/notifications/{user_id}/`
- **Functionality**:
  - Sends personalized notifications to users
  - Supports different notification types (appointment updates, reminders, system messages)
  - Real-time notification badges and counters
  - Mark notifications as read functionality

### 3. Real-time Chat System
- **WebSocket Consumer**: `ChatConsumer` handles real-time messaging
- **URL Pattern**: `ws/chat/{room_name}/`
- **Functionality**:
  - Real-time messaging between users
  - Support for multiple chat rooms
  - Message persistence in database
  - User-friendly chat interface

## Technical Implementation

### Django Channels Setup
```python
# settings.py
INSTALLED_APPS = [
    # ... existing apps
    'channels',
]

# Channel Layers Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        # For production, use Redis:
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {
        #     "hosts": [('127.0.0.1', 6379)],
        # },
    },
}

# ASGI Application
ASGI_APPLICATION = 'pulsecal_system.asgi.application'
```

### New Models
1. **Notification**: Stores user notifications with read status
2. **ChatRoom**: Manages chat rooms and participants
3. **ChatMessage**: Stores chat messages with timestamps

### WebSocket Consumers
- `AppointmentConsumer`: Handles appointment updates
- `NotificationConsumer`: Handles user notifications
- `ChatConsumer`: Handles real-time chat

### JavaScript Integration
- `websocket.js`: Main WebSocket manager
- `websocket.css`: Styles for notifications and chat
- Auto-reconnection logic
- Real-time UI updates

## Usage

### For Developers

#### Sending Notifications
```python
from appointments.utils import send_notification

# Send a notification to a user
send_notification(
    user_id=123,
    notification_type='appointment_update',
    title='Appointment Updated',
    message='Your appointment has been confirmed',
    data={'appointment_id': 456}
)
```

#### Sending Appointment Updates
```python
from appointments.utils import send_appointment_update

# Send appointment update to organization
send_appointment_update(
    organization_id=1,
    appointment_id=123,
    status='confirmed',
    patient_status='waiting'
)
```

#### Sending Chat Messages
```python
from appointments.utils import send_chat_message

# Send a chat message
send_chat_message(
    room_name='room_1_2',
    user_id=123,
    username='John Doe',
    message='Hello, how are you?'
)
```

### For Users

#### Notifications
- Notifications appear in real-time in the top-right corner
- Click the bell icon to view all notifications
- Mark notifications as read individually or all at once
- Notification badge shows unread count

#### Chat
- Access chat rooms from the navigation menu
- Create new chat rooms with multiple participants
- Real-time messaging with message history
- Messages are automatically saved to the database

#### Appointment Updates
- Appointment status changes are reflected immediately
- No need to refresh the page to see updates
- Real-time notifications for status changes

## Configuration

### Development Setup
1. Install dependencies:
   ```bash
   pip install channels channels-redis redis
   ```

2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Production Setup
1. Use Redis for channel layers:
   ```python
   CHANNEL_LAYERS = {
       'default': {
           'BACKEND': 'channels_redis.core.RedisChannelLayer',
           'CONFIG': {
               "hosts": [('127.0.0.1', 6379)],
           },
       },
   }
   ```

2. Install and configure Redis server

3. Use ASGI server (Daphne, uvicorn, etc.):
   ```bash
   daphne pulsecal_system.asgi:application
   ```

## Security Considerations

1. **Authentication**: WebSocket connections require user authentication
2. **Authorization**: Users can only access their own notifications and authorized chat rooms
3. **CSRF Protection**: All forms include CSRF tokens
4. **Input Validation**: All user inputs are validated server-side

## Performance Considerations

1. **Connection Limits**: Implement connection limits per user
2. **Message Rate Limiting**: Limit message frequency to prevent spam
3. **Database Optimization**: Use database indexes for frequently queried fields
4. **Caching**: Cache frequently accessed data

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if Django Channels is properly installed
   - Verify ASGI configuration
   - Check browser console for errors

2. **Notifications Not Appearing**
   - Verify user authentication
   - Check notification permissions
   - Ensure WebSocket connection is established

3. **Chat Messages Not Sending**
   - Check room permissions
   - Verify WebSocket connection
   - Check database for message storage

### Debug Mode
Enable debug logging for WebSocket issues:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'channels': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Future Enhancements

1. **File Sharing**: Add file upload capability to chat
2. **Voice/Video Calls**: Integrate WebRTC for voice/video calls
3. **Push Notifications**: Add browser push notifications
4. **Message Encryption**: End-to-end encryption for sensitive messages
5. **Message Search**: Add search functionality for chat messages
6. **Read Receipts**: Show when messages are read
7. **Typing Indicators**: Show when users are typing

## API Endpoints

### WebSocket URLs
- `ws/appointments/{room_name}/` - Appointment updates
- `ws/notifications/{user_id}/` - User notifications
- `ws/chat/{room_name}/` - Chat messages

### HTTP API Endpoints
- `POST /appointments/update-status-websocket/{id}/` - Update appointment with WebSocket
- `POST /appointments/api/send-notification/` - Send notification
- `POST /appointments/api/mark-notification-read/{id}/` - Mark notification as read
- `GET /appointments/api/unread-notifications-count/` - Get unread count
- `GET /appointments/notifications/` - View notifications page
- `GET /appointments/chat/` - Chat rooms list
- `GET /appointments/chat/{room_name}/` - Chat room 