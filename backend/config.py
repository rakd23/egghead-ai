"""
Centralized configuration for Egghead AI backend.
Loads environment variables and defines constants used across modules.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- External API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
UCD_DIRECTORY_API_KEY = os.getenv("UCD_DIRECTORY_API_KEY", "")

# --- Server ---
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_URL", "https://egghead-ai-tau.vercel.app"),
]

# --- Vector Search ---
SIMILARITY_THRESHOLD = 0.72          # minimum cosine similarity to include a result
MAX_VECTOR_RESULTS = 8               # candidates pulled from Supabase
TOP_K_RESULTS = 5                    # returned to the user after ranking

# --- Cache ---
CACHE_TTL_SECONDS = 300              # 5 minutes
CACHE_MAX_SIZE = 256                 # max entries before LRU eviction

# --- Rate Limiting ---
RATE_LIMIT_REQUESTS = 30             # requests per window
RATE_LIMIT_WINDOW_SECONDS = 60       # 1-minute window

# --- LLM ---
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 300                 # keep summaries concise

# --- UC Davis ---
UC_DAVIS_COORDS = (38.5382, -121.7617)
UC_DAVIS_SEARCH_RADIUS = 3000       # meters
