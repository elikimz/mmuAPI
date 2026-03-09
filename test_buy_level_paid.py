
import asyncio
import random
import string
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.database import engine, AsyncSessionLocal
from app.models.models import User, Wallet, Level, UserLevel, Transaction, Task
from app.core.jwt import hash_password
from sqlalchemy import select, delete, text

async def setup_test_data(level_id):
    async with AsyncSessionLocal() as session:
        # 1. Get the specific level
        result = await session.execute(select(Level).filter(Level.id == level_id))
        level = result.scalar_one_or_none()
        if not level:
            print(f"Level {level_id} not found!")
            return None, None, None
        
        # 2. Create a test user with enough balance
        random_suffix = "".join(random.choices(string.digits, k=8))
        number = f"+2547{random_suffix}"
        user = User(
            number=number,
            country_code="+254",
            password=hash_password("testpassword"),
            referral_code="TESTREF" + random_suffix,
            is_admin=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Give user enough balance to buy the level
        wallet = Wallet(user_id=user.id, balance=level.earnest_money + 100.0, income=0.0)
        session.add(wallet)
        await session.commit()
        
        return user, level, "testpassword"

async def test_buy_level(level_id):
    user, level, password = await setup_test_data(level_id)
    if not user: return
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login to get token
        login_data = {"username": user.number, "password": password}
        login_res = await ac.post("/auth/login", data=login_data)
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"User {user.number} (ID: {user.id}) attempting to buy Level {level.name} (ID: {level.id}) for {level.earnest_money}")
        
        # 2. Buy Level
        buy_data = {"level_id": level.id}
        buy_res = await ac.post("/user-levels/buy", json=buy_data, headers=headers)
        
        print(f"Response Status: {buy_res.status_code}")
        print(f"Response Body: {buy_res.text}")
        
        if buy_res.status_code == 200:
            print("✅ Purchase successful via API")
            # Verify DB state
            async with AsyncSessionLocal() as session:
                # Check wallet
                wallet_res = await session.execute(select(Wallet).filter(Wallet.user_id == user.id))
                wallet = wallet_res.scalar_one()
                print(f"New Wallet Balance: {wallet.balance}")
                assert wallet.balance == 100.0 # Started with level.earnest_money + 100
                
                # Check UserLevel
                user_level_res = await session.execute(select(UserLevel).filter(UserLevel.user_id == user.id))
                user_level = user_level_res.scalar_one_or_none()
                assert user_level is not None
                assert user_level.level_id == level.id
                print("✅ Database state verified")
        else:
            print(f"❌ Purchase failed: {buy_res.text}")

if __name__ == "__main__":
    # Using level_id 17 from previous check
    asyncio.run(test_buy_level(17))
