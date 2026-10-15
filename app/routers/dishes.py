from pathlib import Path
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import (
    get_current_user, require_editor_or_admin, require_admin,
    get_flashed_messages, flash
)
from app.repositories.dish_repo import dish_repo
from app.repositories.restaurant_repo import restaurant_repo
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import generate_csrf_token, verify_csrf_token
from app.schemas import DishCreate, DishUpdate, DishResponse

router = APIRouter(tags=["Dishes"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# --- HTML Endpoints ---

@router.get("/dishes", response_class=HTMLResponse)
async def list_dishes_view(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    restaurant: Optional[str] = None,
    category: Optional[str] = None,
    allergen: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    limit = 10
    skip = max(0, (page - 1) * limit)

    dishes = dish_repo.list_dishes(skip=skip, limit=limit, search=search, restaurant_id=restaurant, category=category, allergen_id=allergen)
    total_count = dish_repo.count_dishes(search=search, restaurant_id=restaurant, category=category, allergen_id=allergen)
    total_pages = max(1, (total_count + limit - 1) // limit)

    restaurants = restaurant_repo.list_restaurants(limit=1000)
    categories = dish_repo.get_distinct_categories()
    allergens = allergen_repo.list_allergens(limit=500)
    sid = get_session_id(request)

    return templates.TemplateResponse("dishes/list.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "dishes",
        "dishes": dishes,
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "search": search,
        "selected_restaurant": restaurant,
        "selected_category": category,
        "selected_allergen": allergen,
        "restaurants": restaurants,
        "categories": categories,
        "allergens": allergens,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/dishes/new", response_class=HTMLResponse)
async def new_dish_view(
    request: Request,
    current_user = Depends(require_editor_or_admin)
):
    all_restaurants = restaurant_repo.list_restaurants(limit=1000)
    all_ingredients = ingredient_repo.list_ingredients(limit=1000)
    all_allergens = allergen_repo.list_allergens(limit=500)
    sid = get_session_id(request)

    return templates.TemplateResponse("dishes/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "dishes",
        "is_edit": False,
        "dish": None,
        "all_restaurants": all_restaurants,
        "all_ingredients": all_ingredients,
        "all_allergens": all_allergens,
        "selected_restaurant_ids": [],
        "selected_ingredient_ids": [],
        "selected_may_contain_ids": [],
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/dishes/new")
async def create_dish_view(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("Main Course"),
    price: float = Form(0.0),
    vegetarian: Optional[str] = Form(None),
    vegan: Optional[str] = Form(None),
    preparation_notes: str = Form(""),
    availability_status: str = Form("AVAILABLE"),
    ingredient_data_status: str = Form("PARTIAL"),
    restaurant_ids: List[str] = Form([]),
    ingredient_ids: List[str] = Form([]),
    may_contain_allergen_ids: List[str] = Form([]),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/dishes/new", status_code=303)

    data = {
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "vegetarian": bool(vegetarian),
        "vegan": bool(vegan),
        "preparation_notes": preparation_notes,
        "availability_status": availability_status,
        "ingredient_data_status": ingredient_data_status
    }
    created = dish_repo.create(data, restaurant_ids, ingredient_ids, may_contain_allergen_ids)

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Dish",
        entity_id=created["id"],
        description=f"Created dish '{created['name']}' with {len(ingredient_ids)} ingredients."
    )

    flash(request, f"Dish '{created['name']}' created successfully!", "success")
    return RedirectResponse(url=f"/dishes/{created['id']}", status_code=303)

@router.get("/dishes/{dish_id}", response_class=HTMLResponse)
async def view_dish_detail(
    request: Request,
    dish_id: str,
    current_user = Depends(get_current_user)
):
    dish = dish_repo.get_by_id(dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    return templates.TemplateResponse("dishes/detail.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "dishes",
        "dish": dish,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/dishes/{dish_id}/edit", response_class=HTMLResponse)
async def edit_dish_view(
    request: Request,
    dish_id: str,
    current_user = Depends(require_editor_or_admin)
):
    dish = dish_repo.get_by_id(dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    all_restaurants = restaurant_repo.list_restaurants(limit=1000)
    all_ingredients = ingredient_repo.list_ingredients(limit=1000)
    all_allergens = allergen_repo.list_allergens(limit=500)

    selected_restaurant_ids = [r["id"] for r in dish.get("restaurants", [])]
    selected_ingredient_ids = [i["id"] for i in dish.get("ingredients", [])]
    selected_may_contain_ids = [m["id"] for m in dish.get("may_contain_allergens", [])]

    sid = get_session_id(request)

    return templates.TemplateResponse("dishes/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "dishes",
        "is_edit": True,
        "dish": dish,
        "all_restaurants": all_restaurants,
        "all_ingredients": all_ingredients,
        "all_allergens": all_allergens,
        "selected_restaurant_ids": selected_restaurant_ids,
        "selected_ingredient_ids": selected_ingredient_ids,
        "selected_may_contain_ids": selected_may_contain_ids,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/dishes/{dish_id}/edit")
async def update_dish_view(
    request: Request,
    dish_id: str,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("Main Course"),
    price: float = Form(0.0),
    vegetarian: Optional[str] = Form(None),
    vegan: Optional[str] = Form(None),
    preparation_notes: str = Form(""),
    availability_status: str = Form("AVAILABLE"),
    ingredient_data_status: str = Form("PARTIAL"),
    restaurant_ids: List[str] = Form([]),
    ingredient_ids: List[str] = Form([]),
    may_contain_allergen_ids: List[str] = Form([]),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url=f"/dishes/{dish_id}/edit", status_code=303)

    data = {
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "vegetarian": bool(vegetarian),
        "vegan": bool(vegan),
        "preparation_notes": preparation_notes,
        "availability_status": availability_status,
        "ingredient_data_status": ingredient_data_status
    }
    updated = dish_repo.update(dish_id, data, restaurant_ids, ingredient_ids, may_contain_allergen_ids)
    if not updated:
        raise HTTPException(status_code=404, detail="Dish not found")

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Dish",
        entity_id=dish_id,
        description=f"Updated dish recipe '{updated['name']}'."
    )

    flash(request, f"Dish '{updated['name']}' updated successfully!", "success")
    return RedirectResponse(url=f"/dishes/{dish_id}", status_code=303)

@router.post("/dishes/{dish_id}/delete")
async def delete_dish_view(
    request: Request,
    dish_id: str,
    csrf_token: str = Form(...),
    current_user = Depends(require_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/dishes", status_code=303)

    dish = dish_repo.get_by_id(dish_id)
    name = dish["name"] if dish else dish_id
    success = dish_repo.delete(dish_id)

    if success:
        activity_log_repo.log(
            actor_id=current_user["id"],
            actor_name=current_user["full_name"],
            action="DELETE",
            entity_type="Dish",
            entity_id=dish_id,
            description=f"Deleted dish '{name}'."
        )
        flash(request, f"Dish '{name}' deleted successfully.", "success")
    else:
        flash(request, "Could not delete dish.", "error")

    return RedirectResponse(url="/dishes", status_code=303)

# --- REST APIs ---

@router.get("/api/dishes")
async def api_list_dishes(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    restaurant_id: Optional[str] = None,
    category: Optional[str] = None,
    allergen_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    return dish_repo.list_dishes(skip=skip, limit=limit, search=search, restaurant_id=restaurant_id, category=category, allergen_id=allergen_id)

@router.post("/api/dishes", status_code=201)
async def api_create_dish(
    payload: DishCreate,
    current_user = Depends(require_editor_or_admin)
):
    dish_data = payload.model_dump(exclude={"restaurant_ids", "ingredient_ids", "may_contain_allergen_ids"})
    created = dish_repo.create(
        dish_data,
        payload.restaurant_ids,
        payload.ingredient_ids,
        payload.may_contain_allergen_ids
    )
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Dish",
        entity_id=created["id"],
        description=f"API: Created dish '{created['name']}'."
    )
    return created

@router.get("/api/dishes/{dish_id}")
async def api_get_dish(
    dish_id: str,
    current_user = Depends(get_current_user)
):
    res = dish_repo.get_by_id(dish_id)
    if not res:
        raise HTTPException(status_code=404, detail="Dish not found")
    return res

@router.put("/api/dishes/{dish_id}")
async def api_update_dish(
    dish_id: str,
    payload: DishUpdate,
    current_user = Depends(require_editor_or_admin)
):
    update_data = payload.model_dump(exclude_unset=True, exclude={"restaurant_ids", "ingredient_ids", "may_contain_allergen_ids"})
    updated = dish_repo.update(
        dish_id,
        update_data,
        payload.restaurant_ids,
        payload.ingredient_ids,
        payload.may_contain_allergen_ids
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Dish not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Dish",
        entity_id=dish_id,
        description=f"API: Updated dish '{updated['name']}'."
    )
    return updated

@router.delete("/api/dishes/{dish_id}")
async def api_delete_dish(
    dish_id: str,
    current_user = Depends(require_admin)
):
    success = dish_repo.delete(dish_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dish not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="DELETE",
        entity_type="Dish",
        entity_id=dish_id,
        description=f"API: Deleted dish '{dish_id}'."
    )
    return {"message": "Dish deleted successfully"}
