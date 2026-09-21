import os
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="researchos-tests-"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(TEST_DIR / "test.db")
os.environ["DATA_DIR"] = str(TEST_DIR)
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_API_KEY"] = ""
import pytest
from fastapi.testclient import TestClient
from backend.main import app, requests
from backend.db import Base, engine


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    requests.clear()
    with TestClient(app) as client:
        yield client
