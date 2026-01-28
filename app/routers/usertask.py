from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta
import asyncio

from app.database.database import get_async_db
from app.models.models import User, UserTask, UserTaskPending, UserTaskCompleted, Task, Wallet, Transaction
from app.routers.auth import get_current_user
from app.schema.schema import CompleteTaskRequest, UserTaskResponse

router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])


# -------------------------
# USER: Get all tasks assigned to them
# -------------------------
@router.get("/me", response_model=List[UserTaskResponse])
async def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(UserTask).filter(UserTask.user_id == current_user.id))
    tasks = result.scalars().all()
    return tasks


# -------------------------
# USER: Complete a task
# -------------------------
@router.post("/complete", response_model=UserTaskResponse)
async def complete_task(
    request: CompleteTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Fetch the task
    result = await db.execute(
        select(UserTask).filter(UserTask.user_id == current_user.id, UserTask.id == request.user_task_id)
    )
    user_task = result.scalar_one_or_none()
    if not user_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user_task.completed:
        raise HTTPException(status_code=400, detail="Task already completed")

    # Mark as pending
    pending_task = UserTaskPending(
        user_id=current_user.id,
        task_id=user_task.task_id,
        video_url=user_task.video_url,
        pending_until=datetime.utcnow() + timedelta(seconds=10),
        created_at=datetime.utcnow()
    )
    db.add(pending_task)

    # Mark original user_task as completed
    user_task.completed = True
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)

    # Run async background to move pending to completed after 10s
    async def finalize_task(user_task_id: int):
        await asyncio.sleep(10)
        async with AsyncSession(db.bind) as background_db:
            # Reload pending task
            result = await background_db.execute(
                select(UserTaskPending).filter(
                    UserTaskPending.user_id == current_user.id,
                    UserTaskPending.task_id == user_task_id
                )
            )
            pending = result.scalar_one_or_none()
            if pending:
                # Move to completed
                completed_task = UserTaskCompleted(
                    user_id=pending.user_id,
                    task_id=pending.task_id,
                    video_url=pending.video_url,
                    completed_at=datetime.utcnow()
                )
                background_db.add(completed_task)
                await background_db.delete(pending)

                # Reward user
                task_result = await background_db.execute(select(Task).filter(Task.id == pending.task_id))
                task = task_result.scalar_one_or_none()
                if task:
                    wallet_result = await background_db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
                    wallet = wallet_result.scalar_one_or_none()
                    if wallet:
                        wallet.income += task.reward
                        background_db.add(wallet)
                        # Record transaction
                        background_db.add(Transaction(
                            user_id=current_user.id,
                            type=f"task reward: {task.name}",
                            amount=task.reward,
                            created_at=datetime.utcnow()
                        ))

                await background_db.commit()

    asyncio.create_task(finalize_task(user_task.task_id))

    return user_task
