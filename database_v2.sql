-- Salon Pro: Database Initialization Script
-- Use this script in the Supabase SQL Editor

-- 1. Users Table (Updated with blocking logic)
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'customer',
    cancellation_count INT DEFAULT 0,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Services Table
CREATE TABLE IF NOT EXISTS services (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    duration INT NOT NULL,
    gender VARCHAR(50) NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Appointments Table (Updated for cancellation tracking)
CREATE TABLE IF NOT EXISTS appointments (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_id BIGINT NOT NULL REFERENCES services(id),
    date DATE NOT NULL,
    time VARCHAR(5) NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed', -- confirmed, cancelled
    cancellation_reason TEXT,
    payment_id VARCHAR(255),
    order_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(service_id, date, time)
);

-- 4. Initial Seed Data
INSERT INTO services (name, description, price, duration, gender, image_url) VALUES
('Classic Fade & Cut', 'Masterful clippers and scissors work for a sharp look.', 30.00, 30, 'male', '/static/images/male-service.png'),
('Premium Beard Sculpting', 'Hot towel treatment and precision beard shaping.', 25.00, 20, 'male', '/static/images/male-service.png'),
('Executive Facial', 'Deep pore cleansing and hydration for men.', 45.00, 40, 'male', '/static/images/spa.png'),
('Glamour Blowout', 'Professional wash, dry, and elegant styling.', 50.00, 45, 'female', '/static/images/female-service.png'),
('Bridal Makeup Artistry', 'Complete professional makeover for your special day.', 75.00, 60, 'female', '/static/images/female-service.png'),
('Zen Stone Therapy', 'Relaxing full-body massage with heated volcanic stones.', 80.00, 60, 'female', '/static/images/spa.png');

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