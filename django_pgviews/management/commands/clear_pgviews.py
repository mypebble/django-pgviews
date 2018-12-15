import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connections, router

from django_pgviews.view import clear_view, View, MaterializedView


log = logging.getLogger('django_pgviews.sync_pgviews')


class Command(BaseCommand):
    help = """Clear Postgres views. Use this before running a migration"""

    def handle(self, **options):
        """
        """
        for view_cls in apps.get_models():
            if not (isinstance(view_cls, type) and
                    issubclass(view_cls, View) and
                    hasattr(view_cls, 'sql')):
                continue
            python_name = '{}.{}'.format(view_cls._meta.app_label, view_cls.__name__)
            using = router.db_for_write(view_cls)
            connection = connections[using]
            status = clear_view(
                connection, view_cls._meta.db_table,
                materialized=isinstance(view_cls(), MaterializedView))
            if status == 'DROPPED':
                msg = 'dropped'
            else:
                msg = 'not dropped'
            log.info("%(python_name)s (%(view_name)s): %(msg)s" % {
                'python_name': python_name,
                'view_name': view_cls._meta.db_table,
                'msg': msg})
