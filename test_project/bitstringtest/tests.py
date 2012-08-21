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


class BitStringExpressionTest(TestCase):

    def test_can_update_bitstrings_atomically(self):
        models.BloomFilter.objects.create(name='foo')
        models.BloomFilter.objects.create(name='bar')

        models.BloomFilter.objects \
                .filter(name='foo') \
                .update(bitmap=B('bitmap') | Bits('0b10100101'))

        assert models.BloomFilter.objects.get(name='foo').bitmap.bin == '10100101'
        assert models.BloomFilter.objects.get(name='bar').bitmap.bin == '00000000'
