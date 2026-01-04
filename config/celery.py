"""
Celery configuration for SD LMS project.
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("sd_lms")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure task queues
app.conf.task_queues = {
    "high_priority": {
        "exchange": "high_priority",
        "routing_key": "high_priority",
    },
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "reports": {
        "exchange": "reports",
        "routing_key": "reports",
    },
    "media": {
        "exchange": "media",
        "routing_key": "media",
    },
    "sync": {
        "exchange": "sync",
        "routing_key": "sync",
    },
    "notifications": {
        "exchange": "notifications",
        "routing_key": "notifications",
    },
}

# Task routing
app.conf.task_routes = {
    "apps.notifications.tasks.*": {"queue": "notifications"},
    "apps.reports.tasks.*": {"queue": "reports"},
    "apps.courses.tasks.process_*": {"queue": "media"},
    "apps.sync.tasks.*": {"queue": "sync"},
}

# Default queue
app.conf.task_default_queue = "default"


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
