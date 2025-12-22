from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from models.models import Feedback, User
from schemas.feedback import FeedbackCreate
from routes.auth import get_current_user_from_cookies
from settings import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/feedback", response_class=RedirectResponse)
async def create_feedback(
    request: Request,
    content: str = Form(...),
    rating: int = Form(...),
    current_user: User = Depends(get_current_user_from_cookies),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new feedback entry
    """
    feedback = Feedback(
        content=content,
        rating=rating,
        user_id=current_user["id"]
    )
    
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    # Redirect back to home page with success message
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("feedback_message", "Дякуємо за ваш відгук!", httponly=True, max_age=5)
    return response


@router.get("/feedbacks", response_class=HTMLResponse)
async def list_feedbacks(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Show all feedbacks
    """
    result = await db.execute(
        select(Feedback, User.username)
        .join(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
    )
    feedbacks_with_users = result.all()
    
    # Calculate average rating
    avg_rating_result = await db.execute(
        select(func.avg(Feedback.rating))
    )
    avg_rating = avg_rating_result.scalar()
    
    if avg_rating is not None:
        avg_rating = round(float(avg_rating), 1)
    
    return templates.TemplateResponse("feedback/list.html", {
        "request": request,
        "feedbacks": feedbacks_with_users,
        "avg_rating": avg_rating
    })