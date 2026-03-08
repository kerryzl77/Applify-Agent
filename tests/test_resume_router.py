import importlib.util
import sys
import types
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules.setdefault("trafilatura", types.SimpleNamespace(fetch_url=lambda *args, **kwargs: None))
sys.modules.setdefault(
    "app.enhanced_resume_processor",
    types.SimpleNamespace(
        enhanced_resume_processor=types.SimpleNamespace(
            get_user_extraction=lambda user_id: None,
            start_processing=lambda *args, **kwargs: None,
        )
    ),
)
sys.modules.setdefault(
    "scraper.retriever",
    types.SimpleNamespace(
        DataRetriever=lambda: types.SimpleNamespace(scrape_job_posting=lambda url: {})
    ),
)
sys.modules.setdefault(
    "scraper.url_validator",
    types.SimpleNamespace(
        URLValidator=lambda: types.SimpleNamespace(
            validate_and_parse_url=lambda url: {"valid": True}
        )
    ),
)

resume_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "resume.py"
spec = importlib.util.spec_from_file_location("test_resume_module", resume_path)
resume_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(resume_module)


class FakeToken:
    def __init__(self, user_id):
        self.user_id = user_id


class FakeDB:
    def get_candidate_data(self, user_id):
        return {"resume": {"summary": "Builder"}}


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return None

    def set(self, key, value, ttl=1800):
        self.store[key] = value
        return False


def build_client():
    app = FastAPI()
    app.include_router(resume_module.router, prefix="/api/resume")
    app.dependency_overrides[resume_module.get_current_user] = lambda: FakeToken("user-1")
    app.dependency_overrides[resume_module.get_db] = lambda: FakeDB()
    app.dependency_overrides[resume_module.get_redis] = lambda: FakeRedis()
    return TestClient(app)


class ResumeRouterTests(unittest.TestCase):
    def setUp(self):
        with resume_module._resume_refinement_progress_lock:
            resume_module._resume_refinement_progress.clear()

    def test_refinement_progress_uses_in_memory_fallback_when_redis_misses(self):
        resume_module._set_progress(
            "user-1",
            "task-1",
            {
                "task_id": "task-1",
                "step": "tailoring",
                "progress": 30,
                "message": "AI is tailoring your resume to the job...",
                "status": "processing",
                "timestamp": "2026-03-08T00:00:00",
                "data": {},
            },
            None,
        )
        client = build_client()

        response = client.get("/api/resume/refinement-progress/task-1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["task_id"], "task-1")
        self.assertEqual(body["progress"], 30)
        self.assertEqual(body["step"], "tailoring")

    def test_refine_seeds_initial_progress_before_background_work(self):
        client = build_client()
        response = client.post(
            "/api/resume/refine",
            json={
                "input_type": "manual",
                "job_description": "Build backend systems",
            },
        )

        self.assertEqual(response.status_code, 200)
        task_id = response.json()["task_id"]
        progress = resume_module._get_progress("user-1", task_id, None)
        self.assertIsNotNone(progress)
        self.assertIn(progress["status"], {"processing", "completed", "error"})
        self.assertGreaterEqual(progress["progress"], 0)


if __name__ == "__main__":
    unittest.main()
