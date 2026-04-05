"""
Response builder — assembles the final ChatResponse.

The LLM is used here ONLY to generate a short natural-language summary
paragraph from the already-ranked results. All structured data (professor
cards, source attributions, campus resources) comes from the pipeline,
not from the LLM.

This is the key architectural distinction: the LLM summarizes data that
our pipeline already retrieved and ranked — it doesn't decide what to
show or how to rank it.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from models import (
    QueryIntent,
    ChatResponse,
    SourceAttribution,
    ProfessorCard,
    DirectoryContact,
    CampusResource,
    HistoryMessage,
)
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


_llm: Optional[ChatOpenAI] = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
    return _llm


_SUMMARY_SYSTEM_PROMPT = """You are a helpful UC Davis campus assistant. You will be given
retrieved context about a student's question. Write a concise, friendly summary
paragraph (3-5 sentences max) that answers their question based ONLY on the
provided context.

Rules:
- Only state facts that appear in the provided context.
- If professor rating data is present, mention the key numbers.
- If no relevant data was found, say so honestly.
- Never fabricate ratings, facts, or URLs.
- Do not repeat the raw data — summarize it naturally.
- Keep it under 150 words."""


async def build_response(
    query: str,
    intent: QueryIntent,
    ranked_sources: list[SourceAttribution],
    professor_card: Optional[ProfessorCard],
    directory_contacts: list[DirectoryContact],
    campus_resources: list[CampusResource],
    conversation_history: list[HistoryMessage],
    image_content: Optional[str],
    query_time_ms: int,
    cached: bool = False,
) -> ChatResponse:
    """
    Build the final response by generating an LLM summary from ranked context.
    """
    # Assemble context block from ranked sources
    context_parts = []

    if image_content:
        context_parts.append(f"[Uploaded Image Text]: {image_content[:1000]}")

    if professor_card:
        context_parts.append(
            f"[Professor Data]: {professor_card.name} — "
            f"Rating: {professor_card.overall_rating}/5.0, "
            f"Difficulty: {professor_card.difficulty}/5.0, "
            f"Department: {professor_card.department}, "
            f"Would Take Again: {professor_card.would_take_again}%, "
            f"Total Ratings: {professor_card.num_ratings}"
        )

    if directory_contacts:
        for contact in directory_contacts[:3]:
            parts = [f"{contact.full_name}"]
            if contact.title:
                parts.append(f"Title: {contact.title}")
            if contact.department:
                parts.append(f"Dept: {contact.department}")
            if contact.email:
                parts.append(f"Email: {contact.email}")
            if contact.phone:
                parts.append(f"Phone: {contact.phone}")
            context_parts.append(f"[UC Davis Directory]: {', '.join(parts)}")

    for src in ranked_sources[:5]:
        context_parts.append(
            f"[{src.source_type.value} | score={src.relevance_score}]: {src.snippet}"
        )

    if campus_resources:
        res_text = ", ".join(f"{r.name} ({r.description})" for r in campus_resources)
        context_parts.append(f"[Campus Resources]: {res_text}")

    context_block = "\n\n".join(context_parts) if context_parts else "No relevant data found."

    # Build LLM messages
    messages = [SystemMessage(content=_SUMMARY_SYSTEM_PROMPT)]

    # Include last few turns of conversation for continuity
    for msg in conversation_history[-6:]:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    user_prompt = f"Context:\n{context_block}\n\nStudent question: {query}"
    messages.append(HumanMessage(content=user_prompt))

    # Generate summary
    try:
        llm = _get_llm()
        response = await asyncio.to_thread(llm.invoke, messages)
        summary = response.content
    except Exception as e:
        print(f"[llm] Error generating summary: {e}")
        summary = _build_fallback_summary(query, ranked_sources, professor_card)

    return ChatResponse(
        intent=intent,
        summary=summary,
        sources=ranked_sources,
        professor_card=professor_card,
        directory_contacts=directory_contacts[:3],
        campus_resources=campus_resources,
        cached=cached,
        query_time_ms=query_time_ms,
    )


def _build_fallback_summary(
    query: str,
    sources: list[SourceAttribution],
    professor_card: Optional[ProfessorCard],
) -> str:
    """Generate a basic summary without the LLM if it fails."""
    parts = []

    if professor_card and professor_card.overall_rating:
        parts.append(
            f"{professor_card.name} has a {professor_card.overall_rating}/5.0 "
            f"rating on RateMyProfessor with {professor_card.num_ratings} reviews."
        )

    if sources:
        parts.append(
            f"I found {len(sources)} relevant sources. "
            "Check the source cards below for details."
        )
    else:
        parts.append(
            "I couldn't find specific information for your question. "
            "Try rephrasing or check the UC Davis resources linked below."
        )

    return " ".join(parts)
