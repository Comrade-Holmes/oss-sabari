import pytest

def test_graph_page(admin_client):
    response = admin_client.get("/graph")
    assert response.status_code == 200
    assert "Knowledge Graph Explorer" in response.text or "Graph" in response.text

def test_api_graph_data(admin_client):
    response = admin_client.get("/api/graph/data?limit=50")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0

    first_node = data["nodes"][0]["data"]
    assert "id" in first_node
    assert "label" in first_node
    assert "type" in first_node

def test_api_graph_filter_types(admin_client):
    response = admin_client.get("/api/graph/data?types=Restaurant,Dish")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    types = {n["data"]["type"] for n in data["nodes"]}
    assert types.issubset({"Restaurant", "Dish"})

def test_api_graph_expand(admin_client):
    # Get a node id first
    resp = admin_client.get("/api/graph/data?limit=10")
    nodes = resp.json().get("nodes", [])
    assert len(nodes) > 0

    node_id = nodes[0]["data"]["id"]
    expand_resp = admin_client.get(f"/api/graph/expand/{node_id}")
    assert expand_resp.status_code == 200
    expand_data = expand_resp.json()
    assert "nodes" in expand_data
    assert "edges" in expand_data

def test_api_graph_paths(admin_client):
    response = admin_client.get("/api/graph/paths")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
