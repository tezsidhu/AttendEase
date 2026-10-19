
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load the .env file from this project's folder
load_dotenv(Path(__file__).resolve().parent / ".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_PUBLISHABLE_KEY")

if not url or not key:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY in .env"
    )

supabase = create_client(url, key)

try:
    result = supabase.table("subjects").select("id").limit(1).execute()
    print("Supabase connection successful!")
    print("Subjects table is accessible.")
except Exception as error:
    print("Connection test failed.")
    print(type(error).__name__, str(error))
