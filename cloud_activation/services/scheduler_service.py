"""
Scheduler Service – APScheduler-based cron for OCI stack automation.

Schedule: 6:00 AM, 9:00 AM, 7:00 PM, 11:00 PM IST daily.
Workflow:
  1. Create Plan job on OCI stack
  2. If Plan succeeds → Wait 2 minutes
  3. Create Apply job with the plan
  4. If Apply succeeds → Send email via Brevo → Stop scheduler
  5. If Apply fails (e.g. out of capacity) → Wait for next scheduled run
"""

import os
import logging
import time
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

WAIT_AFTER_PLAN_SECONDS = 120  # Wait 2 minutes between Plan and Apply


def run_activation_job():
    """
    Execute the full activation workflow:
    1. Plan stack
    2. Wait 2 minutes
    3. Apply stack
    4. Send email (on success)
    5. Stop scheduler (on success)
    """
    from cloud_activation.models import JobRun, AllocationStatus
    from cloud_activation.services.oci_service import create_plan_job, create_apply_job
    from cloud_activation.services.email_service import send_success_email

    status = AllocationStatus.load()

    # If already allocated, do not run
    if status.is_allocated:
        logger.info("Cloud already allocated. Skipping job and stopping scheduler.")
        stop_scheduler()
        return

    stack_ocid = os.getenv('OCI_STACK_OCID')
    if not stack_ocid:
        logger.error("OCI_STACK_OCID not set in environment.")
        return

    # Create job run record
    job_run = JobRun.objects.create(status='PLANNING')
    status.total_attempts += 1
    status.last_attempt_at = timezone.now()
    status.last_attempt_status = 'PLANNING'
    status.save()

    logger.info(f"═══ Activation attempt #{status.total_attempts} started ═══")

    try:
        # ─────────────────────────────────────────────────────────────
        # Step 1: PLAN
        # ─────────────────────────────────────────────────────────────
        logger.info("Step 1: Starting OCI Plan job...")
        plan_result = create_plan_job(stack_ocid)
        job_run.plan_job_ocid = plan_result.get('job_id')

        if plan_result.get('status') != 'SUCCEEDED':
            job_run.status = 'PLAN_FAILED'
            job_run.error_message = f"Plan job completed with status: {plan_result.get('status')}"
            status.last_attempt_status = 'PLAN_FAILED'
            status.save()
            logger.warning(f"Plan failed: {job_run.error_message}")
            return

        # Plan succeeded!
        job_run.status = 'PLAN_SUCCEEDED'
        job_run.save()
        status.last_attempt_status = 'PLAN_SUCCEEDED'
        status.save()
        logger.info(f"✅ Plan SUCCEEDED (Job: {job_run.plan_job_ocid})")

        # ─────────────────────────────────────────────────────────────
        # Step 2: WAIT 2 MINUTES
        # ─────────────────────────────────────────────────────────────
        logger.info(f"⏳ Waiting {WAIT_AFTER_PLAN_SECONDS} seconds (2 minutes) before applying plan...")
        time.sleep(WAIT_AFTER_PLAN_SECONDS)

        # ─────────────────────────────────────────────────────────────
        # Step 3: APPLY
        # ─────────────────────────────────────────────────────────────
        logger.info("Step 3: Creating and running OCI Apply job...")
        job_run.status = 'APPLYING'
        job_run.save()
        status.last_attempt_status = 'APPLYING'
        status.save()

        apply_result = create_apply_job(stack_ocid, plan_result['job_id'])
        job_run.apply_job_ocid = apply_result.get('job_id')

        if apply_result.get('status') == 'SUCCEEDED':
            # Apply SUCCEEDED! Instance is allotted!
            job_run.status = 'APPLY_SUCCEEDED'
            job_run.completed_at = timezone.now()
            job_run.save()

            logger.info("🎉 Stack apply SUCCEEDED! Cloud has been allotted.")

            # Step 4: Send success email
            email_sent = send_success_email()
            if email_sent:
                job_run.email_sent = True
                job_run.status = 'EMAIL_SENT'
                job_run.save()

            # Mark cloud as allocated
            status.is_allocated = True
            status.allocated_at = timezone.now()
            status.last_attempt_status = 'APPLY_SUCCEEDED'
            status.scheduler_active = False
            status.save()

            # Step 5: Stop scheduler permanently
            logger.info("Stopping scheduler permanently as cloud is now allotted.")
            stop_scheduler()

        else:
            job_run.status = 'APPLY_FAILED'
            job_run.error_message = f"Apply job completed with status: {apply_result.get('status')}"
            status.last_attempt_status = 'APPLY_FAILED'
            status.save()
            logger.warning(f"Apply failed: {job_run.error_message}")

    except Exception as e:
        logger.error(f"Activation workflow error: {e}", exc_info=True)
        job_run.status = 'ERROR'
        job_run.error_message = str(e)
        status.last_attempt_status = 'ERROR'
        status.save()

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

    try:
        from cloud_activation.models import AllocationStatus
        status = AllocationStatus.load()
        status.scheduler_active = False
        status.save()
    except Exception:
        pass


def get_next_run_times(count=4):
    """Get the next scheduled run times in Asia/Kolkata timezone."""
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
