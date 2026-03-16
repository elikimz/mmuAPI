"""
Comprehensive API QA Test Suite for MMU API
Tests all major endpoints end-to-end using correct routes
"""
import requests
import json
import sys
import random
import string

BASE_URL = "http://localhost:8000"
RESULTS = []

def log(status, endpoint, detail=""):
    icon = "✅" if status == "PASS" else "❌"
    msg = f"{icon} [{status}] {endpoint}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    RESULTS.append({"status": status, "endpoint": endpoint, "detail": detail})

def test(name, method, path, expected_status, token=None, json_body=None, form_data=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            if form_data:
                r = requests.post(url, data=form_data, headers=headers, timeout=10)
            else:
                r = requests.post(url, json=json_body, headers=headers, timeout=10)
        elif method == "PATCH":
            r = requests.patch(url, json=json_body, headers=headers, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=10)
        else:
            log("FAIL", name, "Unknown method")
            return None

        if r.status_code == expected_status:
            log("PASS", name, f"HTTP {r.status_code}")
        else:
            log("FAIL", name, f"Expected {expected_status}, got {r.status_code}: {r.text[:300]}")
        return r
    except Exception as e:
        log("FAIL", name, f"Exception: {e}")
        return None

print("=" * 60)
print("MMU API — Comprehensive QA Test Suite")
print("=" * 60)

# ─── 1. Root ───────────────────────────────────────────────
print("\n[1] Root Endpoint")
test("GET /", "GET", "/", 200)

# ─── 2. Public Levels ──────────────────────────────────────
print("\n[2] Public Levels")
r_levels = test("GET /levels/", "GET", "/levels/", 200)
levels = []
if r_levels and r_levels.status_code == 200:
    levels = r_levels.json()
    print(f"    Found {len(levels)} levels: {[l['name'] for l in levels]}")

# ─── 3. Public News ────────────────────────────────────────
print("\n[3] Public News")
test("GET /news/", "GET", "/news/", 200)

# ─── 4. Public Wealth Funds ────────────────────────────────
print("\n[4] Public Wealth Funds")
test("GET /wealthfunds/", "GET", "/wealthfunds/", 200)

# ─── 5. Public App Contacts ────────────────────────────────
print("\n[5] Public App Contacts")
test("GET /app-contacts/", "GET", "/app-contacts/", 200)

# ─── 6. Public Tasks by Level ──────────────────────────────
print("\n[6] Public Tasks by Level")
if levels:
    level_id = levels[0]["id"]
    test(f"GET /tasks/level/{level_id}", "GET", f"/tasks/level/{level_id}", 200)

# ─── 7. Auth — Register ────────────────────────────────────
print("\n[7] Auth — Register")
rand_suffix = ''.join(random.choices(string.digits, k=6))
test_number = f"07{rand_suffix}"
test_password = "TestPass123!"

r_reg = test("POST /auth/register", "POST", "/auth/register", 201, json_body={
    "number": test_number,
    "country_code": "+254",
    "password": test_password,
    "referral_code": None
})

# ─── 8. Auth — Register Duplicate ──────────────────────────
print("\n[8] Auth — Register Duplicate (should 400)")
test("POST /auth/register (duplicate)", "POST", "/auth/register", 400, json_body={
    "number": test_number,
    "country_code": "+254",
    "password": test_password,
    "referral_code": None
})

# ─── 9. Auth — Login ───────────────────────────────────────
print("\n[9] Auth — Login")
r_login = test("POST /auth/login", "POST", "/auth/login", 200, form_data={
    "username": f"+254{test_number}",
    "password": test_password
})

token = None
if r_login and r_login.status_code == 200:
    token = r_login.json().get("access_token")
    print(f"    Token obtained: {token[:30]}...")

# ─── 10. Auth — Invalid Login ──────────────────────────────
print("\n[10] Auth — Invalid Login (wrong password)")
test("POST /auth/login (wrong pw)", "POST", "/auth/login", 401, form_data={
    "username": f"+254{test_number}",
    "password": "WrongPassword"
})

# ─── 11. Auth — Validation Error ───────────────────────────
print("\n[11] Auth — Validation Error (missing fields)")
test("POST /auth/register (missing fields)", "POST", "/auth/register", 422, json_body={"number": "0712345678"})

# ─── 12. Users — Get Me ────────────────────────────────────
print("\n[12] Users — Get Me")
test("GET /users/me", "GET", "/users/me", 200, token=token)
test("GET /users/me (no token)", "GET", "/users/me", 401)

# ─── 13. Auth — Get Me ─────────────────────────────────────
print("\n[13] Auth — Get Me")
test("GET /auth/me", "GET", "/auth/me", 200, token=token)
test("GET /auth/me (no token)", "GET", "/auth/me", 401)

# ─── 14. User Profile ──────────────────────────────────────
print("\n[14] User Profile")
test("GET /users/profile", "GET", "/users/profile", 200, token=token)
test("GET /users/profile (no token)", "GET", "/users/profile", 401)

# ─── 15. Countdown ─────────────────────────────────────────
print("\n[15] Countdown")
r_cd = test("GET /countdown/me", "GET", "/countdown/me", 200, token=token)
if r_cd and r_cd.status_code == 200:
    cd = r_cd.json()
    print(f"    task_reset_seconds={cd.get('task_reset_seconds')}, has_expiry={cd.get('has_expiry')}")
test("GET /countdown/me (no token)", "GET", "/countdown/me", 401)

# ─── 16. Earnings ──────────────────────────────────────────
print("\n[16] Earnings")
test("GET /earnings/overview", "GET", "/earnings/overview", 200, token=token)
test("GET /earnings/overview (no token)", "GET", "/earnings/overview", 401)

# ─── 17. User Tasks ────────────────────────────────────────
print("\n[17] User Tasks")
test("GET /user-tasks/me", "GET", "/user-tasks/me", 200, token=token)
test("GET /user-tasks/me/pending", "GET", "/user-tasks/me/pending", 200, token=token)
test("GET /user-tasks/me/completed", "GET", "/user-tasks/me/completed", 200, token=token)
test("GET /user-tasks/me (no token)", "GET", "/user-tasks/me", 401)

# ─── 18. User Levels ───────────────────────────────────────
print("\n[18] User Levels")
test("GET /user-levels/me", "GET", "/user-levels/me", 200, token=token)
test("GET /user-levels/me (no token)", "GET", "/user-levels/me", 401)

# ─── 19. Deposits ──────────────────────────────────────────
print("\n[19] Deposits")
test("GET /deposits/me", "GET", "/deposits/me", 200, token=token)
test("GET /deposits/me (no token)", "GET", "/deposits/me", 401)

# ─── 20. Withdrawals ───────────────────────────────────────
print("\n[20] Withdrawals")
test("GET /withdrawals/me", "GET", "/withdrawals/me", 200, token=token)
test("GET /withdrawals/me (no token)", "GET", "/withdrawals/me", 401)

# ─── 21. Referrals ─────────────────────────────────────────
print("\n[21] Referrals")
test("GET /referrals/me", "GET", "/referrals/me", 200, token=token)
test("GET /referrals/me (no token)", "GET", "/referrals/me", 401)

# ─── 22. Spin Wheel ────────────────────────────────────────
print("\n[22] Spin Wheel")
test("GET /spin/user/rewards", "GET", "/spin/user/rewards", 200, token=token)
test("GET /spin/user/history", "GET", "/spin/user/history", 200, token=token)
test("GET /spin/user/rewards (no token)", "GET", "/spin/user/rewards", 401)

# ─── 23. Gift Codes ────────────────────────────────────────
print("\n[23] Gift Codes")
test("GET /gift-codes/my-history/", "GET", "/gift-codes/my-history/", 200, token=token)
test("POST /gift-codes/redeem/ (no level = 403)", "POST", "/gift-codes/redeem/", 403, token=token, json_body={"code": "INVALID_CODE_XYZ"})
test("GET /gift-codes/my-history/ (no token)", "GET", "/gift-codes/my-history/", 401)

# ─── 24. User Wealth Funds ─────────────────────────────────
print("\n[24] User Wealth Funds")
test("GET /user-wealthfunds/", "GET", "/user-wealthfunds/", 200, token=token)
test("GET /user-wealthfunds/ (no token)", "GET", "/user-wealthfunds/", 401)

# ─── 25. Admin Endpoints — Unauthorized ────────────────────
print("\n[25] Admin Endpoints — Unauthorized Access")
test("GET /tasks/ (no admin)", "GET", "/tasks/", 401)
test("POST /levels/ (no admin)", "POST", "/levels/", 401, json_body={"name": "test"})
test("GET /deposits/ (no admin)", "GET", "/deposits/", 401)
test("GET /withdrawals/ (no admin)", "GET", "/withdrawals/", 401)
test("GET /auth/admin/users (no admin)", "GET", "/auth/admin/users", 401)
test("GET /user-tasks/admin/all (no admin)", "GET", "/user-tasks/admin/all", 401)

# ─── Summary ───────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for r in RESULTS if r["status"] == "PASS")
failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
print(f"RESULTS: {passed} PASSED, {failed} FAILED out of {len(RESULTS)} tests")
print("=" * 60)

if failed > 0:
    print("\nFailed Tests:")
    for r in RESULTS:
        if r["status"] == "FAIL":
            print(f"  ❌ {r['endpoint']}: {r['detail']}")

sys.exit(0 if failed == 0 else 1)
