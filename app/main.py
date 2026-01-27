from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth,deposit,withdrawal

app = FastAPI()

# ----------------------------
# CORS Middleware (updated)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ only for testing!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Include Routers
# ----------------------------
app.include_router(auth.router)
app.include_router(deposit.router)
app.include_router(withdrawal.router)



@app.get("/")
async def root():
    return {"message": "Api is running!"}

