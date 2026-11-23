"""
Scheduler Service – APScheduler-based cron for OCI stack automation.

Schedule: 6:00 AM, 9:00 AM, 7:00 PM, 11:00 PM IST daily.
Workflow:  Plan → Apply → Email (on success) → Stop scheduler.
"""

import os
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('cloud_activation')

# Module-level scheduler instance
scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
_scheduler_started = False


def run_activation_job():
    """
    Execute the full activation workflow:
    1. Create Plan job on the OCI stack
    2. If Plan succeeds → Create Apply job
    3. If Apply succeeds → Send email → Stop scheduler
    """
    # Import here to avoid circular imports
    from cloud_activation.models import JobRun, AllocationStatus
    from cloud_activation.services.oci_service import run_plan_and_apply
    from cloud_activation.services.email_service import send_success_email

    status = AllocationStatus.load()

    # If already allocated, don't run
    if status.is_allocated:
        logger.info("Cloud already allocated. Skipping job and stopping scheduler.")
        stop_scheduler()
        return

    stack_ocid = os.getenv('OCI_STACK_OCID')
    if not stack_ocid:
        logger.error("OCI_STACK_OCID not set in environment.")
        return

    # Create a job run record
    job_run = JobRun.objects.create(status='PLANNING')
    status.total_attempts += 1
    status.last_attempt_at = timezone.now()
    status.save()

    logger.info(f"═══ Activation attempt #{status.total_attempts} started ═══")

    try:
        result = run_plan_and_apply(stack_ocid)

        if result['plan']:
            job_run.plan_job_ocid = result['plan']['job_id']
            if result['plan']['status'] != 'SUCCEEDED':
                job_run.status = 'PLAN_FAILED'
                job_run.error_message = result.get('error', 'Plan did not succeed')

        if result['apply']:
            job_run.apply_job_ocid = result['apply']['job_id']

        if result['success']:
            # Apply succeeded!
            job_run.status = 'APPLY_SUCCEEDED'
            job_run.completed_at = timezone.now()

            # Send notification email
            email_sent = send_success_email()
            if email_sent:
                job_run.email_sent = True
                job_run.status = 'EMAIL_SENT'

            # Update allocation status
            status.is_allocated = True
            status.allocated_at = timezone.now()
            status.last_attempt_status = 'APPLY_SUCCEEDED'
            status.scheduler_active = False
            status.save()

            # Stop the scheduler
            logger.info("🎉 Cloud allocated successfully! Stopping scheduler.")
            stop_scheduler()

        else:
            job_run.status = 'APPLY_FAILED' if result.get('apply') else 'PLAN_FAILED'
            job_run.error_message = result.get('error', 'Unknown error')
            status.last_attempt_status = job_run.status
            status.save()
            logger.warning(f"Attempt failed: {result.get('error')}")

    except Exception as e:
        job_run.status = 'ERROR'
        job_run.error_message = str(e)
        status.last_attempt_status = 'ERROR'
        status.save()
        logger.error(f"Activation job error: {e}")

    finally:
        job_run.completed_at = timezone.now()
        job_run.save()
        logger.info(f"═══ Attempt #{status.total_attempts} finished: {job_run.status} ═══")


def start_scheduler():
    """Start the APScheduler with IST cron triggers."""
    global _scheduler_started

    if _scheduler_started:
        logger.info("Scheduler already running.")
        return

    # Import here to avoid startup issues
    from cloud_activation.models import AllocationStatus
    status = AllocationStatus.load()

    if status.is_allocated:
        logger.info("Cloud already allocated. Scheduler will not start.")
        return

    # Schedule: 6:00, 9:00, 19:00, 23:00 IST
    trigger = CronTrigger(
        hour='6,9,19,23',
        minute='0',
        timezone='Asia/Kolkata',
    )

    scheduler.add_job(
        run_activation_job,
        trigger=trigger,
        id='oci_activation_job',
        name='OCI Stack Activation',
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    _scheduler_started = True
    status.scheduler_active = True
    status.save()

    logger.info("✅ Scheduler started – runs at 6:00 AM, 9:00 AM, 7:00 PM, 11:00 PM IST")


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler_started

    if scheduler.running:
        scheduler.shutdown(wait=False)
        _scheduler_started = False
        logger.info("Scheduler stopped.")

    # Update DB
    try:
        from cloud_activation.models import AllocationStatus
        status = AllocationStatus.load()
        status.scheduler_active = False
        status.save()
    except Exception:
        pass


def get_next_run_times(count=4):
    """Get the next scheduled run times."""
    from datetime import datetime
    import pytz

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    schedule_hours = [6, 9, 19, 23]
    upcoming = []

    for day_offset in range(7):
        for hour in schedule_hours:
            run_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if day_offset > 0:
                run_time = run_time + __import__('datetime').timedelta(days=day_offset)
            if run_time > now:
                upcoming.append(run_time)
            if len(upcoming) >= count:
                break
        if len(upcoming) >= count:
            break

    return upcoming
