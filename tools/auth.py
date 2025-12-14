import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.security import check_password_hash, generate_password_hash

from models.models import User
from settings import api_config, async_session


# openssl rand -hex 32
def generate_secret_key():
    return os.urandom(32).hex()


def create_access_token(payload: dict, expires_delta: timedelta | None = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=api_config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload.update({"exp": expire})
    jwt_token = jwt.encode(
        payload, api_config.SECRET_KEY, algorithm=api_config.ALGORITHM
    )
    return jwt_token


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            api_config.SECRET_KEY,
            algorithms=[api_config.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен закінчився",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user(username: str, password: str):
    async with async_session() as session:
        # Шукаємо користувача за username або email
        stmt = select(User).where(
            (User.username == username) | (User.email == username)
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None
        if not check_password_hash(user.password, password):
            return None
        return user