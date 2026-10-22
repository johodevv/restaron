import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_spa_traversal_dotdot(client):
    response = client.get("/../../backend/.env")
    assert "SECRET_KEY" not in response.text


def test_spa_traversal_encoded(client):
    response = client.get("/..%2f..%2fbackend%2f.env")
    assert "SECRET_KEY" not in response.text
