-- Migration: Add last_interest_update column to user_wealthfunds
-- Purpose: Track when daily interest was last accrued for each fund
--          to prevent duplicate accruals when the scheduler runs
--          more frequently than once per day.
-- Date: 2026-03-18
-- Run this against your production PostgreSQL database.

-- Step 1: Add the column (nullable, no default — existing rows get NULL)
ALTER TABLE user_wealthfunds
ADD COLUMN IF NOT EXISTS last_interest_update TIMESTAMP WITHOUT TIME ZONE;

-- Step 2: Back-fill existing active funds so the scheduler doesn't
--         re-accrue interest for days that were already processed.
--         We set last_interest_update = start_date + (total_profit / daily_gain_per_day) days
--         but a simpler safe approach: set it to NOW() for any fund that already has profit.
UPDATE user_wealthfunds
SET last_interest_update = NOW()
WHERE status = 'active'
  AND total_profit > 0
  AND last_interest_update IS NULL;

-- For active funds with zero profit (just created), leave NULL.
-- The scheduler will use start_date as the fallback and accrue
-- once 24 hours have passed since start_date.
