"""Syncronise SQL Views.
"""
from django.core.management.base import BaseCommand

from django_postgres.view import create_views


class Command(BaseCommand):
    args = '<appname appname ...>'
    help = 'Creates and Updates all SQL Views'

    def handle(self, *args, **options):
        """Run the create_views command.
        """
        self.stdout.write('Creating Views')
        create_views()
