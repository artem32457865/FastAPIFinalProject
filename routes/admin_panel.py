from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from routes.auth import require_admin
from settings import get_db
from models.models import User, RepairRequest, RequestStatus, AdminMessage, Order, OrderStatus, OrderItem, Product
from datetime import datetime



router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


"""a) Перегляд всіх заявок, та тільки тих що мають статус «Нова» (фільтр) (/admin/repairs?new=1)
b) Прийняття заявки (/admin/repair/{repair_id}/self/get)
c) Перегляд всіх заявок що взяв на опрацювання (/admin/self/repairs)
d) Зміна статуса заявки (закриття, взяття на опрацювання і тд)
(/admin/repair/{repair_id}/change/status)
e) Створення повідомлень (коментарів)(/admin/repair/{repair_id}/change/comment)"""

@router.get("/")
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Адміністративна панель"""
    current_user = await require_admin(request, db)
    
    # Отримати загальну статистику
    users_count = await db.execute(select(User))
    users_count = len(users_count.scalars().all())
    
    repairs_count = await db.execute(select(RepairRequest))
    repairs_count = len(repairs_count.scalars().all())
    
    new_repairs_count = await db.execute(select(RepairRequest).where(RepairRequest.status == RequestStatus.NEW))
    new_repairs_count = len(new_repairs_count.scalars().all())
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "users_count": users_count,
            "repairs_count": repairs_count,
            "new_repairs_count": new_repairs_count
        }
    )


@router.get("/repairs", response_class=HTMLResponse)
async def admin_repairs_list(
    request: Request, 
    new: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд всіх заявок або тільки нових"""
    current_user = await require_admin(request, db)
    
    # Отримати всі заявки
    if new:
        stmt = select(RepairRequest).where(RepairRequest.status == RequestStatus.NEW)\
            .options(selectinload(RepairRequest.user))
    else:
        stmt = select(RepairRequest).options(selectinload(RepairRequest.user))
    
    result = await db.execute(stmt)
    repairs = result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/repairs.html",
        {
            "request": request,
            "current_user": current_user,
            "repairs": repairs,
            "show_new_only": new
        }
    )


@router.get("/repair/{repair_id}", response_class=HTMLResponse)
async def admin_repair_detail(
    request: Request, 
    repair_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд деталей заявки"""
    current_user = await require_admin(request, db)
    
    # Отримати заявку
    stmt = select(RepairRequest)\
        .where(RepairRequest.id == repair_id)\
        .options(selectinload(RepairRequest.user), selectinload(RepairRequest.messages))
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    
    return templates.TemplateResponse(
        "admin/repair_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "repair": repair
        }
    )


@router.post("/repair/{repair_id}/assign")
async def assign_repair_to_admin(
    request: Request, 
    repair_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Прийняти заявку адміном"""
    current_user = await require_admin(request, db)
    
    # Отримати заявку
    stmt = select(RepairRequest).where(RepairRequest.id == repair_id)
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    
    # Оновити заявку
    repair.admin_id = current_user["id"]
    repair.status = RequestStatus.IN_PROGRESS
    
    await db.commit()
    
    return RedirectResponse(url=f"/admin/repair/{repair_id}", status_code=303)


@router.get("/self/repairs", response_class=HTMLResponse)
async def admin_assigned_repairs(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд заявок, призначених поточному адміну"""
    current_user = await require_admin(request, db)
    
    # Отримати заявки, призначені поточному адміну
    stmt = select(RepairRequest)\
        .where(RepairRequest.admin_id == current_user["id"])\
        .options(selectinload(RepairRequest.user))
    result = await db.execute(stmt)
    repairs = result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/self_repairs.html",
        {
            "request": request,
            "current_user": current_user,
            "repairs": repairs
        }
    )


@router.post("/repair/{repair_id}/change/status")
async def change_repair_status(
    request: Request,
    repair_id: int,
    status: RequestStatus = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Змінити статус заявки"""
    current_user = await require_admin(request, db)
    
    # Отримати заявку
    stmt = select(RepairRequest).where(RepairRequest.id == repair_id)
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    
    # Оновити статус
    repair.status = status
    
    await db.commit()
    
    return RedirectResponse(url=f"/admin/repair/{repair_id}", status_code=303)


@router.post("/repair/{repair_id}/change/comment")
async def add_comment_to_repair(
    request: Request,
    repair_id: int,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Додати коментар до заявки"""
    current_user = await require_admin(request, db)
    
    # Отримати заявку
    stmt = select(RepairRequest).where(RepairRequest.id == repair_id)
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    
    # Створити повідомлення
    comment = AdminMessage(
        message=message,
        request_id=repair_id,
        admin_id=current_user["id"]
    )
    
    db.add(comment)
    await db.commit()
    
    return RedirectResponse(url=f"/admin/repair/{repair_id}", status_code=303)


@router.get("/users", response_class=HTMLResponse)
async def admin_users_list(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд всіх користувачів"""
    current_user = await require_admin(request, db)
    
    # Отримати всіх користувачів
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users
        }
    )


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_list(
        request: Request,
        status: str | None = None,
        db: AsyncSession = Depends(get_db)
):
    """Перегляд всіх замовлень"""
    current_user = await require_admin(request, db)

    # Отримуємо замовлення
    stmt = select(Order).options(
        selectinload(Order.user)
    )

    if status:
        try:
            status_enum = OrderStatus(status)
            stmt = stmt.where(Order.status == status_enum)
        except ValueError:
            pass

    stmt = stmt.order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    orders = result.scalars().all()

    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "current_user": current_user,
            "orders": orders,
            "statuses": list(OrderStatus),
            "selected_status": status,
            "now": datetime.now()
        }
    )


@router.get("/order/{order_id}", response_class=HTMLResponse)
async def admin_order_detail(
        request: Request,
        order_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Деталі замовлення для адміна"""
    current_user = await require_admin(request, db)

    # Отримуємо замовлення
    stmt = select(Order).where(Order.id == order_id).options(
        selectinload(Order.user),
        selectinload(Order.items).selectinload(OrderItem.product)
    )

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")

    return templates.TemplateResponse(
        "admin/order_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "order": order,
            "statuses": list(OrderStatus),
            "now": datetime.now()
        }
    )


@router.post("/order/{order_id}/update-status")
async def update_order_status(
        request: Request,
        order_id: int,
        status: OrderStatus = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """Оновлення статусу замовлення"""
    current_user = await require_admin(request, db)

    # Отримуємо замовлення
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")

    # Оновлюємо статус
    order.status = status
    await db.commit()

    return RedirectResponse(
        url=f"/admin/order/{order_id}",
        status_code=303
    )


@router.post("/order/{order_id}/add-note")
async def add_order_note(
        request: Request,
        order_id: int,
        note: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """Додати примітку до замовлення"""
    current_user = await require_admin(request, db)

    # Отримуємо замовлення
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")

    # Оновлюємо примітку
    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')
    if order.notes:
        order.notes += f"\n[{timestamp}] {note}"
    else:
        order.notes = f"[{timestamp}] {note}"

    await db.commit()

    return RedirectResponse(
        url=f"/admin/order/{order_id}",
        status_code=303
    )