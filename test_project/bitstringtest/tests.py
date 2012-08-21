from django.test import TestCase
from django_postgres import Bits, B

import models


class SimpleTest(TestCase):

    def test_can_create_bitstrings(self):
        bloom = models.BloomFilter.objects.create(name='foo')
        # Default bit string is all zeros.
        assert bloom.bitmap.bin == ('0' * 8)

    def test_can_change_bitstrings(self):
        bloom = models.BloomFilter.objects.create(name='foo')
        bloom.bitmap = Bits(bin='01011010')
        bloom.save()

        refetch = models.BloomFilter.objects.get(id=bloom.id)
        assert refetch.bitmap.bin == '01011010'

    def test_can_search_for_equal_bitstrings(self):
        models.BloomFilter.objects.create(name='foo', bitmap='01011010')

        results = models.BloomFilter.objects.filter(bitmap='01011010')
        assert results.count() == 1
        assert results[0].name == 'foo'


class BitStringExpressionUpdateTest(TestCase):

    def check_update(self, initial, expression, result):
        models.BloomFilter.objects.create(name='foo', bitmap=initial)
        models.BloomFilter.objects.create(name='bar')

        models.BloomFilter.objects \
                .filter(name='foo') \
                .update(bitmap=expression)

        assert models.BloomFilter.objects.get(name='foo').bitmap.bin == result
        assert models.BloomFilter.objects.get(name='bar').bitmap.bin == '00000000'

    def test_or(self):
        self.check_update('00000000',
                          B('bitmap') | Bits('0b10100101'),
                          '10100101')

    def test_and(self):
        self.check_update('10100101',
                          B('bitmap') & Bits('0b11000011'),
                          '10000001')

    def test_xor(self):
        self.check_update('10100101',
                          B('bitmap') ^ Bits('0b11000011'),
                          '01100110')

    def test_not(self):
        self.check_update('10100101',
                          ~B('bitmap'),
                          '01011010')

    def test_lshift(self):
        self.check_update('10100101',
                          B('bitmap') << 3,
                          '00101000')

    def test_rshift(self):
        self.check_update('10100101',
                          B('bitmap') >> 3,
                          '00010100')
