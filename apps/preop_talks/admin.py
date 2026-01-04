"""
Admin configuration for preop_talks app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import PreopTalk, TalkAttachment, TalkAttendee, TalkTemplate


class TalkAttendeeInline(admin.TabularInline):
    """Inline for attendees in talk admin."""

    model = TalkAttendee
    extra = 1
    raw_id_fields = ["user"]
    readonly_fields = ["signed_at"]


class TalkAttachmentInline(admin.TabularInline):
    """Inline for attachments in talk admin."""

    model = TalkAttachment
    extra = 1


@admin.register(TalkTemplate)
class TalkTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for TalkTemplate model."""

    list_display = [
        "title",
        "talk_type",
        "estimated_duration",
        "requires_signature",
        "is_active",
    ]
    list_filter = ["talk_type", "is_active", "requires_signature"]
    search_fields = ["title", "description", "content"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            None,
            {
                "fields": ["title", "description", "talk_type"],
            },
        ),
        (
            _("Contenido"),
            {
                "fields": ["content", "key_points", "safety_topics"],
            },
        ),
        (
            _("Configuración"),
            {
                "fields": [
                    "estimated_duration",
                    "requires_signature",
                    "target_activities",
                    "is_active",
                ],
            },
        ),
        (
            _("Auditoría"),
            {
                "fields": ["created_by", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PreopTalk)
class PreopTalkAdmin(admin.ModelAdmin):
    """Admin configuration for PreopTalk model."""

    list_display = [
        "title",
        "project_name",
        "status",
        "scheduled_at",
        "attendee_count",
        "conducted_by",
    ]
    list_filter = ["status", "scheduled_at", "project_name"]
    search_fields = ["title", "project_name", "location", "work_activity"]
    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]
    date_hierarchy = "scheduled_at"
    inlines = [TalkAttendeeInline, TalkAttachmentInline]
    raw_id_fields = ["conducted_by", "supervisor"]
    autocomplete_fields = ["template"]

    fieldsets = [
        (
            None,
            {
                "fields": ["template", "title", "content", "key_points"],
            },
        ),
        (
            _("Ubicación y actividad"),
            {
                "fields": [
                    "project_name",
                    "location",
                    "work_activity",
                    "weather_conditions",
                    "special_risks",
                ],
            },
        ),
        (
            _("Programación"),
            {
                "fields": [
                    "status",
                    "scheduled_at",
                    "started_at",
                    "completed_at",
                    "duration",
                ],
            },
        ),
        (
            _("Responsables"),
            {
                "fields": ["conducted_by", "supervisor"],
            },
        ),
        (
            _("GPS"),
            {
                "fields": ["gps_latitude", "gps_longitude"],
                "classes": ["collapse"],
            },
        ),
        (
            _("Notas"),
            {
                "fields": ["notes"],
            },
        ),
    ]
