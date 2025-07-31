// WebSocket functionality for real-time updates
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.userId = this.getUserId();
        this.organizationId = this.getOrganizationId();
    }

    getUserId() {
        // Get user ID from meta tag or data attribute
        const userIdElement = document.querySelector('meta[name="user-id"]');
        return userIdElement ? userIdElement.getAttribute('content') : null;
    }

    getOrganizationId() {
        // Get organization ID from meta tag or data attribute
        const orgIdElement = document.querySelector('meta[name="organization-id"]');
        return orgIdElement ? orgIdElement.getAttribute('content') : null;
    }

    connectAppointments() {
        if (!this.organizationId) return;

        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/appointments/org_${this.organizationId}/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('Appointment WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleAppointmentUpdate(data);
        };

        this.socket.onclose = () => {
            console.log('Appointment WebSocket disconnected');
            this.scheduleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    connectNotifications() {
        if (!this.userId) return;

        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/notifications/${this.userId}/`;
        
        this.notificationSocket = new WebSocket(wsUrl);
        
        this.notificationSocket.onopen = () => {
            console.log('Notification WebSocket connected');
        };

        this.notificationSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleNotification(data);
        };

        this.notificationSocket.onclose = () => {
            console.log('Notification WebSocket disconnected');
        };

        this.notificationSocket.onerror = (error) => {
            console.error('Notification WebSocket error:', error);
        };
    }

    connectChat(roomName) {
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/chat/${roomName}/`;
        
        this.chatSocket = new WebSocket(wsUrl);
        
        this.chatSocket.onopen = () => {
            console.log('Chat WebSocket connected');
        };

        this.chatSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleChatMessage(data);
        };

        this.chatSocket.onclose = () => {
            console.log('Chat WebSocket disconnected');
        };

        this.chatSocket.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
        };
    }

    handleAppointmentUpdate(data) {
        if (data.type === 'appointment_update') {
            // Update appointment status in the UI
            this.updateAppointmentStatus(data.appointment_id, data.status, data.patient_status);
            
            // Show notification
            this.showNotification('Appointment Update', `Appointment status changed to ${data.status}`);
        }
        if (data.type === 'doctor_status_update') {
            this.updateDoctorStatus(data.doctor_id, data.on_duty);
            this.showNotification('Doctor Availability', `Doctor availability updated.`);
        }
    }

    handleNotification(data) {
        if (data.type === 'notification') {
            this.showNotification(data.notification_type, data.message);
            this.updateNotificationBadge();
        }
    }

    handleChatMessage(data) {
        if (data.type === 'chat_message') {
            this.displayChatMessage(data);
        }
    }

    updateAppointmentStatus(appointmentId, status, patientStatus) {
        // Find appointment element and update its status
        const appointmentElement = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
        if (appointmentElement) {
            const statusElement = appointmentElement.querySelector('.appointment-status');
            const patientStatusElement = appointmentElement.querySelector('.patient-status');
            
            if (statusElement) {
                statusElement.textContent = status;
                statusElement.className = `appointment-status status-${status}`;
            }
            
            if (patientStatusElement && patientStatus) {
                patientStatusElement.textContent = patientStatus;
                patientStatusElement.className = `patient-status status-${patientStatus}`;
            }
        }
    }

    updateDoctorStatus(doctorId, onDuty) {
        // Find all elements showing this doctor's status
        const statusElements = document.querySelectorAll(`[data-doctor-id="${doctorId}"] .doctor-on-duty-badge`);
        statusElements.forEach(el => {
            if (onDuty === true || onDuty === 'true' || onDuty === 1 || onDuty === '1') {
                el.textContent = 'On Duty';
                el.className = 'badge bg-success ms-2 doctor-on-duty-badge';
            } else {
                el.textContent = 'Off Duty';
                el.className = 'badge bg-secondary ms-2 doctor-on-duty-badge';
            }
        });
    }

    showNotification(title, message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification toast';
        notification.innerHTML = `
            <div class="notification-header">
                <strong>${title}</strong>
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">&times;</button>
            </div>
            <div class="notification-body">${message}</div>
        `;

        // Add to notification container
        const container = document.getElementById('notification-container') || document.body;
        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    updateNotificationBadge() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            const currentCount = parseInt(badge.textContent || '0');
            badge.textContent = currentCount + 1;
            badge.style.display = 'block';
        }
    }

    displayChatMessage(data) {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = 'chat-message';
        messageElement.innerHTML = `
            <div class="message-header">
                <strong>${data.username}</strong>
                <small>${new Date(data.timestamp).toLocaleTimeString()}</small>
            </div>
            <div class="message-body">${data.message}</div>
        `;

        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    sendChatMessage(message) {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                message: message,
                user_id: this.userId,
                username: this.getCurrentUsername()
            }));
        }
    }

    getCurrentUsername() {
        const usernameElement = document.querySelector('meta[name="username"]');
        return usernameElement ? usernameElement.getAttribute('content') : 'Anonymous';
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connectAppointments();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
        if (this.notificationSocket) {
            this.notificationSocket.close();
        }
        if (this.chatSocket) {
            this.chatSocket.close();
        }
    }
}

// Initialize WebSocket manager
const wsManager = new WebSocketManager();

// Connect when page loads
document.addEventListener('DOMContentLoaded', () => {
    wsManager.connectAppointments();
    wsManager.connectNotifications();
});

// Connect to chat if on chat page
if (window.location.pathname.includes('/chat/')) {
    const roomName = window.location.pathname.split('/').pop();
    wsManager.connectChat(roomName);
}

// Handle chat form submission
document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    
    if (chatForm && messageInput) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                wsManager.sendChatMessage(message);
                messageInput.value = '';
            }
        });
    }
}); 