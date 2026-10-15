from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import (
    get_current_user, require_editor_or_admin, require_admin,
    get_flashed_messages, flash
)
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import generate_csrf_token, verify_csrf_token
from app.schemas import RestaurantCreate, RestaurantUpdate, RestaurantResponse

router = APIRouter(tags=["Restaurants"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# --- HTML Endpoints ---

@router.get("/restaurants", response_class=HTMLResponse)
async def list_restaurants_view(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    limit = 10
    skip = max(0, (page - 1) * limit)
    restaurants = restaurant_repo.list_restaurants(skip=skip, limit=limit, search=search, city=city, cuisine=cuisine)
    total_count = restaurant_repo.count_restaurants(search=search, city=city, cuisine=cuisine)
    total_pages = max(1, (total_count + limit - 1) // limit)

    cities = restaurant_repo.get_distinct_cities()
    cuisines = restaurant_repo.get_distinct_cuisines()
    sid = get_session_id(request)

    return templates.TemplateResponse("restaurants/list.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "restaurants",
        "restaurants": restaurants,
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "search": search,
        "selected_city": city,
        "selected_cuisine": cuisine,
        "cities": cities,
        "cuisines": cuisines,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/restaurants/new", response_class=HTMLResponse)
async def new_restaurant_view(
    request: Request,
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    return templates.TemplateResponse("restaurants/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "restaurants",
        "is_edit": False,
        "restaurant": None,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/restaurants/new")
async def create_restaurant_view(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    cuisine_type: str = Form("Various"),
    city: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    status: str = Form("ACTIVE"),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/restaurants/new", status_code=303)

    data = {
        "name": name,
        "description": description,
        "cuisine_type": cuisine_type,
        "city": city,
        "address": address,
        "phone": phone,
        "email": email,
        "status": status
    }
    created = restaurant_repo.create(data)
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Restaurant",
        entity_id=created["id"],
        description=f"Registered new partner restaurant '{created['name']}' in {created['city']}."
    )

    flash(request, f"Restaurant '{created['name']}' created successfully!", "success")
    return RedirectResponse(url=f"/restaurants/{created['id']}", status_code=303)

@router.get("/restaurants/{restaurant_id}", response_class=HTMLResponse)
async def view_restaurant_detail(
    request: Request,
    restaurant_id: str,
    current_user = Depends(get_current_user)
):
    restaurant = restaurant_repo.get_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    dishes = restaurant_repo.get_restaurant_dishes(restaurant_id)

    return templates.TemplateResponse("restaurants/detail.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "restaurants",
        "restaurant": restaurant,
        "dishes": dishes,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/restaurants/{restaurant_id}/edit", response_class=HTMLResponse)
async def edit_restaurant_view(
    request: Request,
    restaurant_id: str,
    current_user = Depends(require_editor_or_admin)
):
    restaurant = restaurant_repo.get_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    sid = get_session_id(request)
    return templates.TemplateResponse("restaurants/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "restaurants",
        "is_edit": True,
        "restaurant": restaurant,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/restaurants/{restaurant_id}/edit")
async def update_restaurant_view(
    request: Request,
    restaurant_id: str,
    name: str = Form(...),
    description: str = Form(""),
    cuisine_type: str = Form("Various"),
    city: str = Form(...),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    status: str = Form("ACTIVE"),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url=f"/restaurants/{restaurant_id}/edit", status_code=303)

    data = {
        "name": name,
        "description": description,
        "cuisine_type": cuisine_type,
        "city": city,
        "address": address,
        "phone": phone,
        "email": email,
        "status": status
    }
    updated = restaurant_repo.update(restaurant_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Restaurant",
        entity_id=restaurant_id,
        description=f"Updated profile for restaurant '{updated['name']}'."
    )

    flash(request, f"Restaurant '{updated['name']}' updated successfully!", "success")
    return RedirectResponse(url=f"/restaurants/{restaurant_id}", status_code=303)

@router.post("/restaurants/{restaurant_id}/delete")
async def delete_restaurant_view(
    request: Request,
    restaurant_id: str,
    csrf_token: str = Form(...),
    current_user = Depends(require_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/restaurants", status_code=303)

    rest = restaurant_repo.get_by_id(restaurant_id)
    name = rest["name"] if rest else restaurant_id
    success = restaurant_repo.delete(restaurant_id)

    if success:
        activity_log_repo.log(
            actor_id=current_user["id"],
            actor_name=current_user["full_name"],
            action="DELETE",
            entity_type="Restaurant",
            entity_id=restaurant_id,
            description=f"Removed restaurant '{name}'."
        )
        flash(request, f"Restaurant '{name}' has been deleted.", "success")
    else:
        flash(request, "Could not delete restaurant or it did not exist.", "error")

    return RedirectResponse(url="/restaurants", status_code=303)

# --- REST APIs ---

@router.get("/api/restaurants")
async def api_list_restaurants(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    return restaurant_repo.list_restaurants(skip=skip, limit=limit, search=search, city=city, cuisine=cuisine)

@router.post("/api/restaurants", status_code=201)
async def api_create_restaurant(
    payload: RestaurantCreate,
    current_user = Depends(require_editor_or_admin)
):
    res = restaurant_repo.create(payload.model_dump())
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Restaurant",
        entity_id=res["id"],
        description=f"API: Created restaurant '{res['name']}'."
    )
    return res

@router.get("/api/restaurants/{restaurant_id}")
async def api_get_restaurant(
    restaurant_id: str,
    current_user = Depends(get_current_user)
):
    res = restaurant_repo.get_by_id(restaurant_id)
    if not res:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return res

@router.put("/api/restaurants/{restaurant_id}")
async def api_update_restaurant(
    restaurant_id: str,
    payload: RestaurantUpdate,
    current_user = Depends(require_editor_or_admin)
):
    res = restaurant_repo.update(restaurant_id, payload.model_dump(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Restaurant",
        entity_id=restaurant_id,
        description=f"API: Updated restaurant '{res['name']}'."
    )
    return res

@router.delete("/api/restaurants/{restaurant_id}")
async def api_delete_restaurant(
    restaurant_id: str,
    current_user = Depends(require_admin)
):
    success = restaurant_repo.delete(restaurant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="DELETE",
        entity_type="Restaurant",
        entity_id=restaurant_id,
        description=f"API: Deleted restaurant '{restaurant_id}'."
    )
    return {"message": "Restaurant deleted successfully"}
