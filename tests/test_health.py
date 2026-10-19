"""Verify health behaviour during a database outage without disrupting PostgreSQL."""
import sys
import unittest
from unittest.mock import patch

import psycopg

sys.path.insert(0, "/app")
from app import app


class HealthBehaviour(unittest.TestCase):
    def test_database_outage_affects_readiness_but_not_liveness(self):
        with patch("app.connect", side_effect=psycopg.OperationalError("test outage")) as database:
            client = app.test_client()
            self.assertEqual(client.get("/healthz").status_code, 200)
            database.assert_not_called()
            response = client.get("/ready")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json, {"error": "Database temporarily unavailable."})
            database.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
