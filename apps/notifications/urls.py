"""
URL configuration for notifications app.
"""

from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    # Notification list
    path("", views.notification_list, name="list"),
    path("items/", views.notification_items, name="items"),
    # Mark as read
    path("<int:notification_id>/read/", views.mark_read, name="mark-read"),
    path("mark-all-read/", views.mark_all_read, name="mark-all-read"),
    # Unread count (for navbar)
    path("unread-count/", views.unread_count, name="unread-count"),
    # Preferences
    path("preferences/", views.preferences, name="preferences"),
]
