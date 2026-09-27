"""
Integration tests for Flask Web App and REST API
"""

import unittest
import json
from app import create_app

class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.app = create_app(simulation_mode=True)
        self.client = self.app.test_client()

    def test_unauthorized_access(self):
        # API requires session login
        res = self.client.get("/api/scooter/status")
        self.assertEqual(res.status_code, 401)

    def test_login_flow(self):
        # Login with default admin credentials
        res = self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Now API request should succeed
        res = self.client.get("/api/scooter/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["connected"])
        self.assertEqual(data["battery_percent"], 78)
        self.assertEqual(data["estimated_range_km"], 82)

    def test_command_requires_pin_and_confirmation(self):
        # Login
        self.client.post("/login", data={"username": "admin", "password": "admin123"})

        # Try lock without confirmation
        res = self.client.post("/api/scooter/lock", json={})
        self.assertEqual(res.status_code, 400)

        # Try lock with wrong PIN
        res = self.client.post("/api/scooter/lock", json={
            "confirmed": True,
            "pin": "0000"
        })
        self.assertEqual(res.status_code, 400)

        # Lock with valid PIN
        res = self.client.post("/api/scooter/lock", json={
            "confirmed": True,
            "pin": "1234"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["command"], "lock")

    def test_history_endpoints(self):
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/api/history/battery")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)

if __name__ == "__main__":
    unittest.main()
