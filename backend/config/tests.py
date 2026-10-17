from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok_with_database_connected(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})

    def test_health_check_requires_no_authentication(self):
        response = self.client.get("/health/")
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
