# SQL Views for Postgres

[![Gitter](https://badges.gitter.im/Join Chat.svg)](https://gitter.im/mypebble/django-pgviews?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Circle CI](https://circleci.com/gh/mypebble/django-pgviews.png)](https://circleci.com/gh/mypebble/django-pgviews)

Adds first-class support for [PostgreSQL Views][pg-views] in the Django ORM

[pg-views]: http://www.postgresql.org/docs/9.1/static/sql-createview.html


## Installation

Install via pip:

    pip install django-pgviews

Add to installed applications in settings.py:

```python
INSTALLED_APPS = (
  # ...
  'django_pgviews',
)
```

## Examples

```python
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
from django_pgviews import view as pg


VIEW_SQL = """
    SELECT name, post_code FROM myapp_customer WHERE is_preferred = TRUE
"""


class PreferredCustomer(pg.View):
    name = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)

    sql = VIEW_SQL
```

## Usage

To map onto a View, simply extend `pg_views.view.View`, assign SQL to the
`sql` argument and define a `db_table`. You must _always_ set `managed = False`
on the `Meta` class.

Views can be created in a number of ways:

1. Define fields to map onto the VIEW output
2. Define a projection that describes the VIEW fields

### Define Fields

Define the fields as you would with any Django Model:

```python
from django_pgviews import view as pg


VIEW_SQL = """
    SELECT name, post_code FROM myapp_customer WHERE is_preferred = TRUE
"""


class PreferredCustomer(pg.View):
    name = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)

    sql = VIEW_SQL

    class Meta:
      managed = False
      db_table = 'my_sql_view'
```

### Define Projection

`django-pgviews` can take a projection to figure out what fields it needs to
map onto for a view. To use this, set the `projection` attribute:

```python
from django_pgviews import view as pg


class PreferredCustomer(pg.View):
    projection = ['myapp.Customer.*',]
    sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

    class Meta:
      db_table = 'my_sql_view'
      managed = False
```

This will take all fields on `myapp.Customer` and apply them to
`PreferredCustomer`

## Features

### Updating Views

Sometimes your models change and you need your Database Views to reflect the new
data. Updating the View logic is as simple as modifying the underlying SQL and
running:

```
python manage.py sync_pgviews --force
```

This will forcibly update any views that conflict with your new SQL.

### Dependencies

You can specify other views you depend on. This ensures the other views are
installed beforehand. Using dependencies also ensures that your views get
refreshed correctly when using `sync_pgviews --force`.

**Note:** Views are synced after the Django application has migrated and adding
models to the dependency list will cause syncing to fail.

Example:

```python
from django_pgviews import view as pg

class PreferredCustomer(pg.View):
    dependencies = ['myapp.OtherView',]
    sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

    class Meta:
      app_label = 'myapp'
      db_table = 'myapp_preferredcustomer'
      managed = False
```

### Materialized Views

Postgres 9.3 and up supports [materialized views](http://www.postgresql.org/docs/current/static/sql-creatematerializedview.html)
which allow you to cache the results of views, potentially allowing them
to load faster.

However, you do need to manually refresh the view. To do this automatically,
you can attach [signals](https://docs.djangoproject.com/en/1.8/ref/signals/)
and call the refresh function.

Example:

```python
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
```

Postgres 9.4 and up allow materialized views to be refreshed concurrently, without blocking reads, as long as a
unique index exists on the materialized view. To enable concurrent refresh, specify the name of a column that can be
used as a unique index on the materialized view. Unique index can be defined on more than one column of a materialized 
view. Once enabled, passing `concurrently=True` to the model's refresh method will result in postgres performing the 
refresh concurrently. (Note that the refresh method itself blocks until the refresh is complete; concurrent refresh is 
most useful when materialized views are updated in another process or thread.)

Example:

```python
from django_pgviews import view as pg


VIEW_SQL = """
    SELECT id, name, post_code FROM myapp_customer WHERE is_preferred = TRUE
"""

class PreferredCustomer(pg.MaterializedView):
    concurrent_index = 'id, post_code'
    sql = VIEW_SQL

    name = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)


@receiver(post_save, sender=Customer)
def customer_saved(sender, action=None, instance=None, **kwargs):
    PreferredCustomer.refresh(concurrently=True)
```

### Custom Schema

You can define any table name you wish for your views. They can even live inside your own custom
[PostgreSQL schema](http://www.postgresql.org/docs/current/static/ddl-schemas.html).

```python
from django_pgviews import view as pg


class PreferredCustomer(pg.View):
    sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""

    class Meta:
      db_table = 'my_custom_schema.preferredcustomer'
      managed = False
```

### Sync Listeners

django-pgviews 0.5.0 adds the ability to listen to when a `post_sync` event has
occurred.

#### `view_synced`

Fired every time a VIEW is synchronised with the database.

Provides args:
* `sender` - View Class
* `update` - Whether the view to be updated
* `force` - Whether `force` was passed
* `status` - The result of creating the view e.g. `EXISTS`, `FORCE_REQUIRED`
* `has_changed` - Whether the view had to change

#### `all_views_synced`

Sent after all Postgres VIEWs are synchronised.

Provides args:
* `sender` - Always `None`


## Django Compatibility

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
    <tr>
      <td>1.9</td>
      <td>0.1.0</td>
    </tr>
    <tr>
      <td>1.10</td>
      <td>0.2.0</td>
    </tr>
  </tbody>
</table>

### Django 1.7 Note

Django 1.7 changed how models are loaded so that it's no longer possible to do
`sql = str(User.objects.all().query)` because the dependent models aren't
yet loaded by Django.

### Django 1.9 Note

You now have to use the `.view` module directly.

### Django 1.10 Note

When updating to Django 1.10, if you see `AttributeError: can't set attribute`
when you try to migrate or run tests, you need to check your migrations for
where `_base_manager` or `_default_manager` get set on the model and replace it
with `objects` inside the migration.

This also applies to [Django MPTT](https://django-mptt.github.io/django-mptt/upgrade.html#id1)
who have covered this in a bit more detail.

## Python 3 Support

Django PGViews supports Python 3 in versions 0.0.7 and above.
