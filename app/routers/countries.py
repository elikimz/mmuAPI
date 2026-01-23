# # routers/countries.py
# from fastapi import APIRouter
# import httpx

# router = APIRouter(prefix="/countries", tags=["Countries"])

# RESTCOUNTRIES_URL = "https://restcountries.com/v3.1/all?fields=name,idd,cca2"

# # Convert ISO country code to emoji flag
# def country_code_to_emoji(country_code: str):
#     OFFSET = 127397
#     return "".join([chr(ord(c) + OFFSET) for c in country_code.upper()])

# @router.get("/")
# async def get_countries():
#     async with httpx.AsyncClient() as client:
#         res = await client.get(RESTCOUNTRIES_URL)
#         data = res.json()

#     countries = []
#     for country in data:
#         name = country.get("name", {}).get("common")
#         idd = country.get("idd", {})
#         root = idd.get("root", "")
#         suffixes = idd.get("suffixes", [""])
#         iso = country.get("cca2", "")
#         flag = country_code_to_emoji(iso)

#         for suffix in suffixes:
#             code = f"{root}{suffix}"
#             countries.append({
#                 "name": name,
#                 "code": code,
#                 "flag": flag
#             })

#     # Sort alphabetically by name
#     countries.sort(key=lambda x: x["name"])
#     return countries


# routers/countries.py
from fastapi import APIRouter
import httpx
import asyncio
from datetime import datetime, timedelta

router = APIRouter(prefix="/countries", tags=["Countries"])

RESTCOUNTRIES_URL = "https://restcountries.com/v3.1/all?fields=name,idd,cca2"

# Convert ISO country code to emoji flag
def country_code_to_emoji(country_code: str):
    OFFSET = 127397
    return "".join([chr(ord(c) + OFFSET) for c in country_code.upper()])

# --- Simple cache ---
COUNTRIES_CACHE = None
CACHE_TIMESTAMP = None
CACHE_DURATION = timedelta(hours=24)  # refresh once per day

@router.get("/")
async def get_countries():
    global COUNTRIES_CACHE, CACHE_TIMESTAMP

    # Check if cache exists and is still valid
    if COUNTRIES_CACHE and CACHE_TIMESTAMP and datetime.utcnow() - CACHE_TIMESTAMP < CACHE_DURATION:
        return COUNTRIES_CACHE

    # Fetch from REST Countries
    async with httpx.AsyncClient() as client:
        res = await client.get(RESTCOUNTRIES_URL)
        data = res.json()

    countries = []
    for country in data:
        name = country.get("name", {}).get("common")
        idd = country.get("idd", {})
        root = idd.get("root", "")
        suffixes = idd.get("suffixes", [""])
        iso = country.get("cca2", "")
        flag = country_code_to_emoji(iso)

        for suffix in suffixes:
            code = f"{root}{suffix}"
            countries.append({
                "name": name,
                "code": code,
                "flag": flag
            })

    countries.sort(key=lambda x: x["name"])

    # Save to cache
    COUNTRIES_CACHE = countries
    CACHE_TIMESTAMP = datetime.utcnow()

    return countries
