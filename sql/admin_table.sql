-- =============================================================
-- Admin users table for the crypto admin dashboard
-- Run this in your Supabase SQL editor, or just run:
--   cd backend && python seed_admin.py
-- which creates the table AND seeds the default admin user.
-- =============================================================

CREATE TABLE IF NOT EXISTS admins (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- NOTE: Do NOT insert the admin row via raw SQL.
-- The password must be hashed by Python (werkzeug).
-- Run the seeder instead:
--   cd backend && python seed_admin.py
