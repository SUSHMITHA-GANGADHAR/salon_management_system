import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

print("Checking Services...")
male = supabase.table('services').select('*').eq('gender', 'male').execute()
female = supabase.table('services').select('*').eq('gender', 'female').execute()

print(f"Male services found: {len(male.data)}")
print(f"Female services found: {len(female.data)}")

if len(male.data) == 0 and len(female.data) == 0:
    print("WARNING: No services found in database! Seeding defaults...")
    services = [
        {'name': 'Classic Haircut', 'price': 350, 'gender': 'male', 'duration': 30, 'description': 'Standard haircut'},
        {'name': 'Beard Grooming', 'price': 200, 'gender': 'male', 'duration': 20, 'description': 'Trim and shape'},
        {'name': 'Signature Facial', 'price': 800, 'gender': 'female', 'duration': 60, 'description': 'Luxury facial'},
        {'name': 'Hair Styling', 'price': 500, 'gender': 'female', 'duration': 45, 'description': 'Wash and style'}
    ]
    supabase.table('services').insert(services).execute()
    print("Seed complete.")
else:
    print("Services table is healthy.")
