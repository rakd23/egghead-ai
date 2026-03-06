# 🥚 Egghead AI

A natural language search platform for UC Davis students. Ask questions in plain English and get answers pulled from real course reviews, Reddit discussions, and campus resources — no more digging through Rate My Professors or scrolling r/UCDavis.

> **Note:** The live deployment has been taken offline. The app was hosted on Vercel and served **100+ students** in its first week before being sunset due to API costs.

---

## Architecture
```
User Query (natural language)
         ↓
  Next.js Frontend
         ↓
   FastAPI Backend
         ↓
  OpenAI Embeddings API
  (query → vector)
         ↓
  Vector Index Search
  (cosine similarity)
         ↓
  Ranked Document Chunks
  (RateMyProfessors · r/UCDavis · Course Catalog)
         ↓
  Structured Response
         ↓
  Next.js Frontend
```

---

## What it does

Students can type queries like *"Is Professor X's ECS 36A hard?"* or *"What's the best way to find housing near campus?"* and get semantically relevant results ranked by meaning, not just keywords.

---

## How it works

1. **Data ingestion** — Course reviews from Rate My Professors, discussions from r/UCDavis, and UC Davis course catalog data are scraped, cleaned, and chunked into documents. Course schedule screenshots are parsed into structured records using OCR-based extraction.

2. **Embedding & indexing** — Each document chunk is embedded using the OpenAI Embeddings API and stored in a vector index for semantic similarity search.

3. **Query pipeline** — When a user submits a query, it's embedded using the same model, and the nearest document chunks are retrieved by cosine similarity. Results are ranked and returned to the frontend.

4. **Backend** — FastAPI handles query processing, result ranking, caching, and response formatting. Caching logic keeps latency low under concurrent load.

5. **Frontend** — Built with Next.js (TypeScript). Clean search interface with structured result cards.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript |
| Backend | Python, FastAPI |
| Embeddings | OpenAI Embeddings API |
| Data sources | Rate My Professors, r/UCDavis, UC Davis course catalog |
| Deployment | Vercel (frontend), Python backend |

---

## Repo Structure
```
egghead-ai/
├── frontend/   # Next.js app
└── backend/    # FastAPI server, embedding pipeline, data ingestion
```

---

## Why it was shut down

Running OpenAI embeddings at scale with real concurrent users gets expensive quickly. After hitting meaningful usage in the first week, the project was taken offline to avoid ongoing API costs. The codebase remains here as a reference.
