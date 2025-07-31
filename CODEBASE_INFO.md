# Codebase Information

## Frameworks & Libraries
- Django 5.2 (Python 3.13+)
- PostgreSQL (production database)
- Channels (WebSocket support)
- django-allauth (authentication)
- Chart.js (analytics UI)
- Bootstrap 5, FontAwesome (UI)

## Key Features
- Modern, accessible UI/UX
- Role-based dashboards (doctor, patient, receptionist, admin)
- Appointment management (book, filter, bulk actions)
- Admin tools: analytics, import/export, role management, audit logs
- Real-time notifications
- Profile management (avatar, edit, default fallback)
- Mobile-first, responsive design
- Security: CSRF, permissions, error handling

## Directory Structure
- `appointments/`: Main Django app (models, views, admin, forms, consumers)
- `pulsecal_system/`: Project settings, URLs, ASGI/WSGI
- `static/`, `templates/`: Frontend assets and HTML
- `instance/`: (legacy, can be removed)

## Environment
- See `env_example.txt` for required environment variables
- Use `.env` for local secrets

## Deployment
- Use Gunicorn/Daphne for production
- Set `DEBUG = False`, configure `ALLOWED_HOSTS`
- Use WhiteNoise or S3 for static/media files

## Notes
- No SQLite, Flask, or SQLAlchemy in use
- Allauth handles all authentication flows
- All admin tools are accessible via `/admin/analytics/` and navigation bar 