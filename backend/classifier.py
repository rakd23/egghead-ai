"""
Query intent classification using weighted keyword matching.

This is a rule-based classifier that assigns an intent category to each
user query. It uses weighted keyword groups and pattern-matching heuristics
rather than an LLM, keeping classification fast (~0.1ms) and deterministic.

The classifier scores each intent category and picks the highest. Ties are
broken by specificity (more specific intents like PROFESSOR beat GENERAL).
"""

import re
from models import QueryIntent


# Each intent maps to a list of (keyword_or_pattern, weight) tuples.
# Higher weight = stronger signal for that intent.
_INTENT_KEYWORDS: dict[QueryIntent, list[tuple[str, float]]] = {
    QueryIntent.PROFESSOR: [
        ("professor", 3.0),
        ("prof ", 3.0),      # trailing space avoids matching "professional"
        ("prof.", 3.0),
        ("instructor", 2.5),
        ("teacher", 2.0),
        ("ratemyprofessor", 3.0),
        ("rmp", 2.5),
        ("rating", 1.5),
        ("teaches", 2.0),
        ("taught by", 2.5),
        ("teaching style", 2.5),
        ("grading", 1.5),
        ("office hours", 2.0),
        ("lecture", 1.0),
    ],
    QueryIntent.COURSE: [
        ("ecs ", 2.5),
        ("mat ", 2.5),
        ("phy ", 2.5),
        ("che ", 2.5),
        ("bis ", 2.5),
        ("sta ", 2.5),
        ("eng ", 2.0),
        ("course", 2.5),
        ("class", 2.0),
        ("prerequisite", 2.5),
        ("prereq", 2.5),
        ("midterm", 2.0),
        ("final exam", 2.0),
        ("syllabus", 2.5),
        ("units", 1.5),
        ("credit", 1.5),
        ("ge ", 2.0),
        ("major", 1.5),
        ("minor", 1.5),
        ("schedule", 1.5),
        ("enroll", 2.0),
        ("waitlist", 2.0),
    ],
    QueryIntent.HOUSING: [
        ("housing", 3.0),
        ("dorm", 3.0),
        ("apartment", 2.5),
        ("rent", 2.5),
        ("lease", 2.0),
        ("roommate", 2.5),
        ("move in", 2.0),
        ("residence hall", 3.0),
        ("tercero", 2.5),
        ("segundo", 2.5),
        ("cuarto", 2.5),
        ("living", 1.5),
        ("sublease", 2.5),
    ],
    QueryIntent.DINING: [
        ("dining", 3.0),
        ("food", 2.5),
        ("eat", 2.0),
        ("restaurant", 2.5),
        ("meal plan", 3.0),
        ("dc", 1.5),
        ("dining commons", 3.0),
        ("cafe", 2.0),
        ("coffee", 2.0),
        ("hungry", 2.0),
        ("silo", 2.0),
        ("coho", 2.0),
    ],
    QueryIntent.CAMPUS_RESOURCE: [
        ("tutoring", 3.0),
        ("counseling", 3.0),
        ("mental health", 3.0),
        ("health center", 3.0),
        ("career center", 3.0),
        ("financial aid", 3.0),
        ("scholarship", 2.5),
        ("library", 2.5),
        ("club", 2.0),
        ("organization", 2.0),
        ("recreation", 2.0),
        ("arc", 2.0),
        ("pantry", 2.5),
        ("basic needs", 3.0),
        ("shcs", 3.0),
        ("aatc", 3.0),
        ("internship", 2.0),
        ("job", 1.5),
        ("resume", 2.0),
    ],
    QueryIntent.LOCATION: [
        ("where is", 3.0),
        ("how to get to", 3.0),
        ("directions", 2.5),
        ("location", 2.0),
        ("building", 2.0),
        ("map", 2.5),
        ("parking", 2.5),
        ("bus", 2.0),
        ("unitrans", 3.0),
        ("bike", 2.0),
        ("walk", 1.5),
    ],
}

# Regex patterns for professor name detection (First Last)
_PROFESSOR_NAME_PATTERN = re.compile(
    r"\b(?:prof(?:essor)?\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)

_NAME_BLACKLIST = {
    "University", "Davis", "Quarter", "Course", "Spring",
    "Winter", "Fall", "Summer", "Monday", "Tuesday",
    "Wednesday", "Thursday", "Friday", "Computer", "Science",
    "Engineering", "General", "Education", "College", "Office",
    "Student", "Center", "Academic", "United", "States",
    "Rate", "Professor", "Campus", "Aggie", "Sacramento",
}

# Course code pattern (e.g., ECS 36A, MAT 21D, PHY 9A)
_COURSE_CODE_PATTERN = re.compile(
    r"\b([A-Z]{2,4})\s*(\d{1,3}[A-Z]?)\b"
)


def classify_query(message: str) -> QueryIntent:
    """
    Classify a user message into an intent category.

    Scoring:
        1. Normalize the message to lowercase.
        2. For each intent, sum the weights of all matching keywords.
        3. Apply bonus points for regex pattern matches (professor names,
           course codes).
        4. Return the intent with the highest score, defaulting to GENERAL.
    """
    lower = message.lower()
    scores: dict[QueryIntent, float] = {intent: 0.0 for intent in QueryIntent}

    # Keyword scoring
    for intent, keywords in _INTENT_KEYWORDS.items():
        for keyword, weight in keywords:
            if keyword in lower:
                scores[intent] += weight

    # Pattern bonuses
    if _COURSE_CODE_PATTERN.search(message):
        scores[QueryIntent.COURSE] += 4.0

    if extract_professor_names(message):
        scores[QueryIntent.PROFESSOR] += 4.0

    # Find the best intent
    best_intent = QueryIntent.GENERAL
    best_score = 0.0

    for intent, score in scores.items():
        if score > best_score:
            best_score = score
            best_intent = intent

    # Only assign a specific intent if the score passes a minimum threshold
    if best_score < 1.5:
        return QueryIntent.GENERAL

    return best_intent


def extract_professor_names(text: str) -> list[str]:
    """
    Pull probable professor names from a query string.

    Uses a capitalized-word pattern and filters against a blacklist
    of common UC Davis terms that would cause false positives.
    """
    if not text:
        return []

    matches = _PROFESSOR_NAME_PATTERN.findall(text.replace("\n", " "))

    cleaned = [
        name.strip()
        for name in matches
        if all(word not in _NAME_BLACKLIST for word in name.split())
    ]

    return list(set(cleaned))


def extract_course_codes(text: str) -> list[str]:
    """
    Extract course codes like 'ECS 36A' or 'MAT 21D' from a query.
    Returns a list of normalized codes (uppercase, single space).
    """
    matches = _COURSE_CODE_PATTERN.findall(text.upper())
    return [f"{dept} {num}" for dept, num in matches]
