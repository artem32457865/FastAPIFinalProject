from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Product, ProductCategory
from settings import get_db
from routes.auth import get_current_user_from_cookies

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    category: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Страница каталога товаров"""
    
    # Получаем текущего пользователя для шаблона
    current_user = await get_current_user_from_cookies(request, db)
    
    # Базовый запрос
    stmt = select(Product)
    
    # Применяем фильтры
    if category:
        stmt = stmt.where(Product.category == category)
    
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    
    if search:
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
            "categories": [cat for cat in ProductCategory],
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
        "product/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "is_authenticated": current_user is not None,
            "product": product,
            "similar_products": similar_products,
            "now": datetime.now()
        }
    )


# Импортируем datetime
from datetime import datetime