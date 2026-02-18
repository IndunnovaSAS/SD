"""
Celery tasks for accounts app - SMS OTP delivery and cleanup.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="notifications",
)
def send_sms_otp_task(self, phone: str, message: str):
    """Send SMS OTP asynchronously via Twilio."""
    from apps.accounts.services import SMSOTPService

    try:
        SMSOTPService._send_sms_sync(phone, message)
        logger.info(f"SMS OTP task completed for {phone}")
    except Exception as e:
        logger.error(f"SMS OTP task failed for {phone}: {e}")
        raise self.retry(exc=e)


@shared_task
def cleanup_expired_otp_codes():
    """Periodic task to clean up old OTP codes (schedule via django-celery-beat)."""
    from apps.accounts.services import SMSOTPService

    deleted = SMSOTPService.cleanup_expired_codes(days=7)
    logger.info(f"Cleaned up {deleted} expired OTP codes")
    return deleted
