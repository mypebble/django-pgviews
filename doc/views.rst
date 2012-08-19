Views
=====

For more info on Postgres views, see the `official Postgres docs
<http://www.postgresql.org/docs/9.1/static/sql-createview.html>`_. Effectively,
views are named queries which can be accessed as if they were regular database
tables.

Quickstart
----------

Given the following view in SQL:

.. code-block:: sql

    CREATE OR REPLACE VIEW myapp_viewname AS
    SELECT * FROM myapp_table WHERE condition;

You can create this view by just subclassing :class:`django_postgres.View`. In
``myapp/models.py``::

    import django_postgres

    class ViewName(django_postgres.View):
        projection = ['myapp.Table.*']
        sql = """SELECT * FROM myapp_table WHERE condition"""

:class:`View`
-------------

.. class:: django_postgres.View

  Inherit from this class to define and interact with your database views.

  You need to either define the field types manually (using standard Django
  model fields), or use :attr:`projection` to copy field definitions from other
  models.

  .. attribute:: sql

    The SQL for this view (typically a ``SELECT`` query). This attribute is
    optional, but if present, the view will be created on ``syncdb`` (which is
    probably what you want).

  .. attribute:: projection

    A list of field specifiers which will be automatically copied to this view.
    If your view directly presents fields from another table, you can
    effectively 'import' those here, like so::

        projection = ['auth.User.username', 'auth.User.password',
                      'admin.LogEntry.change_message']

    If your view represents a subset of rows in another table (but the same
    columns), you might want to import all the fields from that table, like
    so::

        projection = ['myapp.Table.*']

    Of course you can mix wildcards with normal field specifiers::

        projection = ['myapp.Table.*', 'auth.User.username', 'auth.User.email']

Migrations
----------

Views play well with South migrations; just create the view using raw SQL in a
schema migration:

.. code-block:: bash

    $ ./manage.py schemamigration --empty myapp create_view_viewname
    Created 0001_create_view_latest_override.py.
    $ edit myapp/migrations/0001_create_view_viewname.py

In the migration file::

    def forwards(self, orm):
        db.execute('''CREATE OR REPLACE VIEW myapp_viewname AS
                      SELECT * FROM myapp_table WHERE condition;''')

    def backwards(self, orm):
        db.execute('''DROP VIEW myapp_viewname;''')
