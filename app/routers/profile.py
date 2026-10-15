from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, get_flashed_messages, flash
from app.repositories.user_repo import user_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import (
    generate_csrf_token, verify_csrf_token,
    verify_password, hash_password, validate_password_strength,
)

router = APIRouter(prefix="/profile", tags=["Profile"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _sid(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]


@router.get("", response_class=HTMLResponse)
async def profile_view(request: Request, current_user=Depends(get_current_user)):
    sid = _sid(request)
    logs = activity_log_repo.list_logs(user_id=current_user["id"], limit=10)
    return templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "profile",
            "logs": logs,
            "csrf_token": generate_csrf_token(sid),
            "flashed_messages": get_flashed_messages(request),
        },
    )


@router.post("/update-name", response_class=HTMLResponse)
async def update_name(
    request: Request,
    current_user=Depends(get_current_user),
    full_name: str = Form(...),
    csrf_token: str = Form(...),
):
    sid = _sid(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token invalid. Please try again.", "error")
        return RedirectResponse(url="/profile", status_code=303)

    name = full_name.strip()
    if len(name) < 2:
        flash(request, "Name must be at least 2 characters.", "error")
        return RedirectResponse(url="/profile", status_code=303)

    updated = user_repo.update_profile(current_user["id"], name)
    if updated:
        request.session["user_id"] = current_user["id"]   # keep session alive
        flash(request, "Profile updated successfully.", "success")
        activity_log_repo.log(
            user_id=current_user["id"],
            user_name=current_user.get("full_name", ""),
            action="UPDATE_PROFILE",
            entity_type="User",
            entity_id=current_user["id"],
            details=f"Full name changed to '{name}'",
        )
    else:
        flash(request, "Could not update profile.", "error")

    return RedirectResponse(url="/profile", status_code=303)


@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_user=Depends(get_current_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    sid = _sid(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token invalid.", "error")
        return RedirectResponse(url="/profile", status_code=303)

    # Verify current password
    user_full = user_repo.get_by_id(current_user["id"])
    if not user_full or not verify_password(current_password, user_full.get("password_hash", "")):
        flash(request, "Current password is incorrect.", "error")
        return RedirectResponse(url="/profile", status_code=303)

    if new_password != confirm_password:
        flash(request, "New passwords do not match.", "error")
        return RedirectResponse(url="/profile", status_code=303)

    strength_ok, strength_msg = validate_password_strength(new_password)
    if not strength_ok:
        flash(request, strength_msg, "error")
        return RedirectResponse(url="/profile", status_code=303)

    new_hash = hash_password(new_password)
    ok = user_repo.update_password(current_user["id"], new_hash)
    if ok:
        flash(request, "Password changed successfully.", "success")
        activity_log_repo.log(
            user_id=current_user["id"],
            user_name=current_user.get("full_name", ""),
            action="CHANGE_PASSWORD",
            entity_type="User",
            entity_id=current_user["id"],
            details="Password changed via profile settings.",
        )
    else:
        flash(request, "Password update failed.", "error")

    return RedirectResponse(url="/profile", status_code=303)
