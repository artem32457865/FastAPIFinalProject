import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from models.models import User, Product, ProductCategory
from settings import async_session, async_engine, Base


async def insert_data():
    """Добавление тестовых данных"""
    print("🔄 Добавление тестовых данных...")
    
    async with async_session() as session:
        # 1. Пользователи
        admin_user = User(
            username="admin",
            email="admin@example.com",
            is_admin=True,
            password=generate_password_hash("admin123"),
        )
        
        regular_user = User(
            username="user",
            email="user@example.com",
            password=generate_password_hash("user123"),
        )
        
        session.add_all([admin_user, regular_user])
        await session.commit()
        
        # 2. Товары
        products = [
            Product(
                name="Пилосос Dyson V11",
                description="Потужний бездротовий пилосос",
                price=19999.99,
                category=ProductCategory.VACUUM_CLEANER,
                stock_quantity=10,
            ),
            Product(
                name="Холодильник Samsung RB38",
                description="Двохкамерний холодильник з No Frost",
                price=25999.99,
                category=ProductCategory.REFRIGERATOR,
                stock_quantity=5,
            ),
            Product(
                name="Ноутбук Lenovo IdeaPad",
                description="15.6 дюймів, Intel Core i5, 8GB RAM",
                price=21999.99,
                category=ProductCategory.COMPUTER,
                stock_quantity=7,
            ),
            Product(
                name="Смартфон iPhone 13",
                description="128GB, синій",
                price=28999.99,
                category=ProductCategory.SMARTPHONE,
                stock_quantity=3,
            ),
            Product(
                name="Телевізор Samsung 50\"",
                description="4K UHD, Smart TV",
                price=19999.99,
                category=ProductCategory.TV,
                stock_quantity=4,
            ),
            
             Product(
        name="Ноутбук ASUS VivoBook",
        description="15.6 дюймів, AMD Ryzen 5, 16GB RAM, 512GB SSD",
        price=24999.99,
        category=ProductCategory.COMPUTER,
        stock_quantity=8,
        image_url="/static/images/laptop2.jpg"
    ),
    Product(
        name="Смартфон Samsung Galaxy S23",
        description="256GB, чорний, 120Hz дисплей",
        price=32999.99,
        category=ProductCategory.SMARTPHONE,
        stock_quantity=6,
        image_url="/static/images/galaxy.jpg"
    ),
    Product(
        name="Телевізор LG 55\" OLED",
        description="4K OLED, Smart TV, Google TV",
        price=34999.99,
        category=ProductCategory.TV,
        stock_quantity=3,
        image_url="/static/images/tv2.jpg"
    ),
    Product(
        name="Пральна машина Samsung",
        description="Завантаження 8 кг, Eco Bubble, Digital Inverter",
        price=18999.99,
        category=ProductCategory.KITCHEN,
        stock_quantity=7,
        image_url="/static/images/washer.jpg"
    ),
    Product(
        name="Мікрохвильова піч Samsung",
        description="25 літрів, гриль, конвекція",
        price=5999.99,
        category=ProductCategory.KITCHEN,
        stock_quantity=15,
        image_url="/static/images/microwave.jpg"
    ),
    Product(
        name="Пилосос Philips PowerPro",
        description="Потужність 650W, мішок для пилу",
        price=3999.99,
        category=ProductCategory.VACUUM_CLEANER,
        stock_quantity=12,
        image_url="/static/images/vacuum2.jpg"
    ),
        ]
        
        session.add_all(products)
        await session.commit()
    
    print("✅ Тестовые данные добавлены!")



async def create_tables():
    """Создание всех таблиц"""
    print("🔄 Создание таблиц...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы созданы")


async def main():
    """Основная функция"""
    print("🚀 Начало миграции базы данных...")
    
    try:
        await insert_data()
        
        print("🎉 Миграция успешно завершена!")
        print("📊 База данных: repairhub.db")
        print("👤 Админ: email=admin@example.com / пароль=admin123")
        print("👤 Пользователь: email=user@example.com / пароль=user123")
        
    except Exception as e:
        print(f"❌ Помилка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())