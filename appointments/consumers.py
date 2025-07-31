import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Appointment, UserProfile
from datetime import datetime

class AppointmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'appointments_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'update')
        
        if message_type == 'appointment_update':
            appointment_id = text_data_json.get('appointment_id')
            status = text_data_json.get('status')
            patient_status = text_data_json.get('patient_status')
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'appointment_update',
                    'appointment_id': appointment_id,
                    'status': status,
                    'patient_status': patient_status,
                    'timestamp': datetime.now().isoformat(),
                }
            )
        elif message_type == 'doctor_status_update':
            doctor_id = text_data_json.get('doctor_id')
            on_duty = text_data_json.get('on_duty')
            # Broadcast doctor status update to the org group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'doctor_status_update',
                    'doctor_id': doctor_id,
                    'on_duty': on_duty,
                    'timestamp': datetime.now().isoformat(),
                }
            )

    # Receive message from room group
    async def appointment_update(self, event):
        appointment_id = event['appointment_id']
        status = event['status']
        patient_status = event['patient_status']
        timestamp = event['timestamp']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'appointment_update',
            'appointment_id': appointment_id,
            'status': status,
            'patient_status': patient_status,
            'timestamp': timestamp,
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'notification')
        
        if message_type == 'mark_read':
            notification_id = text_data_json.get('notification_id')
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'notification_read',
                    'notification_id': notification_id,
                }
            )

    # Receive message from room group
    async def notification_message(self, event):
        notification_type = event['notification_type']
        message = event['message']
        data = event.get('data', {})
        timestamp = event['timestamp']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': notification_type,
            'message': message,
            'data': data,
            'timestamp': timestamp,
        }))

    async def notification_read(self, event):
        notification_id = event['notification_id']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification_read',
            'notification_id': notification_id,
        }))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user_id = text_data_json.get('user_id')
        username = text_data_json.get('username', 'Anonymous')

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now().isoformat(),
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        user_id = event['user_id']
        username = event['username']
        timestamp = event['timestamp']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'user_id': user_id,
            'username': username,
            'timestamp': timestamp,
        })) 

    async def doctor_status_update(self, event):
        doctor_id = event['doctor_id']
        on_duty = event['on_duty']
        timestamp = event['timestamp']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'doctor_status_update',
            'doctor_id': doctor_id,
            'on_duty': on_duty,
            'timestamp': timestamp,
        })) 