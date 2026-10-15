"""
LIVE-database CRUD tests (need Neo4j running + schema initialised, same as the
other tests in this folder). They create their own uniquely named records and
delete them afterwards, so they are safe to run against the seeded demo DB.
"""
import uuid
import pytest

from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo


def _tag():
    return f"zz-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def cleanup():
    created = []  # (repo, id)
    yield created
    for repo, rid in reversed(created):
        try:
            repo.delete(rid)
        except Exception:
            pass


def test_restaurant_crud(cleanup):
    t = _tag()
    r = restaurant_repo.create({"name": t, "city": "Chennai", "cuisine_type": "Test"})
    cleanup.append((restaurant_repo, r["id"]))
    assert restaurant_repo.get_by_id(r["id"])["name"] == t

    u = restaurant_repo.update(r["id"], {"city": "Madurai", "status": "INACTIVE"})
    assert u["city"] == "Madurai" and u["status"] == "INACTIVE" and u["name"] == t

    assert restaurant_repo.delete(r["id"]) is True
    assert restaurant_repo.get_by_id(r["id"]) is None
    assert restaurant_repo.delete(r["id"]) is False


def test_allergen_crud(cleanup):
    t = _tag()
    a = allergen_repo.create({"name": t, "allergen_category": "Major"})
    cleanup.append((allergen_repo, a["id"]))
    assert allergen_repo.get_by_name(t)["id"] == a["id"]

    u = allergen_repo.update(a["id"], {"description": "changed"})
    assert u["description"] == "changed" and u["name"] == t

    assert allergen_repo.delete(a["id"]) is True
    assert allergen_repo.get_by_id(a["id"]) is None


def test_ingredient_crud_with_allergen_links(cleanup):
    a1 = allergen_repo.create({"name": _tag()}); cleanup.append((allergen_repo, a1["id"]))
    a2 = allergen_repo.create({"name": _tag()}); cleanup.append((allergen_repo, a2["id"]))

    i = ingredient_repo.create({"name": _tag(), "category": "Test"}, [a1["id"]])
    cleanup.append((ingredient_repo, i["id"]))
    assert [a["id"] for a in i["allergens"]] == [a1["id"]]

    # replace links
    i = ingredient_repo.update(i["id"], {"verification_status": "VERIFIED"}, [a2["id"]])
    assert [a["id"] for a in i["allergens"]] == [a2["id"]]
    assert i["verification_status"] == "VERIFIED" and i.get("last_verified_at")

    # None = leave links alone, [] = clear them
    i = ingredient_repo.update(i["id"], {"category": "Test2"}, None)
    assert len(i["allergens"]) == 1
    i = ingredient_repo.update(i["id"], {}, [])
    assert i["allergens"] == []

    assert ingredient_repo.delete(i["id"]) is True
    assert ingredient_repo.get_by_id(i["id"]) is None


def test_dish_crud_with_all_relationship_kinds(cleanup):
    rest = restaurant_repo.create({"name": _tag(), "city": "X"}); cleanup.append((restaurant_repo, rest["id"]))
    ing = ingredient_repo.create({"name": _tag()}); cleanup.append((ingredient_repo, ing["id"]))
    alg = allergen_repo.create({"name": _tag()}); cleanup.append((allergen_repo, alg["id"]))

    # NOTE: no restaurant on purpose -> ingredients / may-contain must STILL be linked
    d = dish_repo.create({"name": _tag(), "price": 10}, [], [ing["id"]], [alg["id"]])
    cleanup.append((dish_repo, d["id"]))
    assert [i["id"] for i in d["ingredients"]] == [ing["id"]]
    assert [a["id"] for a in d["may_contain_allergens"]] == [alg["id"]]
    assert d["restaurants"] == []

    d = dish_repo.update(d["id"], {"price": 12.5, "vegan": True}, [rest["id"]], None, None)
    assert d["price"] == 12.5 and d["vegan"] is True
    assert [r["id"] for r in d["restaurants"]] == [rest["id"]]
    assert len(d["ingredients"]) == 1 and len(d["may_contain_allergens"]) == 1  # untouched

    d = dish_repo.update(d["id"], {}, [], [], [])
    assert d["restaurants"] == [] and d["ingredients"] == [] and d["may_contain_allergens"] == []

    assert dish_repo.delete(d["id"]) is True
    assert dish_repo.get_by_id(d["id"]) is None
    assert dish_repo.update("does-not-exist", {"name": "x"}) is None
