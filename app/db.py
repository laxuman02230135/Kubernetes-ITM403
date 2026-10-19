"""Database settings come from Kubernetes environment variables."""
import os

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=2,
        options="-c statement_timeout=3000",
        row_factory=dict_row,
    )
