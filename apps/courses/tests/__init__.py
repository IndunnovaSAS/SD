"""
Tests package for the courses app.

This package contains comprehensive tests for:
- Models (test_models.py)
- Services (test_services.py)
- API endpoints (test_api.py)
- Test factories (factories.py)

Usage:
    Run all course tests:
        pytest apps/courses/tests/

    Run specific test module:
        pytest apps/courses/tests/test_models.py
        pytest apps/courses/tests/test_services.py
        pytest apps/courses/tests/test_api.py

    Run specific test class:
        pytest apps/courses/tests/test_models.py::TestCourse

    Run specific test:
        pytest apps/courses/tests/test_models.py::TestCourse::test_create_course

    Run with coverage:
        pytest apps/courses/tests/ --cov=apps.courses --cov-report=html
"""
