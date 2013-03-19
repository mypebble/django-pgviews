#!/bin/bash

DATABASE_URL="postgresql://localhost/django_postgres_viewtest"
rm -Rf test__views/
DROP_CMD=$(psql -P format=unaligned -P tuples_only -d "$DATABASE_URL" -c "select 'DROP TABLE \"' || array_to_string(array_agg(tablename), '\", \"') || '\" CASCADE;' from pg_tables where schemaname = 'public';")
echo "$DROP_CMD"
psql -d "$DATABASE_URL" -c "$DROP_CMD"
