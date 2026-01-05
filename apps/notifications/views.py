"""
Notification views for SD LMS.
"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.notifications.models import Notification, UserNotificationPreference
from apps.notifications.services import NotificationService, UserPreferenceService


@login_required
@require_GET
def notification_list(request):
    """Notification list page."""
    filter_type = request.GET.get("filter", "all")
    unread_count = NotificationService.get_unread_count(request.user)

    context = {
        "filter": filter_type,
        "unread_count": unread_count,
    }

    # Check if this is an HTMX request for the list
    if request.headers.get("HX-Request"):
        return notification_items(request)

    return render(request, "notifications/notification_list.html", context)


@login_required
@require_GET
def notification_items(request):
    """Get notification items (HTMX partial)."""
    filter_type = request.GET.get("filter", "all")
    page = request.GET.get("page", 1)

    notifications = NotificationService.get_user_notifications(
        request.user,
        unread_only=(filter_type == "unread"),
        limit=100,
    )

    paginator = Paginator(list(notifications), 20)
    page_obj = paginator.get_page(page)

    context = {
        "notifications": page_obj,
        "filter": filter_type,
    }
    return render(request, "notifications/partials/notification_items.html", context)


@login_required
@require_POST
def mark_read(request, notification_id):
    """Mark a notification as read."""
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    NotificationService.mark_as_read(notification)

    # Return updated notification item
    context = {"notification": notification}
    return render(request, "notifications/partials/notification_item_single.html", context)


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read."""
    count = NotificationService.mark_all_as_read(request.user)

    # Return refreshed list
    return notification_items(request)


@login_required
@require_GET
def unread_count(request):
    """Get unread notification count (for navbar badge)."""
    count = NotificationService.get_unread_count(request.user)

    if count > 0:
        return HttpResponse(f'<span class="badge badge-primary badge-sm">{count}</span>')
    return HttpResponse("")


@login_required
def preferences(request):
    """Notification preferences page."""
    prefs = UserPreferenceService.get_or_create_preferences(request.user)

    if request.method == "POST" or request.method == "PUT":
        # Update preferences
        updates = {
            "email_enabled": "email_enabled" in request.POST,
            "push_enabled": "push_enabled" in request.POST,
            "sms_enabled": "sms_enabled" in request.POST,
            "in_app_enabled": "in_app_enabled" in request.POST,
            "course_reminders": "course_reminders" in request.POST,
            "assessment_results": "assessment_results" in request.POST,
            "certificate_issued": "certificate_issued" in request.POST,
            "new_assignments": "new_assignments" in request.POST,
            "deadline_reminders": "deadline_reminders" in request.POST,
            "lesson_learned_updates": "lesson_learned_updates" in request.POST,
        }

        # Handle quiet hours
        quiet_start = request.POST.get("quiet_hours_start")
        quiet_end = request.POST.get("quiet_hours_end")

        if quiet_start:
            from datetime import datetime
            updates["quiet_hours_start"] = datetime.strptime(quiet_start, "%H:%M").time()
        else:
            updates["quiet_hours_start"] = None

        if quiet_end:
            from datetime import datetime
            updates["quiet_hours_end"] = datetime.strptime(quiet_end, "%H:%M").time()
        else:
            updates["quiet_hours_end"] = None

        prefs = UserPreferenceService.update_preferences(request.user, **updates)

        if request.headers.get("HX-Request"):
            # Return success message via HTMX
            return HttpResponse(
                '<div class="alert alert-success">'
                '<span>Preferencias guardadas correctamente</span>'
                '</div>'
            )

    context = {"preferences": prefs}
    return render(request, "notifications/preferences.html", context)
