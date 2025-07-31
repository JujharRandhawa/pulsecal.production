# PulseCal Testing Guide

This guide covers all aspects of testing for the PulseCal SaaS application, from unit tests to production monitoring.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Types](#test-types)
3. [Running Tests](#running-tests)
4. [Test Organization](#test-organization)
5. [Writing Tests](#writing-tests)
6. [Test Data Management](#test-data-management)
7. [Continuous Integration](#continuous-integration)
8. [Performance Testing](#performance-testing)
9. [Security Testing](#security-testing)
10. [Production Monitoring](#production-monitoring)

## Testing Philosophy

### Why Testing is Essential for SaaS

1. **Reliability**: Users expect 24/7 availability
2. **Security**: Healthcare data requires strict security
3. **Compliance**: HIPAA and other regulations require audit trails
4. **Scalability**: Must handle growth without breaking
5. **User Experience**: Bugs directly impact user satisfaction

### Testing Pyramid

```
    /\
   /  \     E2E Tests (Few)
  /____\    Integration Tests (Some)
 /______\   Unit Tests (Many)
```

## Test Types

### 1. Unit Tests
- **Purpose**: Test individual functions and methods
- **Location**: `appointments/tests.py`, `appointments/test_models.py`
- **Coverage**: 80% minimum
- **Speed**: Fast (< 1 second per test)

### 2. Integration Tests
- **Purpose**: Test how components work together
- **Examples**: API endpoints, database operations
- **Location**: `appointments/tests.py::TestIntegration`

### 3. API Tests
- **Purpose**: Test REST API endpoints
- **Examples**: Appointment CRUD, authentication
- **Location**: `appointments/tests.py::TestAPIEndpoints`

### 4. Security Tests
- **Purpose**: Test authentication, authorization, vulnerabilities
- **Examples**: SQL injection, XSS, CSRF
- **Location**: `appointments/tests.py::TestSecurity`

### 5. Performance Tests
- **Purpose**: Test under load and stress
- **Examples**: Concurrent users, database queries
- **Location**: `appointments/tests.py::TestPerformance`

### 6. End-to-End Tests
- **Purpose**: Test complete user workflows
- **Examples**: Appointment booking flow
- **Location**: `appointments/tests.py::TestIntegration`

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py --all

# Run specific test types
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --security

# Run with coverage
python run_tests.py --coverage
```

### Using pytest

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest appointments/tests.py

# Run specific test class
python -m pytest appointments/tests.py::TestModels

# Run specific test method
python -m pytest appointments/tests.py::TestModels::test_appointment_creation

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=appointments --cov-report=html
```

### Using Django's test command

```bash
# Run Django tests
python manage.py test

# Run specific app
python manage.py test appointments

# Run with verbosity
python manage.py test --verbosity=2

# Run with coverage
python manage.py test --coverage
```

## Test Organization

### File Structure

```
appointments/
├── tests.py              # Main test file
├── test_models.py        # Model-specific tests
├── test_views.py         # View-specific tests
├── test_forms.py         # Form-specific tests
├── test_api.py           # API-specific tests
├── factories.py          # Test data factories
└── conftest.py           # pytest configuration
```

### Test Class Organization

```python
@pytest.mark.django_db
class TestModels:
    """Test model functionality"""
    
    def test_appointment_creation(self):
        """Test appointment creation"""
        # Test code here
    
    def test_appointment_validation(self):
        """Test appointment validation"""
        # Test code here


@pytest.mark.django_db
class TestViews:
    """Test view functionality"""
    
    def setup_method(self):
        """Set up test data"""
        self.client = Client()
        self.user = UserFactory()
    
    def test_home_view(self):
        """Test home page view"""
        # Test code here
```

## Writing Tests

### Test Naming Convention

```python
def test_what_we_are_testing_under_what_conditions():
    """Brief description of what the test does"""
    # Arrange
    user = UserFactory()
    
    # Act
    response = client.get('/dashboard/')
    
    # Assert
    assert response.status_code == 200
```

### Test Structure (AAA Pattern)

```python
def test_appointment_creation():
    """Test that appointments can be created successfully"""
    # Arrange
    patient = PatientFactory()
    doctor = DoctorFactory()
    appointment_data = {
        'patient': patient.pk,
        'doctor': doctor.pk,
        'appointment_date': '2024-01-15 10:00:00'
    }
    
    # Act
    appointment = Appointment.objects.create(**appointment_data)
    
    # Assert
    assert appointment.patient == patient
    assert appointment.doctor == doctor
    assert appointment.status == 'scheduled'
```

### Using Factories

```python
# Create test data
patient = PatientFactory()
doctor = DoctorFactory()
appointment = AppointmentFactory(patient=patient, doctor=doctor)

# Create multiple instances
patients = PatientFactory.create_batch(5)
appointments = AppointmentFactory.create_batch(10)
```

### Testing Database Operations

```python
@pytest.mark.django_db
def test_appointment_save():
    """Test appointment save operation"""
    appointment = AppointmentFactory()
    
    # Test that appointment was saved
    assert appointment.pk is not None
    
    # Test that we can retrieve it
    saved_appointment = Appointment.objects.get(pk=appointment.pk)
    assert saved_appointment == appointment
```

### Testing Views

```python
@pytest.mark.django_db
def test_dashboard_view_authenticated():
    """Test dashboard view for authenticated user"""
    # Arrange
    user = UserFactory()
    client = Client()
    client.force_login(user)
    
    # Act
    response = client.get(reverse('dashboard'))
    
    # Assert
    assert response.status_code == 200
    assert 'appointments' in response.context
```

### Testing Forms

```python
@pytest.mark.django_db
def test_appointment_form_valid():
    """Test valid appointment form"""
    # Arrange
    patient = PatientFactory()
    doctor = DoctorFactory()
    
    form_data = {
        'patient': patient.pk,
        'doctor': doctor.pk,
        'appointment_date': '2024-01-15 10:00:00'
    }
    
    # Act
    form = AppointmentForm(data=form_data)
    
    # Assert
    assert form.is_valid()
```

## Test Data Management

### Using Factories

```python
# Basic factory usage
user = UserFactory()
patient = PatientFactory(user=user)

# Factory with specific attributes
doctor = DoctorFactory(specialization='Cardiology')

# Factory with relationships
appointment = AppointmentFactory(
    patient=patient,
    doctor=doctor,
    status='confirmed'
)
```

### Creating Test Scenarios

```python
def test_complete_appointment_workflow():
    """Test complete appointment booking workflow"""
    # Create complete scenario
    scenario = CompleteAppointmentScenarioFactory.create_scenario()
    
    # Test the scenario
    assert scenario['appointment'].patient == scenario['patient']
    assert scenario['appointment'].doctor == scenario['doctor']
    assert scenario['notification'].user == scenario['patient'].user
```

### Database Transactions

```python
@pytest.mark.django_db(transaction=True)
def test_appointment_creation_with_notification():
    """Test appointment creation triggers notification"""
    # This test will use database transactions
    appointment = AppointmentFactory()
    
    # Check that notification was created
    notification = Notification.objects.filter(
        user=appointment.patient.user
    ).first()
    assert notification is not None
```

## Continuous Integration

### GitHub Actions

The CI pipeline runs on every push and pull request:

1. **Install Dependencies**
2. **Run Linting**
3. **Run Security Scan**
4. **Run Tests**
5. **Generate Coverage Report**
6. **Deploy to Staging** (if tests pass)

### Local CI Simulation

```bash
# Run the full CI pipeline locally
python run_tests.py --all
```

## Performance Testing

### Load Testing

```python
@pytest.mark.django_db
class TestLoad:
    """Test application under load"""
    
    def test_multiple_concurrent_appointments(self):
        """Test creating multiple appointments concurrently"""
        import threading
        
        def create_appointment():
            appointment = AppointmentFactory()
            return appointment
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_appointment)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
```

### Database Performance

```python
@pytest.mark.django_db
def test_appointment_query_performance():
    """Test appointment query performance"""
    # Create test data
    appointments = AppointmentFactory.create_batch(100)
    
    # Test query performance
    import time
    start_time = time.time()
    
    # Perform query
    result = Appointment.objects.filter(status='scheduled')
    
    end_time = time.time()
    assert (end_time - start_time) < 1.0  # Should complete in under 1 second
```

## Security Testing

### Authentication Tests

```python
@pytest.mark.django_db
def test_authentication_required():
    """Test that authentication is required for protected views"""
    client = Client()
    response = client.get(reverse('dashboard'))
    assert response.status_code == 302  # Redirect to login
```

### Authorization Tests

```python
@pytest.mark.django_db
def test_user_can_only_access_own_data():
    """Test that users can only access their own data"""
    user1 = UserFactory()
    user2 = UserFactory()
    
    appointment1 = AppointmentFactory(patient__user=user1)
    appointment2 = AppointmentFactory(patient__user=user2)
    
    client = Client()
    client.force_login(user1)
    
    # Should be able to access own appointment
    response1 = client.get(reverse('appointment_detail', kwargs={'pk': appointment1.pk}))
    assert response1.status_code == 200
    
    # Should not be able to access other user's appointment
    response2 = client.get(reverse('appointment_detail', kwargs={'pk': appointment2.pk}))
    assert response2.status_code == 404
```

### Vulnerability Tests

```python
@pytest.mark.django_db
def test_sql_injection_protection():
    """Test SQL injection protection"""
    malicious_input = "'; DROP TABLE appointments; --"
    
    response = client.get(f'/search-appointments/?q={malicious_input}')
    assert response.status_code == 200  # Should not crash
    
    # Check that table still exists
    appointments = Appointment.objects.all()
    assert appointments.exists()
```

## Production Monitoring

### Error Tracking

```python
# In production settings
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### Performance Monitoring

```python
# Monitor slow queries
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_slow_query_detection():
    """Test detection of slow database queries"""
    # This would be implemented in production monitoring
    pass
```

### Health Checks

```python
@pytest.mark.django_db
def test_health_check_endpoint():
    """Test health check endpoint"""
    response = client.get('/health/')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use database transactions
- Clean up after tests

### 2. Test Data
- Use factories for consistent test data
- Avoid hardcoded values
- Use realistic but fake data

### 3. Test Coverage
- Aim for 80%+ coverage
- Focus on critical paths
- Test edge cases

### 4. Test Performance
- Keep tests fast (< 1 second each)
- Use database transactions
- Mock external services

### 5. Test Maintenance
- Update tests when code changes
- Remove obsolete tests
- Keep tests simple and readable

## Common Issues and Solutions

### 1. Database Issues
```python
# Use database transactions
@pytest.mark.django_db(transaction=True)
def test_with_database():
    pass
```

### 2. Authentication Issues
```python
# Force login for tests
client.force_login(user)
```

### 3. Time-based Tests
```python
# Mock time for consistent tests
from unittest.mock import patch

@patch('django.utils.timezone.now')
def test_time_based_function(mock_now):
    mock_now.return_value = datetime(2024, 1, 1)
    # Test code here
```

### 4. External API Tests
```python
# Mock external APIs
from unittest.mock import patch

@patch('appointments.services.external_api')
def test_external_api_call(mock_api):
    mock_api.return_value = {'status': 'success'}
    # Test code here
```

## Conclusion

Testing is essential for a professional SaaS application. This guide provides the foundation for comprehensive testing that ensures reliability, security, and performance. Regular testing helps catch issues early and maintains code quality as the application grows.

Remember:
- Write tests as you write code
- Keep tests simple and focused
- Use appropriate test types for different scenarios
- Monitor test performance and coverage
- Integrate testing into your development workflow 