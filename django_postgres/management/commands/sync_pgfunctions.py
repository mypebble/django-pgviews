from optparse import make_option
import logging

from django.core.management.base import NoArgsCommand
from django.db import models

from django_postgres.function import create_functions


log = logging.getLogger('django_postgres.sync_pgfunctions')


class Command(NoArgsCommand):
    help = """Create/update Postgres functions for all installed apps."""
    option_list = NoArgsCommand.option_list + (
        make_option(
            '--no-update',
            action='store_false',
            dest='update',
            default=True,
            help="""Don't update existing functions, only create new ones."""),
    )

    def handle_noargs(self, force, update, **options):
        for module in models.get_apps():
            log.info("Creating functions for %s", module.__name__)
            try:
                create_result = create_functions(module, update=update)

                for status, function_cls, python_name in create_result:
                    if status == 'CREATED':
                        msg = "created"
                    elif status == 'UPDATED':
                        msg = "updated"
                    elif status == 'EXISTS':
                        msg = "already exists, skipping"
                    elif status == 'FORCE_REQUIRED':
                        msg = (
                            "exists with incompatible schema, which must be "
                            "manually removed")
                    log.info("%(python_name)s (%(function_name)s): %(msg)s" % {
                        'python_name': python_name,
                        'function_name': function_cls._meta.db_table,
                        'msg': msg})
            except Exception, exc:
                if not hasattr(exc, 'function_cls'):
                    raise
                log.exception("Error creating function %s (%r)",
                              exc.python_name,
                              exc.function_cls._meta.db_table)

