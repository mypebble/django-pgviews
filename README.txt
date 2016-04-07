SQL Views for Postgres
======================

|Gitter| |Circle CI|

Adds first-class support for `PostgreSQL
Views <http://www.postgresql.org/docs/9.1/static/sql-createview.html>`__
in the Django ORM

This project is a fork of
`django-postgres <https://github.com/zacharyvoase/django-postgres>`__
with support for specific data types stripped out, in favour of focusing
support on maintaining SQL View compatibility with the latest versions
of Django.

This project will eventually be superseded by the work being done on
`django.contrib.postgres <https://docs.djangoproject.com/en/dev/ref/contrib/postgres/>`__

Installation
------------

Install via pip:

::

    pip install django-pgviews

Add to installed applications in settings.py:

.. code:: python

    INSTALLED_APPS = (
      # ...
      'django_pgviews',
    )

Examples
--------

.. code:: python

    from django.db import models

    from django_pgviews import view as pg


    class Customer(models.Model):
        name = models.CharField(max_length=100)
        post_code = models.CharField(max_length=20)
        is_preferred = models.BooleanField(default=False)

        class Meta:
            app_label = 'myapp'

    class PreferredCustomer(pg.View):
        projection = ['myapp.Customer.*',]
        dependencies = ['myapp.OtherView',]
        sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

        class Meta:
          app_label = 'myapp'
          db_table = 'myapp_preferredcustomer'
          managed = False

**NOTE** It is important that we include the ``managed = False`` in the
``Meta`` so Django 1.7 migrations don't attempt to create DB tables for
this view.

The SQL produced by this might look like:

.. code:: postgresql

    CREATE VIEW myapp_preferredcustomer AS
    SELECT * FROM myapp_customer WHERE is_preferred = TRUE;

To create all your views, run ``python manage.py sync_pgviews``

You can also specify field names, which will map onto fields in your
View:

.. code:: python

    from django_pgviews import view as pg


    VIEW_SQL = """
        SELECT name, post_code FROM myapp_customer WHERE is_preferred = TRUE
    """


    class PreferredCustomer(pg.View):
        name = models.CharField(max_length=100)
        post_code = models.CharField(max_length=20)

        sql = VIEW_SQL

Features
--------

Dependencies
~~~~~~~~~~~~

You can specify other views you depend on. This ensures the other views
are installed beforehand.

Note: Views are synced after the Django application has migrated and
adding models to the dependency list will cause syncing to fail.

Example:

.. code:: python

    from django_pgviews import view as pg

    class PreferredCustomer(pg.View):
        dependencies = ['myapp.OtherView',]
        sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

        class Meta:
          app_label = 'myapp'
          db_table = 'myapp_preferredcustomer'
          managed = False

Materialized Views
~~~~~~~~~~~~~~~~~~

Postgres 9.3 and up supports `materialized
views <http://www.postgresql.org/docs/current/static/sql-creatematerializedview.html>`__
which allow you to cache the results of views, potentially allowing them
to load faster.

However, you do need to manually refresh the view. To do this
automatically, you can attach
`signals <https://docs.djangoproject.com/en/1.8/ref/signals/>`__ and
call the refresh function.

Example:

.. code:: python

    from django_pgviews import view as pg


    VIEW_SQL = """
        SELECT name, post_code FROM myapp_customer WHERE is_preferred = TRUE
    """

    class Customer(models.Model):
        name = models.CharField(max_length=100)
        post_code = models.CharField(max_length=20)
        is_preferred = models.BooleanField(default=True)


    class PreferredCustomer(pg.MaterializedView):
        name = models.CharField(max_length=100)
        post_code = models.CharField(max_length=20)

        sql = VIEW_SQL


    @receiver(post_save, sender=Customer)
    def customer_saved(sender, action=None, instance=None, **kwargs):
        PreferredCustomer.refresh()

Custom Schema
~~~~~~~~~~~~~

You can define any table name you wish for your views. They can even
live inside your own custom `PostgreSQL
schema <http://www.postgresql.org/docs/current/static/ddl-schemas.html>`__.

.. code:: python

    from django_pgviews import view as pg


    class PreferredCustomer(pg.View):
        sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

        class Meta:
          db_table = 'my_custom_schema.preferredcustomer'
          managed = False

Django Compatibility
--------------------

.. raw:: html

   <table>
     <thead>
       <tr>
         <th>

Django Version

.. raw:: html

   </th>
         <th>

Django-PGView Version

.. raw:: html

   </th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td>

1.4 and down

.. raw:: html

   </td>
         <td>

Unsupported

.. raw:: html

   </td>
       </tr>
       <tr>
         <td>

1.5

.. raw:: html

   </td>
         <td>

0.0.1

.. raw:: html

   </td>
       </tr>
       <tr>
         <td>

1.6

.. raw:: html

   </td>
         <td>

0.0.3

.. raw:: html

   </td>
       </tr>
       <tr>
         <td>

1.7

.. raw:: html

   </td>
         <td>

0.0.4

.. raw:: html

   </td>
       </tr>
       <tr>
         <td>

1.9

.. raw:: html

   </td>
         <td>

0.0.6

.. raw:: html

   </td>
       </tr>
     </tbody>
   </table>

Django 1.7 Note
~~~~~~~~~~~~~~~

Django 1.7 changed how models are loaded so that it's no longer possible
to do ``sql = str(User.objects.all().query)`` because the dependent
models aren't yet loaded by Django.

Django 1.9 Note
~~~~~~~~~~~~~~~

You now have to use the ``.view`` module directly.

Python 3 Support
----------------

Django PGViews supports Python 3 in versions 0.0.7 and above.

.. |Gitter| image:: https://badges.gitter.im/Join%20Chat.svg
   :target: https://gitter.im/mypebble/django-pgviews?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
.. |Circle CI| image:: https://circleci.com/gh/mypebble/django-pgviews.png
   :target: https://circleci.com/gh/mypebble/django-pgviews
