from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, require_admin, get_flashed_messages
from app.repositories.activity_log_repo import activity_log_repo
from app.repositories.reports_repo import reports_repo

router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

ENTITY_TYPES = ["Restaurant", "Dish", "Ingredient", "Allergen", "User"]
ACTIONS = [
    "CREATE_RESTAURANT", "UPDATE_RESTAURANT", "DELETE_RESTAURANT",
    "CREATE_DISH", "UPDATE_DISH", "DELETE_DISH",
    "CREATE_INGREDIENT", "UPDATE_INGREDIENT", "DELETE_INGREDIENT",
    "CREATE_ALLERGEN", "UPDATE_ALLERGEN", "DELETE_ALLERGEN",
    "UPDATE_PROFILE", "CHANGE_PASSWORD",
    "UPDATE_USER_ROLE", "TOGGLE_USER_STATUS",
    "LOGIN", "LOGOUT", "REGISTER",
]


@router.get("", response_class=HTMLResponse)
async def activity_logs_page(
    request: Request,
    current_user=Depends(require_admin),
    page: int = 1,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
):
    limit = 25
    skip = max(0, (page - 1) * limit)

    logs = activity_log_repo.list_logs(
        skip=skip, limit=limit,
        entity_type=entity_type,
        action=action,
    )
    total_count = activity_log_repo.count_logs(entity_type=entity_type, action=action)
    total_pages = max(1, (total_count + limit - 1) // limit)

    return templates.TemplateResponse(
        "activity_logs/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "activity_logs",
            "logs": logs,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "entity_types": ENTITY_TYPES,
            "actions": ACTIONS,
            "selected_entity_type": entity_type,
            "selected_action": action,
            "flashed_messages": get_flashed_messages(request),
        },
    )


@router.get("/export/csv")
async def export_logs_csv(
    current_user=Depends(require_admin),
    report_type: str = "allergen_distribution",
):
    """Export a supported report as CSV."""
    valid_types = {"allergen_distribution", "unverified_ingredients", "incomplete_dishes", "data_quality"}
    if report_type not in valid_types:
        report_type = "allergen_distribution"

    csv_content = reports_repo.export_csv(report_type)
    filename = f"allergraph_{report_type}_report.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
