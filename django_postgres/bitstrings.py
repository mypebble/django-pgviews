from contextlib import closing

from bitstring import Bits
from django.db import models
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PGDatabaseWrapper
from django.db.backends.signals import connection_created
from psycopg2 import extensions as ext


__all__ = ['Bits', 'BitStringField', 'BitStringExpression']


def adapt_bits(bits):
    """psycopg2 adapter function for ``bitstring.Bits``.

    Encode SQL parameters from ``bitstring.Bits`` instances to SQL strings.
    """
    if bits.length % 4 == 0:
        return ext.AsIs("X'%s'" % (bits.hex,))
    return ext.AsIs("B'%s'" % (bits.bin,))
ext.register_adapter(Bits, adapt_bits)


def cast_bits(value, cur):
    """psycopg2 caster for bit strings.

    Turns query results from the database into ``bitstring.Bits`` instances.
    """
    if value is None:
        return None
    return Bits(bin=value)


def register_bitstring_types(connection):
    """Register the BIT and VARBIT casters on the provided connection.

    This ensures that BIT and VARBIT instances returned from the database will
    be represented in Python as ``bitstring.Bits`` instances.
    """
    with closing(connection.cursor()) as cur:
        cur.execute("SELECT NULL::BIT")
        bit_oid = cur.description[0].type_code
        cur.execute("SELECT NULL::VARBIT")
        varbit_oid = cur.description[0].type_code
    bit_caster = ext.new_type((bit_oid, varbit_oid), 'BIT', cast_bits)
    ext.register_type(bit_caster, connection)


def register_types_on_connection_creation(connection, sender, *args, **kwargs):
    if not issubclass(sender, PGDatabaseWrapper):
        return
    register_bitstring_types(connection.connection)
connection_created.connect(register_types_on_connection_creation)


class BitStringField(models.Field):

    """A Postgres bit string."""

    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.setdefault('max_length', 1)
        self.varying = kwargs.pop('varying', False)

        if 'default' in kwargs:
            default = kwargs.pop('default')
        elif kwargs.get('null', False):
            default = None
        elif self.max_length is not None and not self.varying:
            default = '0' * self.max_length
        else:
            default = '0'
        kwargs['default'] = self.to_python(default)

        super(BitStringField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        if self.varying:
            if self.max_length is not None:
                return 'VARBIT(%d)' % (self.max_length,)
            return 'VARBIT'
        elif self.max_length is not None:
            return 'BIT(%d)' % (self.max_length,)
        return 'BIT'

    def to_python(self, value):
        if value is None or isinstance(value, Bits):
            return value
        elif isinstance(value, basestring):
            if value.startswith('0x'):
                return Bits(hex=value)
            return Bits(bin=value)
        raise TypeError("Cannot coerce into bit string: %r" % (value,))

    def get_prep_value(self, value):
        return self.to_python(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return map(self.get_prep_value, value)
        raise TypeError("Lookup type %r not supported on bit strings" % lookup_type)

    def get_default(self):
        default = super(BitStringField, self).get_default()
        return self.to_python(default)


class BitStringExpression(models.expressions.F):

    ADD = '||'  # The Postgres concatenation operator.
    XOR = '#'
    LSHIFT = '<<'
    RSHIFT = '>>'
    NOT = '~'

    def __init__(self, field, *args, **kwargs):
        super(BitStringExpression, self).__init__(field, *args, **kwargs)
        self.lookup = field

    def __and__(self, other):
        return self.bitand(other)

    def __or__(self, other):
        return self.bitor(other)

    def __xor__(self, other):
        return self._combine(other, self.XOR, False)

    def __rxor__(self, other):
        return self._combine(other, self.XOR, True)

    def __lshift__(self, other):
        return self._combine(other, self.LSHIFT, False)

    def __rshift__(self, other):
        return self._combine(other, self.RSHIFT, False)

    def _unary(self, operator):
        # This is a total hack, but you need to combine a raw empty space with
        # the current node, in reverse order, with the connector being the
        # unary operator you want to apply.
        return self._combine(ext.AsIs(''), operator, True)

    def __invert__(self):
        return self._unary(self.NOT)
