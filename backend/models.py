"""
Request and response schemas for all API endpoints.
Every field is validated through Pydantic so nothing unexpected
reaches the backend logic or leaves the API.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    """Categories the classifier can assign to a user query."""
    PROFESSOR = "professor"
    COURSE = "course"
    HOUSING = "housing"
    DINING = "dining"
    CAMPUS_RESOURCE = "campus_resource"
    LOCATION = "location"
    GENERAL = "general"


class SourceType(str, Enum):
    """Where a piece of retrieved information came from."""
    VECTOR_DB = "vector_db"
    RATE_MY_PROFESSOR = "rate_my_professor"
    REDDIT = "reddit"
    WEB = "web"
    GOOGLE_MAPS = "google_maps"
    UCD_DIRECTORY = "ucd_directory"
    CURATED = "curated"


# ── Request Models ───────────────────────────────────────────────────────

class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: List[HistoryMessage] = Field(default_factory=list, max_length=20)
    image_content: Optional[str] = Field(default=None, max_length=10000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        return v.strip()


# ── Response Models ──────────────────────────────────────────────────────

class SourceAttribution(BaseModel):
    """One retrieved source with its relevance score."""
    title: str
    source_type: SourceType
    url: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str = ""


class ProfessorCard(BaseModel):
    """Structured professor data extracted from RateMyProfessor."""
    name: str
    department: str = "N/A"
    overall_rating: Optional[float] = None
    difficulty: Optional[float] = None
    would_take_again: Optional[float] = None
    num_ratings: int = 0
    profile_url: Optional[str] = None


class CampusResource(BaseModel):
    """A curated UC Davis resource link."""
    name: str
    category: str
    url: Optional[str] = None
    description: str = ""


class DirectoryContact(BaseModel):
    """Structured contact info from UC Davis Directory API."""
    full_name: str
    email: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ChatResponse(BaseModel):
    """The full structured response returned to the frontend."""
    intent: QueryIntent
    summary: str                                    # LLM-generated natural language paragraph
    sources: List[SourceAttribution] = []            # ranked sources with scores
    professor_card: Optional[ProfessorCard] = None   # present only for professor queries
    directory_contacts: List[DirectoryContact] = []  # UC Davis directory results
    campus_resources: List[CampusResource] = []      # relevant curated links
    cached: bool = False                             # whether this was a cache hit
    query_time_ms: int = 0                           # total processing time


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
    cache_size: int = 0
    total_queries: int = 0


class AnalyticsResponse(BaseModel):
    total_queries: int = 0
    cache_hits: int = 0
    cache_hit_rate: float = 0.0
    queries_by_intent: dict = {}
    avg_response_time_ms: float = 0.0
