from pathlib import Path
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, get_flashed_messages
from app.repositories.graph_repo import graph_repo
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.allergen_repo import allergen_repo

router = APIRouter(tags=["Graph"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _sid(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]


@router.get("/graph", response_class=HTMLResponse)
async def graph_view(
    request: Request,
    current_user=Depends(get_current_user),
):
    restaurants = restaurant_repo.list_restaurants(limit=50)
    allergens = allergen_repo.list_allergens(limit=50)
    return templates.TemplateResponse(
        "graph/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "graph",
            "restaurants": restaurants,
            "allergens": allergens,
            "flashed_messages": get_flashed_messages(request),
        },
    )


# --- API endpoints consumed by the graph JS ---

@router.get("/api/graph/data")
async def api_graph_data(
    request: Request,
    current_user=Depends(get_current_user),
    limit: int = Query(default=120, ge=10, le=400),
    types: Optional[str] = Query(default=None, description="Comma-separated: Restaurant,Dish,Ingredient,Allergen"),
    search: Optional[str] = Query(default=None),
):
    node_types = [t.strip() for t in types.split(",")] if types else None
    data = graph_repo.get_graph_data(limit=limit, node_types=node_types, search=search)
    return data


@router.get("/api/graph/expand/{node_id}")
async def api_expand_node(
    node_id: str,
    current_user=Depends(get_current_user),
    limit: int = Query(default=30, ge=5, le=100),
):
    data = graph_repo.expand_node(node_id=node_id, limit=limit)
    return data


@router.get("/api/graph/allergen-paths")
@router.get("/api/graph/paths")
async def api_allergen_paths(
    current_user=Depends(get_current_user),
    restaurant_id: Optional[str] = Query(default=None),
    allergen_id: Optional[str] = Query(default=None),
):
    data = graph_repo.get_allergen_paths(restaurant_id=restaurant_id, allergen_id=allergen_id)
    return data
