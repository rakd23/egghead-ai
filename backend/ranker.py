"""
Result ranking and scoring pipeline.

After retrieving candidates from multiple sources (vector DB, RMP,
Reddit, web), this module:

  1. Normalizes scores to 0-1 across sources
  2. Applies source-type weight multipliers based on query intent
  3. Deduplicates near-identical snippets
  4. Returns the top-K results sorted by final score

This is the core "non-wrapper" logic — the LLM never decides which
results to show or how to rank them.
"""

from __future__ import annotations
from difflib import SequenceMatcher
from models import QueryIntent, SourceType, SourceAttribution
from config import SIMILARITY_THRESHOLD, TOP_K_RESULTS


# Weight multipliers per (intent, source_type) pair.
# A professor query boosts RMP results; a housing query boosts Reddit, etc.
_SOURCE_WEIGHTS: dict[QueryIntent, dict[SourceType, float]] = {
    QueryIntent.PROFESSOR: {
        SourceType.RATE_MY_PROFESSOR: 1.5,
        SourceType.UCD_DIRECTORY: 1.3,
        SourceType.VECTOR_DB: 1.0,
        SourceType.REDDIT: 0.9,
        SourceType.WEB: 0.7,
    },
    QueryIntent.COURSE: {
        SourceType.VECTOR_DB: 1.4,
        SourceType.REDDIT: 1.1,
        SourceType.WEB: 0.8,
        SourceType.RATE_MY_PROFESSOR: 0.6,
    },
    QueryIntent.HOUSING: {
        SourceType.REDDIT: 1.4,
        SourceType.VECTOR_DB: 1.0,
        SourceType.WEB: 0.9,
        SourceType.GOOGLE_MAPS: 0.8,
    },
    QueryIntent.DINING: {
        SourceType.GOOGLE_MAPS: 1.3,
        SourceType.VECTOR_DB: 1.1,
        SourceType.REDDIT: 1.0,
        SourceType.WEB: 0.8,
    },
    QueryIntent.LOCATION: {
        SourceType.GOOGLE_MAPS: 1.5,
        SourceType.VECTOR_DB: 1.0,
        SourceType.WEB: 0.8,
    },
    QueryIntent.CAMPUS_RESOURCE: {
        SourceType.VECTOR_DB: 1.3,
        SourceType.CURATED: 1.4,
        SourceType.WEB: 0.8,
        SourceType.REDDIT: 0.7,
    },
    QueryIntent.GENERAL: {
        SourceType.VECTOR_DB: 1.0,
        SourceType.REDDIT: 1.0,
        SourceType.WEB: 1.0,
        SourceType.GOOGLE_MAPS: 0.8,
    },
}

# Default weight for any (intent, source) pair not explicitly listed
_DEFAULT_WEIGHT = 0.8


def _get_weight(intent: QueryIntent, source_type: SourceType) -> float:
    """Look up the weight multiplier for a given intent + source combo."""
    return _SOURCE_WEIGHTS.get(intent, {}).get(source_type, _DEFAULT_WEIGHT)


def _is_duplicate(a: str, b: str, threshold: float = 0.75) -> bool:
    """Check if two snippets are near-duplicates using sequence matching."""
    if not a or not b:
        return False
    # Compare only first 200 chars for performance
    return SequenceMatcher(None, a[:200], b[:200]).ratio() > threshold


def rank_results(
    candidates: list[SourceAttribution],
    intent: QueryIntent,
    top_k: int = TOP_K_RESULTS,
    min_score: float = SIMILARITY_THRESHOLD,
) -> list[SourceAttribution]:
    """
    Score, deduplicate, and rank a list of source attributions.

    Steps:
      1. Apply intent-based source-type weight to each candidate's
         raw relevance score.
      2. Filter out candidates below the minimum score threshold.
      3. Sort descending by weighted score.
      4. Walk the sorted list and drop near-duplicate snippets.
      5. Return the top_k survivors.
    """
    # Step 1: Apply weights
    scored: list[tuple[float, SourceAttribution]] = []
    for candidate in candidates:
        weight = _get_weight(intent, candidate.source_type)
        weighted_score = min(candidate.relevance_score * weight, 1.0)

        scored.append((
            weighted_score,
            candidate.model_copy(update={"relevance_score": round(weighted_score, 3)}),
        ))

    # Step 2: Filter by threshold (skip for curated resources)
    scored = [
        (s, c) for s, c in scored
        if s >= min_score or c.source_type == SourceType.CURATED
    ]

    # Step 3: Sort descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Step 4: Deduplicate
    deduped: list[SourceAttribution] = []
    for _, candidate in scored:
        if any(_is_duplicate(candidate.snippet, existing.snippet) for existing in deduped):
            continue
        deduped.append(candidate)

    # Step 5: Top-K
    return deduped[:top_k]
