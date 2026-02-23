from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"URL: {supabase_url}")
print(f"Key exists: {supabase_key is not None}")
print(f"Key length: {len(supabase_key) if supabase_key else 0}")

print("Attempting connection...")
supabase = create_client(supabase_url, supabase_key)
print("✓ Connected!")

# Try a simple query
result = supabase.table("documents").select("count").execute()
print(f"Documents in database: {result}")