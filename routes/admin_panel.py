from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from routes.auth import require_admin
from settings import get_db

router = APIRouter()

"""a) Перегляд всіх заявок, та тільки тих що мають статус «Нова» (фільтр) (/admin/repairs?new=1)
b) Прийняття заявки (/admin/repair/{repair_id}/self/get)
c) Перегляд всіх заявок що взяв на опрацювання (/admin/self/repairs)
d) Зміна статуса заявки (закриття, взяття на опрацювання і тд)
(/admin/repair/{repair_id}/change/status)
e) Створення повідомлень (коментарів)(/admin/repair/{repair_id}/change/comment)"""


@router.get("/user/admin/me")
async def only_for_admin(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await require_admin(request, db)
    return {"is admin": current_user}