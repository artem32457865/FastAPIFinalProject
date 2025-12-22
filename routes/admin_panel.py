from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
from typing import Optional

from routes.auth import require_admin
from settings import get_db
from models.models import User, RepairRequest, RequestStatus, AdminMessage, Order, OrderStatus, OrderItem, Product, ProductCategory

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Адміністративна панель"""
    current_user = await require_admin(request, db)
    
    # Статистика користувачів
    users_count = await db.execute(select(User))
    users_count = len(users_count.scalars().all())
    
    # Статистика заявок
    repairs_count = await db.execute(select(RepairRequest))
    repairs_count = len(repairs_count.scalars().all())
    
    new_repairs_count = await db.execute(select(RepairRequest).where(RepairRequest.status == RequestStatus.NEW))
    new_repairs_count = len(new_repairs_count.scalars().all())
    
    # Статистика замовлень
    orders_count = await db.execute(select(Order))
    orders_count = len(orders_count.scalars().all())
    
    new_orders_count = await db.execute(select(Order).where(Order.status == OrderStatus.NEW))
    new_orders_count = len(new_orders_count.scalars().all())
    
    # Загальний дохід
    total_revenue_result = await db.execute(select(func.sum(Order.total_amount)))
    total_revenue = total_revenue_result.scalar() or 0
    
    # Замовлення за сьогодні
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
    
    today_orders_stmt = select(func.count(Order.id)).where(
        Order.created_at.between(today_start, today_end)
    )
    today_orders_result = await db.execute(today_orders_stmt)
    today_orders = today_orders_result.scalar() or 0
    
    today_revenue_stmt = select(func.sum(Order.total_amount)).where(
        Order.created_at.between(today_start, today_end)
    )
    today_revenue_result = await db.execute(today_revenue_stmt)
    today_revenue = today_revenue_result.scalar() or 0
    
    # Останні 5 замовлень
    latest_orders_stmt = select(Order)\
        .options(selectinload(Order.user))\
        .order_by(Order.created_at.desc())\
        .limit(5)
    latest_orders_result = await db.execute(latest_orders_stmt)
    latest_orders = latest_orders_result.scalars().all()
    
    # Останні 5 заявок
    latest_repairs_stmt = select(RepairRequest)\
        .options(selectinload(RepairRequest.user))\
        .order_by(RepairRequest.created_at.desc())\
        .limit(5)
    latest_repairs_result = await db.execute(latest_repairs_stmt)
    latest_repairs = latest_repairs_result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "users_count": users_count,
            "repairs_count": repairs_count,
            "new_repairs_count": new_repairs_count,
            "orders_count": orders_count,
            "new_orders_count": new_orders_count,
            "total_revenue": total_revenue,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "latest_orders": latest_orders,
            "latest_repairs": latest_repairs
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
    
    # Базовый запрос
    if new:
        stmt = select(RepairRequest).where(RepairRequest.status == RequestStatus.NEW)
    else:
        stmt = select(RepairRequest)
    
    stmt = stmt.options(selectinload(RepairRequest.user))
    stmt = stmt.order_by(RepairRequest.created_at.desc())
    
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
        .options(
            selectinload(RepairRequest.user), 
            selectinload(RepairRequest.admin),
            selectinload(RepairRequest.messages).selectinload(AdminMessage.admin)
        )
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
        .options(selectinload(RepairRequest.user))\
        .order_by(RepairRequest.created_at.desc())
    
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
    
    # Простой запрос без поиска
    stmt = select(User).order_by(User.id.desc())
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
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд всіх замовлень"""
    current_user = await require_admin(request, db)
    
    # Базовый запрос
    stmt = select(Order)\
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.product)
        )
    
    # Фильтр по статусу
    if status and status != "all":
        try:
            order_status = OrderStatus(status)
            stmt = stmt.where(Order.status == order_status)
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
            "selected_status": status
        }
    )


@router.get("/order/{order_id}", response_class=HTMLResponse)
async def admin_order_detail(
    request: Request, 
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Перегляд деталей замовлення"""
    current_user = await require_admin(request, db)
    
    # Отримати замовлення
    stmt = select(Order)\
        .where(Order.id == order_id)\
        .options(
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
            "statuses": list(OrderStatus)
        }
    )


@router.post("/order/{order_id}/update-status")
async def update_order_status(
    request: Request,
    order_id: int,
    status: OrderStatus = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Оновити статус замовлення"""
    current_user = await require_admin(request, db)
    
    # Отримати замовлення
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")
    
    # Оновити статус
    order.status = status
    
    await db.commit()
    
    return RedirectResponse(url=f"/admin/order/{order_id}", status_code=303)


@router.get("/products", response_class=HTMLResponse)
async def admin_products_list(
    request: Request,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Управління товарами"""
    current_user = await require_admin(request, db)
    
    # Базовый запрос
    stmt = select(Product)
    
    # Фильтр по категории
    if category and category != "all":
        try:
            category_enum = ProductCategory(category)
            stmt = stmt.where(Product.category == category_enum)
        except ValueError:
            pass
    
    stmt = stmt.order_by(Product.created_at.desc())
    
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "current_user": current_user,
            "products": products,
            "categories": list(ProductCategory),
            "selected_category": category
        }
    )


@router.get("/product/create", response_class=HTMLResponse)
async def admin_create_product_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Сторінка створення товару"""
    current_user = await require_admin(request, db)
    
    return templates.TemplateResponse(
        "admin/product_create.html",
        {
            "request": request,
            "current_user": current_user,
            "categories": list(ProductCategory)
        }
    )


@router.post("/product/create")
async def admin_create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    stock_quantity: int = Form(...),
    image_url: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Створити новий товар"""
    current_user = await require_admin(request, db)
    
    try:
        product = Product(
            name=name,
            description=description,
            price=price,
            category=ProductCategory(category),
            stock_quantity=stock_quantity,
            image_url=image_url
        )
        
        db.add(product)
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/products?message=Товар+{name}+створено+успішно",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Помилка створення товару: {str(e)}")


@router.get("/product/{product_id}/edit", response_class=HTMLResponse)
async def admin_edit_product_page(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Сторінка редагування товару"""
    current_user = await require_admin(request, db)
    
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    
    return templates.TemplateResponse(
        "admin/product_edit.html",
        {
            "request": request,
            "current_user": current_user,
            "product": product,
            "categories": list(ProductCategory)
        }
    )


@router.post("/product/{product_id}/edit")
async def admin_update_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    stock_quantity: int = Form(...),
    image_url: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Оновити товар"""
    current_user = await require_admin(request, db)
    
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    
    try:
        product.name = name
        product.description = description
        product.price = price
        product.category = ProductCategory(category)
        product.stock_quantity = stock_quantity
        if image_url:
            product.image_url = image_url
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/admin/products?message=Товар+{name}+оновлено+успішно",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Помилка оновлення товару: {str(e)}")


@router.post("/product/{product_id}/delete")
async def admin_delete_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Видалити товар"""
    current_user = await require_admin(request, db)
    
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    
    # Проверяем, нет ли товара в заказах
    order_items_count = await db.execute(
        select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id)
    )
    
    if order_items_count.scalar() > 0:
        raise HTTPException(
            status_code=400, 
            detail="Не можна видалити товар, який є в замовленнях."
        )
    
    try:
        await db.delete(product)
        await db.commit()
        
        return RedirectResponse(
            url="/admin/products?message=Товар+видалено+успішно",
            status_code=303
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Помилка видалення товару: {str(e)}")


@router.get("/statistics", response_class=HTMLResponse)
async def admin_statistics(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Статистика"""
    current_user = await require_admin(request, db)
    
    # Общая статистика по заказам
    total_orders = await db.execute(select(func.count(Order.id)))
    total_orders = total_orders.scalar() or 0
    
    total_revenue = await db.execute(select(func.sum(Order.total_amount)))
    total_revenue = total_revenue.scalar() or 0
    
    # Статистика по статусам заказов
    orders_by_status = await db.execute(
        select(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status)
    )
    orders_by_status = orders_by_status.all()
    
    # Статистика по категориям товаров
    products_by_category = await db.execute(
        select(
            Product.category,
            func.count(Product.id).label('count'),
            func.sum(Product.stock_quantity).label('stock')
        ).group_by(Product.category)
    )
    products_by_category = products_by_category.all()
    
    # Топ товаров по продажам
    top_products = await db.execute(
        select(
            Product.name,
            func.sum(OrderItem.quantity).label('sold_quantity'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.quantity * OrderItem.price).desc())
        .limit(5)
    )
    top_products = top_products.all()
    
    # Топ клиентов
    top_customers = await db.execute(
        select(
            User.username,
            func.count(Order.id).label('orders_count'),
            func.sum(Order.total_amount).label('total_spent')
        )
        .join(Order, Order.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(5)
    )
    top_customers = top_customers.all()
    
    return templates.TemplateResponse(
        "admin/statistics.html",
        {
            "request": request,
            "current_user": current_user,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "orders_by_status": orders_by_status,
            "products_by_category": products_by_category,
            "top_products": top_products,
            "top_customers": top_customers
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Налаштування"""
    current_user = await require_admin(request, db)
    
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "current_user": current_user
        }
    )