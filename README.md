# 🥚 Egghead AI

A semantic search and campus assistant platform for UC Davis students. Ask questions in plain English and get structured, source-attributed answers pulled from course reviews, Reddit discussions, campus resources, and more.

> **Note:** The live deployment has been taken offline. The app was hosted on Vercel (frontend) and Render (backend) and served **100+ students** in its first week before being sunset due to API costs.

---

## Architecture

```
User Query
     │
     ▼
┌─────────────────────────────┐
│   Next.js Frontend          │
│   (TypeScript, Tailwind)    │
│   ┌───────────────────────┐ │
│   │ /api/chat (BFF proxy) │ │
│   └──────────┬────────────┘ │
└──────────────┼──────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│   FastAPI Backend                                │
│                                                  │
│   1. Rate Limiter (per-IP sliding window)        │
│   2. Cache Lookup (TTL + LRU)                    │
│   3. Query Classifier (weighted keyword/regex)   │
│   4. Source Dispatcher ─┬── Vector DB (Supabase) │
│                         ├── RateMyProfessor       │
│                         ├── UC Davis Directory API│
│                         ├── Reddit (r/UCDavis)    │
│                         ├── Web Search (DDG)      │
│                         ├── Google Maps           │
│                         └── Curated Resources     │
│   5. Result Ranker (source-weighted scoring)     │
│   6. Response Builder (LLM summary only)         │
│   7. Cache Store + Analytics                     │
└──────────────────────────────────────────────────┘
               │
               ▼
       Structured JSON Response
       ├── intent classification
       ├── ranked sources with scores
       ├── professor card (if applicable)
       ├── directory contact cards (if applicable)
       ├── campus resource links
       ├── LLM-generated summary paragraph
       └── metadata (cache hit, response time)
```

---

## How It Works

### Query Classification

When a student submits a query, it's first classified into one of seven intent categories — `professor`, `course`, `housing`, `dining`, `campus_resource`, `location`, or `general` — using a weighted keyword matcher with regex pattern bonuses (e.g., detecting course codes like "ECS 36A" or professor names). This classification is deterministic and runs in ~0.1ms with no LLM involvement.

### Intent-Based Source Routing

Based on the classified intent, the backend dispatches to different combinations of data sources concurrently:

- **Professor queries** → Vector DB + RateMyProfessor scraper + UC Davis Directory API + Reddit
- **Course queries** → Vector DB + Reddit + Web search
- **Housing queries** → Vector DB + Reddit + Web search
- **Dining queries** → Vector DB + Google Maps + Reddit
- **Location queries** → Vector DB + Google Maps
- **Campus resource queries** → Vector DB + Web search + Curated resource matcher

### Result Ranking

Retrieved results are scored using source-type weight multipliers that vary by intent. For example, RateMyProfessor results get a 1.5x boost for professor queries, while Reddit results get a 1.4x boost for housing queries. Results are then deduplicated using sequence matching and returned as the top-K ranked list.

### Response Generation

The LLM (GPT-4o-mini) is used **only** to generate a short summary paragraph from the already-ranked context. All structured data — professor cards, source attributions with relevance scores, campus resource links — comes directly from the pipeline, not from the LLM. If the LLM fails, a fallback summary is constructed from the structured data.

### Caching

An in-memory TTL cache with LRU eviction stores complete responses keyed by normalized queries. Identical queries within the TTL window return instantly without hitting any external APIs.

---

## Features

- **Semantic search** over 59 scraped UC Davis data files (housing, dining, academics, health services, etc.) via OpenAI embeddings + Supabase vector store
- **RateMyProfessor integration** — structured professor cards with rating, difficulty, take-again %, and review count
- **UC Davis Directory API integration** — official contact info (email, phone, office, department, title) for faculty and staff via the IET Directory Search REST API
- **Reddit context** — relevant r/UCDavis discussions surfaced and ranked
- **Campus resource matching** — curated links to SHCS, AATC, Career Center, Pantry, etc. matched by keyword relevance
- **Image upload + OCR** — upload a course schedule screenshot and ask questions about it (GPT-4o-mini vision)
- **Source attribution** — every response shows where information came from, with relevance scores and direct links
- **Per-IP rate limiting** — sliding window rate limiter on the chat endpoint
- **Query caching** — TTL + LRU cache to reduce latency and API costs
- **Analytics endpoint** — `/analytics` returns query counts by intent, cache hit rates, and average response times
- **Auth0 integration** — Google OAuth restricted to @ucdavis.edu emails
- **Conversation history** — multi-turn conversations persisted in localStorage

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | Python 3, FastAPI, Pydantic v2 |
| Embeddings | OpenAI Embeddings API |
| Vector Store | Supabase (pgvector) |
| LLM | GPT-4o-mini (summary generation only) |
| Data Sources | RateMyProfessor, r/UCDavis (via DuckDuckGo), Google Maps API, UC Davis IET Directory API |
| Auth | Auth0 (Google OAuth, @ucdavis.edu restriction) |
| Deployment | Vercel (frontend), Render (backend) |

---

## Repo Structure

```
egghead-ai/
├── README.md
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Auth gate → Chat
│   │   ├── chat.tsx              # Main chat UI with structured rendering
│   │   ├── types.ts              # Shared TypeScript types
│   │   ├── layout.tsx            # Root layout
│   │   ├── globals.css           # Tailwind imports
│   │   ├── guard.tsx             # Auth helper
│   │   ├── login/page.tsx        # Login page
│   │   └── api/chat/route.ts     # BFF proxy to FastAPI
│   ├── lib/auth0.ts              # Auth0 client config
│   └── package.json
│
└── backend/
    ├── main.py                   # FastAPI app, routes, pipeline orchestrator
    ├── config.py                 # Environment variables and constants
    ├── models.py                 # Pydantic request/response schemas
    ├── classifier.py             # Query intent classification
    ├── ranker.py                 # Result ranking and deduplication
    ├── sources.py                # Data source retrieval (vector, RMP, Reddit, web, maps)
    ├── resources.py              # Curated UC Davis resource matcher
    ├── response_builder.py       # LLM summary generation
    ├── cache.py                  # TTL + LRU query cache
    ├── scrape_ucdavis.py         # Web scraper for UC Davis pages
    ├── build_vectorstore.py      # FAISS vector store builder
    ├── build_vectorstore_supabase.py  # Supabase vector store uploader
    ├── uc_davis_data/             # 59 scraped data files
    └── requirements.txt
```

---

## Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- OpenAI API key
- Supabase project (with pgvector enabled)
- Auth0 tenant (configured for Google OAuth)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Fill in: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
#          GOOGLE_MAPS_API_KEY (optional)

# Build vector store (first time only)
python build_vectorstore_supabase.py

# Run server
python main.py
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "BACKEND_URL=http://localhost:8000" > .env.local
# Add Auth0 variables: AUTH0_SECRET, AUTH0_ISSUER_BASE_URL, etc.

npm run dev
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health + cache size + total queries |
| `GET` | `/analytics` | Query counts by intent, cache hit rate, avg response time |
| `POST` | `/chat` | Main query pipeline (rate limited) |
| `POST` | `/upload-image` | Image upload + OCR text extraction |

### `POST /chat` Request

```json
{
  "message": "Is Professor Smith's ECS 36A hard?",
  "conversation_history": [],
  "image_content": null
}
```

### `POST /chat` Response

```json
{
  "intent": "professor",
  "summary": "Professor Smith has a 4.2/5.0 rating on RateMyProfessor...",
  "sources": [
    {
      "title": "RateMyProfessor — John Smith",
      "source_type": "rate_my_professor",
      "url": "https://ratemyprofessors.com/professor/12345",
      "relevance_score": 0.95,
      "snippet": "John Smith: 4.2/5.0 rating, 3.1/5.0 difficulty, 42 ratings"
    }
  ],
  "professor_card": {
    "name": "John Smith",
    "department": "Computer Science",
    "overall_rating": 4.2,
    "difficulty": 3.1,
    "would_take_again": 78.0,
    "num_ratings": 42,
    "profile_url": "https://ratemyprofessors.com/professor/12345"
  },
  "directory_contacts": [
    {
      "full_name": "John Smith",
      "email": "jsmith@ucdavis.edu",
      "department": "COMPUTER SCIENCE",
      "title": "Professor",
      "phone": "+1 530 752 1234",
      "address": "2063 Kemper Hall, Davis, CA 95616"
    }
  ],
  "campus_resources": [],
  "cached": false,
  "query_time_ms": 1842
}
```

---

## Design Decisions

**Why not just use an LLM for everything?** The LLM is good at natural language generation but bad at ranking, deduplication, and structured data extraction. By handling those in custom Python code, the system is faster (cached responses return in <1ms), cheaper (fewer LLM tokens), and more transparent (every answer shows exactly where the information came from with relevance scores).

**Why keyword classification instead of LLM classification?** Speed and determinism. The classifier runs in microseconds and always produces the same result for the same input. LLM classification would add 500ms+ latency and cost per query for a task that weighted keywords handle well enough.

**Why Supabase over FAISS?** The initial prototype used FAISS (local vector store). Supabase with pgvector was chosen for the production version because it supports concurrent access from multiple backend instances without loading the entire index into memory.

---

## Why It Was Shut Down

Running OpenAI embeddings + GPT-4o-mini with real concurrent users costs money. After hitting meaningful usage in the first week (100+ unique UC Davis students), the project was taken offline to avoid ongoing API costs. The codebase remains here as a reference.
