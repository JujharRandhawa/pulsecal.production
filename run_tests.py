#!/usr/bin/env python
"""
Test runner script for PulseCal SaaS application.
This script provides easy access to different types of tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description or command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Error output: {e.stderr}")
        return False


def run_unit_tests():
    """Run unit tests"""
    return run_command(
        "python -m pytest appointments/tests.py -v --tb=short",
        "Unit Tests"
    )


def run_model_tests():
    """Run model tests"""
    return run_command(
        "python -m pytest appointments/test_models.py -v --tb=short",
        "Model Tests"
    )


def run_integration_tests():
    """Run integration tests"""
    return run_command(
        "python -m pytest appointments/tests.py::TestIntegration -v --tb=short",
        "Integration Tests"
    )


def run_security_tests():
    """Run security tests"""
    return run_command(
        "python -m pytest appointments/tests.py::TestSecurity -v --tb=short",
        "Security Tests"
    )


def run_performance_tests():
    """Run performance tests"""
    return run_command(
        "python -m pytest appointments/tests.py::TestPerformance -v --tb=short",
        "Performance Tests"
    )


def run_load_tests():
    """Run load tests"""
    return run_command(
        "python -m pytest appointments/tests.py::TestLoad -v --tb=short",
        "Load Tests"
    )


def run_coverage():
    """Run tests with coverage"""
    return run_command(
        "python -m pytest --cov=appointments --cov-report=html --cov-report=term-missing",
        "Coverage Report"
    )


def run_all_tests():
    """Run all tests"""
    return run_command(
        "python -m pytest --tb=short",
        "All Tests"
    )


def run_django_tests():
    """Run Django's built-in test command"""
    return run_command(
        "python manage.py test --verbosity=2",
        "Django Tests"
    )


def run_linting():
    """Run code linting"""
    return run_command(
        "python -m flake8 appointments/ --max-line-length=120 --ignore=E501,W503",
        "Code Linting"
    )


def run_security_scan():
    """Run security scanning"""
    return run_command(
        "python -m bandit -r appointments/ -f json -o security_report.json",
        "Security Scan"
    )


def main():
    """Main function to run different types of tests"""
    parser = argparse.ArgumentParser(description='PulseCal Test Runner')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--models', action='store_true', help='Run model tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--load', action='store_true', help='Run load tests')
    parser.add_argument('--coverage', action='store_true', help='Run tests with coverage')
    parser.add_argument('--django', action='store_true', help='Run Django tests')
    parser.add_argument('--lint', action='store_true', help='Run code linting')
    parser.add_argument('--scan', action='store_true', help='Run security scan')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
    
    print("PulseCal Test Runner")
    print("=" * 60)
    
    success = True
    
    if args.unit:
        success &= run_unit_tests()
    
    if args.models:
        success &= run_model_tests()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.security:
        success &= run_security_tests()
    
    if args.performance:
        success &= run_performance_tests()
    
    if args.load:
        success &= run_load_tests()
    
    if args.coverage:
        success &= run_coverage()
    
    if args.django:
        success &= run_django_tests()
    
    if args.lint:
        success &= run_linting()
    
    if args.scan:
        success &= run_security_scan()
    
    if args.all or not any(vars(args).values()):
        print("\nRunning all tests...")
        success &= run_all_tests()
        success &= run_coverage()
        success &= run_linting()
        success &= run_security_scan()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == '__main__':
    main() 