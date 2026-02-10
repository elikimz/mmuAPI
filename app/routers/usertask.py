


# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import joinedload
# from typing import List
# from datetime import datetime, timedelta
# import asyncio

# from app.core.process_task_completion_referral_bonus import process_task_completion_referral_bonus
# from app.database.database import get_async_db
# from app.models.models import (
#     User,
#     UserTask,
#     UserTaskPending,
#     UserTaskCompleted,
#     Task,
#     Wallet,
#     Transaction,
#     TransactionType,
# )
# from app.routers.auth import get_current_user, get_current_admin
# from app.schema.schema import (
#     CompleteTaskRequest,
#     UserTaskResponse,
#     UserTaskPendingResponse,
#     UserTaskCompletedResponse,
# )

# router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])

# # -------------------------
# # USER: Get my tasks
# # -------------------------
# @router.get("/me", response_model=List[UserTaskResponse])
# async def get_my_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task).joinedload(Task.level))
#         .filter(UserTask.user_id == current_user.id)
#     )
#     user_tasks = result.scalars().all()

#     return [
#         {
#             "id": ut.id,
#             "user_id": ut.user_id,
#             "task_id": ut.task_id,
#             "video_url": ut.video_url,
#             "completed": ut.completed,
#             "locked": ut.locked,
#             "reward": ut.task.reward,
#             "description": ut.description,
#             "level_name": ut.task.level.name,
#         }
#         for ut in user_tasks
#         if ut.task and ut.task.level
#     ]


# # -------------------------
# # USER: Pending tasks
# # -------------------------
# @router.get("/me/pending", response_model=List[UserTaskPendingResponse])
# async def get_my_pending_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(UserTaskPending)
#         .options(joinedload(UserTaskPending.task).joinedload(Task.level))
#         .filter(UserTaskPending.user_id == current_user.id)
#     )
#     pending = result.scalars().all()

#     return [
#         {
#             "id": p.id,
#             "user_id": p.user_id,
#             "task_id": p.task_id,
#             "video_url": p.video_url,
#             "pending_until": p.pending_until,
#             "created_at": p.created_at,
#             "reward": p.task.reward,
#             "level_name": p.task.level.name,
#         }
#         for p in pending
#         if p.task and p.task.level
#     ]


# # -------------------------
# # USER: Completed tasks
# # -------------------------
# @router.get("/me/completed", response_model=List[UserTaskCompletedResponse])
# async def get_my_completed_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(UserTaskCompleted)
#         .options(joinedload(UserTaskCompleted.task).joinedload(Task.level))
#         .filter(UserTaskCompleted.user_id == current_user.id)
#     )
#     completed = result.scalars().all()

#     return [
#         {
#             "id": c.id,
#             "user_id": c.user_id,
#             "task_id": c.task_id,
#             "video_url": c.video_url,
#             "completed_at": c.completed_at,
#             "reward": c.task.reward,
#             "level_name": c.task.level.name,
#         }
#         for c in completed
#         if c.task and c.task.level
#     ]


# # -------------------------
# # USER: Complete task
# # -------------------------
# @router.post("/complete", response_model=UserTaskResponse)
# async def complete_task(
#     request: CompleteTaskRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task).joinedload(Task.level))
#         .filter(
#             UserTask.user_id == current_user.id,
#             UserTask.id == request.user_task_id,
#         )
#     )
#     user_task = result.scalar_one_or_none()

#     if not user_task:
#         raise HTTPException(status_code=404, detail="Task not found")
#     if user_task.completed:
#         raise HTTPException(status_code=400, detail="Task already completed")
#     if user_task.locked:
#         raise HTTPException(status_code=403, detail="Task is locked")

#     pending = UserTaskPending(
#         user_id=current_user.id,
#         task_id=user_task.task_id,
#         video_url=user_task.video_url,
#         pending_until=datetime.utcnow() + timedelta(seconds=10),
#         created_at=datetime.utcnow(),
#     )
#     db.add(pending)

#     user_task.completed = True
#     await db.commit()
#     await db.refresh(user_task)

#     async def finalize_task(task_id: int):
#         await asyncio.sleep(10)
#         async with AsyncSession(db.bind) as bg_db:
#             result = await bg_db.execute(
#                 select(UserTaskPending)
#                 .options(joinedload(UserTaskPending.task))
#                 .filter(
#                     UserTaskPending.user_id == current_user.id,
#                     UserTaskPending.task_id == task_id,
#                 )
#             )
#             pending_task = result.scalar_one_or_none()
#             if not pending_task:
#                 return

#             completed = UserTaskCompleted(
#                 user_id=pending_task.user_id,
#                 task_id=pending_task.task_id,
#                 video_url=pending_task.video_url,
#                 completed_at=datetime.utcnow(),
#             )
#             bg_db.add(completed)
#             await bg_db.delete(pending_task)

#             wallet = (
#                 await bg_db.execute(
#                     select(Wallet).filter(Wallet.user_id == current_user.id)
#                 )
#             ).scalar_one_or_none()

#             if wallet:
#                 wallet.income += pending_task.task.reward
#                 bg_db.add(
#                     Transaction(
#                         user_id=current_user.id,
#                         type=TransactionType.TASK_REWARD.value,
#                         amount=pending_task.task.reward,
#                         created_at=datetime.utcnow(),
#                     )
#                 )

#             await bg_db.commit()

#             await process_task_completion_referral_bonus(
#                 db=bg_db,
#                 completed_user_id=current_user.id,
#             )

#     asyncio.create_task(finalize_task(user_task.task_id))

#     return {
#         "id": user_task.id,
#         "user_id": user_task.user_id,
#         "task_id": user_task.task_id,
#         "video_url": user_task.video_url,
#         "completed": user_task.completed,
#         "locked": user_task.locked,
#         "reward": user_task.task.reward,
#         "description": user_task.description,
#         "level_name": user_task.task.level.name,
#     }


# # -------------------------
# # ADMIN: Lock / Unlock
# # -------------------------
# @router.patch("/{user_task_id}/lock", response_model=UserTaskResponse)
# async def lock_user_task(
#     user_task_id: int,
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     task = (
#         await db.execute(
#             select(UserTask)
#             .options(joinedload(UserTask.task).joinedload(Task.level))
#             .filter(UserTask.id == user_task_id)
#         )
#     ).scalar_one_or_none()

#     if not task:
#         raise HTTPException(status_code=404, detail="User task not found")

#     task.locked = True
#     await db.commit()
#     await db.refresh(task)

#     return {
#         "id": task.id,
#         "user_id": task.user_id,
#         "task_id": task.task_id,
#         "video_url": task.video_url,
#         "completed": task.completed,
#         "locked": task.locked,
#         "reward": task.task.reward,
#         "description": task.description,
#         "level_name": task.task.level.name,
#     }


# @router.patch("/{user_task_id}/unlock", response_model=UserTaskResponse)
# async def unlock_user_task(
#     user_task_id: int,
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     task = (
#         await db.execute(
#             select(UserTask)
#             .options(joinedload(UserTask.task).joinedload(Task.level))
#             .filter(UserTask.id == user_task_id)
#         )
#     ).scalar_one_or_none()

#     if not task:
#         raise HTTPException(status_code=404, detail="User task not found")

#     task.locked = False
#     await db.commit()
#     await db.refresh(task)

#     return {
#         "id": task.id,
#         "user_id": task.user_id,
#         "task_id": task.task_id,
#         "video_url": task.video_url,
#         "completed": task.completed,
#         "locked": task.locked,
#         "reward": task.task.reward,
#         "description": task.description,
#         "level_name": task.task.level.name,
#     }






# @router.get("/admin/all", response_model=List[UserTaskResponse])
# async def get_all_user_tasks(
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task).joinedload(Task.level))
#     )
#     all_tasks = result.scalars().all()

#     tasks_with_reward_and_level = []
#     for user_task in all_tasks:
#         if user_task.task and user_task.task.level:
#             task_data = {
#                 "id": user_task.id,
#                 "user_id": user_task.user_id,
#                 "task_id": user_task.task_id,
#                 "video_url": user_task.video_url,
#                 "completed": user_task.completed,
#                 "locked": user_task.locked if hasattr(user_task, 'locked') else False,
#                 "reward": user_task.task.reward,
#                 "description": user_task.description,
#                 "level_name": user_task.task.level.name
#             }
#             tasks_with_reward_and_level.append(task_data)

#     return tasks_with_reward_and_level



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List
from datetime import datetime

from app.core.process_task_completion_referral_bonus import process_task_completion_referral_bonus
from app.database.database import get_async_db
from app.models.models import (
    User,
    UserTask,
    UserTaskCompleted,
    Task,
    Wallet,
    Transaction,
    TransactionType,
)
from app.routers.auth import get_current_user, get_current_admin
from app.schema.schema import (
    CompleteTaskRequest,
    UserTaskResponse,
    UserTaskCompletedResponse,
)

router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])

# -------------------------
# USER: Get my tasks
# -------------------------
@router.get("/me", response_model=List[UserTaskResponse])
async def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(UserTask.user_id == current_user.id)
    )
    user_tasks = result.scalars().all()

    return [
        {
            "id": ut.id,
            "user_id": ut.user_id,
            "task_id": ut.task_id,
            "video_url": ut.video_url,
            "completed": ut.completed,
            "locked": ut.locked,
            "reward": ut.task.reward,
            "description": ut.description,
            "level_name": ut.task.level.name,
        }
        for ut in user_tasks
        if ut.task and ut.task.level
    ]

# -------------------------
# USER: Completed tasks
# -------------------------
@router.get("/me/completed", response_model=List[UserTaskCompletedResponse])
async def get_my_completed_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserTaskCompleted)
        .options(joinedload(UserTaskCompleted.task).joinedload(Task.level))
        .filter(UserTaskCompleted.user_id == current_user.id)
    )
    completed = result.scalars().all()

    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "task_id": c.task_id,
            "video_url": c.video_url,
            "completed_at": c.completed_at,
            "reward": c.task.reward,
            "level_name": c.task.level.name,
        }
        for c in completed
        if c.task and c.task.level
    ]

# -------------------------
# USER: Complete task
# -------------------------
@router.post("/complete", response_model=UserTaskResponse)
async def complete_task(
    request: CompleteTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(
            UserTask.user_id == current_user.id,
            UserTask.id == request.user_task_id,
        )
    )
    user_task = result.scalar_one_or_none()

    if not user_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user_task.completed:
        raise HTTPException(status_code=400, detail="Task already completed")
    if user_task.locked:
        raise HTTPException(status_code=403, detail="Task is locked")

    # Mark task as completed
    user_task.completed = True

    # Create a completed task entry
    completed_task = UserTaskCompleted(
        user_id=current_user.id,
        task_id=user_task.task_id,
        video_url=user_task.video_url,
        completed_at=datetime.utcnow(),
    )
    db.add(completed_task)

    # Update wallet and add transaction
    wallet = (
        await db.execute(
            select(Wallet).filter(Wallet.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if wallet:
        wallet.income += user_task.task.reward
        db.add(
            Transaction(
                user_id=current_user.id,
                type=TransactionType.TASK_REWARD.value,
                amount=user_task.task.reward,
                created_at=datetime.utcnow(),
            )
        )

    await db.commit()
    await db.refresh(user_task)

    # Process referral bonus
    await process_task_completion_referral_bonus(
        db=db,
        completed_user_id=current_user.id,
    )

    return {
        "id": user_task.id,
        "user_id": user_task.user_id,
        "task_id": user_task.task_id,
        "video_url": user_task.video_url,
        "completed": user_task.completed,
        "locked": user_task.locked,
        "reward": user_task.task.reward,
        "description": user_task.description,
        "level_name": user_task.task.level.name,
    }

# -------------------------
# ADMIN: Lock / Unlock
# -------------------------
@router.patch("/{user_task_id}/lock", response_model=UserTaskResponse)
async def lock_user_task(
    user_task_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    task = (
        await db.execute(
            select(UserTask)
            .options(joinedload(UserTask.task).joinedload(Task.level))
            .filter(UserTask.id == user_task_id)
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="User task not found")

    task.locked = True
    await db.commit()
    await db.refresh(task)

    return {
        "id": task.id,
        "user_id": task.user_id,
        "task_id": task.task_id,
        "video_url": task.video_url,
        "completed": task.completed,
        "locked": task.locked,
        "reward": task.task.reward,
        "description": task.description,
        "level_name": task.task.level.name,
    }

@router.patch("/{user_task_id}/unlock", response_model=UserTaskResponse)
async def unlock_user_task(
    user_task_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    task = (
        await db.execute(
            select(UserTask)
            .options(joinedload(UserTask.task).joinedload(Task.level))
            .filter(UserTask.id == user_task_id)
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="User task not found")

    task.locked = False
    await db.commit()
    await db.refresh(task)

    return {
        "id": task.id,
        "user_id": task.user_id,
        "task_id": task.task_id,
        "video_url": task.video_url,
        "completed": task.completed,
        "locked": task.locked,
        "reward": task.task.reward,
        "description": task.description,
        "level_name": task.task.level.name,
    }

# -------------------------
# ADMIN: Get all user tasks
# -------------------------
@router.get("/admin/all", response_model=List[UserTaskResponse])
async def get_all_user_tasks(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
    )
    all_tasks = result.scalars().all()

    tasks_with_reward_and_level = []
    for user_task in all_tasks:
        if user_task.task and user_task.task.level:
            task_data = {
                "id": user_task.id,
                "user_id": user_task.user_id,
                "task_id": user_task.task_id,
                "video_url": user_task.video_url,
                "completed": user_task.completed,
                "locked": user_task.locked if hasattr(user_task, 'locked') else False,
                "reward": user_task.task.reward,
                "description": user_task.description,
                "level_name": user_task.task.level.name
            }
            tasks_with_reward_and_level.append(task_data)

    return tasks_with_reward_and_level
