import unittest
from datetime import datetime

from pydantic import ValidationError

from app.schemas import ArticleCreate, ArticleResponse


class ArticleSchemaTests(unittest.TestCase):
    def test_response_accepts_incomplete_legacy_draft(self):
        now = datetime(2026, 8, 20)
        article = ArticleResponse.model_validate(
            {
                "id": 229,
                "title": "Legacy draft",
                "content": "",
                "status": "DRAFT",
                "created_at": now,
                "updated_at": now,
                "author": {
                    "id": 1,
                    "username": "reporter",
                    "role": "JOURNALIST",
                    "created_at": now,
                },
            }
        )

        self.assertEqual(article.content, "")

    def test_create_still_rejects_empty_content(self):
        with self.assertRaises(ValidationError):
            ArticleCreate(
                title="Valid headline",
                content="",
                summary="A valid article summary",
                category="News",
            )


if __name__ == "__main__":
    unittest.main()
