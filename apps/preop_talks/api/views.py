"""
ViewSets for pre-operational talks API.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.preop_talks.models import (
    PreopTalk,
    TalkAttendee,
    TalkTemplate,
)

from .serializers import (
    AddAttendeeSerializer,
    PreopTalkCreateSerializer,
    PreopTalkListSerializer,
    PreopTalkSerializer,
    TalkAttachmentSerializer,
    TalkAttendeeSerializer,
    TalkAttendeeSignatureSerializer,
    TalkTemplateListSerializer,
    TalkTemplateSerializer,
)


class TalkTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing talk templates."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = TalkTemplate.objects.select_related("created_by")

        # Filter by type
        talk_type = self.request.query_params.get("type")
        if talk_type:
            queryset = queryset.filter(talk_type=talk_type)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return TalkTemplateListSerializer
        return TalkTemplateSerializer


class PreopTalkViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pre-operational talks."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = PreopTalk.objects.select_related(
            "template", "conducted_by", "supervisor"
        ).prefetch_related("attendees", "attachments")

        # Filter by status
        talk_status = self.request.query_params.get("status")
        if talk_status:
            queryset = queryset.filter(status=talk_status)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(scheduled_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(scheduled_at__date__lte=date_to)

        # Filter by project
        project = self.request.query_params.get("project")
        if project:
            queryset = queryset.filter(project_name__icontains=project)

        # Filter by conductor
        conducted_by = self.request.query_params.get("conducted_by")
        if conducted_by:
            queryset = queryset.filter(conducted_by_id=conducted_by)

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(project_name__icontains=search)
                | Q(location__icontains=search)
            )

        return queryset.order_by("-scheduled_at")

    def get_serializer_class(self):
        if self.action == "list":
            return PreopTalkListSerializer
        if self.action == "create":
            return PreopTalkCreateSerializer
        return PreopTalkSerializer

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start a talk."""
        talk = self.get_object()

        if talk.status != PreopTalk.Status.SCHEDULED:
            return Response(
                {"error": "La charla no está programada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        talk.status = PreopTalk.Status.IN_PROGRESS
        talk.started_at = timezone.now()
        talk.save()

        return Response(PreopTalkSerializer(talk).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete a talk."""
        talk = self.get_object()

        if talk.status != PreopTalk.Status.IN_PROGRESS:
            return Response(
                {"error": "La charla no está en progreso"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        talk.status = PreopTalk.Status.COMPLETED
        talk.completed_at = timezone.now()

        # Calculate duration
        if talk.started_at:
            duration_seconds = (talk.completed_at - talk.started_at).total_seconds()
            talk.duration = int(duration_seconds / 60)

        talk.save()

        return Response(PreopTalkSerializer(talk).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a talk."""
        talk = self.get_object()

        if talk.status == PreopTalk.Status.COMPLETED:
            return Response(
                {"error": "No se puede cancelar una charla completada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        talk.status = PreopTalk.Status.CANCELLED
        talk.save()

        return Response(PreopTalkSerializer(talk).data)

    @action(detail=True, methods=["post"])
    def add_attendees(self, request, pk=None):
        """Add attendees to a talk."""
        talk = self.get_object()

        serializer = AddAttendeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data.get("user_ids", [])
        user_id = serializer.validated_data.get("user_id")
        if user_id:
            user_ids.append(user_id)

        if not user_ids:
            return Response(
                {"error": "Debe especificar al menos un usuario"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = User.objects.filter(id__in=user_ids, is_active=True)
        added = 0

        for user in users:
            attendee, created = TalkAttendee.objects.get_or_create(
                talk=talk,
                user=user,
            )
            if created:
                added += 1

        return Response({"added": added})

    @action(detail=True, methods=["post"])
    def remove_attendee(self, request, pk=None):
        """Remove an attendee from a talk."""
        talk = self.get_object()
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = TalkAttendee.objects.filter(
            talk=talk,
            user_id=user_id,
        ).delete()

        return Response({"removed": deleted > 0})

    @action(detail=True, methods=["get"])
    def attendees(self, request, pk=None):
        """Get talk attendees."""
        talk = self.get_object()
        attendees = talk.attendees.select_related("user").order_by("user__last_name")
        serializer = TalkAttendeeSerializer(attendees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        """Sign attendance for current user."""
        talk = self.get_object()

        if talk.status == PreopTalk.Status.CANCELLED:
            return Response(
                {"error": "La charla está cancelada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create attendee record
        attendee, created = TalkAttendee.objects.get_or_create(
            talk=talk,
            user=request.user,
        )

        if attendee.signed_at:
            return Response(
                {"error": "Ya has firmado esta charla"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TalkAttendeeSignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attendee.signature = serializer.validated_data.get("signature")
        attendee.understood_content = serializer.validated_data.get("understood_content", True)
        attendee.comments = serializer.validated_data.get("comments", "")
        attendee.signed_at = timezone.now()
        attendee.save()

        return Response(TalkAttendeeSerializer(attendee).data)

    @action(detail=True, methods=["post"])
    def add_attachment(self, request, pk=None):
        """Add an attachment to a talk."""
        talk = self.get_object()

        if talk.conducted_by != request.user and not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TalkAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(talk=talk)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def my_talks(self, request):
        """Get talks conducted by current user."""
        talks = PreopTalk.objects.filter(conducted_by=request.user).order_by("-scheduled_at")

        serializer = PreopTalkListSerializer(talks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_attendances(self, request):
        """Get talks where current user is an attendee."""
        talk_ids = TalkAttendee.objects.filter(user=request.user).values_list("talk_id", flat=True)

        talks = PreopTalk.objects.filter(id__in=talk_ids).order_by("-scheduled_at")

        serializer = PreopTalkListSerializer(talks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def today(self, request):
        """Get talks scheduled for today."""
        today = timezone.localdate()
        today_start = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )
        today_end = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.max.time())
        )
        talks = PreopTalk.objects.filter(
            scheduled_at__gte=today_start,
            scheduled_at__lte=today_end,
        ).order_by("scheduled_at")

        serializer = PreopTalkListSerializer(talks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        """Get talk report data."""
        talk = self.get_object()

        attendees = talk.attendees.select_related("user")
        signed_count = attendees.filter(signed_at__isnull=False).count()
        total_count = attendees.count()

        return Response(
            {
                "talk": PreopTalkSerializer(talk).data,
                "statistics": {
                    "total_attendees": total_count,
                    "signed": signed_count,
                    "unsigned": total_count - signed_count,
                    "sign_rate": (signed_count / total_count * 100) if total_count > 0 else 0,
                },
            }
        )
