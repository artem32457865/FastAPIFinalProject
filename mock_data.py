import asyncio

from werkzeug.security import generate_password_hash

from models import User
from settings import Base, api_config, async_engine, async_session


async def create_bd():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def insert_data():
    async with async_session() as session:
        u1 = User(
            username="admin",
            email="admin@ex.com",
            is_admin=True,
            password=generate_password_hash("admin"),
        )
        u2 = User(
            username="user",
            email="user@ex.com",
            password=generate_password_hash("user"),
        )

        session.add_all([u1, u2])
        await session.commit()


async def main():
    await create_bd()
    print(f"database {api_config.DATABASE_NAME} created")

    await insert_data()
    print(f"data added to {api_config.DATABASE_NAME}")

    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
