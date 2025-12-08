from fastapi import APIRouter, Depends

from models import User
from routes.auth import get_current_user, require_admin

router = APIRouter()


@router.get("/user/me")
async def user_me_data(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/user/admin/me")
async def only_for_admin(current_user: User = Depends(require_admin)):
    return {"is admin": current_user}
