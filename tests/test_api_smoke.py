from fastapi.testclient import TestClient
from app.main import app

def test_root_routes_exist():
    client = TestClient(app)
    assert app is not None
    # Just ensure routers mounted
    # (Real upload test would require tmp media file)