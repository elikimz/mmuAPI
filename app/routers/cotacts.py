from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime

from app.database.database import get_async_db
from app.models.models import AppContact

from pydantic import BaseModel

router = APIRouter(prefix="/app-contacts", tags=["App Contacts"])

# ==========================
# Schemas
# ==========================
class AppContactCreate(BaseModel):
    number: Optional[str] = None
    whatsapp_link: Optional[str] = None
    customer_link: Optional[str] = None

class AppContactUpdate(BaseModel):
    number: Optional[str] = None
    whatsapp_link: Optional[str] = None
    customer_link: Optional[str] = None

class AppContactOut(BaseModel):
    id: int
    number: Optional[str]
    whatsapp_link: Optional[str]
    customer_link: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}  # for SQLAlchemy async

# ==========================
# Routes
# ==========================

# Create
@router.post("/", response_model=AppContactOut)
async def create_contact(contact: AppContactCreate, db: AsyncSession = Depends(get_async_db)):
    new_contact = AppContact(**contact.dict())
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    return new_contact

# Get all
@router.get("/", response_model=List[AppContactOut])
async def get_contacts(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AppContact))
    contacts = result.scalars().all()
    return contacts

# Get one
@router.get("/{contact_id}", response_model=AppContactOut)
async def get_contact(contact_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AppContact).filter(AppContact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

# Update
@router.put("/{contact_id}", response_model=AppContactOut)
async def update_contact(contact_id: int, updated_data: AppContactUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AppContact).filter(AppContact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(contact, key, value)

    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact

# Delete
@router.delete("/{contact_id}")
async def delete_contact(contact_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AppContact).filter(AppContact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(contact)
    await db.commit()
    return {"message": "Contact deleted successfully"}
