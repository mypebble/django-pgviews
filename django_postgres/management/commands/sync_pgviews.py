"""Syncronise SQL Views.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models

from django_postgres.view import create_views


class Command(BaseCommand):
    args = '<appname appname ...>'
    help = 'Creates and Updates all SQL Views'

    def handle(self, *args, **options):
        """Run the create_views command.
        """
        if args:
            modules = [a for a in args if a in settings.INSTALLED_APPS]
            imported = [__import__(m) for m in modules]
            self.stdout.write(
                'Creating Views for {modules}'.format(modules=modules))
            for module in imported:
                create_views(module)
        else:
            self.handle_noargs(**options)

    def handle_noargs(self, **options):
        all_modules = models.get_apps()
        self.stdout.write(
            'Creating Views for all modules: {modules}'.format(
                modules=all_modules
            )
        )
        for module in all_modules:
            create_views(module)
