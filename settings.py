import os
import dotenv
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
    AsyncSession 
)
from sqlalchemy.orm import DeclarativeBase

dotenv.load_dotenv()


class DatabaseConfig:
    DATABASE_NAME = os.getenv("DATABASE_NAME", "repairhub.db")
    
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 5
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    STATIC_IMAGES_DIR = "static/images"
    
    def uri_sqlite(self):
        return f"sqlite+aiosqlite:///{self.DATABASE_NAME}"


api_config = DatabaseConfig()


async_engine: AsyncEngine = create_async_engine(
    api_config.uri_sqlite(),
    echo=True
)


async_session = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession 
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()