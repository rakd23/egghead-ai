# 🥚 Egghead AI

UC Davis students waste time jumping between RateMyProfessors, Reddit, and a dozen official UC Davis pages just to answer basic questions like "is this professor good" or "where do I get free tutoring." We built Egghead AI to collapse all of that into one place.

The app was deployed on Vercel and Render, hit 100+ students in its first week, and got taken down because OpenAI costs at real usage scale add up fast.

---

## What it does

- Answers questions about professors, courses, housing, dining, campus resources, and locations
- Pulls from RateMyProfessors, Reddit, the UC Davis directory API, Google Maps, and our own scraped vector store — all at the same time
- Shows structured data like professor rating cards and contact info alongside a short written answer
- Cites where every piece of information came from with relevance scores

---

## How a query actually works

1. The query comes in and gets classified into an intent — professor, course, housing, dining, location, campus resource, or general
2. Based on the intent, different sources get queried in parallel. A professor question hits RMP and the UC Davis directory. A dining question hits Google Maps and Reddit. A housing question hits Reddit and the vector store.
3. Results from all sources get scored and ranked using weighted multipliers that depend on the intent. RMP results rank higher for professor queries, Reddit ranks higher for housing questions, etc.
4. Near-duplicate results get filtered out using sequence matching
5. The ranked results get passed to GPT-4o-mini which writes a short summary paragraph. The LLM only summarizes — all the retrieval and ranking decisions happen before it ever sees the data.
6. The frontend renders the summary alongside structured cards for professor ratings, directory contacts, and source attributions

The main design decision was keeping the LLM out of retrieval and ranking entirely. It doesn't decide what sources to use or how to order results — the pipeline does that.

---

## Features

- Intent classifier routes queries to the right sources without using an LLM
- Parallel retrieval across 5+ sources using asyncio
- Weighted source ranking with near-duplicate deduplication
- Semantic search over scraped UC Davis data stored in Supabase pgvector
- Live RateMyProfessors scraping with structured professor cards
- UC Davis Directory API integration for faculty contact info
- Reddit search scoped to r/UCDavis
- Google Maps Places API for campus locations
- Image upload — students can photograph their course schedule and ask questions about it
- In-memory LRU cache with TTL expiry
- Per-IP sliding window rate limiting
- Analytics endpoint tracking query volume, cache hit rate, and intent distribution

---

## Tech Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** FastAPI (Python)
- **Vector DB:** Supabase with pgvector
- **LLM:** GPT-4o-mini via OpenAI API
- **Other APIs:** Google Maps Places, UC Davis IET Directory, DuckDuckGo Search

---

## Project Structure

```
backend/
  main.py              # request pipeline and route handlers
  classifier.py        # keyword-based query intent classification
  sources.py           # all external API and scraping logic
  ranker.py            # weighted scoring and deduplication
  response_builder.py  # assembles final response and calls LLM
  cache.py             # LRU cache with TTL eviction
  models.py            # Pydantic request/response schemas
  config.py            # environment variables and constants
  resources.py         # curated UC Davis resource links

frontend/
  app/chat.tsx         # main chat UI
  app/types.ts         # shared TypeScript types
  app/api/chat/        # backend proxy route
```

---

## Design decisions

**Why keyword classification instead of asking GPT to classify?**
It's about 100x faster and completely deterministic. For a finite set of intent categories that map cleanly to keyword patterns, a rule-based classifier is the right tool. The latency savings matter when you're already making 4-5 API calls per query.

**Why not just let the LLM decide what sources to search?**
Because then the system's behavior becomes unpredictable and hard to debug. Keeping retrieval and ranking as explicit pipeline steps means we know exactly why a result showed up and can tune it without touching the model.

**Why multiple sources instead of just the vector store?**
The vector store has official UC Davis content but it goes stale and misses student perspectives entirely. Reddit has real student opinions but no structured data. RMP has ratings but nothing else. The sources complement each other and we needed all of them.

**Why in-memory cache instead of Redis?**
For this scale it was fine. The next step would be Redis if we were running multiple server instances or needed the cache to survive deploys.

---

## What we'd do differently

- Retrieval quality metrics — right now we have no way to measure whether the ranking actually produces better answers, just that it runs
- The in-process cache doesn't survive server restarts or work across multiple instances
- Some source APIs are slow or rate-limit unpredictably, which occasionally tanks response time
- We'd add streaming responses so the frontend can show results as they come in instead of waiting for all sources to finish

---

## Why it got shut down

Running OpenAI embeddings plus GPT-4o-mini across hundreds of real queries a day costs actual money. After the first week we hit a point where keeping it live wasn't worth it for a side project. The architecture is here if anyone wants to run it.
