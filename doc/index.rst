===============
django-postgres
===============

Adds first-class support for `PostgreSQL <http://www.postgresql.org/>`_
features to the Django ORM.

Planned features include:

-  `Arrays <http://www.postgresql.org/docs/9.1/static/arrays.html>`_
-  `Enums <http://www.postgresql.org/docs/9.1/static/datatype-enum.html>`_
-  `Constraints <http://www.postgresql.org/docs/9.1/static/ddl-constraints.html>`_
-  `Triggers <http://www.postgresql.org/docs/9.1/static/sql-createtrigger.html>`_
-  `Domains <http://www.postgresql.org/docs/9.1/static/sql-createdomain.html>`_
-  `Composite Types <http://www.postgresql.org/docs/9.1/static/rowtypes.html>`_
-  `Views <http://www.postgresql.org/docs/9.1/static/sql-createview.html>`_

Obviously this is quite a large project, but I think it would provide a huge
amount of value to Django developers.


Why?
====

PostgreSQL is an excellent data store, with a host of useful and
efficiently-implemented features. Unfortunately these features are not exposed
through Django's ORM, primarily because the framework has to support several
SQL backends and so can only provide a set of features common to all of them.

The features made available here replace some of the following practices:

-  Manual denormalization on ``save()`` (such that model saves may result in
   three or more separate queries).
-  Sequences represented by a one-to-many, with an ``order`` integer field.
-  Complex types represented by JSON in a text field.


Contents
========

This is a WIP, so the following list may grow and change over time.

.. toctree::
   :maxdepth: 4

   views


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

