from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, RepairRequest
from routes.auth import get_current_user, require_admin
from schemas.user import UserOut
from settings import get_db
from datetime import datetime
from tools.file_upload import generate_file_url, save_file


router = APIRouter()

"""
a) Створення заявок, (назва, опис, додавання фотографій) (/user/account/create_repair_request)
b) Перегляд всіх створених заявок GET (/user/account/repairs)
c) Перегляд конкретної створеної заявки та її статус GET (/user/account/{repair_id})
d) Редагування створених заявок користувачем PUT (/user/account/{repair_id})
e) Видалення користувачем створеної заявки DELETE (/user/account/{repair_id})
"""


@router.get("/user/me", response_model=UserOut)
async def user_me_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Отримуємо поточного користувача через залежність
    current_user = await get_current_user(request, db)
    
    stmt = select(User).where(User.id == int(current_user["id"]))
    user = await db.scalar(stmt)
    return user


@router.post("/repair/add")
async def create_repair_request(
    request: Request,
    bgt: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    description: str = Form(...),
    image: UploadFile | None = File(None),
    required_time: datetime = Form(None)
):
    # Отримуємо поточного користувача
    current_user = await get_current_user(request, db)
    
    user_id = current_user["id"]
    image_url = None
    if image:
        image_url = await generate_file_url(image.filename)  # type: ignore
        bgt.add_task(save_file, image, image_url)

    new_req = RepairRequest(
        user_id=int(user_id),
        description=description,
        photo_url=image_url,
        required_time=required_time
    )

    db.add(new_req)
    await db.commit()
    await db.refresh(new_req)
    return new_req


@router.get("/repairs")
async def get_all_repairs(request: Request, db: AsyncSession = Depends(get_db)):
    # Отримуємо поточного користувача
    current_user = await get_current_user(request, db)
    
    user_id = current_user["id"]
    
    # Отримуємо всі заявки користувача
    stmt = select(RepairRequest).where(RepairRequest.user_id == int(user_id))
    result = await db.execute(stmt)
    repairs = result.scalars().all()
    
    return repairs


@router.get("/repair/{repair_id}")
async def get_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    # Отримуємо поточного користувача
    current_user = await get_current_user(request, db)
    
    user_id = current_user["id"]
    
    # Отримуємо конкретну заявку користувача
    stmt = select(RepairRequest).where(
        (RepairRequest.id == repair_id) & 
        (RepairRequest.user_id == int(user_id))
    )
    result = await db.execute(stmt)
    repair = result.scalar_one_or_none()
    
    if not repair:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Заявка не знайдена")
    
    return repair


@router.put("/repair/{repair_id}")
async def update_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    # Отримуємо поточного користувача
    current_user = await get_current_user(request, db)
    
    return {"message": f"Update repair request {repair_id} endpoint (TODO)"}


@router.delete("/repair/{repair_id}")
async def delete_repair_request(
    repair_id: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    # Отримуємо поточного користувача
    current_user = await get_current_user(request, db)
    
    return {"message": f"Delete repair request {repair_id} endpoint (TODO)"}