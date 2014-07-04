from optparse import make_option
import logging

from django.core.management.base import NoArgsCommand
from django.db import models

from django_pgviews.view import create_views


log = logging.getLogger('django_pgviews.sync_pgviews')


class Command(NoArgsCommand):
    help = """Create/update Postgres views for all installed apps."""
    option_list = NoArgsCommand.option_list + (
        make_option('--no-update',
                    action='store_false',
                    dest='update',
                    default=True,
                    help="""Don't update existing views, only create new ones."""),
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help="""Force replacement of pre-existing views where
                    breaking changes have been made to the schema."""),
    )

    def handle_noargs(self, force, update, **options):
        for module in models.get_apps():
            log.info("Creating views for %s", module.__name__)
            try:
                for status, view_cls, python_name in create_views(module, update=update, force=force):
                    if status == 'CREATED':
                        msg = "created"
                    elif status == 'UPDATED':
                        msg = "updated"
                    elif status == 'EXISTS':
                        msg = "already exists, skipping"
                    elif status == 'FORCED':
                        msg = "forced overwrite of existing schema"
                    elif status == 'FORCE_REQUIRED':
                        msg = (
                            "exists with incompatible schema, "
                            "--force required to update")
                    log.info("%(python_name)s (%(view_name)s): %(msg)s" % {
                        'python_name': python_name,
                        'view_name': view_cls._meta.db_table,
                        'msg': msg})
            except Exception, exc:
                if not hasattr(exc, 'view_cls'):
                    raise
                log.exception("Error creating view %s (%r)",
                              exc.python_name,
                              exc.view_cls._meta.db_table)
