
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.core.websocket_manager import manager
from app.core.jwt import decode_access_token
from app.database.database import get_async_db
from app.models.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/ws", tags=["WebSocket"])

async def get_user_from_token(token: str, db: AsyncSession):
    payload = decode_access_token(token)
    if not payload:
        return None
    number = payload.get("sub")
    if not number:
        return None
    result = await db.execute(select(User).filter(User.number == number))
    return result.scalar_one_or_none()

@router.websocket("/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Use a fresh DB session for authentication
    from app.database.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4003) # Unauthorized
            return

        await manager.connect(user.id, websocket)
        try:
            while True:
                # We don't expect messages from the client for now,
                # but we need to keep the connection open and handle disconnects.
                data = await websocket.receive_text()
                # Optional: Handle pings or simple client-side commands
        except WebSocketDisconnect:
            manager.disconnect(user.id, websocket)
