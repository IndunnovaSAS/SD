"""
Django settings for local development.
"""

from .base import *  # noqa: F403, F401

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "35.184.159.138", "34.174.86.113", "*"]

# Disable secure cookies in development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar", "django_extensions"]  # noqa: F405

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# Django Extensions
SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

# Simplified static file serving for development
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Cache to local memory in development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Use database sessions in development (simpler)
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Logging - more verbose in development
LOGGING["handlers"]["console"]["level"] = "DEBUG"  # noqa: F405
LOGGING["handlers"]["console"]["filters"] = []  # noqa: F405
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "level": "DEBUG",
    "handlers": ["console"],
}

# Disable axes in development
AXES_ENABLED = False

# Allow all CORS origins in development
CORS_ALLOW_ALL_ORIGINS = True
