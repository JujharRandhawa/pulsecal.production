// Maps functionality for PulseCal
class PulseCalMaps {
    constructor(apiKey, containerId) {
        this.apiKey = apiKey;
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
        this.infoWindows = [];
        this.currentFilter = 'all';
        this.mapData = {
            organizations: [],
            doctors: []
        };
    }

    async init() {
        if (!this.apiKey) {
            this.showError('Google Maps API Key not configured');
            return;
        }

        try {
            await this.loadGoogleMapsAPI();
            this.initMap();
            await this.loadLocationData();
            this.addMarkers();
        } catch (error) {
            console.error('Error initializing maps:', error);
            this.showError('Failed to load maps');
        }
    }

    loadGoogleMapsAPI() {
        return new Promise((resolve, reject) => {
            if (window.google && window.google.maps) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key=${this.apiKey}&libraries=places`;
            script.async = true;
            script.defer = true;
            
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load Google Maps API'));
            
            document.head.appendChild(script);
        });
    }

    initMap() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            throw new Error(`Container ${this.containerId} not found`);
        }

        // Default center (NYC)
        const defaultCenter = { lat: 40.7128, lng: -74.0060 };
        
        this.map = new google.maps.Map(container, {
            zoom: 12,
            center: defaultCenter,
            styles: [
                {
                    featureType: 'poi.medical',
                    elementType: 'labels',
                    stylers: [{ visibility: 'on' }]
                }
            ],
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true
        });

        // Add search box
        this.addSearchBox();
    }

    addSearchBox() {
        const input = document.createElement('input');
        input.setAttribute('placeholder', 'Search for clinics, hospitals, or doctors...');
        input.setAttribute('style', 'width: 300px; height: 40px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; margin: 10px;');
        
        const searchBox = new google.maps.places.SearchBox(input);
        this.map.controls[google.maps.ControlPosition.TOP_LEFT].push(input);
        
        this.map.addListener('bounds_changed', () => {
            searchBox.setBounds(this.map.getBounds());
        });
    }

    async loadLocationData() {
        try {
            const response = await fetch('/api/locations/');
            if (!response.ok) {
                throw new Error('Failed to load location data');
            }
            
            this.mapData = await response.json();
            
            // Update center to first location if available
            const firstLocation = this.mapData.organizations[0] || this.mapData.doctors[0];
            if (firstLocation) {
                this.map.setCenter({ lat: firstLocation.latitude, lng: firstLocation.longitude });
            }
        } catch (error) {
            console.error('Error loading location data:', error);
            // Use fallback data if API fails
            this.mapData = {
                organizations: [],
                doctors: []
            };
        }
    }

    addMarkers() {
        this.clearMarkers();

        // Add organization markers
        this.mapData.organizations.forEach(org => {
            if (this.shouldShowMarker(org, 'organization')) {
                this.addMarker(org, 'organization');
            }
        });

        // Add doctor markers
        this.mapData.doctors.forEach(doctor => {
            if (this.shouldShowMarker(doctor, 'doctor')) {
                this.addMarker(doctor, 'doctor');
            }
        });

        this.updateCount();
    }

    addMarker(item, type) {
        const position = { lat: item.latitude, lng: item.longitude };
        
        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            title: item.name,
            icon: {
                url: type === 'organization' 
                    ? 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'
                    : 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            }
        });

        const infoWindow = new google.maps.InfoWindow({
            content: this.createInfoWindowContent(item, type)
        });

        marker.addListener('click', () => {
            // Close all other info windows
            this.infoWindows.forEach(iw => iw.close());
            infoWindow.open(this.map, marker);
        });

        this.markers.push(marker);
        this.infoWindows.push(infoWindow);
    }

    createInfoWindowContent(item, type) {
        if (type === 'organization') {
            return `
                <div style="padding: 10px; max-width: 300px;">
                    <h4 style="color: #dc3545; margin-bottom: 10px;">🏥 ${item.name}</h4>
                    <p><strong>Type:</strong> ${item.type}</p>
                    <p><strong>Address:</strong> ${item.address}</p>
                    <p><strong>Phone:</strong> ${item.phone || 'N/A'}</p>
                    <p><strong>Email:</strong> ${item.email || 'N/A'}</p>
                    ${item.is_24_hours ? '<p><span style="background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem;">24/7 Service</span></p>' : ''}
                    <p><strong>Specialization:</strong> ${item.specialization}</p>
                    <a href="/organization/${item.id}/map/" class="btn btn-sm btn-primary">View Details</a>
                </div>
            `;
        } else {
            return `
                <div style="padding: 10px; max-width: 300px;">
                    <h4 style="color: #007bff; margin-bottom: 10px;">👨‍⚕️ ${item.name}</h4>
                    <p><strong>Specialization:</strong> ${item.specialization}</p>
                    <p><strong>Organization:</strong> ${item.organization}</p>
                    <p><strong>Address:</strong> ${item.address}</p>
                    <p><strong>Phone:</strong> ${item.phone || 'N/A'}</p>
                    <p><strong>Email:</strong> ${item.email || 'N/A'}</p>
                    ${item.on_duty ? '<p><span style="background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem;">On Duty</span></p>' : ''}
                    <a href="/doctor/${item.id}/" class="btn btn-sm btn-primary">View Profile</a>
                </div>
            `;
        }
    }

    shouldShowMarker(item, type) {
        switch (this.currentFilter) {
            case 'all':
                return true;
            case 'organizations':
                return type === 'organization';
            case 'doctors':
                return type === 'doctor';
            case 'on_duty':
                return item.on_duty;
            case '24_hours':
                return item.is_24_hours;
            default:
                return true;
        }
    }

    clearMarkers() {
        this.markers.forEach(marker => marker.setMap(null));
        this.infoWindows.forEach(iw => iw.close());
        this.markers = [];
        this.infoWindows = [];
    }

    setFilter(filter) {
        this.currentFilter = filter;
        this.addMarkers();
    }

    updateCount() {
        const countElement = document.getElementById('total-count');
        if (countElement) {
            countElement.textContent = this.markers.length;
        }
    }

    showError(message) {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = `
                <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #6c757d;">
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle fa-3x mb-3"></i><br>
                        ${message}
                    </div>
                </div>
            `;
        }
    }
}

// Global functions for filter buttons
function showAll() {
    if (window.pulseCalMaps) {
        window.pulseCalMaps.setFilter('all');
        updateFilterButtons('all');
    }
}

function showOrganizations() {
    if (window.pulseCalMaps) {
        window.pulseCalMaps.setFilter('organizations');
        updateFilterButtons('organizations');
    }
}

function showDoctors() {
    if (window.pulseCalMaps) {
        window.pulseCalMaps.setFilter('doctors');
        updateFilterButtons('doctors');
    }
}

function showOnDuty() {
    if (window.pulseCalMaps) {
        window.pulseCalMaps.setFilter('on_duty');
        updateFilterButtons('on_duty');
    }
}

function show24Hours() {
    if (window.pulseCalMaps) {
        window.pulseCalMaps.setFilter('24_hours');
        updateFilterButtons('24_hours');
    }
}

function updateFilterButtons(activeFilter) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
} 