from django import apps
from django.db.models import signals

from .models import sync_pgviews


class ViewConfig(apps.AppConfig):
    """The base configuration for Django PGViews. We use this to setup our
    post_migrate signal handlers.
    """

    name = 'django_pgviews'
    verbose_name = 'Django Postgres Views'

    def ready(self):
        """Find and setup the apps to set the post_migrate hooks for.
        """
        signals.post_migrate.connect(sync_pgviews)
