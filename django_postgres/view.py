"""Helpers to access Postgres views from the Django ORM."""

import collections
import copy
import re

from django.db import connection
from django.db import models


FIELD_SPEC_REGEX = (r'^([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'([A-Za-z_][A-Za-z0-9_]*)\.'
                    r'(\*|(?:[A-Za-z_][A-Za-z0-9_]*))$')
FIELD_SPEC_RE = re.compile(FIELD_SPEC_REGEX)


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


def create_views(sender, *args, **kwargs):
    """Create the database views after syncdb."""
    models_module = sender
    for name, view_cls in vars(models_module).iteritems():
        if not (isinstance(view_cls, type) and
                issubclass(view_cls, View) and
                hasattr(view_cls, 'sql')):
            continue
        query = "CREATE OR REPLACE VIEW %s AS %s;" % (view_cls._meta.db_table,
                                                      view_cls.sql)
        cursor = connection.cursor()
        try:
            cursor.execute(query)
        finally:
            cursor.close()
models.signals.post_syncdb.connect(create_views)


def get_fields_by_name(model_cls, *field_names):
    """Return a dict of `models.Field` instances for named fields.

    Supports wildcard fetches using `'*'`.

        >>> get_fields_by_name(User, 'username', 'password')
        {'username': <django.db.models.fields.CharField: username>,
         'password': <django.db.models.fields.CharField: password>}

        >>> get_fields_by_name(User, '*')
        {'username': <django.db.models.fields.CharField: username>,
         ...,
         'date_joined': <django.db.models.fields.DateTimeField: date_joined>}
    """
    if '*' in field_names:
        return dict((field.name, field) for field in model_cls._meta.fields)
    return dict((field_name, model_cls._meta.get_field_by_name(field_name)[0])
                for field_name in field_names)


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
