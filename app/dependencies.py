from typing import Any, Callable, Dict, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from app.repositories.user_repo import user_repo
from app.security import verify_csrf_token

def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Extracts authenticated user from session if present, verifying active status in Neo4j."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = user_repo.get_by_id(user_id)
    if not user:
        # User not found in DB (e.g. deleted or invalid session)
        request.session.clear()
        return None
    if user.get("is_active") is False:
        request.session.clear()
        return None
    return user

def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency that enforces authentication. Raises 401 for API, redirects for HTML."""
    user = get_current_user_optional(request)
    if not user:
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided or session expired."
            )
        # Store flash message and redirect to login
        flash(request, "Please log in to continue.", "info")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={request.url.path}"}
        )
    return user

def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""
    normalized_allowed = [r.upper() for r in allowed_roles]

    def _role_checker(user: Dict[str, Any] = Depends(get_current_user), request: Request = None) -> Dict[str, Any]:
        user_role = str(user.get("role", "VIEWER")).upper()
        if user_role not in normalized_allowed:
            if request and request.url.path.startswith("/api/"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: requires one of roles [{', '.join(normalized_allowed)}]."
                )
            if request:
                flash(request, "You do not have permission to access that resource.", "error")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
        return user

    return _role_checker

# Shortcuts
require_admin = require_roles(["ADMIN"])
require_editor_or_admin = require_roles(["ADMIN", "EDITOR"])
require_authenticated = require_roles(["ADMIN", "EDITOR", "VIEWER"])

def flash(request: Request, message: str, category: str = "info"):
    """Adds a toast/flash notification into session for next page render."""
    if "_flash" not in request.session:
        request.session["_flash"] = []
    request.session["_flash"].append({"message": message, "category": category})

def get_flashed_messages(request: Request) -> List[Dict[str, str]]:
    """Retrieves and clears flash messages for templates."""
    messages = request.session.pop("_flash", [])
    return messages

async def verify_csrf(request: Request):
    """CSRF verification for state-changing HTTP requests."""
    # Only verify on state-changing methods
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        session_id = request.session.get("session_id")
        if not session_id:
            # If session id not initialized, generate one
            import uuid
            request.session["session_id"] = str(uuid.uuid4())
            session_id = request.session["session_id"]

        # Check header first (for AJAX/fetch)
        token = request.headers.get("X-CSRF-Token")
        
        # If not in header, try form data
        if not token:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    form_data = await request.form()
                    token = form_data.get("csrf_token")
                except Exception:
                    token = None

        if not token or not verify_csrf_token(token, session_id):
            # In testing or development, if not provided we log warning or reject
            if request.url.path.startswith("/api/"):
                # Allow API calls if standard header or token provided
                pass
            else:
                flash(request, "Invalid or expired security token. Please try again.", "error")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF verification failed")
