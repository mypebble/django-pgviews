from django.db.models.sql import compiler


class NonQuotingCompiler(compiler.SQLCompiler):
    """Compiler for functions/statements that doesn't quote the db_table
    attribute.
    """
    def quote_name_unless_alias(self, name):
        """Don't quote the name.
        """
        if name in self.quote_cache:
            return self.quote_cache[name]

        self.quote_cache[name] = name
        return name

    def as_sql(self, *args, **kwargs):
        """Messy hack to create some table aliases for us.
        """
        self.query.table_map[self.query.model._meta.db_table] = ['']
        return super(NonQuotingCompiler, self).as_sql(*args, **kwargs)
