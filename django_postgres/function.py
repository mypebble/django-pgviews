"""Access function-like features in Postgres using Django's ORM."""
from django.core import exceptions
from django.db import connection, models, transaction

from django_postgres.db import get_fields_by_name
from django_postgres.db.sql import query


def _split_function_args(function_name):
    """Splits the function name into (name, (arg1type, arg2type))
    """
    name, args = function_name.split('(')
    name = name.strip()
    args = args.strip().replace(')', '').split(',')
    return name, tuple(a.strip() for a in args)


def _generate_function(name, args, fields, definition):
    """Generate the SQL for creating the function.
    """
    sql = ("CREATE OR REPLACE FUNCTION {name}({args}) "
      "RETURNS TABLE({fields}) LANGUAGE SQL AS "
      '$$ {definition}; $$')

    arg_string = ', '.join(args)
    field_string = ', '.join(fields)
    sql = sql.format(
        name=name, args=arg_string, fields=field_string, definition=definition)

    return sql


def _function_exists(cursor, name):
    """Returns True or False depending whether function with name exists.
    """
    function_query = (
    u"SELECT  COUNT(*) "
    u"FROM    pg_catalog.pg_namespace n "
    u"JOIN    pg_catalog.pg_proc p "
    u"ON      pronamespace = n.oid "
    u"WHERE   nspname = 'public' and proname = %s;")
    cursor.execute(function_query, [name])
    return cursor.fetchone()[0] > 0


def _force_required(cursor, name, args):
    """Returns whether the function signature is compatible with the new
    definition.
    """
    function_detail_query = (
        u"SELECT  pronargs "
        u"FROM    pg_catalog.pg_namespace n "
        u"JOIN    pg_catalog.pg_proc p "
        u"ON      pronamespace = n.oid "
        u"WHERE   nspname = 'public' and proname = %s;")
    cursor.execute(function_detail_query, [name])
    return cursor.fetchone()[0] != len(args)


def create_function(connection, function_name, function_fields,
        function_definition, update=True):
    """
    Create a named function on a connection.

    Returns a success message if a new function was created (or an existing
    one updated), or an error message otherwise.

    If ``update`` is True (default), attempt to update an existing function.
    """
    cursor_wrapper = connection.cursor()
    cursor = cursor_wrapper.cursor

    name, args = _split_function_args(function_name)

    try:
        force_required = False

        function_exists = _function_exists(cursor, name)

        if function_exists and not update:
            return 'EXISTS'
        elif function_exists:
            force_required = _force_required(cursor, name, args)

        if not force_required:
            function_sql = _generate_function(
                name, args, function_fields, function_definition)

            cursor.execute(function_sql)
            ret = 'UPDATED' if function_exists else 'CREATED'
        else:
            ret = 'ERROR'

        transaction.commit_unless_managed()
        return ret
    finally:
        cursor_wrapper.close()


def _get_field_type(field):
    """Returns the field type as a string for SQL.
    """
    return field.db_type(
        connection).replace(
        'serial', 'bigint').replace(
        'integer', 'bigint')


def create_functions(models_module, update=True):
    """Create the database functions for a given models module.
    """
    for name, function_cls in vars(models_module).iteritems():
        is_function = (
            isinstance(function_cls, type) and
            issubclass(function_cls, Function) and
            hasattr(function_cls, 'sql'))

        if not is_function:
            continue

        function_name = function_cls._meta.db_table
        fields = tuple(
            ' '.join((n, _get_field_type(f))) for n, f in
            get_fields_by_name(function_cls, '*').iteritems())

        definition = function_cls.sql

        full_name = u'{module}.{cls}'.format(
            module=models_module.__name__,
            cls=name)

        try:
            created = create_function(
                connection, function_name, fields, definition)
        except Exception, exc:
            exc.function_cls = function_cls
            exc.python_name = full_name
            raise
        else:
            yield created, function_cls, full_name


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

    name_to_use = '{0}Function'.format(name)
    return type(name_to_use, (models.Model,), attrs)


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

        fields = get_fields_by_name(self.model, '*')
        model = _create_model(
            model_name, execute_function, fields, app_label, module)
        return models.query.QuerySet(model, query.NonQuotingQuery(model))

    def get_query_set(self):
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
