django-postgres
===============

Adds first-class support for [PostgreSQL][] features to the Django ORM.

Planned features include:

*   [Arrays][pg-arrays]
*   [Enums][pg-enums]
*   [Constraints][pg-constraints]
*   [Triggers][pg-triggers]
*   [Domains][pg-domains]
*   [Composite Types][pg-ctypes]
*   [Views][pg-views]

[postgresql]: http://www.postgresql.org/
[pg-arrays]: http://www.postgresql.org/docs/9.1/static/arrays.html
[pg-enums]: http://www.postgresql.org/docs/9.1/static/datatype-enum.html
[pg-constraints]: http://www.postgresql.org/docs/9.1/static/ddl-constraints.html
[pg-triggers]: http://www.postgresql.org/docs/9.1/static/sql-createtrigger.html
[pg-domains]: http://www.postgresql.org/docs/9.1/static/sql-createdomain.html
[pg-ctypes]: http://www.postgresql.org/docs/9.1/static/rowtypes.html
[pg-views]: http://www.postgresql.org/docs/9.1/static/sql-createview.html

Obviously this is quite a large project, but I think it would provide a huge
amount of value to Django developers.

Why?
----

PostgreSQL is an excellent data store, with a host of useful and
efficiently-implemented features. Unfortunately these features are not exposed
through Django's ORM, primarily because the framework has to support several
SQL backends and so can only provide a set of features common to all of them.

The features made available here replace some of the following practices:

-  Manual denormalization on `save()` (such that model saves may result in
   three or more separate queries).
-  Sequences represented by a one-to-many, with an `order` integer field.
-  Complex types represented by JSON in a text field.

Example
-------

The following represents a whirlwind tour of potential features of the project:

```python
from django.db import models
import django_postgres as pg


USStates = pg.Enum('states_of_the_usa', ['AL', ..., 'WY'])


class Address(pg.CompositeType):
    line1 = models.CharField(max_length=100)
    line2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    state = USStates()
    country = models.CharField(max_length=100)


class USPhoneNumber(pg.Domain):
    data_type = models.CharField(max_length=10)
    constraints = [
      r"VALUE ~ '^\d{3}-?\d{3}-?\d{4}$'"
    ]


class Customer(models.Model):
    name = models.CharField(max_length=100)
    shipping_address = Address()
    telephone_numbers = pg.Array(USPhoneNumber())
    is_preferred = models.BooleanField(default=False)


class PreferredCustomer(pg.View):
    projection = ['myapp.Customer.*']
    sql = """SELECT * FROM myapp_customer WHERE is_preferred = TRUE;"""
```

The SQL produced by this might look like:

```postgresql
CREATE TYPE states_of_the_usa AS ENUM ('AL', ..., 'WY');

CREATE TYPE myapp_address AS (
    line1 varchar(100),
    line2 varchar(100),
    city varchar(100),
    zip_code varchar(10),
    state states_of_the_usa,
    country varchar(100)
);

CREATE DOMAIN myapp_usphonenumber AS varchar(10)
    CHECK(VALUE ~ '^\d{3}-?\d{3}-?\d{4}$');

CREATE TABLE myapp_customer (
    id SERIAL PRIMARY KEY,
    shipping_address myapp_address,
    telephone_numbers myapp_usphonenumber[]
);

CREATE VIEW myapp_preferredcustomer AS
SELECT * FROM myapp_customer WHERE is_preferred = TRUE;
```

To create all your views, run ``python manage.py sync_pgviews``
