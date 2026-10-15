import re
import pytest
from app.repositories.allergen_repo import allergen_repo

def test_allergy_checker_page(admin_client):
    response = admin_client.get("/allergy-checker")
    assert response.status_code == 200
    assert "Allergy" in response.text
    assert "Screening Parameters" in response.text

def test_allergy_checker_query_screen(admin_client):
    # Fetch peanut allergen
    allergens = allergen_repo.list_allergens(limit=20)
    peanut = next((a for a in allergens if "peanut" in a["name"].lower()), allergens[0])

    response = admin_client.get(f"/allergy-checker?allergens={peanut['id']}&match_mode=ANY")
    assert response.status_code == 200
    assert "Screening Results" in response.text or "Allergen" in response.text

def test_api_allergy_check(admin_client):
    allergens = allergen_repo.list_allergens(limit=20)
    peanut = next((a for a in allergens if "peanut" in a["name"].lower()), allergens[0])

    response = admin_client.get(f"/api/allergy-checker?allergen_ids={peanut['id']}&match_mode=ANY")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)
