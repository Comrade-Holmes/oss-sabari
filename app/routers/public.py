from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.dependencies import get_current_user_optional, get_flashed_messages, flash
from app.security import generate_csrf_token
from app.repositories.allergen_repo import allergen_repo
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.dish_repo import dish_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.database import db

router = APIRouter(tags=["Public"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request, current_user = Depends(get_current_user_optional)):
    sid = get_session_id(request)
    allergens = allergen_repo.list_allergens(limit=20)
    return templates.TemplateResponse("public/index.html", {
        "request": request,
        "current_user": current_user,
        "allergens": allergens,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, current_user = Depends(get_current_user_optional)):
    return templates.TemplateResponse("public/about.html", {
        "request": request,
        "current_user": current_user,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, current_user = Depends(get_current_user_optional)):
    sid = get_session_id(request)
    return templates.TemplateResponse("public/contact.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/contact", response_class=HTMLResponse)
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    current_user = Depends(get_current_user_optional)
):
    flash(request, f"Thank you, {name}! Your inquiry has been received. Our team will contact you at {email}.", "success")
    sid = get_session_id(request)
    return templates.TemplateResponse("public/contact.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request, current_user = Depends(get_current_user_optional)):
    return templates.TemplateResponse("public/privacy.html", {
        "request": request,
        "current_user": current_user,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/search", response_class=HTMLResponse)
async def global_search(
    request: Request,
    q: Optional[str] = "",
    current_user = Depends(get_current_user_optional)
):
    query = (q or "").strip()
    results = {"restaurants": [], "dishes": [], "ingredients": [], "allergens": []}

    if query:
        results["restaurants"] = restaurant_repo.list_restaurants(limit=8, search=query)
        results["dishes"] = dish_repo.list_dishes(limit=8, search=query)
        results["ingredients"] = ingredient_repo.list_ingredients(limit=12, search=query)
        results["allergens"] = allergen_repo.list_allergens(limit=8, search=query)

    return templates.TemplateResponse("public/search.html", {
        "request": request,
        "current_user": current_user,
        "query": query,
        "results": results,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/api/health")
async def health_check():
    neo4j_healthy = False
    try:
        neo4j_healthy = db.verify_connectivity()
    except Exception:
        neo4j_healthy = False

    return {
        "status": "healthy" if neo4j_healthy else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database_connected": neo4j_healthy
    }
