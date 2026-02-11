from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict, Any
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Curated UC Davis resources (MVP "RAG") ----
AGGIE_RESOURCES = [
    {"id":"aggie_mental_health","title":"Aggie Mental Health","tags":["mental_health"]},
    {"id":"aggie_compass","title":"Aggie Compass - Basic Needs","tags":["basic_needs"]},
    {"id":"asucd_pantry","title":"ASUCD Pantry","tags":["basic_needs","food"]},
    {"id":"shcs","title":"Student Health and Counseling Services","tags":["health","counseling"]},
    {"id":"career_center","title":"Career Center","tags":["career"]},
    {"id":"aatc","title":"AATC","tags":["academics","tutoring"]},
    {"id":"care","title":"CARE (sexual assault/harassment resource center)","tags":["safety","support"]},
    # add the rest from your list as needed
]

Tone = Literal["friendly", "neutral", "formal"]
Depth = Literal["short", "medium", "detailed"]

class Preferences(BaseModel):
    tone: Tone = "friendly"
    depth: Depth = "medium"
    use_ucd_sources: bool = True
    show_references: bool = True
    model: str = "hf:mistralai/Mistral-7B-Instruct"  # example default

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    preferences: Preferences = Preferences()

class Reference(BaseModel):
    title: str
    type: str
    id: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    used_model: str
    references: List[Reference] = []
    safety: Dict[str, Any] = {"category": "none"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/resources")
def resources():
    return {"resources": AGGIE_RESOURCES}

def pick_resources(message: str) -> List[dict]:
    """MVP keyword routing to curated Aggie resources."""
    msg = message.lower()
    refs = []
    if any(k in msg for k in ["anxious", "depressed", "therapy", "counsel", "stress"]):
        refs += [r for r in AGGIE_RESOURCES if r["id"] in ["shcs", "aggie_mental_health"]]
    if any(k in msg for k in ["food", "hungry", "pantry", "money", "rent", "basic needs"]):
        refs += [r for r in AGGIE_RESOURCES if r["id"] in ["aggie_compass", "asucd_pantry"]]
    if any(k in msg for k in ["job", "intern", "resume", "career"]):
        refs += [r for r in AGGIE_RESOURCES if r["id"] == "career_center"]
    if any(k in msg for k in ["tutor", "class help", "study", "academic"]):
        refs += [r for r in AGGIE_RESOURCES if r["id"] == "aatc"]
    return refs[:3]

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # 1) Curated "RAG" context
    refs = pick_resources(req.message) if req.preferences.use_ucd_sources else []

    # 2) Build a reply (MVP: placeholder; replace with Hugging Face call)
    tone = req.preferences.tone
    if tone == "friendly":
        intro = "Got you — "
    elif tone == "formal":
        intro = "Understood. "
    else:
        intro = ""

    reply = intro + f'you asked: "{req.message}".'
    if refs:
        reply += "\n\nHelpful UC Davis resources:"
        for r in refs:
            reply += f"\n- {r['title']}"

    # 3) Return structured response
    return {
        "reply": reply,
        "session_id": session_id,
        "used_model": req.preferences.model,
        "references": [{"title": r["title"], "type": "ucd_resource", "id": r["id"]} for r in refs] if req.preferences.show_references else [],
        "safety": {"category": "none"},
    }
