# Salon Pro: Advanced Management System

A production-ready Salon Management System with role-based dashboards (Customer, Staff, Admin), ₹50 deposit booking model, and real-time business intelligence.

## 🚀 Deployment to Render

This project is configured for one-click deployment to **Render**.

### 1. Prerequisites
- A **Supabase** account (for Postgres DB and Auth)
- A **Razorpay** account (for payment gateway)
- A **GitHub** account

### 2. Environment Variables
Add the following keys in your Render Dashboard:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase `anon` or `service_role` key
- `RAZOR_KEY_ID`: Your Razorpay API Key ID
- `RAZOR_KEY_SECRET`: Your Razorpay API Key Secret
- `SECRET_KEY`: Any long random string (for Flask sessions)

### 3. Build & Start Commands
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

## 🛠️ Database Setup
Run the `database.sql` script in your Supabase SQL Editor to initialize the necessary tables and tracking columns.

## ✨ Features
- **Gender-Based Portals:** Automatic UI themes (Dark/Noir for Men, Orchid/Gold for Women).
- **Collision Prevention:** Blocks double-booking the same specialist at the same time.
- **Reports & Analysis:** Real-time revenue charts and customer statistics for owners.
- **Deposit System:** Mandatory ₹50 advance to secure slots.
