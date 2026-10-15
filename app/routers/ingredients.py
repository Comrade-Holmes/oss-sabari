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
from app.repositories.ingredient_repo import ingredient_repo
from app.repositories.allergen_repo import allergen_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import generate_csrf_token, verify_csrf_token
from app.schemas import IngredientCreate, IngredientUpdate, IngredientResponse

router = APIRouter(tags=["Ingredients"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# --- HTML Endpoints ---

@router.get("/ingredients", response_class=HTMLResponse)
async def list_ingredients_view(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    category: Optional[str] = None,
    verification: Optional[str] = None,
    allergen: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    limit = 10
    skip = max(0, (page - 1) * limit)

    ingredients = ingredient_repo.list_ingredients(
        skip=skip, limit=limit, search=search, category=category,
        verification_status=verification, allergen_id=allergen
    )
    total_count = ingredient_repo.count_ingredients(
        search=search, category=category,
        verification_status=verification, allergen_id=allergen
    )
    total_pages = max(1, (total_count + limit - 1) // limit)

    categories = ingredient_repo.get_distinct_categories()
    allergens = allergen_repo.list_allergens(limit=500)
    sid = get_session_id(request)

    return templates.TemplateResponse("ingredients/list.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "ingredients",
        "ingredients": ingredients,
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "search": search,
        "selected_category": category,
        "selected_verification": verification,
        "selected_allergen": allergen,
        "categories": categories,
        "allergens": allergens,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/ingredients/new", response_class=HTMLResponse)
async def new_ingredient_view(
    request: Request,
    current_user = Depends(require_editor_or_admin)
):
    all_allergens = allergen_repo.list_allergens(limit=500)
    sid = get_session_id(request)
    return templates.TemplateResponse("ingredients/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "ingredients",
        "is_edit": False,
        "ingredient": None,
        "all_allergens": all_allergens,
        "selected_allergen_ids": [],
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/ingredients/new")
async def create_ingredient_view(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("General"),
    verification_status: str = Form("UNVERIFIED"),
    source_reference: str = Form(""),
    allergen_ids: List[str] = Form([]),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/ingredients/new", status_code=303)

    data = {
        "name": name,
        "description": description,
        "category": category,
        "verification_status": verification_status,
        "source_reference": source_reference
    }
    created = ingredient_repo.create(data, allergen_ids)

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Ingredient",
        entity_id=created["id"],
        description=f"Created ingredient '{created['name']}' ({verification_status})."
    )

    flash(request, f"Ingredient '{created['name']}' created successfully!", "success")
    return RedirectResponse(url=f"/ingredients/{created['id']}", status_code=303)

@router.get("/ingredients/{ingredient_id}", response_class=HTMLResponse)
async def view_ingredient_detail(
    request: Request,
    ingredient_id: str,
    current_user = Depends(get_current_user)
):
    ingredient = ingredient_repo.get_by_id(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    return templates.TemplateResponse("ingredients/detail.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "ingredients",
        "ingredient": ingredient,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/ingredients/{ingredient_id}/edit", response_class=HTMLResponse)
async def edit_ingredient_view(
    request: Request,
    ingredient_id: str,
    current_user = Depends(require_editor_or_admin)
):
    ingredient = ingredient_repo.get_by_id(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    all_allergens = allergen_repo.list_allergens(limit=500)
    selected_allergen_ids = [a["id"] for a in ingredient.get("allergens", [])]
    sid = get_session_id(request)

    return templates.TemplateResponse("ingredients/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "ingredients",
        "is_edit": True,
        "ingredient": ingredient,
        "all_allergens": all_allergens,
        "selected_allergen_ids": selected_allergen_ids,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/ingredients/{ingredient_id}/edit")
async def update_ingredient_view(
    request: Request,
    ingredient_id: str,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("General"),
    verification_status: str = Form("UNVERIFIED"),
    source_reference: str = Form(""),
    allergen_ids: List[str] = Form([]),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url=f"/ingredients/{ingredient_id}/edit", status_code=303)

    data = {
        "name": name,
        "description": description,
        "category": category,
        "verification_status": verification_status,
        "source_reference": source_reference
    }
    updated = ingredient_repo.update(ingredient_id, data, allergen_ids)
    if not updated:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Ingredient",
        entity_id=ingredient_id,
        description=f"Updated ingredient '{updated['name']}' ({verification_status})."
    )

    flash(request, f"Ingredient '{updated['name']}' updated successfully!", "success")
    return RedirectResponse(url=f"/ingredients/{ingredient_id}", status_code=303)

@router.post("/ingredients/{ingredient_id}/delete")
async def delete_ingredient_view(
    request: Request,
    ingredient_id: str,
    csrf_token: str = Form(...),
    current_user = Depends(require_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/ingredients", status_code=303)

    ing = ingredient_repo.get_by_id(ingredient_id)
    name = ing["name"] if ing else ingredient_id
    success = ingredient_repo.delete(ingredient_id)

    if success:
        activity_log_repo.log(
            actor_id=current_user["id"],
            actor_name=current_user["full_name"],
            action="DELETE",
            entity_type="Ingredient",
            entity_id=ingredient_id,
            description=f"Deleted ingredient '{name}'."
        )
        flash(request, f"Ingredient '{name}' deleted successfully.", "success")
    else:
        flash(request, "Could not delete ingredient.", "error")

    return RedirectResponse(url="/ingredients", status_code=303)

# --- REST APIs ---

@router.get("/api/ingredients")
async def api_list_ingredients(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    verification_status: Optional[str] = None,
    allergen_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    return ingredient_repo.list_ingredients(
        skip=skip, limit=limit, search=search, category=category,
        verification_status=verification_status, allergen_id=allergen_id
    )

@router.post("/api/ingredients", status_code=201)
async def api_create_ingredient(
    payload: IngredientCreate,
    current_user = Depends(require_editor_or_admin)
):
    data = payload.model_dump(exclude={"allergen_ids"})
    created = ingredient_repo.create(data, payload.allergen_ids)
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Ingredient",
        entity_id=created["id"],
        description=f"API: Created ingredient '{created['name']}'."
    )
    return created

@router.get("/api/ingredients/{ingredient_id}")
async def api_get_ingredient(
    ingredient_id: str,
    current_user = Depends(get_current_user)
):
    res = ingredient_repo.get_by_id(ingredient_id)
    if not res:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return res

@router.put("/api/ingredients/{ingredient_id}")
async def api_update_ingredient(
    ingredient_id: str,
    payload: IngredientUpdate,
    current_user = Depends(require_editor_or_admin)
):
    update_data = payload.model_dump(exclude_unset=True, exclude={"allergen_ids"})
    updated = ingredient_repo.update(ingredient_id, update_data, payload.allergen_ids)
    if not updated:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Ingredient",
        entity_id=ingredient_id,
        description=f"API: Updated ingredient '{updated['name']}'."
    )
    return updated

@router.delete("/api/ingredients/{ingredient_id}")
async def api_delete_ingredient(
    ingredient_id: str,
    current_user = Depends(require_admin)
):
    success = ingredient_repo.delete(ingredient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="DELETE",
        entity_type="Ingredient",
        entity_id=ingredient_id,
        description=f"API: Deleted ingredient '{ingredient_id}'."
    )
    return {"message": "Ingredient deleted successfully"}
