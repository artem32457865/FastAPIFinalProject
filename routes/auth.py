from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.security import generate_password_hash

from models.models import User
from schemas.user import UserInput, UserOut
from settings import api_config, get_db
from tools.auth import authenticate_user, create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"Authorization": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_access_token(token)
    if not user:
        raise credentials_exception
    return user


def require_admin(user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials"
        )
    return user


# ==================== AUTH ROUTES ====================

@router.post("/token")
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise credentials_exception

    data_payload = {"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
    access_token = create_access_token(payload=data_payload)
    print(access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserOut)
async def register_user(user: UserInput, db: AsyncSession = Depends(get_db)):
    new_user = User(**user.model_dump())
    new_user.password = generate_password_hash(user.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
