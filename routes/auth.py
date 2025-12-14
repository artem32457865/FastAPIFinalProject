from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.security import check_password_hash, generate_password_hash

from models.models import User
from schemas.user import UserInput, UserOut
from settings import api_config, get_db
from tools.auth import create_access_token, decode_access_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def get_current_user_from_cookies(
    request: Request, 
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """Отримання поточного користувача з cookies"""
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None
    
    try:
        payload = decode_access_token(access_token)
        # Отримуємо повну інформацію про користувача з БД
        stmt = select(User).where(User.id == int(payload.get("sub")))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    except Exception as e:
        print(f"Error getting user from cookies: {e}")
        return None


# Функція для залежностей Depends()
async def get_current_user(
    request: Request, 
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Отримання поточного користувача для залежностей"""
    user = await get_current_user_from_cookies(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизовано"
        )
    return user


# Функція для залежностей Depends() з require_admin
async def require_admin(
    request: Request, 
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Перевірка, чи є користувач адміністратором"""
    user = await get_current_user_from_cookies(request, db)
    if not user or not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Недостатньо прав доступу"
        )
    return user


async def authenticate_user(username: str, password: str, db: AsyncSession) -> Optional[User]:
    """Аутентифікація користувача"""
    stmt = select(User).where(
        (User.username == username) | (User.email == username)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    if not check_password_hash(user.password, password):
        return None
    
    return user


# ==================== HTML СТОРІНКИ ====================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error": error, "now": datetime.now()}
    )


@router.post("/login")
async def login_form_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(username, password, db)
    
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Невірне ім'я користувача або пароль", "now": datetime.now()}
        )
    
    data_payload = {
        "sub": str(user.id), 
        "username": user.username,
        "email": user.email, 
        "is_admin": user.is_admin
    }
    
    expires_delta = timedelta(days=7) if remember else timedelta(hours=24)
    access_token = create_access_token(payload=data_payload, expires_delta=expires_delta)
    
    response = RedirectResponse(url="/", status_code=303)
    max_age = 604800 if remember else 86400
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=max_age,
        samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "error": error, "now": datetime.now()}
    )


@router.post("/register")
async def register_form_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    errors = []
    
    if password != confirm_password:
        errors.append("Паролі не співпадають")
    
    if len(password) < 6:
        errors.append("Пароль має містити щонайменше 6 символів")
    
    if len(username) < 3:
        errors.append("Ім'я користувача має містити щонайменше 3 символи")
    
    if "@" not in email or "." not in email:
        errors.append("Некоректний email")
    
    if errors:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": ". ".join(errors), "now": datetime.now()}
        )
    
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Користувач з таким email вже існує", "now": datetime.now()}
        )
    
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    existing_username = result.scalar_one_or_none()
    
    if existing_username:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Користувач з таким ім'ям вже існує", "now": datetime.now()}
        )
    
    new_user = User(
        username=username, 
        email=email,
        password=generate_password_hash(password)
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    data_payload = {
        "sub": str(new_user.id), 
        "username": new_user.username,
        "email": new_user.email, 
        "is_admin": new_user.is_admin
    }
    
    access_token = create_access_token(payload=data_payload)
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response


@router.post("/token")
async def generate_token(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(username, password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірне ім'я користувача або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    data_payload = {
        "sub": str(user.id), 
        "username": user.username,
        "email": user.email, 
        "is_admin": user.is_admin
    }
    
    access_token = create_access_token(payload=data_payload)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/register", response_model=UserOut)
async def register_user_api(user: UserInput, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == user.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач з таким email вже існує"
        )
    
    new_user = User(**user.model_dump())
    new_user.password = generate_password_hash(user.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_data = await get_current_user_from_cookies(request, db)
    
    if not user_data:
        return RedirectResponse(url="/auth/login")
    
    return templates.TemplateResponse(
        "auth/profile.html",
        {"request": request, "user": user_data, "now": datetime.now()}
    )