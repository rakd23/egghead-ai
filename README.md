# 🥚 Egghead AI

Egghead AI is a full-stack project I built to help UC Davis students find information about classes, professors, and campus resources in one place.

I originally made it because I kept switching between RateMyProfessor, Reddit, and UC Davis websites just to answer simple questions. This project combines those sources into a single system and returns both a short explanation and structured data.

> Note: The app was previously deployed (Vercel + Render) and used by ~100 students, but I took it down due to API costs.

---

## What it does

- Answers questions about professors, courses, housing, dining, etc.
- Pulls data from multiple sources (RMP, Reddit, UC Davis sites, APIs)
- Shows where information comes from (source links + relevance)
- Displays structured data like professor ratings and contact info

---

## How it works

When a user sends a query:

1. The backend classifies the query into an intent (professor, course, housing, etc.)
2. Based on the intent, it queries different data sources in parallel
3. Results are scored and ranked using custom logic
4. The LLM generates a short summary using the ranked results
5. The frontend renders structured data (cards + sources)

A key design choice was to avoid relying entirely on the LLM — most of the logic (classification, retrieval, ranking) is handled in the backend.

---

## Features

- Semantic search over scraped UC Davis data (housing, academics, services)
- RateMyProfessor integration (ratings, difficulty, etc.)
- UC Davis directory API (email, office, department)
- Reddit results for student discussions
- Google Maps integration for locations
- Source attribution with relevance scores
- Basic caching to reduce repeated API calls
- Rate limiting to prevent abuse
- Image upload (extract text from schedules)

---

## Tech Stack

- Frontend: Next.js, React, TypeScript, Tailwind
- Backend: FastAPI (Python)
- Vector DB: Supabase (pgvector)
- LLM: OpenAI (used for summary generation)
- Other APIs: Google Maps, UC Davis Directory, DuckDuckGo

---

## Project Structure

```
backend/
  main.py              # main request pipeline
  classifier.py        # query intent classification
  ranker.py            # scoring + ranking logic
  sources.py           # API + data fetching
  response_builder.py  # builds final response
  cache.py             # simple in-memory cache

frontend/
  chat.tsx             # main UI
  types.ts             # shared types
  api/chat/route.ts    # backend proxy
```

---

## Design Choices

**Why not just use GPT for everything?**  
I wanted the system to retrieve and rank real data instead of just generating answers. The LLM is only used for summarizing results.

**Why keyword-based classification?**  
It’s fast and predictable. For this use case, it worked well without needing a model.

**Why multiple sources?**  
Different sources provide different types of information (official data vs student opinions).

---

## Limitations / Improvements

- Ranking is heuristic-based and could be improved
- Cache is in-memory (would switch to Redis for scaling)
- Some APIs are slow or unreliable
- Deployment cost was an issue with OpenAI usage

---

## Why I built this

I built this project to solve a problem I personally had as a student — finding reliable information across multiple sites was slow and annoying.

It also helped me learn more about:
- building full-stack applications
- working with APIs
- designing backend pipelines
