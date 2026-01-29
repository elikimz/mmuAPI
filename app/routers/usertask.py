


# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import joinedload
# from typing import List
# from datetime import datetime, timedelta
# import asyncio

# from app.database.database import get_async_db
# from app.models.models import User, UserTask, UserTaskPending, UserTaskCompleted, Task, Wallet, Transaction
# from app.routers.auth import get_current_user, get_current_admin
# from app.schema.schema import CompleteTaskRequest, UserTaskResponse, UserTaskPendingResponse, UserTaskCompletedResponse

# router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])

# # -------------------------
# # USER: Get all tasks assigned to them (with reward)
# # -------------------------
# @router.get("/me", response_model=List[UserTaskResponse])
# async def get_my_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     # Fetch user tasks with joinedload to get the associated task in one query
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task))
#         .filter(UserTask.user_id == current_user.id)
#     )
#     user_tasks = result.scalars().all()

#     tasks_with_reward = []
#     for user_task in user_tasks:
#         if user_task.task:
#             task_data = {
#                 "id": user_task.id,
#                 "user_id": user_task.user_id,
#                 "task_id": user_task.task_id,
#                 "video_url": user_task.video_url,
#                 "completed": user_task.completed,
#                 "locked": user_task.locked,
#                 "reward": user_task.task.reward,
#                 "description": user_task.description
#             }
#             tasks_with_reward.append(task_data)

#     return tasks_with_reward

# # -------------------------
# # USER: Get all pending tasks (with reward)
# # -------------------------
# @router.get("/me/pending", response_model=List[UserTaskPendingResponse])
# async def get_my_pending_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     # Fetch pending tasks with joinedload to get the associated task in one query
#     result = await db.execute(
#         select(UserTaskPending)
#         .options(joinedload(UserTaskPending.task))
#         .filter(UserTaskPending.user_id == current_user.id)
#     )
#     pending_tasks = result.scalars().all()

#     pending_tasks_with_reward = []
#     for pending_task in pending_tasks:
#         if pending_task.task:
#             task_data = {
#                 "id": pending_task.id,
#                 "user_id": pending_task.user_id,
#                 "task_id": pending_task.task_id,
#                 "video_url": pending_task.video_url,
#                 "pending_until": pending_task.pending_until,
#                 "created_at": pending_task.created_at,
#                 "reward": pending_task.task.reward
#             }
#             pending_tasks_with_reward.append(task_data)

#     return pending_tasks_with_reward

# # -------------------------
# # USER: Get all completed tasks (with reward)
# # -------------------------
# @router.get("/me/completed", response_model=List[UserTaskCompletedResponse])
# async def get_my_completed_tasks(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     # Fetch completed tasks with joinedload to get the associated task in one query
#     result = await db.execute(
#         select(UserTaskCompleted)
#         .options(joinedload(UserTaskCompleted.task))
#         .filter(UserTaskCompleted.user_id == current_user.id)
#     )
#     completed_tasks = result.scalars().all()

#     completed_tasks_with_reward = []
#     for completed_task in completed_tasks:
#         if completed_task.task:
#             task_data = {
#                 "id": completed_task.id,
#                 "user_id": completed_task.user_id,
#                 "task_id": completed_task.task_id,
#                 "video_url": completed_task.video_url,
#                 "completed_at": completed_task.completed_at,
#                 "reward": completed_task.task.reward
#             }
#             completed_tasks_with_reward.append(task_data)

#     return completed_tasks_with_reward

# # -------------------------
# # USER: Complete a task
# # -------------------------
# @router.post("/complete", response_model=UserTaskResponse)
# async def complete_task(
#     request: CompleteTaskRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     # Fetch the task
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task))
#         .filter(UserTask.user_id == current_user.id, UserTask.id == request.user_task_id)
#     )
#     user_task = result.scalar_one_or_none()
#     if not user_task:
#         raise HTTPException(status_code=404, detail="Task not found")
#     if user_task.completed:
#         raise HTTPException(status_code=400, detail="Task already completed")
#     if user_task.locked:
#         raise HTTPException(status_code=403, detail="Task is locked and cannot be completed")

#     # Mark as pending
#     pending_task = UserTaskPending(
#         user_id=current_user.id,
#         task_id=user_task.task_id,
#         video_url=user_task.video_url,
#         pending_until=datetime.utcnow() + timedelta(seconds=10),
#         created_at=datetime.utcnow()
#     )
#     db.add(pending_task)

#     # Mark original user_task as completed
#     user_task.completed = True
#     db.add(user_task)
#     await db.commit()
#     await db.refresh(user_task)

#     # Run async background to move pending to completed after 10s
#     async def finalize_task(user_task_id: int):
#         await asyncio.sleep(10)
#         async with AsyncSession(db.bind) as background_db:
#             # Reload pending task
#             result = await background_db.execute(
#                 select(UserTaskPending)
#                 .options(joinedload(UserTaskPending.task))
#                 .filter(
#                     UserTaskPending.user_id == current_user.id,
#                     UserTaskPending.task_id == user_task_id
#                 )
#             )
#             pending = result.scalar_one_or_none()
#             if pending:
#                 # Move to completed
#                 completed_task = UserTaskCompleted(
#                     user_id=pending.user_id,
#                     task_id=pending.task_id,
#                     video_url=pending.video_url,
#                     completed_at=datetime.utcnow()
#                 )
#                 background_db.add(completed_task)
#                 await background_db.delete(pending)

#                 # Reward user
#                 task = pending.task
#                 if task:
#                     wallet_result = await background_db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#                     wallet = wallet_result.scalar_one_or_none()
#                     if wallet:
#                         wallet.income += task.reward
#                         background_db.add(wallet)
#                         # Record transaction
#                         background_db.add(Transaction(
#                             user_id=current_user.id,
#                             type=f"task reward: {task.name}",
#                             amount=task.reward,
#                             created_at=datetime.utcnow()
#                         ))

#                 await background_db.commit()

#     asyncio.create_task(finalize_task(user_task.task_id))

#     return {
#         "id": user_task.id,
#         "user_id": user_task.user_id,
#         "task_id": user_task.task_id,
#         "video_url": user_task.video_url,
#         "completed": user_task.completed,
#         "locked": user_task.locked,
#         "reward": user_task.task.reward,
#         "description": user_task.description
#     }

# # -------------------------
# # ADMIN: Lock a user task
# # -------------------------
# @router.patch("/{user_task_id}/lock", response_model=UserTaskResponse)
# async def lock_user_task(
#     user_task_id: int,
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task))
#         .filter(UserTask.id == user_task_id)
#     )
#     user_task = result.scalar_one_or_none()
#     if not user_task:
#         raise HTTPException(status_code=404, detail="User task not found")

#     user_task.locked = True
#     db.add(user_task)
#     await db.commit()
#     await db.refresh(user_task)

#     return {
#         "id": user_task.id,
#         "user_id": user_task.user_id,
#         "task_id": user_task.task_id,
#         "video_url": user_task.video_url,
#         "completed": user_task.completed,
#         "locked": user_task.locked,
#         "reward": user_task.task.reward,
#         "description": user_task.description
#     }

# # -------------------------
# # ADMIN: Unlock a user task
# # -------------------------
# @router.patch("/{user_task_id}/unlock", response_model=UserTaskResponse)
# async def unlock_user_task(
#     user_task_id: int,
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db)
# ):
#     result = await db.execute(
#         select(UserTask)
#         .options(joinedload(UserTask.task))
#         .filter(UserTask.id == user_task_id)
#     )
#     user_task = result.scalar_one_or_none()
#     if not user_task:
#         raise HTTPException(status_code=404, detail="User task not found")

#     user_task.locked = False
#     db.add(user_task)
#     await db.commit()
#     await db.refresh(user_task)

#     return {
#         "id": user_task.id,
#         "user_id": user_task.user_id,
#         "task_id": user_task.task_id,
#         "video_url": user_task.video_url,
#         "completed": user_task.completed,
#         "locked": user_task.locked,
#         "reward": user_task.task.reward,
#         "description": user_task.description
#     }




from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List
from datetime import datetime, timedelta
import asyncio

from app.database.database import get_async_db
from app.models.models import User, UserTask, UserTaskPending, UserTaskCompleted, Task, Wallet, Transaction, Level
from app.routers.auth import get_current_user, get_current_admin
from app.schema.schema import CompleteTaskRequest, UserTaskResponse, UserTaskPendingResponse, UserTaskCompletedResponse

router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])

# -------------------------
# USER: Get all tasks assigned to them (with reward and level name)
# -------------------------
@router.get("/me", response_model=List[UserTaskResponse])
async def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Fetch user tasks with joinedload to get the associated task and level in one query
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(UserTask.user_id == current_user.id)
    )
    user_tasks = result.scalars().all()

    tasks_with_reward_and_level = []
    for user_task in user_tasks:
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
                "level_name": user_task.task.level.name  # Include level name
            }
            tasks_with_reward_and_level.append(task_data)

    return tasks_with_reward_and_level

# -------------------------
# USER: Get all pending tasks (with reward and level name)
# -------------------------
@router.get("/me/pending", response_model=List[UserTaskPendingResponse])
async def get_my_pending_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Fetch pending tasks with joinedload to get the associated task and level in one query
    result = await db.execute(
        select(UserTaskPending)
        .options(joinedload(UserTaskPending.task).joinedload(Task.level))
        .filter(UserTaskPending.user_id == current_user.id)
    )
    pending_tasks = result.scalars().all()

    pending_tasks_with_reward_and_level = []
    for pending_task in pending_tasks:
        if pending_task.task and pending_task.task.level:
            task_data = {
                "id": pending_task.id,
                "user_id": pending_task.user_id,
                "task_id": pending_task.task_id,
                "video_url": pending_task.video_url,
                "pending_until": pending_task.pending_until,
                "created_at": pending_task.created_at,
                "reward": pending_task.task.reward,
                "level_name": pending_task.task.level.name  # Include level name
            }
            pending_tasks_with_reward_and_level.append(task_data)

    return pending_tasks_with_reward_and_level

# -------------------------
# USER: Get all completed tasks (with reward and level name)
# -------------------------
@router.get("/me/completed", response_model=List[UserTaskCompletedResponse])
async def get_my_completed_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # Fetch completed tasks with joinedload to get the associated task and level in one query
    result = await db.execute(
        select(UserTaskCompleted)
        .options(joinedload(UserTaskCompleted.task).joinedload(Task.level))
        .filter(UserTaskCompleted.user_id == current_user.id)
    )
    completed_tasks = result.scalars().all()

    completed_tasks_with_reward_and_level = []
    for completed_task in completed_tasks:
        if completed_task.task and completed_task.task.level:
            task_data = {
                "id": completed_task.id,
                "user_id": completed_task.user_id,
                "task_id": completed_task.task_id,
                "video_url": completed_task.video_url,
                "completed_at": completed_task.completed_at,
                "reward": completed_task.task.reward,
                "level_name": completed_task.task.level.name  # Include level name
            }
            completed_tasks_with_reward_and_level.append(task_data)

    return completed_tasks_with_reward_and_level

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
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(UserTask.user_id == current_user.id, UserTask.id == request.user_task_id)
    )
    user_task = result.scalar_one_or_none()
    if not user_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user_task.completed:
        raise HTTPException(status_code=400, detail="Task already completed")
    if user_task.locked:
        raise HTTPException(status_code=403, detail="Task is locked and cannot be completed")

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
                select(UserTaskPending)
                .options(joinedload(UserTaskPending.task).joinedload(Task.level))
                .filter(
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
                task = pending.task
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

    return {
        "id": user_task.id,
        "user_id": user_task.user_id,
        "task_id": user_task.task_id,
        "video_url": user_task.video_url,
        "completed": user_task.completed,
        "locked": user_task.locked,
        "reward": user_task.task.reward,
        "description": user_task.description,
        "level_name": user_task.task.level.name  # Include level name
    }

# -------------------------
# ADMIN: Lock a user task
# -------------------------
@router.patch("/{user_task_id}/lock", response_model=UserTaskResponse)
async def lock_user_task(
    user_task_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(UserTask.id == user_task_id)
    )
    user_task = result.scalar_one_or_none()
    if not user_task:
        raise HTTPException(status_code=404, detail="User task not found")

    user_task.locked = True
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)

    return {
        "id": user_task.id,
        "user_id": user_task.user_id,
        "task_id": user_task.task_id,
        "video_url": user_task.video_url,
        "completed": user_task.completed,
        "locked": user_task.locked,
        "reward": user_task.task.reward,
        "description": user_task.description,
        "level_name": user_task.task.level.name  # Include level name
    }

# -------------------------
# ADMIN: Unlock a user task
# -------------------------
@router.patch("/{user_task_id}/unlock", response_model=UserTaskResponse)
async def unlock_user_task(
    user_task_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(UserTask)
        .options(joinedload(UserTask.task).joinedload(Task.level))
        .filter(UserTask.id == user_task_id)
    )
    user_task = result.scalar_one_or_none()
    if not user_task:
        raise HTTPException(status_code=404, detail="User task not found")

    user_task.locked = False
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)

    return {
        "id": user_task.id,
        "user_id": user_task.user_id,
        "task_id": user_task.task_id,
        "video_url": user_task.video_url,
        "completed": user_task.completed,
        "locked": user_task.locked,
        "reward": user_task.task.reward,
        "description": user_task.description,
        "level_name": user_task.task.level.name  # Include level name
    }



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