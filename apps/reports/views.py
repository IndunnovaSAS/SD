"""
Dashboard views for SD LMS.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.models import User
from apps.certifications.models import Certificate
from apps.courses.models import Enrollment
from apps.learning_paths.models import PathAssignment
from apps.reports.services import AnalyticsService, DashboardService


@login_required
@require_GET
def admin_dashboard(request):
    """Main admin dashboard view."""
    return render(request, "dashboard/admin.html")


@login_required
@require_GET
def dashboard_stats(request):
    """Get dashboard statistics cards."""
    # Active users
    active_users = User.objects.filter(is_active=True).count()

    # Users change (vs last month)
    last_month = timezone.now() - timedelta(days=30)
    new_users_this_month = User.objects.filter(
        date_joined__gte=last_month
    ).count()
    users_change = round((new_users_this_month / max(active_users, 1)) * 100, 1)

    # Compliance rate
    compliance_data = AnalyticsService.get_compliance_report()
    compliance_rate = compliance_data.get("compliance_score", 0)

    # Courses completed
    courses_completed = Enrollment.objects.filter(
        status=Enrollment.Status.COMPLETED
    ).count()
    courses_in_progress = Enrollment.objects.filter(
        status=Enrollment.Status.IN_PROGRESS
    ).count()

    # Valid certificates
    valid_certificates = Certificate.objects.filter(
        status=Certificate.Status.ISSUED
    ).count()

    # Expiring certificates (next 30 days)
    expiring_date = timezone.now() + timedelta(days=30)
    expiring_certificates = Certificate.objects.filter(
        status=Certificate.Status.ISSUED,
        expires_at__lte=expiring_date,
        expires_at__gt=timezone.now(),
    ).count()

    context = {
        "stats": {
            "active_users": active_users,
            "users_change": users_change,
            "compliance_rate": compliance_rate,
            "courses_completed": courses_completed,
            "courses_in_progress": courses_in_progress,
            "valid_certificates": valid_certificates,
            "expiring_certificates": expiring_certificates,
        }
    }

    return render(request, "dashboard/partials/stats_cards.html", context)


@login_required
@require_GET
def compliance_chart(request):
    """Get compliance chart data."""
    # Get enrollment stats by status
    enrollments = Enrollment.objects.values("status").annotate(count=Count("id"))

    data = {
        "completed": 0,
        "in_progress": 0,
        "not_started": 0,
        "expired": 0,
    }

    for item in enrollments:
        status = item["status"]
        if status == Enrollment.Status.COMPLETED:
            data["completed"] = item["count"]
        elif status == Enrollment.Status.IN_PROGRESS:
            data["in_progress"] = item["count"]
        elif status == Enrollment.Status.NOT_STARTED:
            data["not_started"] = item["count"]
        elif status == Enrollment.Status.EXPIRED:
            data["expired"] = item["count"]

    context = {"chart_data": data}
    return render(request, "dashboard/partials/compliance_chart.html", context)


@login_required
@require_GET
def training_trend(request):
    """Get training trend chart data."""
    report = AnalyticsService.get_training_report()
    context = {"trend_data": report.get("completion_trend", [])}
    return render(request, "dashboard/partials/training_trend.html", context)


@login_required
@require_GET
def expiring_certs(request):
    """Get expiring certificates list."""
    expiring_date = timezone.now() + timedelta(days=30)
    now = timezone.now()

    certificates = Certificate.objects.filter(
        status=Certificate.Status.ISSUED,
        expires_at__lte=expiring_date,
        expires_at__gt=now,
    ).select_related("user", "course").order_by("expires_at")[:10]

    # Add days until expiry
    for cert in certificates:
        if cert.expires_at:
            cert.days_until_expiry = (cert.expires_at - now).days

    context = {"certificates": certificates}
    return render(request, "dashboard/partials/expiring_certs.html", context)


@login_required
@require_GET
def overdue_assignments(request):
    """Get overdue assignments list."""
    today = timezone.now().date()

    assignments = PathAssignment.objects.filter(
        due_date__lt=today,
        status__in=[
            PathAssignment.Status.ASSIGNED,
            PathAssignment.Status.IN_PROGRESS,
        ],
    ).select_related("user", "learning_path").order_by("due_date")[:10]

    # Add days overdue
    for assignment in assignments:
        if assignment.due_date:
            assignment.days_overdue = (today - assignment.due_date).days

    context = {"assignments": assignments}
    return render(request, "dashboard/partials/overdue_assignments.html", context)


@login_required
@require_GET
def recent_activity(request):
    """Get recent activity feed."""
    filter_type = request.GET.get("filter", "all")
    activities = []

    # Get recent enrollments
    if filter_type in ["all", "enrollments"]:
        enrollments = Enrollment.objects.select_related(
            "user", "course"
        ).order_by("-enrolled_at")[:10]

        for e in enrollments:
            activities.append({
                "type": "enrollment",
                "description": f"Se inscribió en {e.course.title}",
                "user": e.user,
                "timestamp": e.enrolled_at,
                "url": f"/courses/{e.course.id}/",
            })

    # Get recent completions
    if filter_type in ["all", "completions"]:
        completions = Enrollment.objects.filter(
            status=Enrollment.Status.COMPLETED,
            completed_at__isnull=False,
        ).select_related("user", "course").order_by("-completed_at")[:10]

        for e in completions:
            activities.append({
                "type": "completion",
                "description": f"Completó {e.course.title}",
                "user": e.user,
                "timestamp": e.completed_at,
                "url": f"/courses/{e.course.id}/",
            })

    # Get recent certifications
    if filter_type in ["all", "certifications"]:
        certs = Certificate.objects.filter(
            status=Certificate.Status.ISSUED,
        ).select_related("user", "course").order_by("-issued_at")[:10]

        for c in certs:
            activities.append({
                "type": "certification",
                "description": f"Obtuvo certificado de {c.course.title}",
                "user": c.user,
                "timestamp": c.issued_at,
                "url": f"/certifications/{c.id}/",
            })

    # Sort by timestamp
    activities.sort(key=lambda x: x["timestamp"] or timezone.now(), reverse=True)
    activities = activities[:20]

    context = {"activities": activities}
    return render(request, "dashboard/partials/recent_activity.html", context)


# ============================================================================
# Report Views
# ============================================================================

from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods

from apps.reports.models import GeneratedReport, ReportTemplate, ScheduledReport
from apps.reports.services import ReportService, ScheduledReportService


def is_staff(user):
    return user.is_staff


@login_required
@require_GET
def report_list(request):
    """Report templates list."""
    templates = ReportTemplate.objects.filter(is_active=True).order_by("name")
    context = {"templates": templates}
    return render(request, "reports/report_list.html", context)


@login_required
@require_POST
def generate_report(request, template_id):
    """Generate a report from template."""
    template = get_object_or_404(ReportTemplate, id=template_id, is_active=True)

    format_type = request.POST.get("format", template.default_format)
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")

    filters = {}
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    report = ReportService.create_report_request(
        template=template,
        user=request.user,
        format_type=format_type,
        filters=filters,
    )

    # In production, this would trigger a Celery task
    # For now, we'll return the pending report card
    context = {"reports": [report]}
    return render(request, "reports/partials/generated_reports.html", context)


@login_required
@require_GET
def my_reports(request):
    """Get user's generated reports."""
    reports = ReportService.get_user_reports(request.user, limit=20)
    context = {"reports": reports}
    return render(request, "reports/partials/generated_reports.html", context)


@login_required
@require_GET
def report_status(request, report_id):
    """Get report generation status (for polling)."""
    report = get_object_or_404(GeneratedReport, id=report_id, generated_by=request.user)

    if report.status == GeneratedReport.Status.COMPLETED:
        return render(request, "reports/partials/report_row.html", {"report": report})
    elif report.status == GeneratedReport.Status.FAILED:
        return render(request, "reports/partials/report_row.html", {"report": report})
    else:
        # Still processing
        return HttpResponse(
            f'<span class="badge badge-info gap-1" '
            f'hx-get="/reports/{report_id}/status/" '
            f'hx-trigger="every 3s" hx-swap="outerHTML">'
            f'<span class="loading loading-spinner loading-xs"></span>'
            f'Generando</span>'
        )


@login_required
@require_http_methods(["DELETE"])
def delete_report(request, report_id):
    """Delete a generated report."""
    report = get_object_or_404(GeneratedReport, id=report_id, generated_by=request.user)

    if report.file:
        report.file.delete(save=False)
    report.delete()

    return HttpResponse("")  # Empty response removes the row


@login_required
@user_passes_test(is_staff)
@require_GET
def scheduled_list(request):
    """Get scheduled reports list."""
    schedules = ScheduledReport.objects.filter(
        created_by=request.user
    ).select_related("template").order_by("-created_at")

    context = {"schedules": schedules}
    return render(request, "reports/partials/scheduled_list.html", context)


@login_required
@user_passes_test(is_staff)
@require_POST
def schedule_create(request):
    """Create a scheduled report."""
    template_id = request.POST.get("template")
    template = get_object_or_404(ReportTemplate, id=template_id)

    frequency = request.POST.get("frequency", "daily")
    time_str = request.POST.get("time_of_day", "08:00")
    recipients_str = request.POST.get("recipients", "")

    from datetime import datetime
    time_of_day = datetime.strptime(time_str, "%H:%M").time()
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    schedule = ScheduledReportService.create_schedule(
        template=template,
        name=f"{template.name} - {frequency.title()}",
        frequency=frequency,
        format_type=template.default_format,
        time_of_day=time_of_day,
        user=request.user,
        recipients=recipients,
    )

    schedules = ScheduledReport.objects.filter(
        created_by=request.user
    ).select_related("template").order_by("-created_at")

    context = {"schedules": schedules}
    return render(request, "reports/partials/scheduled_list.html", context)


@login_required
@user_passes_test(is_staff)
@require_POST
def schedule_toggle(request, schedule_id):
    """Toggle scheduled report active status."""
    schedule = get_object_or_404(ScheduledReport, id=schedule_id, created_by=request.user)
    ScheduledReportService.toggle_schedule(schedule)

    return HttpResponse(
        f'<span class="badge {"badge-success" if schedule.is_active else "badge-ghost"}">'
        f'{"Activo" if schedule.is_active else "Inactivo"}</span>'
    )
