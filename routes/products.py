from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Product, ProductCategory
from settings import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Приклад товарів для початку (тимчасово, поки не додамо в БД)
MOCK_PRODUCTS = [
    {
        "id": 1,
        "name": "Пилосос Dyson V11",
        "description": "Потужний бездротовий пилосос",
        "price": 19999.99,
        "category": "Пилососи",
        "image_url": "/static/images/vacuum.jpg",
        "stock_quantity": 10
    },
    {
        "id": 2,
        "name": "Холодильник Samsung RB38",
        "description": "Двохкамерний холодильник з No Frost",
        "price": 25999.99,
        "category": "Холодильники",
        "image_url": "/static/images/fridge.jpg",
        "stock_quantity": 5
    },
    # Додайте більше товарів...
]

@router.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    category: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    search: str | None = Query(None)
):
    """Сторінка з товарами та фільтрами"""
    
    # Фільтрація товарів (тимчасово на mock даних)
    filtered_products = MOCK_PRODUCTS.copy()
    
    if category:
        filtered_products = [p for p in filtered_products if p["category"] == category]
    
    if min_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] >= min_price]
    
    if max_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] <= max_price]
    
    if search:
        filtered_products = [
            p for p in filtered_products 
            if search.lower() in p["name"].lower() or search.lower() in p["description"].lower()
        ]
    
    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": filtered_products,
            "categories": [cat.value for cat in ProductCategory],
            "selected_category": category,
            "search_query": search,
            "min_price": min_price,
            "max_price": max_price
        }
    )

@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    """Сторінка деталей товару"""
    # Тимчасово - знаходимо товар в mock даних
    product = next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None)
    
    if not product:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error_code": 404, "error_message": "Товар не знайдено"},
            status_code=404
        )
    
    return templates.TemplateResponse(
        "product_detail.html",
        {"request": request, "product": product}
    )