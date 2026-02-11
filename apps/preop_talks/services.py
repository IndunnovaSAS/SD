"""
Business logic services for pre-operational talks.
"""

import logging
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.preop_talks.models import (
    PreopTalk,
    TalkAttachment,
    TalkAttendee,
    TalkTemplate,
)

logger = logging.getLogger(__name__)


class TalkTemplateService:
    """Service for talk template operations."""

    @staticmethod
    def get_active_templates(talk_type: str = None, activity: str = None):
        """
        Get active talk templates with optional filters.
        """
        queryset = TalkTemplate.objects.filter(is_active=True)

        if talk_type:
            queryset = queryset.filter(talk_type=talk_type)

        if activity:
            queryset = queryset.filter(target_activities__contains=[activity])

        return queryset.order_by("-created_at")

    @staticmethod
    def get_template_for_activity(activity: str):
        """
        Get the best template for a specific activity.
        """
        templates = TalkTemplate.objects.filter(
            is_active=True,
            target_activities__contains=[activity],
        ).order_by("-created_at")

        return templates.first()

    @staticmethod
    def duplicate_template(
        template: TalkTemplate,
        new_title: str = None,
        user=None,
    ) -> TalkTemplate:
        """
        Duplicate an existing template.
        """
        new_template = TalkTemplate.objects.create(
            title=new_title or f"{template.title} (Copia)",
            description=template.description,
            talk_type=template.talk_type,
            content=template.content,
            key_points=template.key_points.copy() if template.key_points else [],
            safety_topics=template.safety_topics.copy() if template.safety_topics else [],
            estimated_duration=template.estimated_duration,
            requires_signature=template.requires_signature,
            target_activities=template.target_activities.copy()
            if template.target_activities
            else [],
            is_active=True,
            created_by=user or template.created_by,
        )

        return new_template


class PreopTalkService:
    """Service for pre-operational talk operations."""

    @staticmethod
    @transaction.atomic
    def create_talk_from_template(
        template: TalkTemplate,
        conducted_by,
        project_name: str,
        location: str,
        work_activity: str,
        scheduled_at=None,
        supervisor=None,
        weather_conditions: str = "",
        special_risks: str = "",
    ) -> PreopTalk:
        """
        Create a new talk from a template.
        """
        talk = PreopTalk.objects.create(
            template=template,
            title=template.title,
            content=template.content,
            key_points=template.key_points.copy() if template.key_points else [],
            status=PreopTalk.Status.SCHEDULED,
            project_name=project_name,
            location=location,
            work_activity=work_activity,
            weather_conditions=weather_conditions,
            special_risks=special_risks,
            scheduled_at=scheduled_at or timezone.now(),
            conducted_by=conducted_by,
            supervisor=supervisor,
        )

        logger.info(f"Talk created from template: {talk.id}")
        return talk

    @staticmethod
    @transaction.atomic
    def create_custom_talk(
        title: str,
        content: str,
        conducted_by,
        project_name: str,
        location: str,
        work_activity: str,
        key_points: list = None,
        scheduled_at=None,
        supervisor=None,
        weather_conditions: str = "",
        special_risks: str = "",
    ) -> PreopTalk:
        """
        Create a custom talk without a template.
        """
        talk = PreopTalk.objects.create(
            title=title,
            content=content,
            key_points=key_points or [],
            status=PreopTalk.Status.SCHEDULED,
            project_name=project_name,
            location=location,
            work_activity=work_activity,
            weather_conditions=weather_conditions,
            special_risks=special_risks,
            scheduled_at=scheduled_at or timezone.now(),
            conducted_by=conducted_by,
            supervisor=supervisor,
        )

        logger.info(f"Custom talk created: {talk.id}")
        return talk

    @staticmethod
    def start_talk(
        talk: PreopTalk,
        gps_latitude: float = None,
        gps_longitude: float = None,
    ) -> PreopTalk:
        """
        Start a pre-operational talk.
        """
        if talk.status != PreopTalk.Status.SCHEDULED:
            raise ValueError("Solo se pueden iniciar charlas programadas")

        talk.status = PreopTalk.Status.IN_PROGRESS
        talk.started_at = timezone.now()

        if gps_latitude is not None:
            talk.gps_latitude = gps_latitude
        if gps_longitude is not None:
            talk.gps_longitude = gps_longitude

        talk.save()

        logger.info(f"Talk started: {talk.id}")
        return talk

    @staticmethod
    @transaction.atomic
    def complete_talk(
        talk: PreopTalk,
        notes: str = "",
    ) -> PreopTalk:
        """
        Complete a pre-operational talk.
        """
        if talk.status != PreopTalk.Status.IN_PROGRESS:
            raise ValueError("Solo se pueden completar charlas en progreso")

        now = timezone.now()
        talk.status = PreopTalk.Status.COMPLETED
        talk.completed_at = now
        talk.notes = notes

        if talk.started_at:
            duration = (now - talk.started_at).total_seconds() / 60
            talk.duration = int(duration)

        talk.save()

        logger.info(f"Talk completed: {talk.id}, duration: {talk.duration} min")
        return talk

    @staticmethod
    def cancel_talk(
        talk: PreopTalk,
        reason: str = "",
    ) -> PreopTalk:
        """
        Cancel a scheduled talk.
        """
        if talk.status not in [PreopTalk.Status.SCHEDULED, PreopTalk.Status.IN_PROGRESS]:
            raise ValueError("Solo se pueden cancelar charlas programadas o en progreso")

        talk.status = PreopTalk.Status.CANCELLED
        talk.notes = f"Cancelada: {reason}" if reason else "Cancelada"
        talk.save()

        logger.info(f"Talk cancelled: {talk.id}")
        return talk

    @staticmethod
    def get_today_talks(conducted_by=None):
        """
        Get talks scheduled for today.
        """
        today = timezone.localdate()
        today_start = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )
        today_end = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.max.time())
        )

        queryset = PreopTalk.objects.filter(
            scheduled_at__gte=today_start,
            scheduled_at__lte=today_end,
        ).select_related("template", "conducted_by", "supervisor")

        if conducted_by:
            queryset = queryset.filter(conducted_by=conducted_by)

        return queryset.order_by("scheduled_at")

    @staticmethod
    def get_upcoming_talks(days_ahead: int = 7, conducted_by=None):
        """
        Get upcoming talks.
        """
        now = timezone.now()
        end_date = now + timedelta(days=days_ahead)

        queryset = PreopTalk.objects.filter(
            scheduled_at__gte=now,
            scheduled_at__lte=end_date,
            status=PreopTalk.Status.SCHEDULED,
        ).select_related("template", "conducted_by")

        if conducted_by:
            queryset = queryset.filter(conducted_by=conducted_by)

        return queryset.order_by("scheduled_at")

    @staticmethod
    def get_overdue_talks():
        """
        Get talks that were scheduled but not completed.
        """
        yesterday = timezone.now() - timedelta(days=1)

        return PreopTalk.objects.filter(
            scheduled_at__lt=yesterday,
            status=PreopTalk.Status.SCHEDULED,
        ).select_related("conducted_by")

    @staticmethod
    def get_talks_by_project(project_name: str, status: str = None):
        """
        Get talks for a specific project.
        """
        queryset = PreopTalk.objects.filter(project_name__icontains=project_name).select_related(
            "template", "conducted_by"
        )

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-scheduled_at")

    @staticmethod
    def get_talk_statistics(
        start_date: date = None,
        end_date: date = None,
        project_name: str = None,
    ) -> dict:
        """
        Get talk statistics.
        """
        queryset = PreopTalk.objects.all()

        if start_date:
            queryset = queryset.filter(scheduled_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_at__date__lte=end_date)
        if project_name:
            queryset = queryset.filter(project_name__icontains=project_name)

        from django.db.models import Avg, Sum

        stats = queryset.aggregate(
            total_talks=Count("id"),
            completed_talks=Count("id", filter=Q(status=PreopTalk.Status.COMPLETED)),
            total_duration=Sum("duration"),
            avg_duration=Avg("duration"),
        )

        total_attendees = TalkAttendee.objects.filter(talk__in=queryset).count()

        return {
            "total_talks": stats["total_talks"] or 0,
            "completed_talks": stats["completed_talks"] or 0,
            "completion_rate": (
                (stats["completed_talks"] or 0) / (stats["total_talks"] or 1) * 100
            ),
            "total_duration_minutes": stats["total_duration"] or 0,
            "average_duration_minutes": float(stats["avg_duration"] or 0),
            "total_attendees": total_attendees,
        }


class TalkAttendeeService:
    """Service for talk attendee operations."""

    @staticmethod
    @transaction.atomic
    def register_attendee(
        talk: PreopTalk,
        user,
        understood_content: bool = True,
        comments: str = "",
    ) -> TalkAttendee:
        """
        Register an attendee to a talk.
        """
        attendee, created = TalkAttendee.objects.get_or_create(
            talk=talk,
            user=user,
            defaults={
                "understood_content": understood_content,
                "comments": comments,
            },
        )

        if not created:
            attendee.understood_content = understood_content
            attendee.comments = comments
            attendee.save()

        return attendee

    @staticmethod
    @transaction.atomic
    def register_multiple_attendees(
        talk: PreopTalk,
        user_ids: list,
    ) -> list:
        """
        Register multiple attendees at once.
        """
        from apps.accounts.models import User

        users = User.objects.filter(id__in=user_ids)
        attendees = []

        for user in users:
            attendee, _ = TalkAttendee.objects.get_or_create(
                talk=talk,
                user=user,
            )
            attendees.append(attendee)

        return attendees

    @staticmethod
    @transaction.atomic
    def capture_signature(
        attendee: TalkAttendee,
        signature_data,
    ) -> TalkAttendee:
        """
        Capture attendee signature.
        """
        if attendee.signed_at:
            raise ValueError("Este asistente ya firmó")

        attendee.signature = signature_data
        attendee.signed_at = timezone.now()
        attendee.save()

        logger.info(f"Signature captured for attendee {attendee.id}")
        return attendee

    @staticmethod
    def get_unsigned_attendees(talk: PreopTalk):
        """
        Get attendees who haven't signed.
        """
        return TalkAttendee.objects.filter(
            talk=talk,
            signed_at__isnull=True,
        ).select_related("user")

    @staticmethod
    def get_attendee_history(user, limit: int = 50):
        """
        Get a user's talk attendance history.
        """
        return (
            TalkAttendee.objects.filter(
                user=user,
            )
            .select_related("talk", "talk__conducted_by")
            .order_by("-talk__scheduled_at")[:limit]
        )

    @staticmethod
    def verify_attendance(
        user,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Verify a user's attendance for a date range.
        """
        attendances = TalkAttendee.objects.filter(
            user=user,
            talk__scheduled_at__date__gte=start_date,
            talk__scheduled_at__date__lte=end_date,
            talk__status=PreopTalk.Status.COMPLETED,
        ).select_related("talk")

        attended_dates = set()
        for att in attendances:
            attended_dates.add(att.talk.scheduled_at.date())

        total_days = (end_date - start_date).days + 1
        # Exclude weekends for work days calculation
        work_days = sum(
            1 for i in range(total_days) if (start_date + timedelta(days=i)).weekday() < 5
        )

        return {
            "total_attendances": attendances.count(),
            "attended_dates": list(attended_dates),
            "work_days_in_range": work_days,
            "attendance_rate": len(attended_dates) / work_days * 100 if work_days > 0 else 0,
        }


class TalkAttachmentService:
    """Service for talk attachments."""

    @staticmethod
    def add_attachment(
        talk: PreopTalk,
        file,
        file_type: str,
        original_name: str,
        description: str = "",
    ) -> TalkAttachment:
        """
        Add an attachment to a talk.
        """
        attachment = TalkAttachment.objects.create(
            talk=talk,
            file=file,
            file_type=file_type,
            original_name=original_name,
            description=description,
        )

        return attachment

    @staticmethod
    def add_group_photo(
        talk: PreopTalk,
        photo,
    ) -> TalkAttachment:
        """
        Add a group photo to a talk.
        """
        return TalkAttachmentService.add_attachment(
            talk=talk,
            file=photo,
            file_type="image",
            original_name=f"grupo_{talk.id}.jpg",
            description="Foto grupal de la charla",
        )


class TalkReportService:
    """Service for generating talk reports."""

    @staticmethod
    def generate_attendance_report(
        talk: PreopTalk,
    ) -> dict:
        """
        Generate an attendance report for a talk.
        """
        attendees = TalkAttendee.objects.filter(talk=talk).select_related("user")

        return {
            "talk_id": talk.id,
            "title": talk.title,
            "project_name": talk.project_name,
            "location": talk.location,
            "scheduled_at": talk.scheduled_at.isoformat(),
            "started_at": talk.started_at.isoformat() if talk.started_at else None,
            "completed_at": talk.completed_at.isoformat() if talk.completed_at else None,
            "duration_minutes": talk.duration,
            "conducted_by": talk.conducted_by.get_full_name() if talk.conducted_by else None,
            "supervisor": talk.supervisor.get_full_name() if talk.supervisor else None,
            "key_points": talk.key_points,
            "total_attendees": attendees.count(),
            "signed_attendees": attendees.filter(signed_at__isnull=False).count(),
            "attendees": [
                {
                    "name": att.user.get_full_name(),
                    "document": att.user.document_number,
                    "signed": att.signed_at is not None,
                    "signed_at": att.signed_at.isoformat() if att.signed_at else None,
                    "understood": att.understood_content,
                    "comments": att.comments,
                }
                for att in attendees
            ],
            "gps_location": {
                "latitude": float(talk.gps_latitude) if talk.gps_latitude else None,
                "longitude": float(talk.gps_longitude) if talk.gps_longitude else None,
            },
        }

    @staticmethod
    def generate_daily_summary(target_date: date = None) -> dict:
        """
        Generate a daily summary of all talks.
        """
        if target_date is None:
            target_date = timezone.localdate()

        day_start = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        day_end = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.max.time())
        )

        talks = (
            PreopTalk.objects.filter(
                scheduled_at__gte=day_start,
                scheduled_at__lte=day_end,
            )
            .select_related("conducted_by")
            .prefetch_related("attendees")
        )

        completed = talks.filter(status=PreopTalk.Status.COMPLETED)
        total_attendees = TalkAttendee.objects.filter(talk__in=completed).count()

        return {
            "date": target_date.isoformat(),
            "total_scheduled": talks.count(),
            "completed": completed.count(),
            "cancelled": talks.filter(status=PreopTalk.Status.CANCELLED).count(),
            "pending": talks.filter(status=PreopTalk.Status.SCHEDULED).count(),
            "total_attendees": total_attendees,
            "talks": [
                {
                    "id": talk.id,
                    "title": talk.title,
                    "project": talk.project_name,
                    "status": talk.status,
                    "attendees": talk.attendees.count(),
                    "conducted_by": talk.conducted_by.get_full_name()
                    if talk.conducted_by
                    else None,
                }
                for talk in talks
            ],
        }
