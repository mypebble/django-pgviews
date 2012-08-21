from django.db import models
import django_postgres


class BloomFilter(models.Model):
    name = models.CharField(max_length=100)
    bitmap = django_postgres.BitStringField(max_length=8)
