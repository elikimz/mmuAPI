from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import List

from app.database.database import get_async_db
from app.models.models import News, User
from app.routers.auth import get_current_admin  # Only admin can manage news
from pydantic import BaseModel

router = APIRouter(prefix="/news", tags=["News"])

# ==========================
# Schemas
# ==========================
class NewsCreateRequest(BaseModel):
    title: str
    content: str

class NewsUpdateRequest(BaseModel):
    title: str = None
    content: str = None

class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

# ==========================
# Create News
# ==========================
@router.post("/", response_model=NewsResponse)
async def create_news(
    request: NewsCreateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    news_item = News(title=request.title, content=request.content)
    db.add(news_item)
    await db.commit()
    await db.refresh(news_item)
    return news_item

# ==========================
# Get all News
# ==========================
@router.get("/", response_model=List[NewsResponse])
async def get_all_news(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(News).order_by(News.created_at.desc()))
    news_items = result.scalars().all()
    return news_items

# ==========================
# Update News
# ==========================
@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: int,
    request: NewsUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(News).filter(News.id == news_id))
    news_item = result.scalar_one_or_none()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    if request.title is not None:
        news_item.title = request.title
    if request.content is not None:
        news_item.content = request.content

    db.add(news_item)
    await db.commit()
    await db.refresh(news_item)
    return news_item

# ==========================
# Delete News
# ==========================
@router.delete("/{news_id}")
async def delete_news(
    news_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(News).filter(News.id == news_id))
    news_item = result.scalar_one_or_none()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    await db.delete(news_item)
    await db.commit()
    return {"detail": "News deleted successfully"}
