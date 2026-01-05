"""
Core models for SD LMS.

Provides base models and mixins used across the application.
"""

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields.

    All app models should inherit from this to get:
    - created_at: Timestamp when the record was created
    - updated_at: Timestamp when the record was last modified
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(BaseModel):
    """
    Abstract model that provides soft delete functionality.

    Instead of deleting records, marks them as deleted.
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the record."""
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the record."""
        super().delete(using=using, keep_parents=keep_parents)


class OrderedModel(BaseModel):
    """
    Abstract model that provides ordering functionality.
    """

    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order"]
