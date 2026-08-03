"""Isolated end-to-end checks for auth, roles, publishing, and feature flags."""

import os
import tempfile
import unittest
from pathlib import Path

_TEMP_DIR = tempfile.TemporaryDirectory(prefix="republic-bulletin-tests-")
_DB_PATH = Path(_TEMP_DIR.name) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-only-secret-key-that-is-long-and-private"

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.auth import get_password_hash  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from sqlalchemy import func, select  # noqa: E402


class ApiWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )
        async with SessionLocal() as session:
            count = (await session.execute(select(func.count(User.id)))).scalar() or 0
            if count == 0:
                for username, role in [
                    ("reader_test", "READER"),
                    ("journalist_test", "JOURNALIST"),
                    ("editor_test", "EDITOR"),
                    ("admin_test", "ADMIN"),
                    ("publisher_test", "SUPER_ADMIN"),
                ]:
                    session.add(User(
                        username=username,
                        email=f"{username}@example.test",
                        hashed_password=get_password_hash("password123"),
                        role=role,
                    ))
                await session.commit()

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)
        await engine.dispose()

    async def login(self, username: str):
        response = await self.client.post(
            "/api/auth/login",
            json={"username": username, "password": "password123"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("HttpOnly", response.headers.get("set-cookie", ""))

    async def test_cookie_auth_and_full_editorial_workflow(self):
        await self.login("journalist_test")
        me = await self.client.get("/api/auth/me")
        self.assertEqual(me.json()["role"], "JOURNALIST")

        created = await self.client.post("/api/articles", json={
            "title": "A Verified Dispatch From the Test Desk",
            "content": "<p>A substantial clean body for readers.</p><script>alert(1)</script><p>End.</p>",
            "summary": "An isolated workflow verification.",
            "category": "Technology",
        })
        self.assertEqual(created.status_code, 201, created.text)
        article = created.json()
        self.assertNotIn("script", article["content"].lower())
        self.assertNotIn("alert(1)", article["content"])

        submitted = await self.client.put(
            f"/api/articles/{article['id']}", json={"status": "SUBMITTED"}
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)

        await self.login("editor_test")
        published = await self.client.put(
            f"/api/articles/{article['id']}", json={"status": "PUBLISHED"}
        )
        self.assertEqual(published.status_code, 200, published.text)
        self.assertEqual(published.json()["status"], "PUBLISHED")

        public = await self.client.get(f"/api/articles/{article['slug']}")
        self.assertEqual(public.status_code, 200, public.text)

        await self.login("reader_test")
        comment = await self.client.post(
            f"/api/articles/{article['slug']}/comments", json={"content": "A useful reader response."}
        )
        self.assertEqual(comment.status_code, 201, comment.text)
        comment_id = comment.json()["id"]
        edited = await self.client.put(
            f"/api/articles/{article['slug']}/comments/{comment_id}",
            json={"content": "An edited reader response."},
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        deleted = await self.client.delete(f"/api/articles/{article['slug']}/comments/{comment_id}")
        self.assertEqual(deleted.status_code, 200, deleted.text)

    async def test_privilege_boundaries_and_feature_flags(self):
        await self.login("admin_test")
        users = (await self.client.get("/api/admin/users")).json()
        reader_id = next(user["id"] for user in users if user["username"] == "reader_test")
        escalation = await self.client.put(
            f"/api/admin/users/{reader_id}/role", json={"role": "SUPER_ADMIN"}
        )
        self.assertEqual(escalation.status_code, 403)

        created_user = await self.client.post("/api/admin/users", json={
            "username": "crud_reader",
            "email": "crud@example.test",
            "password": "password123",
            "role": "READER",
            "bio": "Created by the administration test.",
        })
        self.assertEqual(created_user.status_code, 201, created_user.text)
        crud_id = created_user.json()["id"]
        updated_user = await self.client.put(
            f"/api/admin/users/{crud_id}", json={"bio": "Updated biography.", "is_active": False}
        )
        self.assertEqual(updated_user.status_code, 200, updated_user.text)
        self.assertFalse(updated_user.json()["is_active"])
        deleted_user = await self.client.delete(f"/api/admin/users/{crud_id}")
        self.assertEqual(deleted_user.status_code, 200, deleted_user.text)

        await self.login("publisher_test")
        settings = await self.client.put("/api/settings", json={
            "features": {
                "comments_enabled": False,
                "registration_open": False,
                "maintenance_mode": False,
            }
        })
        self.assertEqual(settings.status_code, 200, settings.text)

        registration = await self.client.post("/api/auth/register", json={
            "username": "closed_reader",
            "email": "closed@example.test",
            "password": "password123",
            "confirm_password": "password123",
        })
        self.assertEqual(registration.status_code, 403)

    async def test_journalist_can_upload_a_valid_cover_image(self):
        await self.login("journalist_test")
        # A small valid PNG signature is sufficient for the API's safe format gate.
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"test-cover-image"
        response = await self.client.post(
            "/api/media/images",
            files={"file": ("test-cover.png", image_bytes, "image/png")},
        )
        self.assertEqual(response.status_code, 201, response.text)

        image_url = response.json()["url"]
        self.assertTrue(image_url.startswith("http://testserver/media/"))
        image_name = image_url.rsplit("/", 1)[-1]
        image_path = Path(__file__).resolve().parent / "uploads" / image_name
        try:
            self.assertTrue(image_path.is_file())
            served = await self.client.get(image_url)
            self.assertEqual(served.status_code, 200, served.text)
            self.assertEqual(served.content, image_bytes)
        finally:
            image_path.unlink(missing_ok=True)

        invalid = await self.client.post(
            "/api/media/images",
            files={"file": ("not-an-image.txt", b"not an image", "text/plain")},
        )
        self.assertEqual(invalid.status_code, 415, invalid.text)


if __name__ == "__main__":
    unittest.main()
