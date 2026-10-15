import re
import pytest
from starlette.testclient import TestClient
from app.main import app

def login_client_as(client, email: str, password: str):
    """Fetch CSRF token from login page and authenticate client."""
    resp = client.get("/login")
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    csrf_token = match.group(1) if match else ""
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": csrf_token},
        follow_redirects=False,
    )

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def admin_client(client):
    """Client authenticated as ADMIN."""
    login_client_as(client, "admin@allergraph.local", "AllerGraph2026!")
    yield client
    client.get("/logout", follow_redirects=False)

@pytest.fixture
def editor_client(client):
    """Client authenticated as EDITOR."""
    login_client_as(client, "editor@allergraph.local", "AllerGraph2026!")
    yield client
    client.get("/logout", follow_redirects=False)

@pytest.fixture
def viewer_client(client):
    """Client authenticated as VIEWER."""
    login_client_as(client, "viewer@allergraph.local", "AllerGraph2026!")
    yield client
    client.get("/logout", follow_redirects=False)
