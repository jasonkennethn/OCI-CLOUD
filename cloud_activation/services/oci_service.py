"""
OCI Service – Handles Resource Manager plan & apply operations.
"""

import os
import logging
import tempfile
import time

import oci
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('cloud_activation')

# ── Job polling config ──
POLL_INTERVAL_SECONDS = 15
MAX_POLL_ATTEMPTS = 120  # 30 minutes max wait


def _get_oci_config():
    """Build OCI config dict from environment variables."""
    private_key = os.getenv('OCI_API_PRIVATE_KEY', '')
    # Handle escaped newlines from .env
    private_key = private_key.replace('\\n', '\n')

    return {
        'user': os.getenv('OCI_USER_OCID'),
        'fingerprint': os.getenv('OCI_FINGERPRINT'),
        'tenancy': os.getenv('OCI_TENANCY_OCID'),
        'region': os.getenv('OCI_REGION'),
        'key_content': private_key,
    }


def _get_resource_manager_client():
    """Create an OCI Resource Manager client."""
    config = _get_oci_config()
    return oci.resource_manager.ResourceManagerClient(config)


def _wait_for_job(client, job_id):
    """
    Poll job status until it reaches a terminal state.
    Returns the final job object.
    """
    for attempt in range(MAX_POLL_ATTEMPTS):
        job = client.get_job(job_id).data
        status = job.lifecycle_state

        logger.info(f"  Polling job {job_id}: {status} (attempt {attempt + 1})")

        if status in ('SUCCEEDED', 'FAILED', 'CANCELED'):
            return job

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Job {job_id} did not complete within timeout")


def create_plan_job(stack_ocid: str) -> dict:
    """
    Create a PLAN job on the given stack.
    Returns dict with 'job_id', 'status', 'display_name'.
    """
    client = _get_resource_manager_client()

    plan_details = oci.resource_manager.models.CreateJobDetails(
        stack_id=stack_ocid,
        operation='PLAN',
        display_name=f'plan-job-auto',
    )

    logger.info(f"Creating PLAN job for stack {stack_ocid}...")
    response = client.create_job(plan_details)
    job = response.data

    logger.info(f"Plan job created: {job.id} – waiting for completion...")
    final_job = _wait_for_job(client, job.id)

    result = {
        'job_id': final_job.id,
        'status': final_job.lifecycle_state,
        'display_name': final_job.display_name,
    }
    logger.info(f"Plan job result: {result}")
    return result


def create_apply_job(stack_ocid: str, plan_job_id: str) -> dict:
    """
    Create an APPLY job using the given plan job.
    Returns dict with 'job_id', 'status', 'display_name'.
    """
    client = _get_resource_manager_client()

    apply_details = oci.resource_manager.models.CreateJobDetails(
        stack_id=stack_ocid,
        operation='APPLY',
        display_name=f'apply-job-auto',
        apply_job_plan_resolution=oci.resource_manager.models.ApplyJobPlanResolution(
            plan_job_id=plan_job_id,
            is_use_latest_job_id=False,
            is_auto_approved=True,
        ),
    )

    logger.info(f"Creating APPLY job for stack {stack_ocid} using plan {plan_job_id}...")
    response = client.create_job(apply_details)
    job = response.data

    logger.info(f"Apply job created: {job.id} – waiting for completion...")
    final_job = _wait_for_job(client, job.id)

    result = {
        'job_id': final_job.id,
        'status': final_job.lifecycle_state,
        'display_name': final_job.display_name,
    }
    logger.info(f"Apply job result: {result}")
    return result


def run_plan_and_apply(stack_ocid: str) -> dict:
    """
    Execute the full plan → apply workflow.
    Returns a summary dict.
    """
    result = {
        'plan': None,
        'apply': None,
        'success': False,
        'error': None,
    }

    try:
        # Step 1: Plan
        plan_result = create_plan_job(stack_ocid)
        result['plan'] = plan_result

        if plan_result['status'] != 'SUCCEEDED':
            result['error'] = f"Plan failed with status: {plan_result['status']}"
            return result

        # Step 2: Apply
        apply_result = create_apply_job(stack_ocid, plan_result['job_id'])
        result['apply'] = apply_result

        if apply_result['status'] == 'SUCCEEDED':
            result['success'] = True
            logger.info("✅ Stack apply SUCCEEDED!")
        else:
            result['error'] = f"Apply failed with status: {apply_result['status']}"

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"OCI operation error: {e}")

    return result
