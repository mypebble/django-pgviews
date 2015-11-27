SQL Views for Postgres
======================
[![Gitter](https://badges.gitter.im/Join Chat.svg)](https://gitter.im/mypebble/django-pgviews?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Circle CI](https://circleci.com/gh/mypebble/django-pgviews.png)](https://circleci.com/gh/mypebble/django-pgviews)

Adds first-class support for [PostgreSQL Views][pg-views] in the Django ORM

This project is a fork of [django-postgres][django-postgres] with support for
specific data types stripped out, in favour of focusing support on maintaining
SQL View compatibility with the latest versions of Django.

This project will eventually be superseded by the work being done on
[django.contrib.postgres][django-contrib-docs]

[django-postgres]: https://github.com/zacharyvoase/django-postgres
[pg-views]: http://www.postgresql.org/docs/9.1/static/sql-createview.html
[django-contrib-docs]: https://docs.djangoproject.com/en/dev/ref/contrib/postgres/


Installation
------------

Install via pip:

    pip install django-pgviews

Add to installed applications in settings.py:

```python
INSTALLED_APPS = (
  # ...
  'django_pgviews',
)
```

Examples
-------

```python
from django.db import models

import django_postgres as pg


class Customer(models.Model):
    name = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)
    is_preferred = models.BooleanField(default=False)

    class Meta:
        app_label = 'myapp'

class PreferredCustomer(pg.View):
    projection = ['myapp.Customer.*',]
    dependencies = ['myapp.Customer',]
    sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

    class Meta:
      app_label = 'myapp'
      db_table = 'myapp_preferredcustomer'
      managed = False
```

**NOTE** It is important that we include the `managed = False` in the `Meta` so
Django 1.7 migrations don't attempt to create DB tables for this view.

The SQL produced by this might look like:

```postgresql
CREATE VIEW myapp_preferredcustomer AS
SELECT * FROM myapp_customer WHERE is_preferred = TRUE;
```

To create all your views, run ``python manage.py sync_pgviews``

You can also specify field names, which will map onto fields in your View:

```python
import django_postgres as pg


VIEW_SQL = """
    SELECT name, post_code FROM myapp_customer WHERE is_preferred = TRUE
"""


class PreferredCustomer(pg.View):
    name = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)

    sql = VIEW_SQL
```

Django Compatibility
--------------------

<table>
  <thead>
    <tr>
      <th>Django Version</th>
      <th>Django-PGView Version</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1.4 and down</td>
      <td>Unsupported</td>
    </tr>
    <tr>
      <td>1.5</td>
      <td>0.0.1</td>
    </tr>
    <tr>
      <td>1.6</td>
      <td>0.0.3</td>
    </tr>
    <tr>
      <td>1.7</td>
      <td>0.0.4</td>
    </tr>
  </tbody>
</table>

### Materialized Views

Postgres 9.3 and up supports [materialized views](http://www.postgresql.org/docs/current/static/sql-creatematerializedview.html)
which allow you to cache the results of views, potentially allowing them
to load faster.

However, you do need to manually refresh the view. To do this automatically,
you can attach [signals](https://docs.djangoproject.com/en/1.8/ref/signals/)
and call the refresh function.

Example:

```python
import django_postgres as pg


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
```

### Django 1.7 Note

Django 1.7 changed how models are loaded so that it's no longer possible to do
`sql = str(User.objects.all().query)` because the dependent models aren't
yet loaded by Django.
