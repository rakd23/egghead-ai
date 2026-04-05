"""
Egghead AI — FastAPI Backend

Main application entry point. Orchestrates the full query pipeline:

    1. Rate limit check
    2. Cache lookup
    3. Query classification (classifier.py)
    4. Parallel data retrieval from sources (sources.py)
    5. Result ranking and deduplication (ranker.py)
    6. LLM summary generation (response_builder.py)
    7. Cache store + analytics update
"""

from __future__ import annotations

import asyncio
import base64
import time
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from config import (
    ALLOWED_ORIGINS,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)
from models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    AnalyticsResponse,
    QueryIntent,
)
from classifier import classify_query, extract_professor_names
from sources import (
    search_vector_db,
    search_ratemyprofessor,
    search_reddit,
    search_web,
    search_campus_map,
    search_ucd_directory,
)
from resources import match_resources
from ranker import rank_results
from response_builder import build_response
from cache import QueryCache


# ── App Setup ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Egghead AI",
    description="Semantic search and campus assistant API for UC Davis",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Shared State ─────────────────────────────────────────────────────────

query_cache = QueryCache()

# Analytics counters
_analytics = {
    "total_queries": 0,
    "cache_hits": 0,
    "intent_counts": defaultdict(int),
    "total_response_time_ms": 0,
}

# Rate limiter: IP → list of request timestamps
_rate_limit_store: dict[str, list[float]] = {}


# ── Rate Limiting Middleware ─────────────────────────────────────────────

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Per-IP sliding window rate limiter.
    Allows RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW_SECONDS.
    Only applied to POST /chat to avoid blocking health checks.
    """
    if request.url.path != "/chat" or request.method != "POST":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    # Get and prune timestamps for this IP
    timestamps = _rate_limit_store.get(client_ip, [])
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": f"Too many requests. Limit: {RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW_SECONDS}s",
                "retry_after_seconds": int(timestamps[0] + RATE_LIMIT_WINDOW_SECONDS - now) + 1,
            },
        )

    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps

    return await call_next(request)


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Service health + basic operational stats."""
    return HealthResponse(
        status="ok",
        version="2.0.0",
        cache_size=query_cache.size,
        total_queries=_analytics["total_queries"],
    )


@app.get("/analytics", response_model=AnalyticsResponse)
def get_analytics():
    """Query analytics dashboard data."""
    total = _analytics["total_queries"]
    return AnalyticsResponse(
        total_queries=total,
        cache_hits=_analytics["cache_hits"],
        cache_hit_rate=query_cache.hit_rate,
        queries_by_intent=dict(_analytics["intent_counts"]),
        avg_response_time_ms=(
            _analytics["total_response_time_ms"] / total if total > 0 else 0.0
        ),
    )


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Accept an image upload, extract text via GPT-4o-mini vision,
    and return the extracted text for use in the chat pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    valid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp")
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type. Accepted: {', '.join(valid_extensions)}",
        )

    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10 MB limit
            raise HTTPException(status_code=400, detail="Image exceeds 10MB limit")

        base64_image = base64.b64encode(content).decode("utf-8")

        vision_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        def _extract():
            message = HumanMessage(content=[
                {"type": "text", "text": "Extract all readable text from this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            ])
            return vision_llm.invoke([message]).content

        extracted_text = await asyncio.to_thread(_extract)

        return {
            "text": extracted_text,
            "filename": file.filename,
            "length": len(extracted_text),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main query pipeline.

    Flow:
      1. Check cache for an existing response
      2. Classify the query intent
      3. Dispatch to data sources based on intent
      4. Rank and deduplicate results
      5. Generate LLM summary from ranked context
      6. Cache the response
    """
    start_time = time.time()

    # ── Step 1: Cache lookup ─────────────────────────────────────────
    cached_response = query_cache.get(req.message)
    if cached_response and not req.image_content:
        _analytics["cache_hits"] += 1
        _analytics["total_queries"] += 1
        cached_response.cached = True
        return cached_response

    # ── Step 2: Classify intent ──────────────────────────────────────
    intent = classify_query(req.message)
    _analytics["intent_counts"][intent.value] += 1

    # ── Step 3: Dispatch to sources (concurrent) ─────────────────────
    all_sources = []
    professor_card = None
    directory_contacts = []

    # Always run vector search
    retrieval_tasks = [search_vector_db(req.message)]

    # Intent-specific sources
    if intent == QueryIntent.PROFESSOR:
        names = extract_professor_names(req.message)
        if req.image_content:
            names += extract_professor_names(req.image_content)
        names = list(set(names))

        for name in names:
            retrieval_tasks.append(_fetch_professor(name))
            retrieval_tasks.append(_fetch_directory(name))

        retrieval_tasks.append(search_reddit(req.message))

    elif intent == QueryIntent.COURSE:
        retrieval_tasks.append(search_reddit(req.message))
        retrieval_tasks.append(search_web(req.message))

    elif intent == QueryIntent.HOUSING:
        retrieval_tasks.append(search_reddit(req.message))
        retrieval_tasks.append(search_web(req.message))

    elif intent == QueryIntent.DINING:
        retrieval_tasks.append(search_campus_map(req.message))
        retrieval_tasks.append(search_reddit(req.message))

    elif intent == QueryIntent.LOCATION:
        retrieval_tasks.append(search_campus_map(req.message))

    elif intent == QueryIntent.CAMPUS_RESOURCE:
        retrieval_tasks.append(search_web(req.message))

    else:  # GENERAL
        retrieval_tasks.append(search_reddit(req.message))
        retrieval_tasks.append(search_web(req.message))

    # Run all retrieval tasks concurrently
    results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            print(f"[pipeline] Source error: {result}")
            continue
        if isinstance(result, tuple) and len(result) == 3:
            # Tagged tuple: ("professor"|"directory", sources, extra)
            tag, sources, extra = result
            all_sources.extend(sources)
            if tag == "professor" and extra and professor_card is None:
                professor_card = extra
            elif tag == "directory" and extra:
                directory_contacts.extend(extra)
        elif isinstance(result, list):
            all_sources.extend(result)

    # ── Step 4: Rank results ─────────────────────────────────────────
    ranked_sources = rank_results(all_sources, intent)

    # ── Step 5: Match curated resources ──────────────────────────────
    campus_resources = match_resources(req.message, intent)

    # ── Step 6: Build response (LLM summary) ─────────────────────────
    elapsed_ms = int((time.time() - start_time) * 1000)

    response = await build_response(
        query=req.message,
        intent=intent,
        ranked_sources=ranked_sources,
        professor_card=professor_card,
        directory_contacts=directory_contacts,
        campus_resources=campus_resources,
        conversation_history=req.conversation_history,
        image_content=req.image_content,
        query_time_ms=elapsed_ms,
    )

    # ── Step 7: Cache and analytics ──────────────────────────────────
    final_time_ms = int((time.time() - start_time) * 1000)
    response.query_time_ms = final_time_ms

    if not req.image_content:
        query_cache.put(req.message, response)

    _analytics["total_queries"] += 1
    _analytics["total_response_time_ms"] += final_time_ms

    return response


# ── Helpers ──────────────────────────────────────────────────────────────

async def _fetch_professor(name: str):
    """Tag professor results so the gather handler can distinguish them."""
    sources, card = await search_ratemyprofessor(name)
    return ("professor", sources, card)


async def _fetch_directory(name: str):
    """Tag directory results so the gather handler can distinguish them."""
    sources, contacts = await search_ucd_directory(name)
    return ("directory", sources, contacts)


# ── Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
