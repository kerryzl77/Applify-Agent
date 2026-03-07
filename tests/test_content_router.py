import unittest
import sys
import types
import importlib.util
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules.setdefault("trafilatura", types.SimpleNamespace(fetch_url=lambda *args, **kwargs: None))

from app.artifact_models import ArtifactMetadata, CoverLetterArtifact, ParagraphBlock

content_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "content.py"
spec = importlib.util.spec_from_file_location("test_content_module", content_path)
content_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(content_module)


class FakeToken:
    def __init__(self, user_id):
        self.user_id = user_id


class FakeDB:
    def __init__(self):
        self.saved = {}
        self.next_id = 1

    def get_candidate_data(self, user_id):
        return {
            "personal_info": {"name": "Alex Applicant", "email": "alex@example.com"},
            "resume": {"summary": "Builder", "skills": ["Python"], "experience": [], "education": []},
        }

    def save_generated_content(self, content_type, content, metadata, user_id):
        current_id = self.next_id
        self.next_id += 1
        self.saved[(user_id, current_id)] = {
            "id": current_id,
            "content_type": content_type,
            "content": content,
            "metadata": metadata,
        }
        return current_id

    def get_generated_content(self, content_id, user_id):
        return self.saved.get((user_id, content_id))


class FakeRedis:
    def get_cached_content(self, *args, **kwargs):
        return None

    def cache_generated_content(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        return True

    def invalidate_user_cache(self, *args, **kwargs):
        return None


class FakeRetriever:
    def parse_manual_job_posting(self, manual_text):
        return {
            "job_title": "Engineer",
            "company_name": "Acme",
            "job_description": manual_text,
            "requirements": manual_text,
            "url": "manual_input",
        }


class FakeFormatter:
    def format_text(self, content, content_type):
        return content

    def render_artifact_bundle(self, artifact, candidate_data, user_id, artifact_id):
        return {"artifact_id": artifact_id, "available_formats": ["docx", "pdf"]}

    def get_artifact_download_path(self, user_id, artifact_id, fmt):
        if user_id == "user-1" and artifact_id == 1 and fmt == "pdf":
            return __file__
        return None


class FakeGenerator:
    def generate_cover_letter_artifact(self, job_data, candidate_data):
        return CoverLetterArtifact(
            greeting="Dear Hiring Team,",
            opening=ParagraphBlock(text="I am excited to apply."),
            body=[ParagraphBlock(text="I have relevant experience.")],
            closing=ParagraphBlock(text="Thank you for your time."),
            metadata=ArtifactMetadata(content_type="cover_letter", company_name="Acme", job_title="Engineer"),
        )

    def _convert_to_html(self, body):
        return f"<p>{body}</p>"

    def generate_email_subject(self, email_body, context_type):
        return "Subject"


def build_client(user_id="user-1", generator=None):
    app = FastAPI()
    app.include_router(content_module.router, prefix="/api/content")

    fake_db = FakeDB()
    fake_redis = FakeRedis()

    app.dependency_overrides[content_module.get_current_user] = lambda: FakeToken(user_id)
    app.dependency_overrides[content_module.get_db] = lambda: fake_db
    app.dependency_overrides[content_module.get_redis] = lambda: fake_redis

    content_module.llm_generator = generator or FakeGenerator()
    content_module.output_formatter = FakeFormatter()
    content_module.data_retriever = FakeRetriever()

    return TestClient(app), fake_db


class ContentRouterTests(unittest.TestCase):
    def test_generate_cover_letter_returns_artifact_metadata(self):
        client, _ = build_client()
        response = client.post(
            "/api/content/generate",
            json={
                "content_type": "cover_letter",
                "input_type": "manual",
                "manual_text": "Build APIs and ship product",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["content_id"], 1)
        self.assertEqual(body["file_info"]["artifact_id"], 1)

    def test_generate_failure_does_not_persist_artifact(self):
        class FailingGenerator(FakeGenerator):
            def generate_cover_letter_artifact(self, job_data, candidate_data):
                raise ValueError("parse failed")

        client, fake_db = build_client(generator=FailingGenerator())
        response = client.post(
            "/api/content/generate",
            json={
                "content_type": "cover_letter",
                "input_type": "manual",
                "manual_text": "Build APIs and ship product",
            },
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(fake_db.saved, {})

    def test_download_requires_correct_owner(self):
        client, fake_db = build_client()
        fake_db.save_generated_content("cover_letter", "body", {}, "user-1")

        ok = client.get("/api/content/download/1/pdf")
        self.assertEqual(ok.status_code, 200)

        other_client, other_db = build_client(user_id="user-2")
        other_db.saved[("user-1", 1)] = {"id": 1, "content_type": "cover_letter", "content": "body", "metadata": {}}
        denied = other_client.get("/api/content/download/1/pdf")
        self.assertEqual(denied.status_code, 404)


if __name__ == "__main__":
    unittest.main()
