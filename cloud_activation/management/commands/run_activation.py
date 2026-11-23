"""
Management command to manually trigger the activation job.
Usage: python manage.py run_activation
"""

from django.core.management.base import BaseCommand
from cloud_activation.services.scheduler_service import run_activation_job


class Command(BaseCommand):
    help = 'Manually trigger the OCI stack plan → apply → email workflow'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting OCI activation job manually...'))
        run_activation_job()
        self.stdout.write(self.style.SUCCESS('Activation job completed.'))
