import importlib.util
import sys
import types
import unittest
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
        self.artifacts = []
        self.next_id = 1
        self.candidate_data = {
            "personal_info": {"name": "Alex Applicant", "email": "alex@example.com"},
            "resume": {"summary": "Builder", "skills": ["Python"], "experience": [], "education": []},
            "story_bank": [],
        }

    def get_candidate_data(self, user_id):
        return self.candidate_data

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

    def create_artifact(self, **kwargs):
        artifact = {"id": len(self.artifacts) + 1, **kwargs}
        self.artifacts.append(artifact)
        return artifact["id"]

    def get_latest_artifact(self, source_type, source_id, artifact_key=None, format=None, user_id=None):
        for artifact in reversed(self.artifacts):
            if artifact["source_type"] != source_type:
                continue
            if str(artifact["source_id"]) != str(source_id):
                continue
            if user_id and artifact["user_id"] != user_id:
                continue
            if artifact_key and artifact["artifact_key"] != artifact_key:
                continue
            if format and artifact.get("format") != format:
                continue
            return artifact
        return None


class FakeRedis:
    def __init__(self):
        self.cache = {}

    def get_cached_content(self, content_type, user_id, cache_context):
        return self.cache.get((content_type, user_id, repr(cache_context)))

    def cache_generated_content(self, content_type, user_id, cache_context, response_payload, ttl=1800):
        self.cache[(content_type, user_id, repr(cache_context))] = {"response": response_payload}
        return "cache-key"

    def get(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        return True

    def invalidate_user_cache(self, *args, **kwargs):
        return None


class FakeRetriever:
    def __init__(self):
        self.parse_manual_job_posting_calls = 0

    def parse_manual_job_posting(self, manual_text):
        self.parse_manual_job_posting_calls += 1
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
        if user_id == "user-1" and artifact_id == 1 and fmt == "docx":
            return __file__
        return None


class FakeObjectStorage:
    def store_file(self, local_path, object_key, metadata=None, content_type=None):
        return {
            "storage_backend": "local",
            "bucket_name": None,
            "object_key": object_key,
            "filename": Path(local_path).name,
            "content_type": content_type or "application/octet-stream",
            "size_bytes": 10,
        }

    def download_bytes(self, artifact):
        return b"artifact-bytes"


class FakeGenerator:
    def __init__(self):
        self.cover_letter_calls = 0

    def generate_cover_letter_artifact(self, job_data, candidate_data, evidence_pack=None):
        self.cover_letter_calls += 1
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
    content_module.object_storage = FakeObjectStorage()
    fake_retriever = FakeRetriever()
    content_module.data_retriever = fake_retriever

    return TestClient(app), fake_db, fake_redis, content_module.llm_generator, fake_retriever


class ContentRouterTests(unittest.TestCase):
    def test_generate_cover_letter_returns_artifact_metadata(self):
        client, fake_db, _, _, _ = build_client()
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
        self.assertEqual(len(fake_db.artifacts), 2)

    def test_generate_failure_does_not_persist_artifact(self):
        class FailingGenerator(FakeGenerator):
            def generate_cover_letter_artifact(self, job_data, candidate_data, evidence_pack=None):
                raise ValueError("parse failed")

        client, fake_db, _, _, _ = build_client(generator=FailingGenerator())
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
        self.assertEqual(fake_db.artifacts, [])

    def test_cache_hit_preserves_content_id_and_file_info(self):
        client, fake_db, fake_redis, generator, fake_retriever = build_client()
        payload = {
            "content_type": "cover_letter",
            "input_type": "manual",
            "manual_text": "Build APIs and ship product",
        }

        first = client.post("/api/content/generate", json=payload)
        self.assertEqual(first.status_code, 200)
        first_body = first.json()
        self.assertFalse(first_body["cached"])
        self.assertEqual(generator.cover_letter_calls, 1)

        second = client.post("/api/content/generate", json=payload)
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertTrue(second_body["cached"])
        self.assertEqual(second_body["content_id"], first_body["content_id"])
        self.assertEqual(second_body["file_info"], first_body["file_info"])
        self.assertEqual(generator.cover_letter_calls, 1)
        self.assertEqual(len(fake_db.saved), 1)
        self.assertTrue(fake_redis.cache)
        self.assertEqual(fake_retriever.parse_manual_job_posting_calls, 1)

    def test_cache_key_distinguishes_manual_inputs(self):
        client, _, _, generator, _ = build_client()

        first = client.post(
            "/api/content/generate",
            json={"content_type": "cover_letter", "input_type": "manual", "manual_text": "Build APIs"},
        )
        second = client.post(
            "/api/content/generate",
            json={"content_type": "cover_letter", "input_type": "manual", "manual_text": "Lead data platform"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(generator.cover_letter_calls, 2)

    def test_cache_key_distinguishes_candidate_data_changes(self):
        client, fake_db, _, generator, _ = build_client()
        payload = {
            "content_type": "cover_letter",
            "input_type": "manual",
            "manual_text": "Build APIs and ship product",
        }

        first = client.post("/api/content/generate", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(generator.cover_letter_calls, 1)

        fake_db.candidate_data = {
            **fake_db.candidate_data,
            "resume": {**fake_db.candidate_data["resume"], "summary": "Platform engineer"},
        }

        second = client.post("/api/content/generate", json=payload)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["cached"])
        self.assertEqual(generator.cover_letter_calls, 2)

    def test_download_requires_correct_owner(self):
        client, fake_db, _, _, _ = build_client()
        fake_db.save_generated_content("cover_letter", "body", {}, "user-1")
        fake_db.create_artifact(
            user_id="user-1",
            source_type="generated_content",
            source_id=1,
            artifact_key="generated_content.pdf",
            artifact_type="cover_letter",
            kind="file",
            format="pdf",
            object_key="generated-content/user-1/1/artifact.pdf",
        )

        ok = client.get("/api/content/download/1/pdf")
        self.assertEqual(ok.status_code, 200)

        other_client, other_db, _, _, _ = build_client(user_id="user-2")
        other_db.saved[("user-1", 1)] = {"id": 1, "content_type": "cover_letter", "content": "body", "metadata": {}}
        denied = other_client.get("/api/content/download/1/pdf")
        self.assertEqual(denied.status_code, 404)


if __name__ == "__main__":
    unittest.main()
