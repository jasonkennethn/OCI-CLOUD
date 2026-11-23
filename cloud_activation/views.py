"""
Views for Cloud Activation app.
"""

import json
from datetime import datetime, timedelta

import pytz
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import JobRun, AllocationStatus


def _get_schedule_info():
    """Calculate next run times and time remaining."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    schedule_hours = [6, 9, 19, 23]
    hour_labels = {6: '6:00 AM', 9: '9:00 AM', 19: '7:00 PM', 23: '11:00 PM'}

    upcoming = []
    for day_offset in range(7):
        for hour in schedule_hours:
            run_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if day_offset > 0:
                run_time = run_time + timedelta(days=day_offset)
            if run_time > now:
                upcoming.append({
                    'time': run_time,
                    'label': hour_labels[hour],
                    'date': run_time.strftime('%d %b %Y'),
                    'iso': run_time.isoformat(),
                })
            if len(upcoming) >= 4:
                break
        if len(upcoming) >= 4:
            break

    next_run = upcoming[0] if upcoming else None
    time_remaining = None
    if next_run:
        delta = next_run['time'] - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_remaining = {
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': int(delta.total_seconds()),
        }

    return {
        'upcoming': upcoming,
        'next_run': next_run,
        'time_remaining': time_remaining,
    }


def dashboard(request):
    """Main dashboard page."""
    status = AllocationStatus.load()
    recent_jobs = JobRun.objects.all()[:10]
    schedule = _get_schedule_info()

    context = {
        'status': status,
        'recent_jobs': recent_jobs,
        'schedule': schedule,
        'next_run_iso': schedule['next_run']['iso'] if schedule['next_run'] else None,
    }
    return render(request, 'dashboard.html', context)


def api_status(request):
    """API endpoint returning current status as JSON."""
    status = AllocationStatus.load()
    schedule = _get_schedule_info()
    recent_jobs = JobRun.objects.all()[:5]

    jobs_data = [
        {
            'id': job.id,
            'status': job.status,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'plan_job_ocid': job.plan_job_ocid,
            'apply_job_ocid': job.apply_job_ocid,
            'error_message': job.error_message,
            'email_sent': job.email_sent,
        }
        for job in recent_jobs
    ]

    return JsonResponse({
        'is_allocated': status.is_allocated,
        'allocated_at': status.allocated_at.isoformat() if status.allocated_at else None,
        'last_attempt_at': status.last_attempt_at.isoformat() if status.last_attempt_at else None,
        'last_attempt_status': status.last_attempt_status,
        'total_attempts': status.total_attempts,
        'scheduler_active': status.scheduler_active,
        'schedule': {
            'next_run': schedule['next_run']['iso'] if schedule['next_run'] else None,
            'next_run_label': schedule['next_run']['label'] if schedule['next_run'] else None,
            'time_remaining': schedule['time_remaining'],
            'upcoming': [
                {'time': u['iso'], 'label': u['label'], 'date': u['date']}
                for u in schedule['upcoming']
            ],
        },
        'recent_jobs': jobs_data,
    })
