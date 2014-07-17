from optparse import make_option
import logging

from django.core.management.base import NoArgsCommand
from django.db import models

from django_pgviews.view import clear_views


log = logging.getLogger('django_pgviews.sync_pgviews')


class Command(NoArgsCommand):
    help = """Clear Postgres views. Use this before running a migration"""

    def handle_noargs(self, **options):
        """
        """
        for module in models.get_apps():
            for status, view_cls, python_name in clear_views(module):
                if status == 'DROPPED':
                    msg = 'dropped'
                else:
                    msg = 'not dropped'
                log.info("%(python_name)s (%(view_name)s): %(msg)s" % {
                    'python_name': python_name,
                    'view_name': view_cls._meta.db_table,
                    'msg': msg})
