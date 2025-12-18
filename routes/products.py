from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Query, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.models import Product, ProductCategory, Order, OrderItem, OrderStatus
from settings import get_db
from routes.auth import get_current_user_from_cookies

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Простая корзина в памяти (для демо)
cart_store = {}


@router.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    category: str = Query(None),
    min_price: str = Query(None),
    max_price: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Страница каталога товаров"""
    
    # Получаем текущего пользователя для шаблона
    current_user = await get_current_user_from_cookies(request, db)
    
    # Базовый запрос
    stmt = select(Product)
    
    # Применяем фильтры
    if category and category != "None":
        # Преобразуем строку в Enum значение
        try:
            category_enum = ProductCategory(category)
            stmt = stmt.where(Product.category == category_enum)
        except ValueError:
            # Если категория не найдена, игнорируем фильтр
            pass
    
    # Преобразуем цену из строки в float
    min_price_float = None
    max_price_float = None
    
    if min_price and min_price != "None":
        try:
            min_price_float = float(min_price)
            stmt = stmt.where(Product.price >= min_price_float)
        except ValueError:
            pass
    
    if max_price and max_price != "None":
        try:
            max_price_float = float(max_price)
            stmt = stmt.where(Product.price <= max_price_float)
        except ValueError:
            pass
    
    if search and search != "None":
        stmt = stmt.where(
            Product.name.ilike(f"%{search}%") | 
            Product.description.ilike(f"%{search}%")
        )
    
    # Выполняем запрос
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    return templates.TemplateResponse(
        "products/catalog.html",
        {
            "request": request,
            "current_user": current_user,
            "is_authenticated": current_user is not None,
            "products": products,
            "categories": list(ProductCategory),
            "selected_category": category,
            "search_query": search,
            "min_price": min_price,
            "max_price": max_price,
            "now": datetime.now()
        }
    )


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Страница деталей товара"""
    
    # Получаем текущего пользователя
    current_user = await get_current_user_from_cookies(request, db)
    
    # Находим товар
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": current_user,
                "error_code": 404,
                "error_message": "Товар не знайдено"
            },
            status_code=404
        )
    
    # Находим похожие товары
    similar_stmt = select(Product).where(
        Product.category == product.category,
        Product.id != product.id
    ).limit(4)
    
    similar_result = await db.execute(similar_stmt)
    similar_products = similar_result.scalars().all()
    
    return templates.TemplateResponse(
        "products/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "is_authenticated": current_user is not None,
            "product": product,
            "similar_products": similar_products,
            "now": datetime.now()
        }
    )


@router.post("/cart/add")
async def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(1),
    db: AsyncSession = Depends(get_db)
):
    """Добавить товар в корзину"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получаем товар из БД
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        return RedirectResponse(url="/products", status_code=303)
    
    # Проверяем наличие на складе
    if product.stock_quantity < quantity:
        return RedirectResponse(
            url=f"/product/{product_id}?error=Недостатня+кількість+на+складі",
            status_code=303
        )
    
    # Простая логика корзины (в памяти)
    user_id = str(user_data["id"])
    if user_id not in cart_store:
        cart_store[user_id] = []
    
    # Проверяем, есть ли уже такой товар в корзине
    found = False
    for item in cart_store[user_id]:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            found = True
            break
    
    # Если товара нет в корзине, добавляем
    if not found:
        cart_store[user_id].append({
            "product_id": product_id,
            "name": product.name,
            "price": float(product.price),
            "quantity": quantity,
            "image_url": product.image_url,
            "stock_quantity": product.stock_quantity
        })
    
    return RedirectResponse(
        url=f"/product/{product_id}?message=Товар+додано+до+кошика",
        status_code=303
    )


@router.get("/cart")
async def view_cart(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Просмотр корзины"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user_id = str(user_data["id"])
    cart_items = cart_store.get(user_id, [])
    
    # Рассчитываем общую сумму
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    
    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "current_user": user_data,
            "is_authenticated": user_data is not None,
            "cart_items": cart_items,
            "total": total,
            "now": datetime.now()
        }
    )


@router.post("/cart/remove")
async def remove_from_cart(
    request: Request,
    product_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Удалить товар из корзины"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user_id = str(user_data["id"])
    
    if user_id in cart_store:
        # Удаляем товар из корзины
        cart_store[user_id] = [
            item for item in cart_store[user_id] 
            if item["product_id"] != product_id
        ]
    
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/clear")
async def clear_cart(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Очистить корзину"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user_id = str(user_data["id"])
    
    if user_id in cart_store:
        cart_store[user_id] = []
    
    return RedirectResponse(url="/cart", status_code=303)


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница оформления заказа"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user_id = str(user_data["id"])
    cart_items = cart_store.get(user_id, [])
    
    if not cart_items:
        return RedirectResponse(url="/cart", status_code=303)
    
    # Проверяем наличие товаров на складе
    for item in cart_items:
        if item["stock_quantity"] < item["quantity"]:
            return RedirectResponse(
                url=f"/cart?error=Товар+{item['name']}+недоступний+в+потрібній+кількості",
                status_code=303
            )
    
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    
    return templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "current_user": user_data,
            "cart_items": cart_items,
            "total": total,
            "now": datetime.now()
        }
    )


@router.post("/checkout")
async def process_checkout(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_email: str = Form(...),
    shipping_address: str = Form(...),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Обработка оформления заказа"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    user_id = str(user_data["id"])
    cart_items = cart_store.get(user_id, [])
    
    if not cart_items:
        return RedirectResponse(url="/cart", status_code=303)
    
    # Проверяем наличие товаров на складе
    for item in cart_items:
        stmt = select(Product).where(Product.id == item["product_id"])
        result = await db.execute(stmt)
        product = result.scalar_one()
        
        if product.stock_quantity < item["quantity"]:
            return RedirectResponse(
                url=f"/cart?error=Товар+{item['name']}+недоступний+в+потрібній+кількості",
                status_code=303
            )
    
    # Рассчитываем общую сумму
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    
    # Создаем заказ в БД
    new_order = Order(
        user_id=user_data["id"],
        total_amount=total,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        shipping_address=shipping_address,
        notes=notes
    )
    
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    
    # Добавляем товары в заказ
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=cart_item["product_id"],
            quantity=cart_item["quantity"],
            price=cart_item["price"]
        )
        db.add(order_item)
    
    # Обновляем количество товаров на складе
    for cart_item in cart_items:
        stmt = select(Product).where(Product.id == cart_item["product_id"])
        result = await db.execute(stmt)
        product = result.scalar_one()
        product.stock_quantity = max(0, product.stock_quantity - cart_item["quantity"])
    
    await db.commit()
    
    # Очищаем корзину
    cart_store[user_id] = []
    
    # Перенаправляем на страницу подтверждения
    return RedirectResponse(
        url=f"/order/confirmation/{new_order.id}",
        status_code=303
    )


@router.get("/order/confirmation/{order_id}", response_class=HTMLResponse)
async def order_confirmation(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Страница подтверждения заказа"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получаем заказ
    stmt = select(Order).where(
        (Order.id == order_id) & 
        (Order.user_id == user_data["id"])
    ).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse(
        "order_confirmation.html",
        {
            "request": request,
            "current_user": user_data,
            "order": order,
            "now": datetime.now()
        }
    )


@router.get("/orders", response_class=HTMLResponse)
async def user_orders(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница заказов пользователя"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получаем заказы пользователя
    stmt = select(Order).where(
        Order.user_id == user_data["id"]
    ).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).order_by(Order.created_at.desc())
    
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    return templates.TemplateResponse(
        "user_orders.html",
        {
            "request": request,
            "current_user": user_data,
            "orders": orders,
            "now": datetime.now()
        }
    )


@router.get("/order/{order_id}", response_class=HTMLResponse)
async def order_detail(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Детали заказа"""
    from routes.auth import get_current_user_from_cookies
    
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Получаем заказ
    stmt = select(Order).where(
        (Order.id == order_id) & 
        (Order.user_id == user_data["id"])
    ).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        return RedirectResponse(url="/orders", status_code=303)
    
    return templates.TemplateResponse(
        "order_detail.html",
        {
            "request": request,
            "current_user": user_data,
            "order": order,
            "now": datetime.now()
        }
    )


@router.get("/categories")
async def get_categories():
    """Получить список категорий"""
    return {"categories": [cat.value for cat in ProductCategory]}