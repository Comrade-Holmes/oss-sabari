from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, require_admin, get_flashed_messages
from app.repositories.reports_repo import reports_repo

router = APIRouter(prefix="/reports", tags=["Reports"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    current_user=Depends(require_admin),
):
    stats = reports_repo.get_dashboard_stats()
    allergen_dist = reports_repo.get_allergen_distribution()
    verification_breakdown = reports_repo.get_verification_status_breakdown()
    top_allergen_restaurants = reports_repo.get_top_allergen_restaurants(limit=10)
    incomplete_dishes = reports_repo.get_incomplete_dishes_report()
    unverified_ingredients = reports_repo.get_unverified_ingredients_report()
    rest_dist = reports_repo.get_restaurant_dish_distribution()

    return templates.TemplateResponse(
        "reports/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "reports",
            "stats": stats,
            "allergen_dist": allergen_dist,
            "rest_dist": rest_dist,
            "verification_breakdown": verification_breakdown,
            "top_allergen_restaurants": top_allergen_restaurants,
            "incomplete_dishes": incomplete_dishes,
            "unverified_ingredients": unverified_ingredients,
            "flashed_messages": get_flashed_messages(request),
        },
    )


# --- JSON API for charts ---

@router.get("/api/reports/stats")
async def api_stats(current_user=Depends(require_admin)):
    return reports_repo.get_dashboard_stats()


@router.get("/api/reports/allergen-distribution")
async def api_allergen_distribution(current_user=Depends(require_admin)):
    return reports_repo.get_allergen_distribution()


@router.get("/api/reports/verification-breakdown")
async def api_verification_breakdown(current_user=Depends(require_admin)):
    return reports_repo.get_verification_status_breakdown()


@router.get("/api/reports/top-allergen-restaurants")
async def api_top_allergen_restaurants(
    current_user=Depends(require_admin),
    limit: int = 10,
):
    return reports_repo.get_top_allergen_restaurants(limit=limit)


@router.get("/api/reports/incomplete-dishes")
async def api_incomplete_dishes(current_user=Depends(require_admin)):
    return reports_repo.get_incomplete_dishes_report()


@router.get("/api/reports/unverified-ingredients")
async def api_unverified_ingredients(current_user=Depends(require_admin)):
    return reports_repo.get_unverified_ingredients_report()
