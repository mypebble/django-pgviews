"""Helpers to access Postgres views from the Django ORM."""

import collections
import copy
import logging
import re

from django.db import connection, transaction
from django.db import models
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
        model_cls._meta.get_field_by_name(field_name)
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
    for view_cls, field_names in pending.iteritems():
        field_instances = get_fields_by_name(sender, *field_names)
        for name, field in field_instances.iteritems():
            # Only assign the field if the view does not already have an
            # attribute or explicitly-defined field with that name.
            if hasattr(view_cls, name) or hasfield(view_cls, name):
                continue
            copy.copy(field).contribute_to_class(view_cls, name)
models.signals.class_prepared.connect(realize_deferred_projections)


def create_views(models_module, update=True, force=False):
    """Create the database views for a given models module."""
    for name, view_cls in vars(models_module).iteritems():
        if not (isinstance(view_cls, type) and
                issubclass(view_cls, View) and
                hasattr(view_cls, 'sql')):
            continue

        try:
            created = create_view(connection, view_cls._meta.db_table,
                                  view_cls.sql, update=update, force=force)
        except Exception, exc:
            exc.view_cls = view_cls
            exc.python_name = models_module.__name__ + '.' + name
            raise
        else:
            yield created, view_cls, models_module.__name__ + '.' + name


def create_view(connection, view_name, view_query, update=True, force=False):
    """
    Create a named view on a connection.

    Returns True if a new view was created (or an existing one updated), or
    False if nothing was done.

    If ``update`` is True (default), attempt to update an existing view. If the
    existing view's schema is incompatible with the new definition, ``force``
    (default: False) controls whether or not to drop the old view and create
    the new one.
    """
    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor.cursor
    try:
        force_required = False
        # Determine if view already exists.
        cursor.execute('SELECT COUNT(*) FROM pg_catalog.pg_class WHERE relname = %s;',
                       [view_name])
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

        if not force_required:
            cursor.execute('CREATE OR REPLACE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = view_exists and 'UPDATED' or 'CREATED'
        elif force:
            cursor.execute('DROP VIEW {0};'.format(view_name))
            cursor.execute('CREATE VIEW {0} AS {1};'.format(view_name, view_query))
            ret = 'FORCED'
        else:
            ret = 'FORCE_REQUIRED'

        transaction.commit_unless_managed()
        return ret
    finally:
        cursor_wrapper.close()


class View(models.Model):

    """Helper for exposing Postgres views as Django models."""

    class ViewMeta(models.base.ModelBase):

        def __new__(metacls, name, bases, attrs):
            projection = attrs.pop('projection', [])
            deferred_projections = []
            for field_name in projection:
                if isinstance(field_name, models.Field):
                    attrs[field_name.name] = copy.copy(field_name)
                elif isinstance(field_name, basestring):
                    match = FIELD_SPEC_RE.match(field_name)
                    if not match:
                        raise TypeError("Unrecognized field specifier: %r" %
                                        field_name)
                    deferred_projections.append(match.groups())
                else:
                    raise TypeError("Unrecognized field specifier: %r" %
                                    field_name)
            view_cls = models.base.ModelBase.__new__(metacls, name, bases,
                                                     attrs)
            for app_label, model_name, field_name in deferred_projections:
                model_spec = (app_label, model_name.lower())
                _DEFERRED_PROJECTIONS[model_spec][view_cls].append(field_name)
                # If the model has already been loaded, run
                # `realize_deferred_projections()` on it.
                model_cls = models.get_model(app_label, model_name,
                                             seed_cache=False)
                if model_cls is not None:
                    realize_deferred_projections(model_cls)
            return view_cls

    __metaclass__ = ViewMeta

    class Meta:
        abstract = True
        managed = False
