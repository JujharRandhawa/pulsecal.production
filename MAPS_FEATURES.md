# Google Maps Integration - PulseCal

## Overview

PulseCal now includes comprehensive Google Maps integration to help users find clinics, hospitals, and doctors in their area. The maps feature displays all registered healthcare providers with their locations, contact information, and availability status.

## Features

### 🗺️ Interactive Maps
- **Real-time Location Display**: Shows all registered organizations and doctors on an interactive Google Map
- **Filter Options**: Filter by organizations, doctors, on-duty status, and 24/7 services
- **Search Functionality**: Built-in search box to find specific locations
- **Responsive Design**: Works seamlessly on desktop and mobile devices

### 📍 Location Information
- **Organization Details**: Name, type, address, contact information
- **Doctor Information**: Specialization, organization, contact details, duty status
- **Interactive Markers**: Click markers to view detailed information
- **Directions**: Direct links to Google Maps for directions

### 🏥 Organization Types
- **Clinics**: General medical clinics with various specializations
- **Hospitals**: Full-service hospitals with emergency departments
- **24/7 Services**: Special markers for round-the-clock facilities
- **Verified Locations**: Status indicators for verified addresses

### 👨‍⚕️ Doctor Information
- **Specialization**: Medical field and expertise
- **Duty Status**: Real-time on/off duty indicators
- **Contact Details**: Phone, email, and direct booking links
- **Organization Affiliation**: Which clinic/hospital they work at

## Setup Instructions

### 1. Google Maps API Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable billing (required for Maps API)

2. **Enable APIs**:
   - Enable "Maps JavaScript API"
   - Enable "Places API" (for search functionality)
   - Enable "Geocoding API" (for address conversion)

3. **Create API Keys**:
   - Go to "Credentials" in the Google Cloud Console
   - Create API key for Maps JavaScript API
   - Create separate API key for Places API (optional)

4. **Restrict API Keys** (Recommended):
   - Set HTTP referrer restrictions to your domain
   - Limit to specific APIs (Maps JavaScript API, Places API)

### 2. Environment Configuration

Add your API keys to your `.env` file:

```env
# Google Maps API Settings
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

### 3. Database Setup

Run the management command to add sample location data:

```bash
python manage.py add_sample_locations
```

This will populate organizations with sample locations around New York City for testing.

### 4. Access the Maps

- **Main Maps Page**: `/maps/` - View all locations
- **Organization Detail**: `/organization/{id}/map/` - View specific organization
- **API Endpoint**: `/api/locations/` - Get location data as JSON

## Usage Guide

### For Patients

1. **Find Healthcare Providers**:
   - Navigate to "Find Locations" in the main menu
   - Use the interactive map to explore nearby clinics and hospitals
   - Filter by type (clinics vs hospitals) or services (24/7, on-duty doctors)

2. **Get Information**:
   - Click on any marker to see detailed information
   - View contact details, operating hours, and available doctors
   - Access direct links to book appointments or get directions

3. **Search and Filter**:
   - Use the search box to find specific locations
   - Filter by "On Duty" to see only available doctors
   - Filter by "24/7 Services" for emergency care options

### For Administrators

1. **Add Organization Locations**:
   - Organizations need latitude/longitude coordinates
   - Use Google Maps to get coordinates for addresses
   - Update organization records with location data

2. **Manage Doctor Locations**:
   - Doctors inherit location from their organization
   - Update doctor duty status for real-time availability
   - Ensure contact information is current

## API Endpoints

### GET /api/locations/
Returns all location data in JSON format:

```json
{
  "organizations": [
    {
      "id": 1,
      "name": "Manhattan Medical Center",
      "type": "Hospital",
      "address": "123 Broadway, New York, NY 10001",
      "phone": "+1-555-0123",
      "email": "info@manhattanmedical.com",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "is_24_hours": true,
      "specialization": "Hospital"
    }
  ],
  "doctors": [
    {
      "id": 1,
      "name": "Dr. John Smith",
      "specialization": "Cardiology",
      "organization": "Manhattan Medical Center",
      "address": "123 Broadway, New York, NY 10001",
      "phone": "+1-555-0124",
      "email": "john.smith@manhattanmedical.com",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "on_duty": true,
      "org_type": "Hospital"
    }
  ],
  "api_key": "your_api_key_here"
}
```

## Customization

### Adding Custom Markers

To add custom marker icons or colors:

1. **Update the JavaScript** in `static/js/maps.js`:
   ```javascript
   icon: {
       url: 'path/to/your/custom/icon.png',
       scaledSize: new google.maps.Size(32, 32)
   }
   ```

2. **Custom Info Windows**:
   - Modify the `createInfoWindowContent()` method
   - Add custom styling and additional information

### Styling the Map

Customize map appearance in the `initMap()` method:

```javascript
this.map = new google.maps.Map(container, {
    zoom: 12,
    center: defaultCenter,
    styles: [
        // Add custom map styles here
        {
            featureType: 'poi.medical',
            elementType: 'labels',
            stylers: [{ visibility: 'on' }]
        }
    ]
});
```

## Security Considerations

1. **API Key Protection**:
   - Never expose API keys in client-side code
   - Use environment variables for all API keys
   - Set up proper restrictions in Google Cloud Console

2. **Rate Limiting**:
   - Monitor API usage to stay within quotas
   - Implement caching for location data
   - Consider using a CDN for static map assets

3. **Data Privacy**:
   - Only display public information on maps
   - Respect user privacy settings
   - Implement proper access controls

## Troubleshooting

### Common Issues

1. **Maps Not Loading**:
   - Check API key configuration
   - Verify API is enabled in Google Cloud Console
   - Check browser console for JavaScript errors

2. **No Markers Displayed**:
   - Ensure organizations have latitude/longitude data
   - Check database for location records
   - Verify API endpoint is accessible

3. **Search Not Working**:
   - Enable Places API in Google Cloud Console
   - Check API key restrictions
   - Verify billing is enabled

### Debug Mode

Enable debug logging by adding to your Django settings:

```python
LOGGING = {
    'loggers': {
        'appointments.maps': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Performance Optimization

1. **Caching**:
   - Cache location data to reduce database queries
   - Use Redis for session storage
   - Implement browser caching for static assets

2. **Lazy Loading**:
   - Load map data asynchronously
   - Implement pagination for large datasets
   - Use clustering for many markers

3. **Mobile Optimization**:
   - Optimize for touch interactions
   - Reduce marker size on small screens
   - Implement responsive design patterns

## Future Enhancements

- **Real-time Updates**: WebSocket integration for live status updates
- **Advanced Filtering**: Filter by specialization, insurance, languages
- **Route Planning**: Built-in directions and route optimization
- **Reviews and Ratings**: Patient reviews and ratings system
- **Telemedicine Integration**: Virtual consultation markers
- **Emergency Services**: Special markers for emergency facilities

## Support

For technical support or feature requests:

1. Check the documentation in this file
2. Review the code comments in the relevant files
3. Test with the sample data provided
4. Contact the development team for assistance

---

**Note**: This feature requires a valid Google Maps API key and proper billing setup in Google Cloud Console. Make sure to follow Google's terms of service and usage guidelines. 