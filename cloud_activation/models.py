"""
Models for Cloud Activation app.
Stores job run history and current allocation status.
"""

from django.db import models
from django.utils import timezone


class JobRun(models.Model):
    """Record of each scheduled OCI stack job execution."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PLANNING', 'Planning'),
        ('PLAN_SUCCEEDED', 'Plan Succeeded'),
        ('PLAN_FAILED', 'Plan Failed'),
        ('APPLYING', 'Applying'),
        ('APPLY_SUCCEEDED', 'Apply Succeeded'),
        ('APPLY_FAILED', 'Apply Failed'),
        ('EMAIL_SENT', 'Email Sent'),
        ('ERROR', 'Error'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    plan_job_ocid = models.CharField(max_length=255, blank=True, null=True)
    apply_job_ocid = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Job Run'
        verbose_name_plural = 'Job Runs'

    def __str__(self):
        return f"Job {self.id} – {self.status} @ {self.started_at:%Y-%m-%d %H:%M}"


class AllocationStatus(models.Model):
    """
    Singleton model that tracks the current cloud allocation state.
    Only one row should ever exist.
    """

    is_allocated = models.BooleanField(default=False)
    allocated_at = models.DateTimeField(blank=True, null=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    last_attempt_status = models.CharField(max_length=20, blank=True, null=True)
    total_attempts = models.IntegerField(default=0)
    scheduler_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Allocation Status'
        verbose_name_plural = 'Allocation Status'

    def save(self, *args, **kwargs):
        # Enforce singleton
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        state = "Allocated" if self.is_allocated else "Not Allocated"
        return f"Cloud: {state}"
