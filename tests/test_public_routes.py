import pytest

def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AllerGraph" in response.text
    assert "Understand Every Ingredient" in response.text

def test_about_page(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert "About Our Mission" in response.text or "AllerGraph" in response.text

def test_contact_page(client):
    response = client.get("/contact")
    assert response.status_code == 200
    assert "Contact" in response.text or "Inquiries" in response.text

def test_privacy_page(client):
    response = client.get("/privacy")
    assert response.status_code == 200
    assert "Privacy" in response.text or "Disclaimer" in response.text

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
