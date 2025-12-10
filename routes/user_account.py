from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy import select

from models import User, RepairRequest
from routes.auth import get_current_user, require_admin
from schemas.user import UserOut
from settings import get_db
from sqlalchemy.ext.asyncio import AsyncSession
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
async def user_me_data(current_user: dict = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db),
                       ):
    user_id = current_user["sub"]

    stmt = select(User).where(User.id == int(user_id))
    user = await db.scalar(stmt)
    return user


@router.post("/repair/add")
async def create_repair_request(bgt: BackgroundTasks,
                                current_user: dict = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db),
                                description: str = Form(...),
                                image: UploadFile | None = File(None),
                                required_time: datetime = Form(None)
                                ):
    user_id = current_user["sub"]
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
async def get_all_repairs(current_user: dict = Depends(get_current_user)):
    return {"message": "Get all repair requests endpoint"}


@router.get("/repair/{repair_id}")
async def get_repair_request(repair_id: int, current_user: dict = Depends(get_current_user)):
    return {"message": f"Get repair request {repair_id} endpoint"}



@router.put("/repair/{repair_id}")
async def update_repair_request(repair_id: int, current_user: dict = Depends(get_current_user)):
    return {"message": f"Update repair request {repair_id} endpoint"}


@router.delete("/repair/{repair_id}")
async def delete_repair_request(repair_id: int, current_user: dict = Depends(get_current_user)):
    return {"message": f"Delete repair request {repair_id} endpoint"}
