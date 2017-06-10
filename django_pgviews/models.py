import logging

from django.apps import apps
from django.db import connection

from django_pgviews.view import create_view, View, MaterializedView
from django_pgviews.signals import view_synced, all_views_synced

log = logging.getLogger('django_pgviews.sync_pgviews')


class ViewSyncer(object):
    def run(self, force, update, **options):
        self.synced = []
        backlog = []
        for view_cls in apps.get_models():
            if not (isinstance(view_cls, type) and
                    issubclass(view_cls, View) and
                    hasattr(view_cls, 'sql')):
                continue
            backlog.append(view_cls)
        loop = 0
        while len(backlog) > 0 and loop < 10:
            loop += 1
            backlog = self.run_backlog(backlog, force, update)

        if loop >= 10:
            log.warn('pgviews dependencies hit limit. Check if your model dependencies are correct')
        else:
            all_views_synced.send(sender=None)

    def run_backlog(self, models, force, update):
        '''Installs the list of models given from the previous backlog

        If the correct dependent views have not been installed, the view
        will be added to the backlog.

        Eventually we get to a point where all dependencies are sorted.
        '''
        backlog = []
        for view_cls in models:
            skip = False
            name = '{}.{}'.format(view_cls._meta.app_label, view_cls.__name__)
            for dep in view_cls._dependencies:
                if dep not in self.synced:
                    skip = True
            if skip is True:
                backlog.append(view_cls)
                log.info('Putting pgview at back of queue: %s', name)
                continue # Skip

            try:
                status = create_view(connection, view_cls._meta.db_table,
                        view_cls.sql, update=update, force=force,
                        materialized=isinstance(view_cls(), MaterializedView),
                        index=view_cls._concurrent_index)
                view_synced.send(
                    sender=view_cls, update=update, force=force, status=status,
                    has_changed=status not in ('EXISTS', 'FORCE_REQUIRED'))
                self.synced.append(name)
            except Exception as exc:
                exc.view_cls = view_cls
                exc.python_name = name
                raise
            else:
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
                log.info("pgview %(python_name)s %(msg)s" % {
                    'python_name': name,
                    'msg': msg})
        return backlog
