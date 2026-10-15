from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, get_flashed_messages
from app.repositories.reports_repo import reports_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.restaurant_repo import restaurant_repo

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request, current_user = Depends(get_current_user)):
    role = str(current_user.get("role", "VIEWER")).upper()
    stats = reports_repo.get_dashboard_stats()

    if role == "ADMIN":
        allergen_dist = reports_repo.get_allergen_distribution()
        verification_breakdown = reports_repo.get_verification_status_breakdown()
        recent_logs = activity_log_repo.list_logs(limit=6)
        
        return templates.TemplateResponse("dashboard/admin.html", {
            "request": request,
            "current_user": current_user,
            "active_page": "dashboard",
            "stats": stats,
            "allergen_dist": allergen_dist,
            "verification_breakdown": verification_breakdown,
            "recent_logs": recent_logs,
            "flashed_messages": get_flashed_messages(request)
        })

    elif role == "EDITOR":
        incomplete_dishes = reports_repo.get_incomplete_dishes_report()
        unverified_ingredients = reports_repo.get_unverified_ingredients_report()

        return templates.TemplateResponse("dashboard/editor.html", {
            "request": request,
            "current_user": current_user,
            "active_page": "dashboard",
            "stats": stats,
            "incomplete_dishes": incomplete_dishes,
            "unverified_ingredients": unverified_ingredients,
            "flashed_messages": get_flashed_messages(request)
        })

    else:
        # VIEWER
        allergens = allergen_repo.list_allergens(limit=12)
        restaurants = restaurant_repo.list_restaurants(limit=5)

        return templates.TemplateResponse("dashboard/viewer.html", {
            "request": request,
            "current_user": current_user,
            "active_page": "dashboard",
            "allergens": allergens,
            "restaurants": restaurants,
            "flashed_messages": get_flashed_messages(request)
        })

@router.get("/api/dashboard/stats")
async def api_dashboard_stats(current_user = Depends(get_current_user)):
    return reports_repo.get_dashboard_stats()
