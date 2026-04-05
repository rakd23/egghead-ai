"""
Curated UC Davis campus resources.

These are hand-maintained links to official university services.
The classifier routes campus_resource queries here, and the results
are returned as CampusResource objects alongside ranked search results.
"""

from models import CampusResource, QueryIntent

# ── Resource Database ────────────────────────────────────────────────────

RESOURCES: list[dict] = [
    {
        "name": "Student Health and Counseling Services (SHCS)",
        "category": "health",
        "url": "https://shcs.ucdavis.edu/",
        "description": "Medical appointments, counseling, and crisis support.",
        "keywords": ["health", "counseling", "therapy", "doctor", "medical", "sick", "mental health", "anxiety", "depression", "stress"],
    },
    {
        "name": "Aggie Mental Health",
        "category": "mental_health",
        "url": "https://shcs.ucdavis.edu/services/counseling-services",
        "description": "Free counseling sessions and mental health workshops for students.",
        "keywords": ["mental health", "anxiety", "depression", "counseling", "therapy", "stress", "lonely"],
    },
    {
        "name": "CARE (Center for Advocacy, Resources & Education)",
        "category": "safety",
        "url": "https://care.ucdavis.edu/",
        "description": "Confidential support for sexual/domestic violence and stalking.",
        "keywords": ["assault", "harassment", "violence", "safety", "stalking", "abuse"],
    },
    {
        "name": "Aggie Compass (Basic Needs)",
        "category": "basic_needs",
        "url": "https://aggiecompass.ucdavis.edu/",
        "description": "Emergency food, housing, and financial assistance.",
        "keywords": ["food", "hungry", "homeless", "money", "emergency", "basic needs", "financial hardship"],
    },
    {
        "name": "ASUCD Pantry",
        "category": "food",
        "url": "https://pantry.ucdavis.edu/",
        "description": "Free groceries available to all UC Davis students.",
        "keywords": ["food", "pantry", "groceries", "hungry", "free food"],
    },
    {
        "name": "Internship and Career Center (ICC)",
        "category": "career",
        "url": "https://icc.ucdavis.edu/",
        "description": "Resume reviews, career fairs, job/internship listings, and mock interviews.",
        "keywords": ["job", "intern", "internship", "resume", "career", "interview", "hire", "employment"],
    },
    {
        "name": "Academic Assistance and Tutoring Centers (AATC)",
        "category": "academics",
        "url": "https://tutoring.ucdavis.edu/",
        "description": "Free tutoring for math, science, writing, and more.",
        "keywords": ["tutor", "tutoring", "study", "help", "academic", "study group", "homework"],
    },
    {
        "name": "Financial Aid Office",
        "category": "financial",
        "url": "https://financialaid.ucdavis.edu/",
        "description": "FAFSA help, scholarships, grants, and work-study.",
        "keywords": ["financial aid", "fafsa", "scholarship", "grant", "loan", "money", "tuition"],
    },
    {
        "name": "Activities and Recreation Center (ARC)",
        "category": "recreation",
        "url": "https://campusrecreation.ucdavis.edu/",
        "description": "Gym facilities, intramural sports, and group fitness classes.",
        "keywords": ["gym", "arc", "workout", "fitness", "exercise", "recreation", "sports", "intramural"],
    },
    {
        "name": "UC Davis Library",
        "category": "academics",
        "url": "https://library.ucdavis.edu/",
        "description": "Shields Library, study rooms, research databases, and printing.",
        "keywords": ["library", "study", "shields", "books", "printing", "study room", "research"],
    },
    {
        "name": "Unitrans",
        "category": "transportation",
        "url": "https://unitrans.ucdavis.edu/",
        "description": "Free bus service for UC Davis students throughout Davis.",
        "keywords": ["bus", "unitrans", "transportation", "ride", "commute"],
    },
    {
        "name": "UC Davis Police Department",
        "category": "safety",
        "url": "https://police.ucdavis.edu/",
        "description": "Campus police, safety escorts, and emergency services.",
        "keywords": ["police", "safety", "emergency", "escort", "crime", "911"],
    },
]


def match_resources(
    message: str,
    intent: QueryIntent,
    max_results: int = 3,
) -> list[CampusResource]:
    """
    Match curated resources to a query using keyword overlap scoring.

    Each resource has a list of keywords. The score is the count of
    keywords found in the message, weighted by intent relevance.
    """
    lower = message.lower()

    scored: list[tuple[int, dict]] = []
    for resource in RESOURCES:
        score = sum(1 for kw in resource["keywords"] if kw in lower)

        # Boost resources whose category matches the intent
        if intent == QueryIntent.CAMPUS_RESOURCE:
            score += 1  # always slightly boost for resource queries

        if score > 0:
            scored.append((score, resource))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        CampusResource(
            name=r["name"],
            category=r["category"],
            url=r.get("url"),
            description=r.get("description", ""),
        )
        for _, r in scored[:max_results]
    ]
