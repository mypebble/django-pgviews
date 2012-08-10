django-postgres
===============

Adds first-class support for [PostgreSQL][] features to the Django ORM.

Planned features include:

*   [Arrays][pg-arrays]
*   [Enums][pg-enums]
*   [Constraints][pg-constraints]
*   [Domains][pg-domains]
*   [Composite Types][pg-ctypes]
*   [Views][pg-views]

[postgresql]: http://www.postgresql.org/
[pg-arrays]: http://www.postgresql.org/docs/9.1/static/arrays.html
[pg-enums]: http://www.postgresql.org/docs/9.1/static/datatype-enum.html
[pg-constraints]: http://www.postgresql.org/docs/9.1/static/ddl-constraints.html
[pg-domains]: http://www.postgresql.org/docs/9.1/static/sql-createdomain.html
[pg-ctypes]: http://www.postgresql.org/docs/9.1/static/rowtypes.html
[pg-views]: http://www.postgresql.org/docs/9.1/static/sql-createview.html

Obviously this is quite a large project, but I think it would provide a large
amount of value to Django developers.

Example
-------

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
    shipping_address = Address()
    telephone_numbers = pg.Array(USPhoneNumber())
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
```
