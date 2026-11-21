import os
import tempfile

# Must be set before app modules are imported.
_tmp = tempfile.mkdtemp(prefix="procureai-test-")
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["FRONTEND_DIST"] = os.path.join(_tmp, "no-dist")
for k in ("SARVAM_API_KEY", "FALLBACK_AI_PROVIDER", "FALLBACK_AI_API_KEY", "AI_USE_CACHED_SAMPLES"):
    os.environ.pop(k, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)
