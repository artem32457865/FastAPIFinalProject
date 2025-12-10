from fastapi import APIRouter, Depends

from models import User
from routes.auth import get_current_user, require_admin

router = APIRouter()

"""a) Перегляд всіх заявок, та тільки тих що мають статус «Нова» (фільтр) (/admin/repairs?new=1)
b) Прийняття заявки (/admin/repair/{repair_id}/self/get)
c) Перегляд всіх заявок що взяв на опрацювання (/admin/self/repairs)
d) Зміна статуса заявки (закриття, взяття на опрацювання і тд)
(/admin/repair/{repair_id}/change/status)
e) Створення повідомлень (коментарів)(/admin/repair/{repair_id}/change/comment)"""


@router.get("/user/admin/me")
async def only_for_admin(current_user: User = Depends(require_admin)):
    return {"is admin": current_user}
