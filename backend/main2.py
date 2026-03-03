from __future__ import annotations

from supabase import create_client, Client

import asyncio
import os
from typing import List, Optional
import re
import base64

from ddgs import DDGS
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field
import googlemaps
import requests
from bs4 import BeautifulSoup


# ------------------------------------------------------------------------------
# App + CORS
# ------------------------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "routes": ["/docs", "/redoc", "/chat", "/upload-image"]}


# ------------------------------------------------------------------------------
# Env + LLM + Supabase
# ------------------------------------------------------------------------------

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
vision_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

print("Connecting to Supabase...")
embeddings = OpenAIEmbeddings()
supabase_client = None

try:
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        supabase_client: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY"),
        )
        print("✓ Connected to Supabase!")
except Exception as e:
    print(f"Supabase connection error: {e}")

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY")) \
    if os.getenv("GOOGLE_MAPS_API_KEY") else None


# ------------------------------------------------------------------------------
# Image Upload & Parsing Endpoint
# ------------------------------------------------------------------------------

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        content = await file.read()

        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            raise HTTPException(status_code=400, detail="Invalid image type")

        base64_image = base64.b64encode(content).decode("utf-8")

        def parse():
            message = HumanMessage(
                content=[
                    {"type": "text", "text": "Extract all text from this image."},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
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
# RateMyProfessor scraper
# ------------------------------------------------------------------------------

async def search_rate_my_professor(professor_name: str) -> str:
    try:
        def scrape():
            import urllib.parse
            encoded = urllib.parse.quote(professor_name)

            url = f"https://www.ratemyprofessors.com/search/professors/1073?q={encoded}"

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.ratemyprofessors.com/",
            }

            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            cards = soup.find_all("a", href=lambda h: h and "/professor/" in h)
            if not cards:
                return None

            prof_url = "https://www.ratemyprofessors.com" + cards[0]["href"]
            prof_page = requests.get(prof_url, headers=headers, timeout=10)

            text = prof_page.text

            rating = re.search(r'"avgRating":([\d.]+)', text)
            difficulty = re.search(r'"avgDifficulty":([\d.]+)', text)
            num = re.search(r'"numRatings":(\d+)', text)
            again = re.search(r'"wouldTakeAgainPercent":([\d.]+)', text)
            dept = re.search(r'"department":"([^"]+)"', text)
            name = re.search(r'"firstName":"([^"]+)","lastName":"([^"]+)"', text)

            if rating:
                return {
                    "name": f"{name.group(1)} {name.group(2)}" if name else professor_name,
                    "rating": rating.group(1),
                    "difficulty": difficulty.group(1) if difficulty else "N/A",
                    "num": num.group(1) if num else "N/A",
                    "again": again.group(1) if again else "N/A",
                    "dept": dept.group(1) if dept else "N/A",
                }

            return None

        result = await asyncio.to_thread(scrape)

        if not result:
            return ""

        return f"""RateMyProfessor Results for {result['name']}:
Overall Rating: {result['rating']}/5.0
Difficulty: {result['difficulty']}/5.0
Department: {result['dept']}
Number of Ratings: {result['num']}
Would Take Again: {result['again']}%"""

    except Exception as e:
        print("RMP error:", e)
        return ""


# ------------------------------------------------------------------------------
# Reddit search
# ------------------------------------------------------------------------------

async def search_reddit(query: str) -> str:
    try:
        def run():
            with DDGS() as ddgs:
                return list(ddgs.text(f"{query} site:reddit.com/r/ucdavis", max_results=5))

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
# Google Maps search helper
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
# Prompt + Schemas
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant.
Use provided knowledge base, Reddit, Google Maps, RateMyProfessor,
and uploaded image content when available.
Be specific and accurate.
"""

class HistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[HistoryMessage] = []
    image_content: Optional[str] = None


# ------------------------------------------------------------------------------
# Chat endpoint
# ------------------------------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        uc_davis_context = ""
        web_results = ""

        # STEP 1: Knowledge base search
        if supabase_client:
            query_embedding = await asyncio.to_thread(
                embeddings.embed_query, req.message
            )

            def search():
                return supabase_client.rpc(
                    "match_documents",
                    {"query_embedding": query_embedding, "match_count": 10},
                ).execute()

            res = await asyncio.to_thread(search)
            if res.data:
                uc_davis_context = "\n\n".join(
                    d["content"] for d in res.data
                )

        # STEP 2: Auto-detect professors (message + image)
        combined_text = req.message
        if req.image_content:
            combined_text += " " + req.image_content

        names = re.findall(r"(?:Professor\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", combined_text)

        for name in names[:2]:
            rmp = await search_rate_my_professor(name)
            if rmp:
                web_results += f"\n=== {rmp} ===\n"

        # STEP 3: Reddit
        reddit = await search_reddit(req.message)
        if reddit:
            web_results += f"\n=== Reddit ===\n{reddit}\n"

        # STEP 4: Maps
        maps = await search_campus_location(req.message)
        if maps:
            web_results += f"\n=== Maps ===\n{maps}\n"

        # STEP 5: Build prompt
        context = []
        if req.image_content:
            context.append(f"=== Image Content ===\n{req.image_content}")
        if uc_davis_context:
            context.append(f"=== Knowledge Base ===\n{uc_davis_context}")
        if web_results:
            context.append(web_results)

        final_message = "\n\n".join(context) + f"\n\nUser question: {req.message}"

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
