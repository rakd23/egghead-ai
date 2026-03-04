from __future__ import annotations

import asyncio
import os
import re
import base64
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from supabase import create_client, Client
from ddgs import DDGS
import googlemaps
import requests


# ------------------------------------------------------------------------------
# App + CORS
# ------------------------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://egghead-ai-tau.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "routes": ["/docs", "/redoc", "/chat", "/upload-image"]}


# ------------------------------------------------------------------------------
# Env + Models
# ------------------------------------------------------------------------------

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
vision_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

embeddings = OpenAIEmbeddings()

supabase_client = None
if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
    supabase_client: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )
    print("✓ Connected to Supabase")

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY")) \
    if os.getenv("GOOGLE_MAPS_API_KEY") else None


# ------------------------------------------------------------------------------
# SYSTEM PROMPT
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a helpful and friendly UC Davis campus assistant.

CRITICAL RULES:
- Only show RateMyProfessor ratings if actual data was retrieved.
- If no rating data was found, say:
  "No RateMyProfessor data was found for this professor."
- Never fabricate ratings.
- Prefer real retrieved data over assumptions.
"""


# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[HistoryMessage] = []
    image_content: Optional[str] = None


# ------------------------------------------------------------------------------
# Image Upload Endpoint
# ------------------------------------------------------------------------------

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        content = await file.read()

        if not file.filename.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp")
        ):
            raise HTTPException(status_code=400, detail="Invalid image type")

        base64_image = base64.b64encode(content).decode("utf-8")

        def parse():
            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Extract all readable text from this image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ]
            )
            return vision_llm.invoke([message]).content

        extracted = await asyncio.to_thread(parse)

        return {
            "text": extracted,
            "filename": file.filename,
            "length": len(extracted)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# Professor Name Extraction
# ------------------------------------------------------------------------------

def extract_professor_names(text: str) -> List[str]:
    """
    Extracts First + Last names only.
    Avoids random capitalized words.
    """
    if not text:
        return []

    text = text.replace("\n", " ")

    pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    matches = re.findall(pattern, text)

    blacklist = {"University", "Davis", "Quarter", "Course"}

    cleaned = [
        m.strip()
        for m in matches
        if all(word not in blacklist for word in m.split())
    ]

    return list(set(cleaned))


# ------------------------------------------------------------------------------
# RateMyProfessor Search
# ------------------------------------------------------------------------------

async def search_rate_my_professor(professor_name: str) -> Optional[str]:
    """
    Uses DuckDuckGo to find RMP page.
    Then extracts rating data from embedded JSON.
    """

    try:
        def search():
            with DDGS() as ddgs:
                return list(
                    ddgs.text(
                        f"{professor_name} UC Davis RateMyProfessor",
                        max_results=5
                    )
                )

        results = await asyncio.to_thread(search)

        if not results:
            return None

        rmp_link = None
        for r in results:
            if "ratemyprofessors.com/professor" in r.get("href", ""):
                rmp_link = r["href"]
                break

        if not rmp_link:
            return None

        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(rmp_link, headers=headers, timeout=10)

        if res.status_code != 200:
            return None

        text = res.text

        rating = re.search(r'"avgRating":([\d.]+)', text)
        difficulty = re.search(r'"avgDifficulty":([\d.]+)', text)
        num = re.search(r'"numRatings":(\d+)', text)
        again = re.search(r'"wouldTakeAgainPercent":([\d.]+)', text)
        dept = re.search(r'"department":"([^"]+)"', text)

        if not rating:
            return None

        return f"""RateMyProfessor Results for {professor_name}:
Overall Rating: {rating.group(1)}/5.0
Difficulty: {difficulty.group(1) if difficulty else "N/A"}/5.0
Department: {dept.group(1) if dept else "N/A"}
Number of Ratings: {num.group(1) if num else "N/A"}
Would Take Again: {again.group(1) if again else "N/A"}%
Profile: {rmp_link}
"""

    except Exception as e:
        print("RMP error:", e)
        return None


# ------------------------------------------------------------------------------
# Reddit Search
# ------------------------------------------------------------------------------

async def search_reddit(query: str) -> str:
    try:
        def run():
            with DDGS() as ddgs:
                return list(
                    ddgs.text(f"{query} site:reddit.com/r/ucdavis", max_results=5)
                )

        results = await asyncio.to_thread(run)

        if not results:
            return ""

        return "\n---\n".join(
            f"Title: {r.get('title')}\nContent: {r.get('body')}\nURL: {r.get('href')}"
            for r in results
        )

    except:
        return ""


# ------------------------------------------------------------------------------
# Google Maps Search
# ------------------------------------------------------------------------------

async def search_campus_location(query: str) -> str:
    if not gmaps:
        return ""

    try:
        def run():
            return gmaps.places(
                query=f"{query} UC Davis",
                location=(38.5382, -121.7617),
                radius=3000,
            )

        results = await asyncio.to_thread(run)

        if not results.get("results"):
            return ""

        formatted = []
        for p in results["results"][:5]:
            formatted.append(
                f"{p.get('name')} | {p.get('formatted_address')} | Rating: {p.get('rating')}"
            )

        return "\n".join(formatted)

    except:
        return ""


# ------------------------------------------------------------------------------
# Chat Endpoint
# ------------------------------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        uc_davis_context = ""
        web_results = ""

        # STEP 1 — Vector search
        if supabase_client:
            query_embedding = await asyncio.to_thread(
                embeddings.embed_query, req.message
            )

            def search():
                return supabase_client.rpc(
                    "match_documents",
                    {"query_embedding": query_embedding, "match_count": 5},
                ).execute()

            res = await asyncio.to_thread(search)

            if res.data:
                uc_davis_context = "\n\n".join(d["content"] for d in res.data)

        # STEP 2 — Professor Detection
        combined_text = req.message or ""
        if req.image_content:
            combined_text += " " + req.image_content

        names = extract_professor_names(combined_text)
        print("Detected professors:", names)

        if names:
            for name in names:
                rmp_data = await search_rate_my_professor(name)
                if rmp_data:
                    web_results += f"\n=== RateMyProfessor ===\n{rmp_data}\n"
                else:
                    web_results += f"\nNo RateMyProfessor data was found for {name}.\n"
        else:
            if "professor" in req.message.lower():
                web_results += "\nPlease provide the full professor name (First and Last).\n"

        # STEP 3 — Reddit
        reddit = await search_reddit(req.message)
        if reddit:
            web_results += f"\n=== Reddit ===\n{reddit}\n"

        # STEP 4 — Maps
        maps = await search_campus_location(req.message)
        if maps:
            web_results += f"\n=== Maps ===\n{maps}\n"

        # STEP 5 — Build Prompt
        context_blocks = []

        if req.image_content:
            context_blocks.append(f"=== Image Content ===\n{req.image_content}")

        if uc_davis_context:
            context_blocks.append(f"=== Knowledge Base ===\n{uc_davis_context}")

        if web_results:
            context_blocks.append(web_results)

        final_message = "\n\n".join(context_blocks) + f"\n\nUser question: {req.message}"

        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        for m in req.conversation_history:
            messages.append(
                HumanMessage(content=m.content)
                if m.role == "user"
                else AIMessage(content=m.content)
            )

        messages.append(HumanMessage(content=final_message))

        response = await asyncio.to_thread(llm.invoke, messages)

        return {"response": response.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))