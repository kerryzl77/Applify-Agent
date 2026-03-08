import os
import tempfile
import unittest
from pathlib import Path

from app.config import get_settings
from app.object_storage import ObjectStorage


class ObjectStorageTests(unittest.TestCase):
    def test_local_store_and_download_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "artifact.txt"
            source_path.write_text("artifact-body", encoding="utf-8")

            previous_root = os.environ.get("ARTIFACT_STORAGE_LOCAL_ROOT")
            previous_backend = os.environ.get("ARTIFACT_STORAGE_BACKEND")
            os.environ["ARTIFACT_STORAGE_LOCAL_ROOT"] = str(Path(tmpdir) / "persisted")
            os.environ["ARTIFACT_STORAGE_BACKEND"] = "local"
            get_settings.cache_clear()
            try:
                storage = ObjectStorage()
                stored = storage.store_file(str(source_path), "test/artifact.txt", content_type="text/plain")
                self.assertEqual(stored["storage_backend"], "local")
                artifact = {
                    "storage_backend": "local",
                    "object_key": stored["object_key"],
                }
                self.assertEqual(storage.download_bytes(artifact), b"artifact-body")
            finally:
                if previous_root is None:
                    os.environ.pop("ARTIFACT_STORAGE_LOCAL_ROOT", None)
                else:
                    os.environ["ARTIFACT_STORAGE_LOCAL_ROOT"] = previous_root
                if previous_backend is None:
                    os.environ.pop("ARTIFACT_STORAGE_BACKEND", None)
                else:
                    os.environ["ARTIFACT_STORAGE_BACKEND"] = previous_backend
                get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
