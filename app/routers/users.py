from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, require_admin, get_flashed_messages, flash
from app.repositories.user_repo import user_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import generate_csrf_token, verify_csrf_token, hash_password

router = APIRouter(prefix="/users", tags=["Users"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _sid(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]


@router.get("", response_class=HTMLResponse)
async def list_users(
    request: Request,
    current_user=Depends(require_admin),
    page: int = 1,
    search: Optional[str] = None,
    role: Optional[str] = None,
):
    limit = 15
    skip = max(0, (page - 1) * limit)

    # Parse is_active filter
    is_active_filter: Optional[bool] = None
    active_param = request.query_params.get("active")
    if active_param == "true":
        is_active_filter = True
    elif active_param == "false":
        is_active_filter = False

    users = user_repo.list_users(skip=skip, limit=limit, search=search, role=role, is_active=is_active_filter)
    total_count = user_repo.count_users(search=search, role=role, is_active=is_active_filter)
    total_pages = max(1, (total_count + limit - 1) // limit)
    sid = _sid(request)

    return templates.TemplateResponse(
        "users/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "users",
            "users": users,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "search": search,
            "selected_role": role,
            "active_filter": active_param,
            "csrf_token": generate_csrf_token(sid),
            "flashed_messages": get_flashed_messages(request),
        },
    )


@router.post("/{user_id}/role", response_class=HTMLResponse)
async def update_user_role(
    request: Request,
    user_id: str,
    current_user=Depends(require_admin),
    role: str = Form(...),
    csrf_token: str = Form(...),
):
    sid = _sid(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Invalid CSRF token.", "error")
        return RedirectResponse(url="/users", status_code=303)

    valid_roles = {"ADMIN", "EDITOR", "VIEWER"}
    if role.upper() not in valid_roles:
        flash(request, "Invalid role specified.", "error")
        return RedirectResponse(url="/users", status_code=303)

    # Prevent demoting last admin
    if role.upper() != "ADMIN":
        target = user_repo.get_by_id(user_id)
        if target and target.get("role", "").upper() == "ADMIN":
            active_admins = user_repo.count_active_admins()
            if active_admins <= 1:
                flash(request, "Cannot demote the last active admin.", "error")
                return RedirectResponse(url="/users", status_code=303)

    updated = user_repo.update_role(user_id, role.upper())
    if updated:
        flash(request, f"User role updated to {role.upper()}.", "success")
        activity_log_repo.log(
            user_id=current_user["id"],
            user_name=current_user.get("full_name", ""),
            action="UPDATE_USER_ROLE",
            entity_type="User",
            entity_id=user_id,
            details=f"Role set to {role.upper()}",
        )
    else:
        flash(request, "Could not update user role.", "error")

    return RedirectResponse(url="/users", status_code=303)


@router.post("/{user_id}/toggle-status", response_class=HTMLResponse)
async def toggle_user_status(
    request: Request,
    user_id: str,
    current_user=Depends(require_admin),
    csrf_token: str = Form(...),
):
    sid = _sid(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Invalid CSRF token.", "error")
        return RedirectResponse(url="/users", status_code=303)

    # Prevent self-deactivation
    if user_id == current_user["id"]:
        flash(request, "You cannot deactivate your own account.", "error")
        return RedirectResponse(url="/users", status_code=303)

    target = user_repo.get_by_id(user_id)
    if not target:
        flash(request, "User not found.", "error")
        return RedirectResponse(url="/users", status_code=303)

    # Prevent disabling last admin
    currently_active = target.get("is_active", True)
    if currently_active and target.get("role", "").upper() == "ADMIN":
        active_admins = user_repo.count_active_admins()
        if active_admins <= 1:
            flash(request, "Cannot deactivate the last active admin.", "error")
            return RedirectResponse(url="/users", status_code=303)

    new_status = not currently_active
    updated = user_repo.update_status(user_id, new_status)
    if updated:
        status_label = "activated" if new_status else "deactivated"
        flash(request, f"User account {status_label}.", "success")
        activity_log_repo.log(
            user_id=current_user["id"],
            user_name=current_user.get("full_name", ""),
            action="TOGGLE_USER_STATUS",
            entity_type="User",
            entity_id=user_id,
            details=f"Account {status_label}",
        )
    else:
        flash(request, "Could not update user status.", "error")

    return RedirectResponse(url="/users", status_code=303)


# JSON API ---

@router.get("/api/users")
async def api_list_users(
    current_user=Depends(require_admin),
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
):
    users = user_repo.list_users(skip=skip, limit=limit, search=search, role=role)
    total = user_repo.count_users(search=search, role=role)
    safe_users = [{k: v for k, v in dict(u).items() if k != "password_hash"} for u in users]
    return {"users": safe_users, "total": total}
