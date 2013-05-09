"""Access function-like features in Postgres using Django's ORM."""
from django.core import exceptions
from django.db import models

from django_postgres.db.sql import query


def _split_function_args(function_name):
    """Splits the function name into (name, (arg1type, arg2type))
    """
    name, args = function_name.split('(')
    name = name.trim()
    args = args.trim().replace(')', '').split(',')
    return name, tuple(a.trim() for a in args)


def _generate_function(name, args, fields, definition):
    """Generate the SQL for creating the function.
    """
    sql = ("CREATE OR REPLACE FUNCTION {name}({args})"
      "RETURNS TABLE({fields}) AS"
      "{definition}"
      "LANGUAGE sql;")

    arg_string = ', '.join(args)
    field_string = ', '.join(fields)
    sql = sql.format(
        name=name, args=arg_string, fields=field_string, definition=definition)


def create_function(connection, function_name, function_definition,
        update=True, force=False):
    """
    Create a named function on a connection.

    Returns True if a new function was created (or an existing one updated), or
    False if nothing was done.

    If ``update`` is True (default), attempt to update an existing function.
    If the existing function's definition is incompatible with the new
    definition, ``force`` (default: False) controls whether or not to drop the
    old view and create the new one.

    Beware that setting ``force`` will drop functions with the same name,
    irrespective of whether their arguments match.
    """
    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor.cursor

    name, args = _split_function_args(function_name)

    try:
        force_required = False
        # Determine if view already exists.
        function_query = (
        u"SELECT  COUNT(*)"
        u"FROM    pg_catalog.pg_namespace n"
        u"JOIN    pg_catalog.pg_proc p"
        u"ON      pronamespace = n.oid"
        u"WHERE   nspname = 'public' and proname = %s;")
        cursor.execute(function_query, [name])
        function_exists = cursor.fetchone()[0] > 0
        force_required = False

        if function_exists and not update:
            return 'EXISTS'
        elif function_exists:
            function_detail_query = (
                u"SELECT  pronargs"
                u"FROM    pg_catalog.pg_namespace n"
                u"JOIN    pg_catalog.pg_proc p"
                u"ON      pronamespace = n.oid"
                u"WHERE   nspname = 'public' and proname = %s;")
            cursor.execute(function_detail_query, [name])
            force_required = cursor.fetchone()[0] != len(args)

        if not force_required:
            cursor.execute(
                _generate_function(name, args, fields, function_definition))
    finally:
        cursor_wrapper.close()

def _create_model(name, execute, fields=None, app_label='', module='',
        options=None):
    """Creates the model that executes the function to query.
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


class FunctionManager(models.Manager):
    """Adds a call() method to the default Manager for Function. This must
    be called before you can filter the queryset, as it runs the execute
    command with the arguments provided.
    """

    def call(self, args=None):
        """Prepare the function for filtering by executing it with the
        arguments passed.
        """
        function_name, function_args = self.model._meta.db_table.split(u'(')
        function_args = u'(' + function_args

        model_name = self.model.__name__
        app_label = self.model._meta.app_label
        module = self.model.__module__

        execute_arguments = ''
        if args:
            execute_arguments = ', '.join(unicode(a) for a in args)

        execute_function = u'{name}({args})'.format(
            name=function_name,
            args=execute_arguments)

        model = _create_model(
            model_name + 'hello', execute_function, None, app_label, module)
        return models.query.QuerySet(model, query.NonQuotingQuery(model))

    def get_queryset(self):
        """No methods that depend on this can be called until the function has
        been called.
        """
        raise exceptions.ObjectDoesNotExist(
            u'You must run call() before filtering the queryset further')


class Function(models.Model):
    """Creates Postgres Prepared Functions, which can then be called and
    queried from the Django ORM. The default Manager for Function implements
    a call() method that must be run for every time you want to prime a
    queryset for execution.
    The called function must return a result set with the field names
    matching the fields set in this model definition.
    `Meta.db_table` is the name of the function that will be called.
    It should take the form `function_name (type, type, type)`
    The function definition is stored in the `sql` attribute.
    The sql definition is simply the SQL that will be executed by the
    function.
    """

    objects = FunctionManager()

    class Meta:
        abstract = True
        managed = False
