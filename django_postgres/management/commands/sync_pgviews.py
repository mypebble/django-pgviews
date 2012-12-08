"""Syncronise SQL Views.
"""
from django.core.management.base import BaseCommand
from django.db import models

from django_postgres.view import create_views


class Command(BaseCommand):
    args = '<appname appname ...>'
    help = 'Creates and Updates all SQL Views'

    def handle(self, *args, **options):
        """Run the create_views command.
        """
        self.stdout.write('Creating Views for {modules}'.format(modules=args))
        if args:
            for module in args:
                create_views(module)
        else:
            self.handle_noargs(**options)
    
    def handle_noargs(self, **options):
        all_modules = models.get_apps()
        self.stdout.write(
            'Creating Views for {modules}'.format(modules=all_modules))
        for module in all_modules:
            create_views(module)
