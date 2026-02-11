"""
Service for notification template operations.
"""

from apps.notifications.models import NotificationTemplate


class NotificationTemplateService:
    """Service for notification template operations."""

    @staticmethod
    def get_template(name: str, channel: str = None) -> NotificationTemplate:
        """
        Get a notification template by name.
        """
        queryset = NotificationTemplate.objects.filter(
            name=name,
            is_active=True,
        )

        if channel:
            queryset = queryset.filter(channel=channel)

        return queryset.first()

    @staticmethod
    def render_template(
        template: NotificationTemplate,
        context: dict,
    ) -> dict:
        """
        Render a notification template with given context.
        Returns rendered subject and body.
        """
        subject = NotificationTemplateService._render_string(template.subject, context)
        body = NotificationTemplateService._render_string(template.body, context)
        html_body = ""
        if template.html_body:
            html_body = NotificationTemplateService._render_string(template.html_body, context)

        return {
            "subject": subject,
            "body": body,
            "html_body": html_body,
        }

    @staticmethod
    def _render_string(template_str: str, context: dict) -> str:
        """
        Render a template string with {{variable}} placeholders.
        """
        result = template_str
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        return result

    @staticmethod
    def get_templates_by_channel(channel: str):
        """
        Get all active templates for a specific channel.
        """
        return NotificationTemplate.objects.filter(
            channel=channel,
            is_active=True,
        ).order_by("name")
