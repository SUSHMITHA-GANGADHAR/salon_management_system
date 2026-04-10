import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

print(f"URL: {url}")
# key check (hidden)
print(f"Key exists: {bool(key)}")

try:
    supabase = create_client(url, key)
    res = supabase.table('users').select('count', count='exact').execute()
    print("SUCCESS: Connected to 'users' table.")
    print(f"User count: {res.count}")
except Exception as e:
    print(f"FAILURE: {e}")
