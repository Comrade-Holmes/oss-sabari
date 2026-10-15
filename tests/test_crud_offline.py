"""
Offline CRUD tests: exercise every create / read / update / delete route
(HTML forms + REST API) for Restaurants, Dishes, Ingredients and Allergens
WITHOUT needing a running Neo4j. The repositories are swapped for in-memory
fakes, so these tests validate routers, forms, templates, RBAC and CSRF.

(The Cypher itself is covered by tests/test_crud_write_operations.py, which
needs a live Neo4j.)
"""
import re
import uuid

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.security import hash_password
from app.routers import (
    restaurants as restaurants_router, dishes as dishes_router,
    ingredients as ingredients_router, allergens as allergens_router,
)
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.user_repo import user_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.database import db


PASSWORD = "AllerGraph2026!"
USERS = {}


def _mk_user(role):
    uid = str(uuid.uuid4())
    USERS[uid] = {
        "id": uid, "full_name": f"{role.title()} Tester", "email": f"{role.lower()}@test.local",
        "password_hash": hash_password(PASSWORD), "role": role, "is_active": True,
    }


class Store:
    """Tiny generic in-memory store that mimics the repo API used by the routers."""
    def __init__(self):
        self.rows = {}

    def create(self, data, **_):
        rid = str(uuid.uuid4())
        row = {k: (getattr(v, "value", v)) for k, v in data.items()}
        row["id"] = rid
        self.rows[rid] = row
        return dict(row)

    def update(self, rid, data, *a, **k):
        if rid not in self.rows:
            return None
        for key, v in data.items():
            if v is not None:
                self.rows[rid][key] = getattr(v, "value", v)
        return dict(self.rows[rid])

    def delete(self, rid):
        return self.rows.pop(rid, None) is not None

    def get(self, rid):
        r = self.rows.get(rid)
        return dict(r) if r else None


@pytest.fixture
def fakes(monkeypatch):
    USERS.clear()
    for role in ("ADMIN", "EDITOR", "VIEWER"):
        _mk_user(role)

    # no real DB
    monkeypatch.setattr(db, "connect", lambda: None)
    monkeypatch.setattr(db, "close", lambda: None)

    monkeypatch.setattr(user_repo, "get_by_email", lambda e: next((u for u in USERS.values() if u["email"] == e.lower()), None))
    monkeypatch.setattr(user_repo, "get_by_id", lambda i: USERS.get(i))
    monkeypatch.setattr(activity_log_repo, "log", lambda **kw: {})

    rest, dish, ing, alg = Store(), Store(), Store(), Store()

    # restaurants
    monkeypatch.setattr(restaurant_repo, "create", lambda d: {**rest.create(d), "dish_count": 0})
    monkeypatch.setattr(restaurant_repo, "update", rest.update)
    monkeypatch.setattr(restaurant_repo, "delete", rest.delete)
    monkeypatch.setattr(restaurant_repo, "get_by_id", rest.get)
    monkeypatch.setattr(restaurant_repo, "list_restaurants", lambda **k: [dict(r, dish_count=0) for r in rest.rows.values()])
    monkeypatch.setattr(restaurant_repo, "count_restaurants", lambda **k: len(rest.rows))
    monkeypatch.setattr(restaurant_repo, "get_distinct_cities", lambda: [])
    monkeypatch.setattr(restaurant_repo, "get_distinct_cuisines", lambda: [])
    monkeypatch.setattr(restaurant_repo, "get_restaurant_dishes", lambda rid: [])

    # allergens
    monkeypatch.setattr(allergen_repo, "create", lambda d: {**alg.create(d), "ingredient_count": 0, "dish_count": 0})
    monkeypatch.setattr(allergen_repo, "update", lambda i, d: (lambda r: r and {**r, "ingredient_count": 0, "dish_count": 0})(alg.update(i, d)))
    monkeypatch.setattr(allergen_repo, "delete", alg.delete)
    monkeypatch.setattr(allergen_repo, "get_by_id", lambda i: (lambda r: r and {**r, "ingredient_count": 0, "dish_count": 0, "restaurant_count": 0})(alg.get(i)))
    monkeypatch.setattr(allergen_repo, "get_by_name", lambda n: next((r for r in alg.rows.values() if r["name"].lower() == n.lower()), None))
    monkeypatch.setattr(allergen_repo, "list_allergens", lambda **k: [dict(r, ingredient_count=0, dish_count=0) for r in alg.rows.values()])
    monkeypatch.setattr(allergen_repo, "count_allergens", lambda **k: len(alg.rows))
    monkeypatch.setattr(allergen_repo, "get_distinct_categories", lambda: [])
    monkeypatch.setattr(allergen_repo, "get_connected_dishes_and_restaurants", lambda i: {"ingredients": [], "dishes": []})

    # ingredients
    def ing_create(d, allergen_ids=None):
        r = ing.create(d); r["allergen_ids"] = list(allergen_ids or []); ing.rows[r["id"]] = r
        return {**r, "allergens": [], "dishes": [], "restaurants": [], "dish_count": 0}
    def ing_update(i, d, allergen_ids=None):
        r = ing.update(i, d)
        if r is None: return None
        if allergen_ids is not None: ing.rows[i]["allergen_ids"] = list(allergen_ids)
        return {**ing.rows[i], "allergens": [], "dishes": [], "restaurants": [], "dish_count": 0}
    monkeypatch.setattr(ingredient_repo, "create", ing_create)
    monkeypatch.setattr(ingredient_repo, "update", ing_update)
    monkeypatch.setattr(ingredient_repo, "delete", ing.delete)
    monkeypatch.setattr(ingredient_repo, "get_by_id", lambda i: (lambda r: r and {**r, "allergens": [], "dishes": [], "restaurants": [], "dish_count": 0})(ing.get(i)))
    monkeypatch.setattr(ingredient_repo, "list_ingredients", lambda **k: [dict(r, allergens=[], dish_count=0) for r in ing.rows.values()])
    monkeypatch.setattr(ingredient_repo, "count_ingredients", lambda **k: len(ing.rows))
    monkeypatch.setattr(ingredient_repo, "get_distinct_categories", lambda: [])

    # dishes
    def dish_full(r):
        return {**r, "restaurants": [], "ingredients": [], "allergens": [], "may_contain_allergens": []}
    def dish_create(d, restaurant_ids=None, ingredient_ids=None, may_contain_allergen_ids=None):
        r = dish.create(d)
        r["_links"] = (restaurant_ids, ingredient_ids, may_contain_allergen_ids)
        dish.rows[r["id"]] = r
        return dish_full(r)
    def dish_update(i, d, restaurant_ids=None, ingredient_ids=None, may_contain_allergen_ids=None):
        r = dish.update(i, d)
        if r is None: return None
        dish.rows[i]["_links"] = (restaurant_ids, ingredient_ids, may_contain_allergen_ids)
        return dish_full(dish.rows[i])
    monkeypatch.setattr(dish_repo, "create", dish_create)
    monkeypatch.setattr(dish_repo, "update", dish_update)
    monkeypatch.setattr(dish_repo, "delete", dish.delete)
    monkeypatch.setattr(dish_repo, "get_by_id", lambda i: (lambda r: r and dish_full(r))(dish.get(i)))
    monkeypatch.setattr(dish_repo, "list_dishes", lambda **k: [dict(dish_full(r), ingredient_count=0) for r in dish.rows.values()])
    monkeypatch.setattr(dish_repo, "count_dishes", lambda **k: len(dish.rows))
    monkeypatch.setattr(dish_repo, "get_distinct_categories", lambda: [])

    yield {"restaurant": rest, "dish": dish, "ingredient": ing, "allergen": alg}


def _csrf(client, url):
    resp = client.get(url)
    assert resp.status_code == 200, (url, resp.status_code)
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    assert m, f"no csrf token on {url}"
    return m.group(1)


def _login(client, role):
    token = _csrf(client, "/login")
    r = client.post("/login", data={"email": f"{role.lower()}@test.local", "password": PASSWORD, "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303, r.text[:300]


@pytest.fixture
def admin(fakes):
    with TestClient(app) as c:
        _login(c, "ADMIN")
        yield c


@pytest.fixture
def viewer(fakes):
    with TestClient(app) as c:
        _login(c, "VIEWER")
        yield c


def _id_from(resp):
    assert resp.status_code == 303, resp.text[:300]
    return resp.headers["location"].rstrip("/").split("/")[-1]


# ---------------------------------------------------------------- HTML forms
HTML_CASES = {
    "restaurants": ("restaurant", {"name": "Thyme Kitchen", "city": "Chennai", "cuisine_type": "South Indian"}, {"name": "Thyme Kitchen 2", "city": "Madurai"}),
    "allergens": ("allergen", {"name": "Lupin", "allergen_category": "Major", "description": "d"}, {"name": "Lupin Flour", "allergen_category": "Minor", "description": "d2"}),
    "ingredients": ("ingredient", {"name": "Almond Flour", "category": "Nuts", "verification_status": "UNVERIFIED"}, {"name": "Almond Meal", "category": "Nuts", "verification_status": "VERIFIED"}),
    "dishes": ("dish", {"name": "Risotto", "category": "Main Course", "price": "12.5", "vegetarian": "true"}, {"name": "Risotto Bianco", "category": "Main Course", "price": "14"}),
}


@pytest.mark.parametrize("path", list(HTML_CASES))
def test_html_full_crud(admin, fakes, path):
    key, create_data, update_data = HTML_CASES[path]
    store = fakes[key]

    # list + new form render
    assert admin.get(f"/{path}").status_code == 200
    token = _csrf(admin, f"/{path}/new")

    # CREATE
    r = admin.post(f"/{path}/new", data={**create_data, "csrf_token": token}, follow_redirects=False)
    rid = _id_from(r)
    assert rid in store.rows
    assert admin.get(f"/{path}/{rid}").status_code == 200                      # READ detail
    assert create_data["name"] in admin.get(f"/{path}").text                    # appears in list

    # UPDATE
    token = _csrf(admin, f"/{path}/{rid}/edit")
    r = admin.post(f"/{path}/{rid}/edit", data={**update_data, "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    assert store.rows[rid]["name"] == update_data["name"]

    # DELETE
    token = _csrf(admin, f"/{path}")
    r = admin.post(f"/{path}/{rid}/delete", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    assert rid not in store.rows
    assert admin.get(f"/{path}/{rid}").status_code == 404


def test_dish_form_passes_relationship_ids(admin, fakes):
    token = _csrf(admin, "/dishes/new")
    r = admin.post("/dishes/new", data={
        "name": "Paneer", "csrf_token": token,
        "restaurant_ids": ["r1", "r2"], "ingredient_ids": ["i1"], "may_contain_allergen_ids": ["a1", "a2"],
    }, follow_redirects=False)
    rid = _id_from(r)
    assert fakes["dish"].rows[rid]["_links"] == (["r1", "r2"], ["i1"], ["a1", "a2"])


def test_csrf_required_on_html_forms(admin, fakes):
    r = admin.post("/restaurants/new", data={"name": "X Cafe", "city": "Y", "csrf_token": "bad"}, follow_redirects=False)
    assert r.status_code == 303
    assert not fakes["restaurant"].rows


def test_duplicate_allergen_name_rejected_on_create_and_update(admin, fakes):
    t = _csrf(admin, "/allergens/new")
    a = _id_from(admin.post("/allergens/new", data={"name": "Soy", "csrf_token": t}, follow_redirects=False))
    b = _id_from(admin.post("/allergens/new", data={"name": "Fish", "csrf_token": t}, follow_redirects=False))
    # duplicate create
    admin.post("/allergens/new", data={"name": "soy", "csrf_token": t}, follow_redirects=False)
    assert len(fakes["allergen"].rows) == 2
    # rename Fish -> Soy must be refused (unique constraint would 500)
    t = _csrf(admin, f"/allergens/{b}/edit")
    admin.post(f"/allergens/{b}/edit", data={"name": "Soy", "csrf_token": t}, follow_redirects=False)
    assert fakes["allergen"].rows[b]["name"] == "Fish"
    # renaming to its own name is fine
    admin.post(f"/allergens/{b}/edit", data={"name": "Fish", "allergen_category": "Major", "csrf_token": t}, follow_redirects=False)
    assert fakes["allergen"].rows[b]["name"] == "Fish"


# ---------------------------------------------------------------- REST API
API_CASES = {
    "restaurants": ("restaurant", {"name": "API Bistro", "city": "Delhi"}, {"city": "Mumbai"}, "city"),
    "allergens": ("allergen", {"name": "Celery"}, {"description": "updated"}, "description"),
    "ingredients": ("ingredient", {"name": "Cashew"}, {"category": "Nuts"}, "category"),
    "dishes": ("dish", {"name": "API Curry", "price": 9.5}, {"price": 11.0}, "price"),
}


@pytest.mark.parametrize("path", list(API_CASES))
def test_api_full_crud(admin, fakes, path):
    key, body, patch, field = API_CASES[path]
    store = fakes[key]

    r = admin.post(f"/api/{path}", json=body)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    assert admin.get(f"/api/{path}").status_code == 200
    assert admin.get(f"/api/{path}/{rid}").json()["id"] == rid

    r = admin.put(f"/api/{path}/{rid}", json=patch)
    assert r.status_code == 200, r.text
    assert store.rows[rid][field] == patch[field]

    assert admin.delete(f"/api/{path}/{rid}").status_code == 200
    assert admin.get(f"/api/{path}/{rid}").status_code == 404
    assert admin.delete(f"/api/{path}/{rid}").status_code == 404


@pytest.mark.parametrize("path", list(API_CASES))
def test_viewer_cannot_write(viewer, fakes, path):
    key, body, *_ = API_CASES[path]
    assert viewer.post(f"/api/{path}", json=body).status_code == 403
    assert viewer.get(f"/api/{path}").status_code == 200       # but can read
    assert viewer.delete(f"/api/{path}/anything").status_code == 403


def test_users_api_does_not_leak_password_hash(admin, fakes, monkeypatch):
    monkeypatch.setattr(user_repo, "list_users", lambda **k: list(USERS.values()))
    monkeypatch.setattr(user_repo, "count_users", lambda **k: len(USERS))
    data = admin.get("/users/api/users").json()
    assert data["users"] and all("password_hash" not in u for u in data["users"])


# ------------------------------------------------------- Allergy checker page
def test_allergy_checker_shows_results_and_honours_filters(admin, fakes, monkeypatch):
    from app.repositories.allergy_checker_repo import allergy_checker_repo
    seen = {}

    def fake_check(**kw):
        seen.update(kw)
        return [{
            "restaurant_id": "r1", "restaurant_name": "Thai House", "restaurant_city": "Chennai",
            "dish_id": "d1", "dish_name": "Pad Thai", "dish_category": "Main Course", "dish_price": 9.5,
            "vegetarian": False, "vegan": False, "ingredient_data_status": "COMPLETE",
            "total_ingredients_recorded": 2, "is_incomplete": False,
            "matched_allergen_names": ["Peanuts"],
            "matched_ingredients": [{"ingredient_id": "i1", "ingredient_name": "Peanut Oil",
                                     "verification_status": "VERIFIED", "source_reference": "",
                                     "allergen_id": "a1", "allergen_name": "Peanuts"}],
            "matched_may_contain": [], "safety_summary": "CONTAINS MATCHED ALLERGENS (Direct recorded ingredient)",
        }]

    monkeypatch.setattr(allergy_checker_repo, "check_allergies", fake_check)
    monkeypatch.setattr(dish_repo, "get_distinct_categories", lambda: ["Soup"])

    # exactly what the form's GET submits
    r = admin.get("/allergy-checker", params=[
        ("allergens", "a1"), ("allergens", "a2"), ("match_mode", "ALL"),
        ("restaurant", "r1"), ("city", "Chennai"), ("category", "Main Course")])
    assert r.status_code == 200
    assert "Pad Thai" in r.text and "Peanut Oil" in r.text          # results are rendered
    assert "1 Matches Detected" in r.text
    assert seen["allergen_ids"] == ["a1", "a2"] and seen["match_mode"] == "ALL"
    assert seen["restaurant_id"] == "r1"                             # restaurant filter reaches the query
    assert seen["city"] == "Chennai"
    assert "Soup" in r.text                                          # custom dish categories are selectable

    # nothing selected -> form only, no results block
    r = admin.get("/allergy-checker")
    assert r.status_code == 200 and "Matches Detected" not in r.text

    # selected but nothing matched -> explicit zero-results message
    monkeypatch.setattr(allergy_checker_repo, "check_allergies", lambda **kw: [])
    r = admin.get("/allergy-checker", params=[("allergens", "a1")])
    assert "0 Matches Detected" in r.text
