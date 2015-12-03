import logging

from django import apps
from django.db.models import signals

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
            # Import here otherwise Django doesn't start properly
            # (models in app init are not allowed)
            from .models import ViewSyncer
            vs = ViewSyncer()
            vs.run(force=True, update=True) 

    def ready(self):
        """Find and setup the apps to set the post_migrate hooks for.
        """
        signals.post_migrate.connect(self.sync_pgviews)
