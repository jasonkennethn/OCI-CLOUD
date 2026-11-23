from django.contrib import admin
from .models import JobRun, AllocationStatus


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'completed_at', 'email_sent')
    list_filter = ('status', 'email_sent')
    readonly_fields = ('plan_job_ocid', 'apply_job_ocid')


@admin.register(AllocationStatus)
class AllocationStatusAdmin(admin.ModelAdmin):
    list_display = ('is_allocated', 'allocated_at', 'total_attempts', 'scheduler_active')
