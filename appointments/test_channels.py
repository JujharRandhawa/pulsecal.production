import asyncio
import json
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.db import database_sync_to_async
from channels.testing import ChannelsLiveServerTestCase
from django.urls import path
from appointments.consumers import AppointmentConsumer
from appointments.models import Appointment, UserProfile, Organization
from appointments.factories import UserFactory, UserProfileFactory, OrganizationFactory
from django.utils import timezone
from datetime import timedelta

class TestAppointmentWebSocket(ChannelsLiveServerTestCase):
    serve_static = True  # emulate StaticLiveServerTestCase

    @database_sync_to_async
    def create_users_and_appointment(self):
        org = OrganizationFactory()
        doctor_user = UserFactory()
        doctor_profile = UserProfileFactory(user=doctor_user, role='doctor', organization=org)
        receptionist_user = UserFactory()
        receptionist_profile = UserProfileFactory(user=receptionist_user, role='receptionist', organization=org)
        patient_user = UserFactory()
        patient_profile = UserProfileFactory(user=patient_user, role='patient', organization=org)
        appointment = Appointment.objects.create(
            patient=patient_user,
            doctor=doctor_user,
            organization=org,
            appointment_date=timezone.now() + timedelta(days=1),
            status='pending',
            appointment_type='new',
            fee=100.0
        )
        return doctor_user, receptionist_user, patient_user, appointment

    async def test_realtime_appointment_updates(self):
        # Set up routing for the test
        application = URLRouter([
            path('ws/appointments/', AppointmentConsumer.as_asgi()),
        ])

        doctor_user, receptionist_user, patient_user, appointment = await self.create_users_and_appointment()

        # Connect as doctor
        communicator_doctor = WebsocketCommunicator(application, '/ws/appointments/?user_id=%d' % doctor_user.id)
        connected_doctor, _ = await communicator_doctor.connect()
        assert connected_doctor

        # Connect as receptionist
        communicator_receptionist = WebsocketCommunicator(application, '/ws/appointments/?user_id=%d' % receptionist_user.id)
        connected_receptionist, _ = await communicator_receptionist.connect()
        assert connected_receptionist

        # Simulate patient booking an appointment (already created above)
        # Simulate broadcast (in real app, this would be triggered by view logic)
        channel_layer = get_channel_layer()
        update_data = {
            'type': 'appointment_update',
            'event': 'booked',
            'appointment_id': appointment.id,
            'status': appointment.status,
            'patient': appointment.patient.id,
            'doctor': appointment.doctor.id,
        }
        await channel_layer.group_send('appointments', {'type': 'appointment_update', 'data': update_data})

        # Both doctor and receptionist should receive the update
        response_doctor = await communicator_doctor.receive_json_from(timeout=5)
        response_receptionist = await communicator_receptionist.receive_json_from(timeout=5)
        assert response_doctor['data']['event'] == 'booked'
        assert response_receptionist['data']['event'] == 'booked'
        assert response_doctor['data']['appointment_id'] == appointment.id
        assert response_receptionist['data']['appointment_id'] == appointment.id

        # Simulate status update (e.g., receptionist confirms appointment)
        appointment.status = 'confirmed'
        await database_sync_to_async(appointment.save)()
        update_data_status = {
            'type': 'appointment_update',
            'event': 'status_updated',
            'appointment_id': appointment.id,
            'status': appointment.status,
            'patient': appointment.patient.id,
            'doctor': appointment.doctor.id,
        }
        await channel_layer.group_send('appointments', {'type': 'appointment_update', 'data': update_data_status})

        # Both doctor and receptionist should receive the status update
        response_doctor_status = await communicator_doctor.receive_json_from(timeout=5)
        response_receptionist_status = await communicator_receptionist.receive_json_from(timeout=5)
        assert response_doctor_status['data']['event'] == 'status_updated'
        assert response_receptionist_status['data']['event'] == 'status_updated'
        assert response_doctor_status['data']['status'] == 'confirmed'
        assert response_receptionist_status['data']['status'] == 'confirmed'

        # Clean up
        await communicator_doctor.disconnect()
        await communicator_receptionist.disconnect() 