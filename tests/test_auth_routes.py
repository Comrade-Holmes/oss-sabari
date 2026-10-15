import re
import pytest
from tests.conftest import login_client_as

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign In" in response.text
    assert 'name="csrf_token"' in response.text

def test_login_invalid_credentials(client):
    resp = client.get("/login")
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    csrf_token = match.group(1) if match else ""

    response = client.post(
        "/login",
        data={
            "email": "nonexistent@allergraph.local",
            "password": "WrongPassword123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert "Invalid email or password" in response.text

def test_login_and_logout_flow(client):
    # 1. Login with valid admin credentials
    response = login_client_as(client, "admin@allergraph.local", "AllerGraph2026!")
    # Successful login redirects (302/303) to /dashboard
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/dashboard"

    # 2. Access dashboard with the active session
    dash_response = client.get("/dashboard")
    assert dash_response.status_code == 200
    assert "Platform Intelligence" in dash_response.text or "Overview" in dash_response.text

    # 3. Logout
    logout_response = client.get("/logout", follow_redirects=False)
    assert logout_response.status_code in (302, 303)
    assert "/login" in logout_response.headers["location"]

def test_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert "Create" in response.text or "Account" in response.text

def test_forgot_password_page(client):
    response = client.get("/forgot-password")
    assert response.status_code == 200
    assert "Reset Password" in response.text or "Forgot" in response.text
