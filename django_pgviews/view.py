"""Helpers to access Postgres views from the Django ORM.
"""
import collections
import copy
import logging
import re

import django
from django.core import exceptions
from django.db import connection
from django.db.models.query import QuerySet
from django.db import models
from django.utils import six
from django.apps import apps
import psycopg2

from django_pgviews.db import get_fields_by_name


FIELD_SPEC_REGEX = (r'^([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'(\*|(?:[A-Za-z_][A-Za-z0-9_]*))$')
FIELD_SPEC_RE = re.compile(FIELD_SPEC_REGEX)

log = logging.getLogger('django_pgviews.view')


def hasfield(model_cls, field_name):
    """Like `hasattr()`, but for model fields.

        >>> from django.contrib.auth.models import User
        >>> hasfield(User, 'password')
        True
        >>> hasfield(User, 'foobarbaz')
        False
    """
    try:
        model_cls._meta.get_field(field_name)
        return True
    except models.FieldDoesNotExist:
        return False


# Projections of models fields onto views which have been deferred due to
# model import and loading dependencies.
# Format: (app_label, model_name): {view_cls: [field_name, ...]}
_DEFERRED_PROJECTIONS = collections.defaultdict(
    lambda: collections.defaultdict(list))


def realize_deferred_projections(sender, *args, **kwargs):
    """Project any fields which were deferred pending model preparation."""
    app_label = sender._meta.app_label
    model_name = sender.__name__.lower()
    pending = _DEFERRED_PROJECTIONS.pop((app_label, model_name), {})
    for view_cls, field_names in pending.items():
        field_instances = get_fields_by_name(sender, *field_names)
        for name, field in field_instances.items():
            # Only assign the field if the view does not already have an
            # attribute or explicitly-defined field with that name.
            if hasattr(view_cls, name) or hasfield(view_cls, name):
                continue
            copy.copy(field).contribute_to_class(view_cls, name)
models.signals.class_prepared.connect(realize_deferred_projections)


def create_view(connection, view_name, view_query, update=True, force=False,
        materialized=False, index=None):
    """
    Create a named view on a connection.

    Returns True if a new view was created (or an existing one updated), or
    False if nothing was done.

    If ``update`` is True (default), attempt to update an existing view. If the
    existing view's schema is incompatible with the new definition, ``force``
    (default: False) controls whether or not to drop the old view and create
    the new one.
    """

    if '.' in view_name:
        vschema, vname = view_name.split('.', 1)
    else:
        vschema, vname = 'public', view_name

    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor
    try:
        force_required = False
        # Determine if view already exists.
        cursor.execute(
            'SELECT COUNT(*) FROM information_schema.views WHERE table_schema = %s and table_name = %s;',
            [vschema, vname]
        )
        view_exists = cursor.fetchone()[0] > 0
        if view_exists and not update:
            return 'EXISTS'
        elif view_exists:
            # Detect schema conflict by copying the original view, attempting to
            # update this copy, and detecting errors.
            cursor.execute('CREATE TEMPORARY VIEW check_conflict AS SELECT * FROM {0};'.format(view_name))
            try:
                cursor.execute('CREATE OR REPLACE TEMPORARY VIEW check_conflict AS {0};'.format(view_query))
            except psycopg2.ProgrammingError:
                force_required = True
                cursor.connection.rollback()
            finally:
                cursor.execute('DROP VIEW IF EXISTS check_conflict;')

        if materialized:
            cursor.execute('DROP MATERIALIZED VIEW IF EXISTS {0} CASCADE;'.format(view_name))
            cursor.execute('CREATE MATERIALIZED VIEW {0} AS {1};'.format(view_name, view_query))
            if index is not None:
                cursor.execute('CREATE UNIQUE INDEX {0}_{1}_index ON {0} ({1})'.format(view_name, index))
            ret = view_exists and 'UPDATED' or 'CREATED'
        elif not force_required:
            cursor.execute('CREATE OR REPLACE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = view_exists and 'UPDATED' or 'CREATED'
        elif force:
            cursor.execute('DROP VIEW IF EXISTS {0} CASCADE;'.format(view_name))
            cursor.execute('CREATE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = 'FORCED'
        else:
            ret = 'FORCE_REQUIRED'

        return ret
    finally:
        cursor_wrapper.close()


def clear_view(connection, view_name, materialized=False):
    """
    Remove a named view on connection.
    """
    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor
    try:
        if materialized:
            cursor.execute('DROP MATERIALIZED VIEW IF EXISTS {0} CASCADE'.format(view_name))
        else:
            cursor.execute('DROP VIEW IF EXISTS {0} CASCADE'.format(view_name))
    finally:
        cursor_wrapper.close()
    return u'DROPPED'.format(view=view_name)


class ViewMeta(models.base.ModelBase):
    def __new__(metacls, name, bases, attrs):
        """Deal with all of the meta attributes, removing any Django does not want
        """
        # Get attributes before Django
        dependencies = attrs.pop('dependencies', [])
        projection = attrs.pop('projection', [])
        concurrent_index = attrs.pop('concurrent_index',None)

        # Get projection
        deferred_projections = []
        for field_name in projection:
            if isinstance(field_name, models.Field):
                attrs[field_name.name] = copy.copy(field_name)
            elif isinstance(field_name, six.string_types):
                match = FIELD_SPEC_RE.match(field_name)
                if not match:
                    raise TypeError("Unrecognized field specifier: %r" %
                                    field_name)
                deferred_projections.append(match.groups())
            else:
                raise TypeError("Unrecognized field specifier: %r" %
                                field_name)

        view_cls = models.base.ModelBase.__new__(metacls, name, bases, attrs)

        # Get dependencies
        setattr(view_cls, '_dependencies', dependencies)
        # Materialized views can have an index allowing concurrent refresh
        setattr(view_cls, '_concurrent_index', concurrent_index)
        for app_label, model_name, field_name in deferred_projections:
            model_spec = (app_label, model_name.lower())

            _DEFERRED_PROJECTIONS[model_spec][view_cls].append(field_name)
            _realise_projections(app_label, model_name)

        return view_cls

    def add_to_class(self, name, value):
        if django.VERSION >= (1, 10) and name == '_base_manager':
            return
        super(ViewMeta, self).add_to_class(name, value)



if django.VERSION >= (1, 10):
    class BaseManagerMeta:
        base_manager_name = 'objects'
else:
    BaseManagerMeta = object


class View(six.with_metaclass(ViewMeta, models.Model)):
    """Helper for exposing Postgres views as Django models.
    """
    _deferred = False

    class Meta:
        abstract = True
        managed = False


def _realise_projections(app_label, model_name):
    """Checks whether the model has been loaded and runs
    realise_deferred_projections() if it has.
    """
    try:
        model_cls = apps.get_model(app_label, model_name)
    except exceptions.AppRegistryNotReady:
        return
    if model_cls is not None:
        realize_deferred_projections(model_cls)


class ReadOnlyViewQuerySet(QuerySet):
    def _raw_delete(self, *args, **kwargs):
        return 0

    def delete(self):
        raise NotImplementedError("Not allowed")

    def update(self, **kwargs):
        raise NotImplementedError("Not allowed")

    def _update(self, values):
        raise NotImplementedError("Not allowed")

    def create(self, **kwargs):
        raise NotImplementedError("Not allowed")

    def update_or_create(self, defaults=None, **kwargs):
        raise NotImplementedError("Not allowed")

    def bulk_create(self, objs, batch_size=None):
        raise NotImplementedError("Not allowed")


class ReadOnlyViewManager(models.Manager):
    def get_queryset(self):
        return ReadOnlyViewQuerySet(self.model, using=self._db)


class ReadOnlyView(View):
    """View which cannot be altered
    """
    _base_manager = ReadOnlyViewManager()
    objects = ReadOnlyViewManager()

    class Meta(BaseManagerMeta):
        abstract = True
        managed = False


class MaterializedView(View):
    """A materialized view.
    More information:
    http://www.postgresql.org/docs/current/static/sql-creatematerializedview.html
    """
    @classmethod
    def refresh(self, concurrently=False):
        cursor_wrapper = connection.cursor()
        cursor = cursor_wrapper.cursor
        try:
            if self._concurrent_index is not None and concurrently:
                cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY {0}'.format(
                    self._meta.db_table))
            else:
                cursor.execute('REFRESH MATERIALIZED VIEW {0}'.format(
                    self._meta.db_table))
        finally:
            cursor_wrapper.close()

    class Meta:
        abstract = True
        managed = False


class ReadOnlyMaterializedView(MaterializedView):
    """Read-only version of the materialized view
    """
    _base_manager = ReadOnlyViewManager()
    objects = ReadOnlyViewManager()

    class Meta(BaseManagerMeta):
        abstract = True
        managed = False
