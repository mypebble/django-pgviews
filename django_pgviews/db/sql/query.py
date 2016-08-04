from django.db import connections
from django.db.models.sql import query

from django_pgviews.db.sql import compiler


class NonQuotingQuery(query.Query):
    """Query class that uses the NonQuotingCompiler.
    """
    def get_compiler(self, using=None, connection=None):
        """Get the NonQuotingCompiler object.
        """
        if using is None and connection is None:
            raise ValueError('Need either using or connection')
        if using:
            connection = connections[using]

        for alias, annotation in self.annotation_select.items():
            connection.ops.check_expression_support(annotation)

        return compiler.NonQuotingCompiler(self, connection, using)
