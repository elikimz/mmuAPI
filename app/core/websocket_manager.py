
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # Map user_id to a list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            data = json.dumps(message)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(data)
                except Exception:
                    # Connection might be closed, we'll clean up on disconnect
                    pass

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(data)
                except Exception:
                    pass

manager = ConnectionManager()
