===========
Bit Strings
===========

Postgres has a `bit string`_ type, which is exposed by django-postgres as
:class:`~django_postgres.BitStringField` and the
:class:`~django_postgres.BitStringExpression` helper (aliased as
``django_postgres.B``). The representation of bit strings in Python is handled
by the `python-bitstring`_ library (a dependency of ``django-postgres``).

.. _bit string: http://www.postgresql.org/docs/9.1/static/arrays.html
.. _python-bitstring: http://packages.python.org/bitstring


Quickstart
==========

Given the following ``models.py``::

    from django.db import models
    import django_postgres

    class BloomFilter(models.Model):
        name = models.CharField(max_length=100)
        bitmap = django_postgres.BitStringField(max_length=8)

You can create objects with bit strings, and update them like so::

    >>> from django_postgres import Bits
    >>> from models import BloomFilter

    >>> bloom = BloomFilter.objects.create(name='test')
    INSERT INTO myapp_bloomfilter
      (name, bitmap) VALUES ('test', B'00000000')
      RETURNING myapp_bloomfilter.id;

    >>> print bloom.bitmap
    Bits('0x00')
    >>> bloom.bitmap |= Bits(bin='00100000')
    >>> print bloom.bitmap
    Bits('0x20')

    >>> bloom.save(force_update=True)
    UPDATE myapp_bloomfilter SET bitmap = B'00100000'
     WHERE myapp_bloomfilter.id = 1;

Several query lookups are defined for filtering on bit strings. Standard
equality::

    >>> BloomFilter.objects.filter(bitmap='00100000')
    SELECT * FROM myapp_bloomfilter WHERE bitmap = B'00100000';

You can also test against bitwise comparison operators (``and``, ``or`` and
``xor``). The SQL produced is slightly convoluted, due to the few functions
provided by Postgres::

    >>> BloomFilter.objects.filter(bitmap__and='00010000')
    SELECT * FROM myapp_bloomfilter WHERE position(B'1' IN bitmap & B'00010000') > 0
    >>> BloomFilter.objects.filter(bitmap__or='00010000')
    SELECT * FROM myapp_bloomfilter WHERE position(B'1' IN bitmap | B'00010000') > 0
    >>> BloomFilter.objects.filter(bitmap__xor='00010000')
    SELECT * FROM myapp_bloomfilter WHERE position(B'1' IN bitmap # B'00010000') > 0

Finally, you can also test the zero-ness of left- and right-shifted bit
strings::

    >>> BloomFilter.objects.filter(bitmap__lshift=3)
    SELECT * FROM myapp_bloomfilter WHERE position(B'1' IN bitmap << 3) > 0
    >>> BloomFilter.objects.filter(bitmap__rshift=3)
    SELECT * FROM myapp_bloomfilter WHERE position(B'1' IN bitmap >> 3) > 0


Bit String Fields
=================

.. class:: django_postgres.BitStringField(max_length=1[, varying=False, ...])

  A bit string field, represented by the Postgres ``BIT`` or ``VARBIT`` types.

  :param max_length:
    The length (in bits) of this field.
  :param varying:
    Use a ``VARBIT`` instead of ``BIT``. Not recommended; it may cause strange
    querying behavior or length mismatch errors.

  If ``varying`` is True and ``max_length`` is ``None``, a ``VARBIT`` of
  unlimited length will be created.

  The default value of a :class:`BitStringField` is chosen as follows:

  *  If a ``default`` kwarg is provided, that value is used.
  *  Otherwise, if ``null=True``, the default value is ``None``.
  *  Otherwise, if the field is not a ``VARBIT``, it defaults to an all-zero
     bit string of ``max_length`` (remember, the default length is 1).
  *  Finally, all other cases will default to a single ``0``.

  All other parameters (``db_column``, ``help_text``, etc.) behave as standard
  for a Django field.


Bit String Expressions
======================

It's useful to be able to atomically modify bit strings in the database, in a
manner similar to Django's `F-expressions <https://docs.djangoproject.com/en/dev/topics/db/queries/#query-expressions>`_.
For this reason, :class:`~django_postgres.BitStringExpression` is provided,
and aliased as ``django_postgres.B`` for convenience.

Here's a short example::

    >>> from django_postgres import B
    >>> BloomFilter.objects.filter(id=1).update(bitmap=B('bitmap') | '00001000')
    UPDATE myapp_bloomfilter SET bitmap = bitmap | B'00001000'
     WHERE myapp_bloomfilter.id = 1;
    >>> bloom = BloomFilter.objects.get(id=1)
    >>> print bloom.bitmap
    Bits('0x28')

.. class:: django_postgres.BitStringExpression(field_name)

  The following operators are supported:

  -   Concatenation (``+``)
  -   Bitwise AND (``&``)
  -   Bitwise OR (``|``)
  -   Bitwise XOR (``^``)
  -   (Unary) bitwise NOT (``~``)
  -   Bitwise left-shift (``<<``)
  -   Bitwise right-shift (``>>``)
