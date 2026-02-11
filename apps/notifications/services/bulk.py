"""
Service for sending bulk notifications.
"""

import logging

from django.db import transaction

from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.services.notification import NotificationService
from apps.notifications.services.templates import NotificationTemplateService

logger = logging.getLogger(__name__)


class BulkNotificationService:
    """Service for sending bulk notifications."""

    @staticmethod
    @transaction.atomic
    def send_to_users(
        users,
        subject: str,
        body: str,
        channel: str = NotificationTemplate.Channel.IN_APP,
        priority: str = Notification.Priority.NORMAL,
        action_url: str = "",
    ) -> list:
        """
        Send notification to multiple users.
        """
        notifications = []

        for user in users:
            notification = NotificationService.create_notification(
                user=user,
                subject=subject,
                body=body,
                channel=channel,
                priority=priority,
                action_url=action_url,
            )
            notifications.append(notification)

        logger.info(f"Bulk notification created for {len(notifications)} users")
        return notifications

    @staticmethod
    @transaction.atomic
    def send_from_template_to_users(
        users,
        template_name: str,
        context: dict,
        user_context_fn=None,
        channel: str = None,
        priority: str = Notification.Priority.NORMAL,
    ) -> list:
        """
        Send notification from template to multiple users.
        user_context_fn can provide per-user context.
        """
        template = NotificationTemplateService.get_template(template_name, channel)

        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        notifications = []

        for user in users:
            # Get user-specific context if function provided
            user_context = context.copy()
            if user_context_fn:
                user_context.update(user_context_fn(user))

            # Always include user name
            user_context.setdefault("user_name", user.get_full_name())
            user_context.setdefault("first_name", user.first_name)

            rendered = NotificationTemplateService.render_template(template, user_context)

            notification = NotificationService.create_notification(
                user=user,
                subject=rendered["subject"],
                body=rendered["body"],
                channel=channel or template.channel,
                template=template,
                priority=priority,
                metadata={"context": user_context},
            )
            notifications.append(notification)

        logger.info(f"Bulk template notification created for {len(notifications)} users")
        return notifications

    @staticmethod
    def send_course_reminder(course, users) -> list:
        """
        Send course reminder notifications.
        """
        context = {
            "course_title": course.title,
            "course_code": course.code,
        }

        def user_context(user):
            return {"user_name": user.get_full_name()}

        return BulkNotificationService.send_from_template_to_users(
            users=users,
            template_name="course_reminder",
            context=context,
            user_context_fn=user_context,
            priority=Notification.Priority.NORMAL,
        )

    @staticmethod
    def send_deadline_reminder(assignment, days_left: int) -> Notification:
        """
        Send deadline reminder for a learning path assignment.
        """
        context = {
            "path_name": assignment.learning_path.name,
            "due_date": assignment.due_date.strftime("%d/%m/%Y"),
            "days_left": days_left,
            "user_name": assignment.user.get_full_name(),
        }

        priority = Notification.Priority.NORMAL
        if days_left <= 3:
            priority = Notification.Priority.HIGH
        if days_left <= 1:
            priority = Notification.Priority.URGENT

        return NotificationService.send_from_template(
            user=assignment.user,
            template_name="deadline_reminder",
            context=context,
            priority=priority,
        )
