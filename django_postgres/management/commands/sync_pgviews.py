"""Synchronise SQL Views.
"""
from django.core.management.base import NoArgsBaseCommand
from django.db import models

from django_postgres.view import create_views


class Command(NoArgsBaseCommand):
    help = 'Creates and Updates all SQL Views'

    def handle_noargs(self, **options):
        all_modules = models.get_apps()
        self.stdout.write(
            'Creating Views for all modules: {modules}'.format(
                modules=all_modules
            )
        )
        for module in all_modules:
            create_views(module)
