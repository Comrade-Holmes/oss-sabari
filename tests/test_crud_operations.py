import pytest
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo

def test_restaurants_list_and_detail(admin_client):
    # List
    resp = admin_client.get("/restaurants")
    assert resp.status_code == 200
    assert "Restaurants" in resp.text

    # Detail
    restaurants = restaurant_repo.list_restaurants(limit=5)
    assert len(restaurants) > 0
    first_id = restaurants[0]["id"]

    detail_resp = admin_client.get(f"/restaurants/{first_id}")
    assert detail_resp.status_code == 200
    assert restaurants[0]["name"] in detail_resp.text

def test_dishes_list_and_detail(admin_client):
    # List
    resp = admin_client.get("/dishes")
    assert resp.status_code == 200
    assert "Dishes" in resp.text

    # Detail
    dishes = dish_repo.list_dishes(limit=5)
    assert len(dishes) > 0
    first_id = dishes[0]["id"]

    detail_resp = admin_client.get(f"/dishes/{first_id}")
    assert detail_resp.status_code == 200
    escaped_name = dishes[0]["name"].replace("'", "&#39;")
    assert (dishes[0]["name"] in detail_resp.text) or (escaped_name in detail_resp.text)

def test_ingredients_list_and_detail(admin_client):
    # List
    resp = admin_client.get("/ingredients")
    assert resp.status_code == 200
    assert "Ingredients" in resp.text

    # Detail
    ingredients = ingredient_repo.list_ingredients(limit=5)
    assert len(ingredients) > 0
    first_id = ingredients[0]["id"]

    detail_resp = admin_client.get(f"/ingredients/{first_id}")
    assert detail_resp.status_code == 200
    assert ingredients[0]["name"] in detail_resp.text

def test_allergens_list_and_detail(admin_client):
    # List
    resp = admin_client.get("/allergens")
    assert resp.status_code == 200
    assert "Allergens" in resp.text

    # Detail
    allergens = allergen_repo.list_allergens(limit=5)
    assert len(allergens) > 0
    first_id = allergens[0]["id"]

    detail_resp = admin_client.get(f"/allergens/{first_id}")
    assert detail_resp.status_code == 200
    assert allergens[0]["name"] in detail_resp.text

def test_profile_view(admin_client):
    resp = admin_client.get("/profile")
    assert resp.status_code == 200
    assert "Admin User" in resp.text or "Profile" in resp.text

def test_activity_logs_and_export(admin_client):
    resp = admin_client.get("/activity-logs")
    assert resp.status_code == 200
    assert "Activity" in resp.text or "Logs" in resp.text

    csv_resp = admin_client.get("/activity-logs/export/csv?report_type=allergen_distribution")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    assert "Allergen" in csv_resp.text
