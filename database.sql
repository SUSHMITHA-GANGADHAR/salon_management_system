-- Salon Pro: Advanced Database Schema v2

-- 1. Business Settings Table
CREATE TABLE IF NOT EXISTS salon_settings (
    id INT PRIMARY KEY DEFAULT 1,
    name VARCHAR(255) DEFAULT 'Salon Pro',
    address TEXT DEFAULT '123 Luxury Lane, Beauty City',
    contact VARCHAR(20) DEFAULT '+91 98765 43210',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT solo_row CHECK (id = 1)
);

-- Seed defaults
INSERT INTO salon_settings (id, name, address) 
VALUES (1, 'Salon Pro', '123 Luxury Lane, Beauty City') 
ON CONFLICT (id) DO NOTHING;

-- 2. Modified Appointments Table (Collision Prevention)
-- We need to track which STAFF is assigned to a booking.
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS staff_id BIGINT REFERENCES users(id);

-- Drop old unique constraint and add staff collision preventer
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_service_id_date_time_key;
ALTER TABLE appointments ADD CONSTRAINT staff_time_unique UNIQUE(staff_id, date, time);

-- 3. Payment & Cancellation Tracking
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS balance_paid BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS payment_amount DECIMAL(10, 2) DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS payment_id TEXT,
    ADD COLUMN IF NOT EXISTS order_id TEXT,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

-- 4. User Reputation tracking
ALTER TABLE users ADD COLUMN IF NOT EXISTS cancellation_count INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;