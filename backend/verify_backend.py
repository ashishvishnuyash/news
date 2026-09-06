import unittest
import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"

class TestNewspaperAPI(unittest.TestCase):
    def make_request(self, path, method="GET", body=None, headers=None):
        if headers is None:
            headers = {}
        if "Content-Type" not in headers and body is not None:
            headers["Content-Type"] = "application/json"
            
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=data,
            headers=headers,
            method=method
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                status_code = response.status
                response_body = response.read().decode("utf-8")
                return status_code, json.loads(response_body) if response_body else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_data = json.loads(err_body)
            except json.JSONDecodeError:
                err_data = err_body
            return e.code, err_data

    def login(self, username, password):
        status, res = self.make_request(
            "/api/auth/login",
            method="POST",
            body={"username": username, "password": password}
        )
        self.assertEqual(status, 200)
        self.assertIn("access_token", res)
        return res["access_token"]

    def test_01_health_and_settings(self):
        status, res = self.make_request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(res.get("status"), "healthy")

        # Test Public Settings
        status, settings = self.make_request("/api/settings")
        self.assertEqual(status, 200)
        self.assertEqual(settings.get("site_name"), "The Republic Bulletin")
        self.assertIn("breaking_news", settings)

    def test_02_superadmin_auth_and_settings_update(self):
        # Login as the seeded super admin
        token = self.login("rajiv_sharma", "password123")
        headers = {"Authorization": f"Bearer {token}"}

        status, me = self.make_request("/api/auth/me", headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(me.get("role"), "SUPER_ADMIN")

        # Super admin updates breaking news banner
        update_payload = {"breaking_news": "BREAKING: Market Hits New Record High"}
        status, res = self.make_request("/api/settings", method="PUT", body=update_payload, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(res.get("breaking_news"), "BREAKING: Market Hits New Record High")

    def test_03_journalist_workflow(self):
        token = self.login("arjun_verma", "password123")
        headers = {"Authorization": f"Bearer {token}"}
        
        article_payload = {
            "title": "Agentic Coding in Vintage Style",
            "content": "<p>Automating retro styled news platforms.</p>",
            "summary": "Short abstract.",
            "category": "Tech",
            "status": "DRAFT"
        }
        status, res = self.make_request(
            "/api/articles",
            method="POST",
            body=article_payload,
            headers=headers
        )
        self.assertEqual(status, 201)
        article_id = res.get("id")
        self.assertIsNotNone(article_id)
        
        # Submit draft
        status, res = self.make_request(
            f"/api/articles/{article_id}",
            method="PUT",
            body={"status": "SUBMITTED"},
            headers=headers
        )
        self.assertEqual(status, 200)
        
        # Editor approves and pins article
        editor_token = self.login("editor", "password123")
        editor_headers = {"Authorization": f"Bearer {editor_token}"}
        
        status, res = self.make_request(
            f"/api/articles/{article_id}",
            method="PUT",
            body={"status": "PUBLISHED", "is_pinned": True},
            headers=editor_headers
        )
        self.assertEqual(status, 200)
        self.assertEqual(res.get("status"), "PUBLISHED")
        self.assertTrue(res.get("is_pinned"))

if __name__ == "__main__":
    unittest.main()
