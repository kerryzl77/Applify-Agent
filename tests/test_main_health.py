import importlib
import os
import sys
import types
import unittest

from fastapi import APIRouter
from fastapi.testclient import TestClient


class HealthCheckTests(unittest.TestCase):
    def test_health_is_degraded_when_redis_is_down_but_database_is_up(self):
        sys.modules.pop("app.main", None)
        fake_routers = types.SimpleNamespace(
            auth_router=APIRouter(),
            content_router=APIRouter(),
            resume_router=APIRouter(),
            gmail_router=APIRouter(),
            jobs_router=APIRouter(),
            agent_router=APIRouter(),
        )
        fake_dependencies = types.SimpleNamespace(get_db=lambda: None, get_redis=lambda: None)
        sys.modules["app.routers"] = fake_routers
        sys.modules["app.dependencies"] = fake_dependencies
        main_module = importlib.import_module("app.main")

        class FakeDB:
            def _get_connection(self):
                return object()

            def _return_connection(self, conn):
                return None

        class FakeRedis:
            def is_available(self):
                return False

        original_get_db = main_module.get_db
        original_get_redis = main_module.get_redis
        main_module.get_db = lambda: FakeDB()
        main_module.get_redis = lambda: FakeRedis()
        try:
            client = TestClient(main_module.app)
            response = client.get("/health")
        finally:
            main_module.get_db = original_get_db
            main_module.get_redis = original_get_redis

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertEqual(response.json()["database"], "up")
        self.assertEqual(response.json()["redis"], "down")
        sys.modules.pop("app.main", None)
        sys.modules.pop("app.routers", None)
        sys.modules.pop("app.dependencies", None)


class OpenAIWebSearchTests(unittest.TestCase):
    def test_search_import_and_call_do_not_require_api_key(self):
        previous_key = os.environ.pop("OPENAI_API_KEY", None)
        config_module = importlib.import_module("app.config")
        config_module.get_settings.cache_clear()
        try:
            search_module = importlib.reload(importlib.import_module("app.search.openai_web_search"))
            search_module._client = None
            self.assertEqual(search_module.openai_web_search("openai careers"), [])
            self.assertEqual(search_module.find_contacts_via_web_search("OpenAI", "Engineer"), [])
        finally:
            if previous_key is not None:
                os.environ["OPENAI_API_KEY"] = previous_key
            config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
