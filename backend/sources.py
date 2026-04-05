"""
Data source retrieval layer.

Each function in this module fetches data from one external source,
normalizes it into SourceAttribution objects, and handles its own
errors gracefully (returning empty lists on failure rather than crashing).

The main pipeline calls these concurrently and feeds results into the ranker.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import requests
from ddgs import DDGS

from models import SourceAttribution, SourceType, ProfessorCard, DirectoryContact
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    GOOGLE_MAPS_API_KEY,
    UCD_DIRECTORY_API_KEY,
    MAX_VECTOR_RESULTS,
    UC_DAVIS_COORDS,
    UC_DAVIS_SEARCH_RADIUS,
)

# ── Lazy-initialized clients ────────────────────────────────────────────

_supabase_client = None
_embeddings = None
_gmaps_client = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_SERVICE_KEY:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase_client


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_openai import OpenAIEmbeddings
        _embeddings = OpenAIEmbeddings()
    return _embeddings


def _get_gmaps():
    global _gmaps_client
    if _gmaps_client is None and GOOGLE_MAPS_API_KEY:
        import googlemaps
        _gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    return _gmaps_client


# ── Vector Database Search ──────────────────────────────────────────────

async def search_vector_db(query: str) -> list[SourceAttribution]:
    """
    Embed the query and retrieve nearest neighbors from Supabase
    via the match_documents RPC. Returns SourceAttribution objects
    with the cosine similarity as the relevance score.
    """
    client = _get_supabase()
    embeddings = _get_embeddings()

    if not client or not embeddings:
        return []

    try:
        query_embedding = await asyncio.to_thread(embeddings.embed_query, query)

        def _search():
            return client.rpc(
                "match_documents",
                {"query_embedding": query_embedding, "match_count": MAX_VECTOR_RESULTS},
            ).execute()

        result = await asyncio.to_thread(_search)

        if not result.data:
            return []

        sources = []
        for doc in result.data:
            similarity = doc.get("similarity", 0.0)
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            sources.append(SourceAttribution(
                title=_extract_title(content, metadata),
                source_type=SourceType.VECTOR_DB,
                url=metadata.get("source"),
                relevance_score=round(float(similarity), 3),
                snippet=content[:300],
            ))

        return sources

    except Exception as e:
        print(f"[vector_db] Error: {e}")
        return []


def _extract_title(content: str, metadata: dict) -> str:
    """Pull a human-readable title from document content or metadata."""
    if "source" in metadata:
        # e.g., "uc_davis_data/housing.txt" → "Housing"
        filename = metadata["source"].split("/")[-1].replace(".txt", "")
        return filename.replace("_", " ").replace("scraped ", "Page ").title()
    first_line = content.split("\n")[0][:80]
    return first_line if first_line else "UC Davis Resource"


# ── RateMyProfessor Lookup ──────────────────────────────────────────────

async def search_ratemyprofessor(professor_name: str) -> tuple[
    list[SourceAttribution], Optional[ProfessorCard]
]:
    """
    Scrape RateMyProfessor for a specific professor.
    Returns both a SourceAttribution (for ranking) and a structured
    ProfessorCard (for the frontend to render directly).
    """
    try:
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    f"{professor_name} UC Davis RateMyProfessor",
                    max_results=5,
                ))

        results = await asyncio.to_thread(_search)
        if not results:
            return [], None

        # Find the RMP profile link
        rmp_url = None
        for r in results:
            href = r.get("href", "")
            if "ratemyprofessors.com/professor" in href:
                rmp_url = href
                break

        if not rmp_url:
            return [], None

        # Fetch the page and extract embedded JSON data
        headers = {"User-Agent": "Mozilla/5.0"}
        res = await asyncio.to_thread(
            lambda: requests.get(rmp_url, headers=headers, timeout=10)
        )

        if res.status_code != 200:
            return [], None

        page_text = res.text
        rating = re.search(r'"avgRating":([\d.]+)', page_text)
        difficulty = re.search(r'"avgDifficulty":([\d.]+)', page_text)
        num_ratings = re.search(r'"numRatings":(\d+)', page_text)
        take_again = re.search(r'"wouldTakeAgainPercent":([\d.]+)', page_text)
        department = re.search(r'"department":"([^"]+)"', page_text)

        if not rating:
            return [], None

        # Build structured card
        card = ProfessorCard(
            name=professor_name,
            department=department.group(1) if department else "N/A",
            overall_rating=float(rating.group(1)),
            difficulty=float(difficulty.group(1)) if difficulty else None,
            would_take_again=float(take_again.group(1)) if take_again else None,
            num_ratings=int(num_ratings.group(1)) if num_ratings else 0,
            profile_url=rmp_url,
        )

        # Build source attribution
        snippet = (
            f"{professor_name}: {card.overall_rating}/5.0 rating, "
            f"{card.difficulty}/5.0 difficulty, "
            f"{card.num_ratings} ratings"
        )

        source = SourceAttribution(
            title=f"RateMyProfessor — {professor_name}",
            source_type=SourceType.RATE_MY_PROFESSOR,
            url=rmp_url,
            relevance_score=0.95,  # high confidence for direct match
            snippet=snippet,
        )

        return [source], card

    except Exception as e:
        print(f"[rmp] Error for {professor_name}: {e}")
        return [], None


# ── Reddit (r/UCDavis) Search ───────────────────────────────────────────

async def search_reddit(query: str) -> list[SourceAttribution]:
    """Search DuckDuckGo for r/UCDavis posts matching the query."""
    try:
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    f"{query} site:reddit.com/r/ucdavis",
                    max_results=5,
                ))

        results = await asyncio.to_thread(_search)
        if not results:
            return []

        sources = []
        for i, r in enumerate(results):
            # Score decreases with rank position
            score = max(0.85 - (i * 0.1), 0.4)
            sources.append(SourceAttribution(
                title=r.get("title", "Reddit Post")[:100],
                source_type=SourceType.REDDIT,
                url=r.get("href"),
                relevance_score=score,
                snippet=r.get("body", "")[:300],
            ))

        return sources

    except Exception as e:
        print(f"[reddit] Error: {e}")
        return []


# ── General Web Search ──────────────────────────────────────────────────

async def search_web(query: str) -> list[SourceAttribution]:
    """General DuckDuckGo search for UC Davis context."""
    try:
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    f"{query} UC Davis",
                    max_results=5,
                ))

        results = await asyncio.to_thread(_search)
        if not results:
            return []

        sources = []
        for i, r in enumerate(results):
            score = max(0.80 - (i * 0.1), 0.3)
            sources.append(SourceAttribution(
                title=r.get("title", "Web Result")[:100],
                source_type=SourceType.WEB,
                url=r.get("href"),
                relevance_score=score,
                snippet=r.get("body", "")[:300],
            ))

        return sources

    except Exception as e:
        print(f"[web] Error: {e}")
        return []


# ── Google Maps / Places ────────────────────────────────────────────────

async def search_campus_map(query: str) -> list[SourceAttribution]:
    """Search Google Maps for campus locations."""
    client = _get_gmaps()
    if not client:
        return []

    try:
        def _search():
            return client.places(
                query=f"{query} UC Davis",
                location=UC_DAVIS_COORDS,
                radius=UC_DAVIS_SEARCH_RADIUS,
            )

        results = await asyncio.to_thread(_search)

        if not results.get("results"):
            return []

        sources = []
        for i, place in enumerate(results["results"][:5]):
            score = max(0.90 - (i * 0.1), 0.4)
            name = place.get("name", "")
            address = place.get("formatted_address", "")
            rating = place.get("rating", "N/A")

            sources.append(SourceAttribution(
                title=name,
                source_type=SourceType.GOOGLE_MAPS,
                relevance_score=score,
                snippet=f"{name} — {address} (Rating: {rating})",
            ))

        return sources

    except Exception as e:
        print(f"[maps] Error: {e}")
        return []


# ── UC Davis Directory API (People/Departments) ────────────────────────

async def search_ucd_directory(
    name: str,
) -> tuple[list[SourceAttribution], list[DirectoryContact]]:
    """
    Query the UC Davis IET Directory Search API for staff/faculty
    contact information by name.

    API docs: https://ucdavis.jira.com/wiki/spaces/IETP/pages/132808748
    Endpoint: https://iet-ws.ucdavis.edu/api/directory/search

    Returns both SourceAttributions (for ranking) and structured
    DirectoryContact objects (for the frontend to render as contact cards).
    """
    if not UCD_DIRECTORY_API_KEY:
        return [], []

    try:
        # Split name into first/last for the API query params
        parts = name.strip().split()
        params: dict[str, str] = {
            "key": UCD_DIRECTORY_API_KEY,
            "v": "1.0",
        }

        if len(parts) >= 2:
            params["givenName"] = parts[0]
            params["sn"] = parts[-1]
        else:
            params["cn"] = name

        def _fetch():
            return requests.get(
                "https://iet-ws.ucdavis.edu/api/directory/search",
                params=params,
                headers={
                    "Accept": "application/json",
                    "Referer": "https://egghead-ai-tau.vercel.app",
                },
                timeout=10,
            )

        resp = await asyncio.to_thread(_fetch)

        if resp.status_code != 200:
            print(f"[directory] API returned {resp.status_code}")
            return [], []

        data = resp.json()
        results = data.get("responseData", {}).get("results", [])

        if not results:
            return [], []

        sources: list[SourceAttribution] = []
        contacts: list[DirectoryContact] = []

        for i, person in enumerate(results[:5]):
            contact = DirectoryContact(
                full_name=person.get("displayName") or person.get("cn", name),
                email=person.get("mail"),
                department=person.get("ou"),
                title=person.get("title"),
                phone=person.get("telephoneNumber"),
                address=person.get("postalAddress", "").replace("$", ", "),
            )
            contacts.append(contact)

            # Build a source attribution for ranking
            snippet_parts = [contact.full_name]
            if contact.title:
                snippet_parts.append(contact.title)
            if contact.department:
                snippet_parts.append(contact.department)
            if contact.email:
                snippet_parts.append(contact.email)

            score = max(0.90 - (i * 0.1), 0.5)

            sources.append(SourceAttribution(
                title=f"UC Davis Directory — {contact.full_name}",
                source_type=SourceType.UCD_DIRECTORY,
                relevance_score=score,
                snippet=" | ".join(snippet_parts),
            ))

        return sources, contacts

    except Exception as e:
        print(f"[directory] Error: {e}")
        return [], []
