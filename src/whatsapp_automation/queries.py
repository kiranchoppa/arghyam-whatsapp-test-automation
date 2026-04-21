"""Central store for all PostgreSQL query strings.

Each query is a named module-level constant so it can be imported by name.
Schema and table identifiers use Python str.format() placeholders ({schema}, {table})
because psycopg2 cannot parameterise identifiers; those values always come from
trusted env vars, never from user input.
Runtime data (tenant_id, config_key, etc.) use %(name)s psycopg2 placeholders.
"""

# ---------------------------------------------------------------------------
# Tenant config queries
# ---------------------------------------------------------------------------

GET_TENANT_CONFIG_VALUE = """
SELECT config_value
FROM {schema}.{table}
WHERE tenant_id = %(tenant_id)s
  AND config_key = %(config_key)s
  AND deleted_at IS NULL;
"""
