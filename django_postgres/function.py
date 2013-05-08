"""Access function-like features in Postgres using Django's ORM."""
from django.core import exceptions
from django.db import models


def _create_model(name, execute, fields=None, app_label='', module='',
        options=None):
    """Creates the model that executes the prepared statement to query.
    Most of the settings need to be pre-formatted, as this function will not
    check them.
    See http://djangosnippets.org/snippets/442/ for more information
    """
    class Meta:
        pass

    Meta.db_table = execute

    if app_label:
        Meta.app_label = app_label

    if options is not None:
        for key, value in options.iteritems():
            setattr(Meta, key, value)

    attrs = {
        '__module__': module,
        'Meta': Meta,
    }

    if fields:
        attrs.update(fields)

    return type(name, (models.Model,), attrs)


class StatementManager(models.Manager):
    """Adds a prepare() method to the default Manager for Statement. This must
    be called before you can filter the queryset, as it runs the execute
    command with the arguments provided.
    """

    def prepare(self, args=None):
        """Prepare the statement for filtering by executing it with the
        arguments passed.
        """
        statement_name = self.model._meta.db_table

    def get_queryset(self):
        """No methods that depend on this can be called until the statement has
        been prepared.
        """
        raise exceptions.ObjectDoesNotExist(
            u'You must run prepare() before filtering the queryset further')


class Statement(models.Model):
    """Creates Postgres Prepared Statements, which can then be called and
    queried from the Django ORM. The default Manager for Statement implements
    a prepare() method that must be run for every time you want to prime a
    queryset for execution.
    The prepared statement must return a result set with the field names
    matching the fields set in this model definition.
    `Meta.db_table` is the name of the prepared statement that will be called.
    It should take the form `statement_name (type, type, type)`
    The prepared statement definition is stored in the `sql` attribute.
    The sql definition is simply the SQL that will be executed by the prepared
    statement.
    """

    objects = StatementManager()

    class Meta:
        abstract = True
        managed = False
