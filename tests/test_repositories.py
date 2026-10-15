import pytest
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.allergy_checker_repo import allergy_checker_repo
from app.repositories.reports_repo import reports_repo
from app.repositories.user_repo import user_repo

def test_restaurant_repo():
    restaurants = restaurant_repo.list_restaurants(limit=10)
    assert isinstance(restaurants, list)
    assert len(restaurants) > 0

    first = restaurants[0]
    assert "id" in first
    assert "name" in first

    by_id = restaurant_repo.get_by_id(first["id"])
    assert by_id is not None
    assert by_id["name"] == first["name"]

def test_dish_repo():
    dishes = dish_repo.list_dishes(limit=10)
    assert isinstance(dishes, list)
    assert len(dishes) > 0

    first = dishes[0]
    assert "id" in first
    assert "name" in first

    by_id = dish_repo.get_by_id(first["id"])
    assert by_id is not None
    assert by_id["name"] == first["name"]

def test_allergen_repo():
    allergens = allergen_repo.list_allergens(limit=20)
    assert isinstance(allergens, list)
    assert len(allergens) >= 9

    names = [a["name"] for a in allergens]
    assert "Peanuts" in names or "Milk / Dairy" in names or "Tree Nuts" in names

def test_ingredient_repo():
    ingredients = ingredient_repo.list_ingredients(limit=10)
    assert isinstance(ingredients, list)
    assert len(ingredients) > 0

    first = ingredients[0]
    assert "id" in first
    assert "name" in first

def test_allergy_checker():
    allergens = allergen_repo.list_allergens(limit=10)
    peanut = next((a for a in allergens if "peanut" in a["name"].lower()), None)
    assert peanut is not None

    # Check ANY mode
    results = allergy_checker_repo.check_allergies(
        allergen_ids=[peanut["id"]],
        match_mode="ANY"
    )
    assert isinstance(results, list)
    # Thai Satay or Peanut noodles should be flagged
    if results:
        first = results[0]
        assert "restaurant_name" in first
        assert "dish_name" in first
        assert "matched_allergen_names" in first
        assert "safety_summary" in first

def test_reports_repo():
    stats = reports_repo.get_dashboard_stats()
    assert "total_restaurants" in stats
    assert "total_dishes" in stats
    assert "total_ingredients" in stats
    assert "total_allergens" in stats
    assert stats["total_restaurants"] > 0
    assert stats["total_dishes"] > 0

    dist = reports_repo.get_allergen_distribution()
    assert isinstance(dist, list)

    breakdown = reports_repo.get_verification_breakdown()
    assert isinstance(breakdown, dict)
    assert "VERIFIED" in breakdown

    csv_data = reports_repo.export_csv("allergen_distribution")
    assert isinstance(csv_data, str)
    assert "Allergen Name" in csv_data

def test_user_repo_get():
    admin = user_repo.get_by_email("admin@allergraph.local")
    assert admin is not None
    assert admin["role"] == "ADMIN"
    assert admin["is_active"] is True
