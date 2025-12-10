from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from routes.auth import get_current_user

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)

@router.get("/")
async def home(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "index.html", {"request": request, "error": error}
    )


# @router.get("/account")
# async def account_dashboard(request: Request, current_user: dict = Depends(get_current_user)):
#     async with httpx.AsyncClient() as client:
#         response = await client.get(
#             f"http://localhost:8000/account/user/me",
#             headers={"Authorization": f"Bearer {request.cookies.get('access_token')}"}
#         )
#         user_data = response.json()

#     return templates.TemplateResponse(
#         "account/dashboard.html", {"request": request, "user_data": user_data}
#     )


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