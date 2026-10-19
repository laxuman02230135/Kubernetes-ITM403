"""Initialise the shared schema before each API Pod starts."""
from db import connect

with connect() as connection:
    # Serialise schema creation when two init containers start together.
    connection.execute("SELECT pg_advisory_xact_lock(2230135)")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name varchar(100) NOT NULL,
            email varchar(254) NOT NULL UNIQUE
        )
    """)
print("Users table is ready.")
