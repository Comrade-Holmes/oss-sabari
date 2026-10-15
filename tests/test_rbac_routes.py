import pytest

def test_unauthenticated_redirect(client):
    # Unauthenticated user visiting protected route should be redirected to /login
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["location"]

def test_viewer_access(viewer_client):
    # Viewer can access dashboard
    resp = viewer_client.get("/dashboard")
    assert resp.status_code == 200
    assert "My Dietary Dashboard" in resp.text or "Welcome" in resp.text

    # Viewer can view restaurants list
    resp = viewer_client.get("/restaurants")
    assert resp.status_code == 200

    # Viewer cannot access admin user management
    resp = viewer_client.get("/users")
    assert resp.status_code == 403

    # Viewer cannot access dish creation form
    resp = viewer_client.get("/dishes/new")
    assert resp.status_code == 403

def test_editor_access(editor_client):
    # Editor can access dashboard
    resp = editor_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Editor Workspace" in resp.text or "Curator" in resp.text

    # Editor can access dish creation form
    resp = editor_client.get("/dishes/new")
    assert resp.status_code == 200
    assert "Dish" in resp.text

    # Editor cannot access admin user management
    resp = editor_client.get("/users")
    assert resp.status_code == 403

def test_admin_access(admin_client):
    # Admin can access admin dashboard
    resp = admin_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Platform Intelligence" in resp.text or "Overview" in resp.text

    # Admin can access user management
    resp = admin_client.get("/users")
    assert resp.status_code == 200
    assert "User Management" in resp.text

    # Admin can access reports
    resp = admin_client.get("/reports")
    assert resp.status_code == 200

    # Admin can access activity logs
    resp = admin_client.get("/activity-logs")
    assert resp.status_code == 200
