# PulseCal Setup Instructions

This document provides step-by-step instructions to set up PulseCal on any machine.

## Prerequisites

- **Python 3.8 or higher**
- **PostgreSQL** (recommended) or SQLite
- **Git** (optional, for version control)

## Quick Setup (Recommended)

### Option 1: Automated Setup (Windows)
1. Double-click `start_server.bat` to run the automated setup
2. Follow the prompts
3. The server will start automatically

### Option 2: PowerShell Setup (Windows)
1. Open PowerShell in the project directory
2. Run: `.\start_server.ps1`
3. Follow the prompts

### Option 3: Python Setup Script
1. Open command prompt/terminal in the project directory
2. Run: `python setup_project.py`
3. Follow the prompts

## Manual Setup

### Step 1: Install Python Dependencies
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 2: Database Setup
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Step 3: Create Superuser
```bash
python manage.py createsuperuser
```

### Step 4: Create Sample Data (Optional)
```bash
python manage.py create_sample_data
```

### Step 5: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 6: Start the Server
```bash
python manage.py runserver
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=pulsecal_db
DB_USER=pulsecal_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# Google APIs (Optional)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
GOOGLE_PLACES_API_KEY=your-google-places-api-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'reportlab'**
   ```bash
   pip install reportlab
   ```

2. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check database credentials in `.env` file
   - For SQLite: No additional setup needed

3. **Port already in use**
   ```bash
   python manage.py runserver 8001
   ```

4. **Permission errors (Windows)**
   - Run PowerShell as Administrator
   - Or use: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

5. **Import errors**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

### Django System Checks

Run this to check for issues:
```bash
python manage.py check
```

### Database Reset (if needed)
```bash
# Remove old migrations
rm -rf appointments/migrations/0*.py

# Create fresh migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## Features

- ✅ User authentication and registration
- ✅ Role-based access (Admin, Doctor, Receptionist, Patient)
- ✅ Appointment scheduling and management
- ✅ Real-time notifications
- ✅ Google Maps integration
- ✅ Import/Export functionality (CSV, Excel, PDF)
- ✅ Chat system
- ✅ Analytics dashboard
- ✅ Mobile-responsive design

## Access URLs

- **Home**: http://127.0.0.1:8000/
- **Admin**: http://127.0.0.1:8000/admin/
- **Dashboard**: http://127.0.0.1:8000/dashboard/
- **Login**: http://127.0.0.1:8000/accounts/login/
- **Register**: http://127.0.0.1:8000/accounts/signup/

## Support

If you encounter any issues:

1. Check the logs in the `logs/` directory
2. Run `python manage.py check` for system issues
3. Ensure all dependencies are installed
4. Verify database connection
5. Check environment variables

## Development

For development, you can use:
```bash
python manage.py runserver --reload
```

This will automatically reload the server when files change. 