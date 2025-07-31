#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from django.core.management import execute_from_command_line


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
    
    # Add test configuration
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Set test-specific environment variables
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
        os.environ.setdefault('TESTING', 'True')
        
        # Add test arguments if not provided
        if len(sys.argv) == 2:
            sys.argv.extend(['--verbosity=2', '--keepdb'])
    
    try:
        execute_from_command_line(sys.argv)
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc


if __name__ == '__main__':
    main()
