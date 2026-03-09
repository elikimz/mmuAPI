
import asyncio
import time
from httpx import AsyncClient, ASGITransport
from app.main import app

async def single_request(client):
    start = time.perf_counter()
    try:
        response = await client.get("/")
        end = time.perf_counter()
        return end - start, response.status_code
    except Exception as e:
        return None, str(e)

async def run_perf_test(concurrent_requests=50):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [single_request(client) for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        latencies = [r[0] for r in results if r[0] is not None]
        status_codes = [r[1] for r in results]
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            print(f"Concurrent Requests: {concurrent_requests}")
            print(f"Average Latency: {avg_latency:.4f}s")
            print(f"Max Latency: {max_latency:.4f}s")
            print(f"Min Latency: {min_latency:.4f}s")
            print(f"Status Codes: {set(status_codes)}")
        else:
            print("All requests failed.")

if __name__ == "__main__":
    asyncio.run(run_perf_test())
