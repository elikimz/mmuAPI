"""
Direct migration script to add missing columns to the database.
Bypasses alembic to avoid transaction issues.
"""
import asyncio
import asyncpg
import ssl

DATABASE_URL = "postgresql://neondb_owner:npg_cqkpDM1T7njo@ep-patient-bonus-aic9tbh4-pooler.c-4.us-east-1.aws.neon.tech/neondb"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

async def apply_migration():
    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_ctx)
    try:
        # Check existing columns in levels
        levels_cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='levels'"
        )
        levels_col_names = [r['column_name'] for r in levels_cols]
        print(f"Existing levels columns: {levels_col_names}")

        # Check existing columns in user_levels
        ul_cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='user_levels'"
        )
        ul_col_names = [r['column_name'] for r in ul_cols]
        print(f"Existing user_levels columns: {ul_col_names}")

        # Add expiry_days to levels if missing
        if 'expiry_days' not in levels_col_names:
            await conn.execute("ALTER TABLE levels ADD COLUMN expiry_days INTEGER")
            print("✅ Added expiry_days to levels")
        else:
            print("ℹ️  expiry_days already exists in levels")

        # Add expires_at to user_levels if missing
        if 'expires_at' not in ul_col_names:
            await conn.execute("ALTER TABLE user_levels ADD COLUMN expires_at TIMESTAMP")
            print("✅ Added expires_at to user_levels")
        else:
            print("ℹ️  expires_at already exists in user_levels")

        # Add created_at to user_levels if missing
        if 'created_at' not in ul_col_names:
            await conn.execute("ALTER TABLE user_levels ADD COLUMN created_at TIMESTAMP DEFAULT NOW()")
            print("✅ Added created_at to user_levels")
        else:
            print("ℹ️  created_at already exists in user_levels")

        # Update alembic_version to reflect the migration
        current = await conn.fetchval("SELECT version_num FROM alembic_version")
        print(f"Current alembic version: {current}")
        if current == '3835e37d22e8':
            await conn.execute(
                "UPDATE alembic_version SET version_num='a1b2c3d4e5f6' WHERE version_num='3835e37d22e8'"
            )
            print("✅ Updated alembic_version to a1b2c3d4e5f6")

        print("\n✅ Migration complete!")
    finally:
        await conn.close()

asyncio.run(apply_migration())
