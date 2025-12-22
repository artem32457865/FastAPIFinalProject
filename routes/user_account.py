from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import RepairRequest, User, Notification
from routes.auth import get_current_user, require_admin
from settings import get_db
from datetime import datetime
from tools.file_upload import generate_file_url, save_file


router = APIRouter()
templates = Jinja2Templates(directory="templates")


"""
Функционал пользователя:
a) Кабинет пользователя (/account/dashboard)
b) Создание заявок (/account/repair/add)
c) Просмотр всех заявок (/account/repairs)
d) Просмотр конкретной заявки (/account/repair/{repair_id})
e) Редактирование заявок (/account/repair/{repair_id}/edit)
f) Удаление заявок (/account/repair/{repair_id}/delete)
"""


# ==================== КАБИНЕТ ПОЛЬЗОВАТЕЛЯ ====================
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница кабинета пользователя (HTML)"""
    # Получаем текущего пользователя
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получить непрочитанные уведомления
    stmt = select(Notification)\
        .where(
            (Notification.user_id == user_data["id"]) &
            (Notification.is_read == False)
        )\
        .order_by(Notification.created_at.desc())\
        .limit(5)
    
    result = await db.execute(stmt)
    unread_notifications = result.scalars().all()
    
    # Получить статистику
    repairs_stmt = select(RepairRequest).where(RepairRequest.user_id == user_data["id"])
    repairs_result = await db.execute(repairs_stmt)
    user_repairs = repairs_result.scalars().all()
    
    return templates.TemplateResponse(
        "account/dashboard.html",
        {
            "request": request,
            "user": user_data,
            "unread_notifications": unread_notifications,
            "repairs_count": len(user_repairs),
            "now": datetime.now()
        }
    )


# ==================== УВЕДОМЛЕНИЯ ====================
@router.get("/notifications", response_class=HTMLResponse)
async def user_notifications(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница уведомлений пользователя"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получить все уведомления
    stmt = select(Notification)\
        .where(Notification.user_id == user_data["id"])\
        .order_by(Notification.created_at.desc())
    
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    # Отметить все как прочитанные
    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
    
    await db.commit()
    
    return templates.TemplateResponse(
        "account/notifications.html",
        {
            "request": request,
            "user": user_data,
            "notifications": notifications,
            "now": datetime.now()
        }
    )


@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Пометить уведомление как прочитанное"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    # Найти уведомление
    stmt = select(Notification).where(
        (Notification.id == notification_id) &
        (Notification.user_id == user_data["id"])
    )
    
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    
    # Отметить как прочитанное
    notification.is_read = True
    await db.commit()
    
    return {"status": "success", "message": "Уведомление отмечено как прочитанное"}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Пометить все уведомления как прочитанные"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    # Найти все непрочитанные уведомления
    stmt = select(Notification).where(
        (Notification.user_id == user_data["id"]) &
        (Notification.is_read == False)
    )
    
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    # Отметить все как прочитанные
    for notification in notifications:
        notification.is_read = True
    
    await db.commit()
    
    return {"status": "success", "message": f"Все уведомления ({len(notifications)}) отмечены как прочитанные"}


# ==================== API ДЛЯ JSON ====================
@router.get("/user/me")
async def user_me_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """API endpoint для получения данных пользователя (JSON)"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    return user_data


# ==================== ЗАЯВКИ НА РЕМОНТ ====================
@router.get("/repairs", response_class=HTMLResponse)
async def user_repairs_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница с заявками пользователя"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получаем заявки пользователя
    stmt = select(RepairRequest).where(RepairRequest.user_id == int(user_data["id"]))
    result = await db.execute(stmt)
    repairs = result.scalars().all()
    
    return templates.TemplateResponse(
        "account/repairs.html",
        {
            "request": request,
            "user": user_data,
            "repairs": repairs,
            "now": datetime.now()
        }
    )


@router.get("/repair/add", response_class=HTMLResponse)
async def add_repair_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница создания заявки"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    return templates.TemplateResponse(
        "account/add_repair.html",
        {
            "request": request,
            "user": user_data,
            "now": datetime.now()
        }
    )


@router.post("/repair/add")
async def create_repair_request(
    request: Request,
    bgt: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    description: str = Form(...),
    image: UploadFile | None = File(None),
    required_time: datetime = Form(None)
):
    """Создание новой заявки"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    user_id = user_data["id"]
    image_url = None
    
    if image:
        image_url = await generate_file_url(image.filename)
        bgt.add_task(save_file, image, image_url)

    new_req = RepairRequest(
        user_id=int(user_id),
        description=description,
        photo_url=image_url,
        required_time=required_time
    )

    db.add(new_req)
    await db.commit()
    await db.refresh(new_req)
    
    # Перенаправляем на страницу заявок
    return RedirectResponse(url="/account/repairs", status_code=303)


@router.get("/repair/{repair_id}")
async def get_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Просмотр конкретной заявки"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    user_id = user_data["id"]
    
    stmt = select(RepairRequest).where(
        (RepairRequest.id == repair_id) & 
        (RepairRequest.user_id == int(user_id))
    )
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        raise HTTPException(status_code=404, detail="Заявка не знайдена")
    
    return repair


@router.put("/repair/{repair_id}")
async def update_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Обновление заявки"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    return {"message": f"Update repair request {repair_id} endpoint (TODO)"}


@router.delete("/repair/{repair_id}")
async def delete_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Удаление заявки"""
    from routes.auth import get_current_user_from_cookies
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    
    return {"message": f"Delete repair request {repair_id} endpoint (TODO)"}