from datetime import datetime
from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from routes.auth import get_current_user_from_cookies
from settings import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)

@router.get("/")
async def home(request: Request, error: str | None = None, db: AsyncSession = Depends(get_db)):
    # Отримуємо поточного користувача з cookies
    current_user = await get_current_user_from_cookies(request, db)
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "error": error,
            "current_user": current_user,
            "is_authenticated": current_user is not None,
            "now": datetime.now(),
            "popular_products": []  # Тимчасово пустий список
        }
    )


@router.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str, db: AsyncSession = Depends(get_db)):
    protected_paths = ["api/", "auth/", "account/", "admin/"]
    for path in protected_paths:
        if full_path.startswith(path):
            return None
    
    # Отримуємо поточного користувача для шаблону помилки
    current_user = await get_current_user_from_cookies(request, db)
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "current_user": current_user,
            "is_authenticated": current_user is not None,
            "error_code": 404,
            "error_message": f"Сторінку '{full_path}' не знайдено",
            "now": datetime.now()
        },
        status_code=404
    )


@router.get("/repairs", response_class=HTMLResponse)
async def repairs_page(request: Request):
    return templates.TemplateResponse(
        "repairs/catalog.html",
        {"request": request}
    )