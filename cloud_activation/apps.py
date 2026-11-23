"""
App configuration for Cloud Activation.
Starts the scheduler when the app is ready (on the web process only).
"""

import os
from django.apps import AppConfig


class CloudActivationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cloud_activation'
    verbose_name = 'OCI Cloud Activation'

    def ready(self):
        """Start the scheduler when Django loads (gunicorn/runserver only)."""
        import sys
        should_start = (
            'runserver' in sys.argv
            or 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '')
            or os.environ.get('RUN_SCHEDULER', 'false').lower() == 'true'
        )
        if should_start:
            # Defer scheduler start to avoid DB access during app init
            import threading
            threading.Timer(2.0, self._start_scheduler).start()

    def _start_scheduler(self):
        try:
            from cloud_activation.services.scheduler_service import start_scheduler
            start_scheduler()
        except Exception as e:
            import logging
            logger = logging.getLogger('cloud_activation')
            logger.error(f"Failed to start scheduler: {e}")
