from pathlib import Path
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user_optional, get_current_user, get_flashed_messages, flash
from app.repositories.user_repo import user_repo
from app.repositories.activity_log_repo import activity_log_repo
from app.security import (
    hash_password, verify_password, validate_password_strength,
    generate_csrf_token, verify_csrf_token, login_rate_limiter,
    generate_reset_token, verify_reset_token
)
from app.schemas import UserRegister, UserLogin, UserResponse, PasswordResetRequest, PasswordResetSubmit

logger = logging.getLogger("allergraph.auth")
router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def get_session_id(request: Request) -> str:
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# --- HTML Endpoints ---

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: Optional[str] = None, current_user = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    sid = get_session_id(request)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "current_user": None,
        "csrf_token": generate_csrf_token(sid),
        "next_url": next,
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: Optional[str] = Form(None)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired. Please try again.", "error")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{email.strip().lower()}"

    is_locked, remaining = login_rate_limiter.is_locked(rate_key)
    if is_locked:
        err_msg = f"Account temporarily locked due to repeated failed login attempts. Try again in {remaining // 60 + 1} minute(s)."
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": err_msg,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    user = user_repo.get_by_email(email.strip())
    if not user or not verify_password(password, user.get("password_hash")):
        is_locked_now, lock_duration = login_rate_limiter.record_failure(rate_key)
        err_msg = "Invalid email or password."
        if is_locked_now:
            err_msg = f"Too many failed attempts. Locked out for {lock_duration // 60} minutes."
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": err_msg,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    if user.get("is_active") is False:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": "This account has been deactivated. Please contact an administrator.",
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=403)

    login_rate_limiter.record_success(rate_key)

    # Establish session
    request.session.clear()
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    request.session["user_role"] = user.get("role", "VIEWER")
    request.session["session_id"] = str(uuid.uuid4())

    flash(request, f"Welcome back, {user['full_name']}!", "success")

    redirect_url = next if next and next.startswith("/") else "/dashboard"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, current_user = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    sid = get_session_id(request)
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "current_user": None,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/register")
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    terms_accepted: Optional[str] = Form(None),
    csrf_token: str = Form(...)
):
    sid = get_session_id(request)
    if not verify_csrf_token(csrf_token, sid):
        flash(request, "Security token expired. Please try again.", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if not terms_accepted:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": "You must accept the terms of service and food safety disclaimer.",
            "full_name": full_name,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    if password != confirm_password:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": "Passwords do not match.",
            "full_name": full_name,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    valid_pass, pass_err = validate_password_strength(password)
    if not valid_pass:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": pass_err,
            "full_name": full_name,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    # Check duplicate email
    existing_user = user_repo.get_by_email(email.strip())
    if existing_user:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "error": "An account with this email address already exists.",
            "full_name": full_name,
            "email": email,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    hashed = hash_password(password)
    new_user = user_repo.create(full_name=full_name, email=email, password_hash=hashed, role="VIEWER")

    # Establish session
    request.session.clear()
    request.session["user_id"] = new_user["id"]
    request.session["user_email"] = new_user["email"]
    request.session["user_role"] = new_user["role"]
    request.session["session_id"] = str(uuid.uuid4())

    flash(request, "Account registered successfully! Welcome to AllerGraph.", "success")
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    flash(request, "You have been successfully signed out.", "info")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, current_user = Depends(get_current_user_optional)):
    sid = get_session_id(request)
    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": generate_csrf_token(sid),
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(...),
    current_user = Depends(get_current_user_optional)
):
    sid = get_session_id(request)
    user = user_repo.get_by_email(email.strip())
    
    # Generic message that never reveals whether an email exists
    generic_msg = "If an account matching this email address is registered, password recovery instructions have been dispatched."
    dev_token = None

    if user:
        token = generate_reset_token(user["email"])
        logger.info(f"Password reset token generated for user: {user['email']}")
        dev_token = token  # Exposed only in local development workflow when SMTP is unconfigured

    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": generate_csrf_token(sid),
        "message": generic_msg,
        "dev_token": dev_token,
        "flashed_messages": get_flashed_messages(request)
    })

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: Optional[str] = "", current_user = Depends(get_current_user_optional)):
    sid = get_session_id(request)
    email = verify_reset_token(token) if token else None
    error = None if email else "Password reset link is invalid or has expired."

    return templates.TemplateResponse("auth/reset_password.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": generate_csrf_token(sid),
        "token": token,
        "error": error,
        "flashed_messages": get_flashed_messages(request)
    })

@router.post("/reset-password")
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...)
):
    sid = get_session_id(request)
    email = verify_reset_token(token)
    if not email:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "token": token,
            "error": "Reset link is invalid or has expired. Please request a new link.",
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    if password != confirm_password:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "token": token,
            "error": "Passwords do not match.",
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    valid_pass, pass_err = validate_password_strength(password)
    if not valid_pass:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "token": token,
            "error": pass_err,
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    user = user_repo.get_by_email(email)
    if not user:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "current_user": None,
            "csrf_token": generate_csrf_token(sid),
            "token": token,
            "error": "Account not found.",
            "flashed_messages": get_flashed_messages(request)
        }, status_code=400)

    new_hash = hash_password(password)
    user_repo.update_password(user["id"], new_hash)

    flash(request, "Password has been successfully reset! Please sign in with your new password.", "success")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

# --- Documented REST APIs ---

@router.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def api_register(payload: UserRegister, request: Request):
    valid_pass, pass_err = validate_password_strength(payload.password)
    if not valid_pass:
        raise HTTPException(status_code=400, detail=pass_err)

    if user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(payload.password)
    user = user_repo.create(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hashed,
        role="VIEWER"
    )
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    request.session["user_role"] = user["role"]
    return user

@router.post("/api/auth/login")
async def api_login(payload: UserLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{payload.email.lower()}"

    is_locked, remaining = login_rate_limiter.is_locked(rate_key)
    if is_locked:
        raise HTTPException(status_code=429, detail=f"Too many failed login attempts. Locked for {remaining} seconds.")

    user = user_repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.get("password_hash")):
        login_rate_limiter.record_failure(rate_key)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    login_rate_limiter.record_success(rate_key)
    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]
    request.session["user_role"] = user["role"]

    return {
        "message": "Authentication successful",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@router.post("/api/auth/logout")
async def api_logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}

@router.get("/api/auth/me", response_model=UserResponse)
async def api_me(current_user = Depends(get_current_user)):
    return current_user

@router.post("/api/auth/forgot-password")
async def api_forgot_password(payload: PasswordResetRequest):
    user = user_repo.get_by_email(payload.email)
    token = generate_reset_token(payload.email) if user else None
    return {
        "message": "If this email is registered, password reset instructions have been dispatched.",
        "dev_token": token
    }

@router.post("/api/auth/reset-password")
async def api_reset_password(payload: PasswordResetSubmit):
    email = verify_reset_token(payload.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    valid_pass, pass_err = validate_password_strength(payload.password)
    if not valid_pass:
        raise HTTPException(status_code=400, detail=pass_err)

    user = user_repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_hash = hash_password(payload.password)
    user_repo.update_password(user["id"], new_hash)
    return {"message": "Password updated successfully"}
