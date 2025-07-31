import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
django.setup()

from django.contrib.auth.models import User
from allauth.account.models import EmailAddress

def verify_superuser_email():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print('No superuser found!')
        return
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={'verified': True, 'primary': True}
    )
    print(f"Email for superuser '{user.username}' marked as verified!")

if __name__ == "__main__":
    verify_superuser_email() 