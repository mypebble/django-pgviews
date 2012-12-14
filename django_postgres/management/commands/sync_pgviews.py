"""Synchronise SQL Views.
"""
from django.core.management.base import NoArgsCommand
from django.db import models

from django_postgres.view import create_views


class Command(NoArgsCommand):
    help = 'Creates and Updates all SQL Views'

    def handle_noargs(self, **options):
        all_modules = models.get_apps()
        modules = '\n '.join((m.__name__ for m in all_modules))
        self.stdout.write(
            'Creating Views for all modules:\n{modules}\n'.format(
                modules=modules
            )
        )
        for module in all_modules:
            create_views(module)
