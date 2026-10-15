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
from app.repositories.allergen_repo import allergen_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import generate_csrf_token, verify_csrf_token
from app.schemas import AllergenCreate, AllergenUpdate, AllergenResponse

router = APIRouter(tags=["Allergens"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# --- HTML Endpoints ---

@router.get("/allergens", response_class=HTMLResponse)
async def list_allergens_view(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    limit = 10
    skip = max(0, (page - 1) * limit)

    allergens = allergen_repo.list_allergens(skip=skip, limit=limit, search=search, category=category)
    total_count = allergen_repo.count_allergens(search=search, category=category)
    total_pages = max(1, (total_count + limit - 1) // limit)
    categories = allergen_repo.get_distinct_categories()
    sid = get_session_id(request)

    return templates.TemplateResponse("allergens/list.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "allergens",
        "allergens": allergens,
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "search": search,
        "selected_category": category,
        "categories": categories,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/allergens/new", response_class=HTMLResponse)
async def new_allergen_view(
    request: Request,
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    return templates.TemplateResponse("allergens/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "allergens",
        "is_edit": False,
        "allergen": None,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/allergens/new")
async def create_allergen_view(
    request: Request,
    name: str = Form(...),
    allergen_category: str = Form("Major"),
    description: str = Form(""),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/allergens/new", status_code=303)

    # Check duplicate name
    existing = allergen_repo.get_by_name(name.strip())
    if existing:
        flash(request, f"An allergen named '{name}' already exists in the knowledge base.", "error")
        return RedirectResponse(url="/allergens/new", status_code=303)

    data = {
        "name": name,
        "allergen_category": allergen_category,
        "description": description
    }
    created = allergen_repo.create(data)

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Allergen",
        entity_id=created["id"],
        description=f"Created allergen '{created['name']}' ({allergen_category})."
    )

    flash(request, f"Allergen '{created['name']}' created successfully!", "success")
    return RedirectResponse(url=f"/allergens/{created['id']}", status_code=303)

@router.get("/allergens/{allergen_id}", response_class=HTMLResponse)
async def view_allergen_detail(
    request: Request,
    allergen_id: str,
    current_user = Depends(get_current_user)
):
    allergen = allergen_repo.get_by_id(allergen_id)
    if not allergen:
        raise HTTPException(status_code=404, detail="Allergen not found")

    connections = allergen_repo.get_connected_dishes_and_restaurants(allergen_id)

    return templates.TemplateResponse("allergens/detail.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "allergens",
        "allergen": allergen,
        "connections": connections,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/allergens/{allergen_id}/edit", response_class=HTMLResponse)
async def edit_allergen_view(
    request: Request,
    allergen_id: str,
    current_user = Depends(require_editor_or_admin)
):
    allergen = allergen_repo.get_by_id(allergen_id)
    if not allergen:
        raise HTTPException(status_code=404, detail="Allergen not found")

    sid = get_session_id(request)
    return templates.TemplateResponse("allergens/form.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "allergens",
        "is_edit": True,
        "allergen": allergen,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/allergens/{allergen_id}/edit")
async def update_allergen_view(
    request: Request,
    allergen_id: str,
    name: str = Form(...),
    allergen_category: str = Form("Major"),
    description: str = Form(""),
    csrf_token: str = Form(...),
    current_user = Depends(require_editor_or_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url=f"/allergens/{allergen_id}/edit", status_code=303)

    existing = allergen_repo.get_by_name(name.strip())
    if existing and existing.get("id") != allergen_id:
        flash(request, f"An allergen named '{name.strip()}' already exists.", "error")
        return RedirectResponse(url=f"/allergens/{allergen_id}/edit", status_code=303)

    data = {
        "name": name,
        "allergen_category": allergen_category,
        "description": description
    }
    updated = allergen_repo.update(allergen_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Allergen not found")

    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Allergen",
        entity_id=allergen_id,
        description=f"Updated allergen definition '{updated['name']}'."
    )

    flash(request, f"Allergen '{updated['name']}' updated successfully!", "success")
    return RedirectResponse(url=f"/allergens/{allergen_id}", status_code=303)

@router.post("/allergens/{allergen_id}/delete")
async def delete_allergen_view(
    request: Request,
    allergen_id: str,
    csrf_token: str = Form(...),
    current_user = Depends(require_admin)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired.", "error")
        return RedirectResponse(url="/allergens", status_code=303)

    alg = allergen_repo.get_by_id(allergen_id)
    name = alg["name"] if alg else allergen_id
    success = allergen_repo.delete(allergen_id)

    if success:
        activity_log_repo.log(
            actor_id=current_user["id"],
            actor_name=current_user["full_name"],
            action="DELETE",
            entity_type="Allergen",
            entity_id=allergen_id,
            description=f"Deleted allergen '{name}'."
        )
        flash(request, f"Allergen '{name}' deleted.", "success")
    else:
        flash(request, "Could not delete allergen.", "error")

    return RedirectResponse(url="/allergens", status_code=303)

# --- REST APIs ---

@router.get("/api/allergens")
async def api_list_allergens(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    return allergen_repo.list_allergens(skip=skip, limit=limit, search=search, category=category)

@router.post("/api/allergens", status_code=201)
async def api_create_allergen(
    payload: AllergenCreate,
    current_user = Depends(require_editor_or_admin)
):
    if allergen_repo.get_by_name(payload.name):
        raise HTTPException(status_code=400, detail="Allergen name already exists")
    created = allergen_repo.create(payload.model_dump())
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="CREATE",
        entity_type="Allergen",
        entity_id=created["id"],
        description=f"API: Created allergen '{created['name']}'."
    )
    return created

@router.get("/api/allergens/{allergen_id}")
async def api_get_allergen(
    allergen_id: str,
    current_user = Depends(get_current_user)
):
    res = allergen_repo.get_by_id(allergen_id)
    if not res:
        raise HTTPException(status_code=404, detail="Allergen not found")
    return res

@router.put("/api/allergens/{allergen_id}")
async def api_update_allergen(
    allergen_id: str,
    payload: AllergenUpdate,
    current_user = Depends(require_editor_or_admin)
):
    new_name = payload.name.strip() if payload.name else None
    if new_name:
        existing = allergen_repo.get_by_name(new_name)
        if existing and existing.get("id") != allergen_id:
            raise HTTPException(status_code=400, detail="Allergen name already exists")
    updated = allergen_repo.update(allergen_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Allergen not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="UPDATE",
        entity_type="Allergen",
        entity_id=allergen_id,
        description=f"API: Updated allergen '{updated['name']}'."
    )
    return updated

@router.delete("/api/allergens/{allergen_id}")
async def api_delete_allergen(
    allergen_id: str,
    current_user = Depends(require_admin)
):
    success = allergen_repo.delete(allergen_id)
    if not success:
        raise HTTPException(status_code=404, detail="Allergen not found")
    activity_log_repo.log(
        actor_id=current_user["id"],
        actor_name=current_user["full_name"],
        action="DELETE",
        entity_type="Allergen",
        entity_id=allergen_id,
        description=f"API: Deleted allergen '{allergen_id}'."
    )
    return {"message": "Allergen deleted successfully"}
