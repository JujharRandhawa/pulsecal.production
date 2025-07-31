from setuptools import setup, find_packages

setup(
    name='pulsecal',
    version='2.0.0',
    description='PulseCal: Modern Django Appointment System with PostgreSQL, Analytics, and Admin Tools',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'Django>=5.2,<6.0',
        'psycopg[binary]>=3.1',
        'channels>=4.0',
        'django-allauth>=0.61',
        'Pillow>=10.0',
        'python-dotenv>=1.0',
        'google-auth-oauthlib>=1.0',
        'google-api-python-client>=2.0',
        'pandas>=2.0',
        'whitenoise>=6.0',
    ],
    python_requires='>=3.13',
) 