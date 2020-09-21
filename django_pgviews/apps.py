import logging

from django import apps
from django.db.models import signals
from django.utils.module_loading import import_string
from django.conf import settings

log = logging.getLogger('django_pgviews.sync_pgviews')


class ViewConfig(apps.AppConfig):
    """The base configuration for Django PGViews. We use this to setup our
    post_migrate signal handlers.
    """
    counter = 0
    name = 'django_pgviews'
    verbose_name = 'Django Postgres Views'

    def sync_pgviews(self, sender, app_config, **kwargs):
        """Forcibly sync the views.
        """
        self.counter = self.counter + 1
        total = len([a for a in apps.apps.get_app_configs() if a.models_module is not None])

        if self.counter == total:
            log.info('All applications have migrated, time to sync')
            view_syncer_cls = self.get_view_syncer_class()
            vs = view_syncer_cls()
            vs.run(force=True, update=True)

    def get_view_syncer_class(self, default='django_pgviews.models.ViewSyncer'):
        return import_string(getattr(settings, 'PGVIEWS_VIEW_SYNCER_CLASS', None) or default)

    def ready(self):
        """Find and setup the apps to set the post_migrate hooks for.
        """
        signals.post_migrate.connect(self.sync_pgviews)
