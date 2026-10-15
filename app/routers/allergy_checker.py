from pathlib import Path
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, get_flashed_messages, flash
from app.repositories.allergy_checker_repo import allergy_checker_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.security import generate_csrf_token

router = APIRouter(tags=["Allergy Checker"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _sid(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]


_DEFAULT_CATEGORIES = ["Starter", "Main Course", "Dessert", "Beverage", "Side Dish", "Snack"]


def _categories() -> List[str]:
    """Default categories plus whatever categories dishes actually use."""
    try:
        existing = dish_repo.get_distinct_categories()
    except Exception:
        existing = []
    return sorted(set(_DEFAULT_CATEGORIES) | set(existing))


@router.get("/allergy-checker", response_class=HTMLResponse)
async def allergy_checker_page(
    request: Request,
    current_user=Depends(get_current_user),
    allergens: List[str] = Query(default=[]),
    match_mode: str = Query(default="ANY"),
    restaurant: Optional[str] = Query(default=None),
    restaurant_id: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
):
    # The HTML form submits the restaurant filter as "restaurant"; the API style is "restaurant_id".
    restaurant_id = (restaurant or restaurant_id or "").strip() or None
    sid = _sid(request)
    all_allergens = allergen_repo.list_allergens(limit=200)
    restaurants = restaurant_repo.list_restaurants(limit=100)
    cities = restaurant_repo.get_distinct_cities()
    categories = _categories()

    results = None
    clean_allergens = [a for a in allergens if a.strip()]
    if clean_allergens:
        results = allergy_checker_repo.check_allergies(
            allergen_ids=clean_allergens,
            match_mode=match_mode.upper(),
            restaurant_id=restaurant_id.strip() if restaurant_id and restaurant_id.strip() else None,
            city=city.strip() if city and city.strip() else None,
            category=category.strip() if category and category.strip() else None,
        )

    return templates.TemplateResponse(
        "allergy_checker/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "allergy_checker",
            "allergens": all_allergens,
            "selected_allergen_ids": clean_allergens,
            "match_mode": match_mode.upper(),
            "selected_restaurant": restaurant_id,
            "selected_city": city,
            "selected_category": category,
            "restaurants": restaurants,
            "cities": cities,
            "categories": categories,
            "results": results or [],
            "has_searched": bool(clean_allergens),
            "csrf_token": generate_csrf_token(sid),
            "flashed_messages": get_flashed_messages(request),
        },
    )


@router.post("/allergy-checker", response_class=HTMLResponse)
async def allergy_checker_submit(
    request: Request,
    current_user=Depends(get_current_user),
    allergen_ids: List[str] = Form(default=[]),
    match_mode: str = Form(default="ANY"),
    restaurant_id: Optional[str] = Form(default=None),
    city: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default=None),
    csrf_token: str = Form(default=""),
):
    sid = _sid(request)
    allergens_all = allergen_repo.list_allergens(limit=200)
    restaurants = restaurant_repo.list_restaurants(limit=100)
    cities = restaurant_repo.get_distinct_cities()
    dish_categories = _categories()

    results = []
    search_params = {}

    if allergen_ids:
        # Clean empty values
        allergen_ids_clean = [a for a in allergen_ids if a.strip()]
        restaurant_id_clean = restaurant_id.strip() if restaurant_id and restaurant_id.strip() else None
        city_clean = city.strip() if city and city.strip() else None
        category_clean = category.strip() if category and category.strip() else None

        search_params = {
            "allergen_ids": allergen_ids_clean,
            "match_mode": match_mode.upper(),
            "restaurant_id": restaurant_id_clean,
            "city": city_clean,
            "category": category_clean,
        }

        results = allergy_checker_repo.check_allergies(
            allergen_ids=allergen_ids_clean,
            match_mode=match_mode.upper(),
            restaurant_id=restaurant_id_clean,
            city=city_clean,
            category=category_clean,
        )

        if not results:
            flash(request, "No matching dishes found for the selected allergens and filters.", "info")
    else:
        flash(request, "Please select at least one allergen to check.", "warning")

    return templates.TemplateResponse(
        "allergy_checker/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "allergy_checker",
            "allergens": allergens_all,
            "restaurants": restaurants,
            "cities": cities,
            "categories": dish_categories,
            "results": results,
            "has_searched": bool(allergen_ids),
            "match_mode": match_mode.upper(),
            "selected_allergen_ids": search_params.get("allergen_ids", []),
            "selected_restaurant": search_params.get("restaurant_id"),
            "selected_city": search_params.get("city"),
            "selected_category": search_params.get("category"),
            "search_params": search_params,
            "csrf_token": generate_csrf_token(sid),
            "flashed_messages": get_flashed_messages(request),
        },
    )


@router.get("/api/allergy-checker")
async def api_allergy_check(
    current_user=Depends(get_current_user),
    allergen_ids: List[str] = Query(default=[]),
    match_mode: str = Query(default="ANY"),
    restaurant_id: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
):
    if not allergen_ids:
        return {"results": [], "count": 0}
    results = allergy_checker_repo.check_allergies(
        allergen_ids=allergen_ids,
        match_mode=match_mode,
        restaurant_id=restaurant_id,
        city=city,
        category=category,
    )
    return {"results": results, "count": len(results)}
