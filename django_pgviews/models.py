from .view import create_views

import logging

log = logging.getLogger('django_pgviews.sync_pgviews')


def sync_pgviews(sender, app_config, **kwargs):
    """Forcibly sync the views.
    """
    create = create_views(sender.models_module, update=True, force=True)

    for status, view_cls, python_name in create:
        if status == 'CREATED':
            msg = "created"
        elif status == 'UPDATED':
            msg = "updated"
        elif status == 'EXISTS':
            msg = "already exists, skipping"
        elif status == 'FORCED':
            msg = "forced overwrite of existing schema"

        log.info("%(python_name)s (%(view_name)s): %(msg)s" % {
            'python_name': python_name,
            'view_name': view_cls._meta.db_table,
            'msg': msg})
