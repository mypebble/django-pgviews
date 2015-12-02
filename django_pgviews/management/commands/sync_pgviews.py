from optparse import make_option
import logging

from django.core.management.base import NoArgsCommand
from django.db import connection
from django.apps import apps

from django_pgviews.models import ViewSyncer


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
        vs = ViewSyncer()
        vs.run(force, update)