from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "index.html", {"request": request, "error": error}
    )



@router.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):

    if full_path.startswith("api/") or full_path.startswith("auth/") or full_path.startswith("account/"):
        return
    

    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 404,
            "error_message": f"Сторінку '{full_path}' не знайдено"
        },
        status_code=404
    )