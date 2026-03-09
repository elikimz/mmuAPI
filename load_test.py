
import asyncio
import time
import httpx
import random
import string
from app.core.jwt import hash_password
from app.database.database import AsyncSessionLocal
from app.models.models import User, Wallet

async def create_test_users(count=100):
    users = []
    async with AsyncSessionLocal() as session:
        for i in range(count):
            number = f"+2547{random.randint(10000000, 99999999)}"
            user = User(
                number=number,
                country_code="+254",
                password=hash_password("password"),
                referral_code=f"LOAD_{i}_{''.join(random.choices(string.ascii_uppercase, k=5))}",
                is_admin=False
            )
            session.add(user)
            await session.flush()
            wallet = Wallet(user_id=user.id, balance=1000.0, income=0.0)
            session.add(wallet)
            users.append({"number": number, "password": "password"})
        await session.commit()
    return users

async def simulate_user_action(client, user_info):
    # 1. Login
    start = time.time()
    login_res = await client.post("/auth/login", data={"username": user_info["number"], "password": user_info["password"]})
    login_time = (time.time() - start) * 1000
    
    if login_res.status_code != 200:
        print(f"Login failed for {user_info['number']}: {login_res.status_code} {login_res.text}")
        return {"action": "login", "time": login_time, "success": False}
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get Profile (First time - No Cache)
    await client.get("/users/profile", headers=headers)
    
    # 3. Get Profile (Second time - Should be cached)
    start = time.time()
    profile_res = await client.get("/users/profile", headers=headers)
    profile_time = (time.time() - start) * 1000
    
    return {"action": "profile_cached", "time": profile_time, "success": profile_res.status_code == 200}

async def run_load_test(user_count=50):
    print(f"Starting load test with {user_count} concurrent users...")
    users = await create_test_users(user_count)
    
    from app.main import app
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [simulate_user_action(client, user) for user in users]
        results = await asyncio.gather(*tasks)
    
    # Analysis
    login_times = [r["time"] for r in results if r["action"] == "login" and r["success"]]
    profile_times = [r["time"] for r in results if r["action"] == "profile_cached" and r["success"]]
    
    print("\n--- Load Test Results ---")
    print(f"Total Users: {user_count}")
    if profile_times:
        print(f"Cached Profile Avg Time: {sum(profile_times)/len(profile_times):.2f}ms")
    else:
        print("Cached Profile Avg Time: N/A")
    print(f"Profile Max Time: {max(profile_times):.2f}ms")
    print(f"Profile Min Time: {min(profile_times):.2f}ms")
    
    success_rate = len([r for r in results if r["success"]]) / (user_count * 2) * 100
    print(f"Success Rate: {success_rate:.2f}%")

if __name__ == "__main__":
    asyncio.run(run_load_test(50))
