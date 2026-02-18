from __future__ import annotations

import asyncio
import os
from typing import List

from ddgs import DDGS
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import googlemaps  # NEW: Google Maps import


# ------------------------------------------------------------------------------
# App + CORS
# ------------------------------------------------------------------------------

app = FastAPI()

# Allow your Next.js dev server to call this backend from the browser
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

# Optional: nice sanity check so "/" doesn't return {"detail":"Not Found"}
@app.get("/")
def root():
    return {"ok": True, "routes": ["/docs", "/redoc", "/chat"]}


# ------------------------------------------------------------------------------
# Env + LLM
# ------------------------------------------------------------------------------

load_dotenv()

# Make sure OPENAI_API_KEY is set in your environment or in a .env file
# e.g. backend/.env with OPENAI_API_KEY=...
if not os.getenv("OPENAI_API_KEY"):
    # Don't hard-fail here; just print a useful message.
    print("WARNING: OPENAI_API_KEY is not set. /chat will fail until it's set.")

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
)

# NEW: Initialize Google Maps client
gmaps = None
if os.getenv("GOOGLE_MAPS_API_KEY"):
    gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
else:
    print("WARNING: GOOGLE_MAPS_API_KEY is not set. Location search will be disabled.")


# ------------------------------------------------------------------------------
# Reddit search helper
# ------------------------------------------------------------------------------

async def search_reddit(query: str) -> str:
    """Search UC Davis subreddit using DuckDuckGo results constrained to r/UCDavis."""
    try:
        def do_search():
            with DDGS() as ddgs:
                return list(
                    ddgs.text(
                        f"{query} site:reddit.com/r/ucdavis",
                        max_results=5,
                    )
                )

        results = await asyncio.to_thread(do_search)

        if not results:
            return ""

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                "Result {i}:\n"
                "Title: {title}\n"
                "Content: {body}\n"
                "URL: {href}\n".format(
                    i=i,
                    title=r.get("title", "N/A"),
                    body=r.get("body", "N/A"),
                    href=r.get("href", "N/A"),
                )
            )

        return "\n---\n".join(formatted)

    except Exception as e:
        print(f"Search error: {e}")
        return ""


# NEW: Google Maps search helper
# ------------------------------------------------------------------------------

async def search_campus_location(query: str) -> str:
    """Search for UC Davis campus locations using Google Maps API."""
    if not gmaps:
        return ""
    
    try:
        def do_maps_search():
            # Search for places near UC Davis
            places_result = gmaps.places(
                query=f"{query} UC Davis",
                location=(38.5382, -121.7617),  # UC Davis coordinates
                radius=3000  # 3km radius
            )
            return places_result
        
        places_result = await asyncio.to_thread(do_maps_search)
        
        if not places_result.get('results'):
            return ""
        
        formatted = []
        for i, place in enumerate(places_result['results'][:5], 1):
            name = place.get('name', 'N/A')
            address = place.get('formatted_address', 'N/A')
            rating = place.get('rating', 'N/A')
            
            # Get coordinates if available
            location = place.get('geometry', {}).get('location', {})
            lat = location.get('lat', 'N/A')
            lng = location.get('lng', 'N/A')
            
            formatted.append(
                "Location {i}:\n"
                "Name: {name}\n"
                "Address: {address}\n"
                "Rating: {rating}\n"
                "Coordinates: {lat}, {lng}\n".format(
                    i=i,
                    name=name,
                    address=address,
                    rating=rating,
                    lat=lat,
                    lng=lng,
                )
            )
        
        return "\n---\n".join(formatted)
    
    except Exception as e:
        print(f"Google Maps API error: {e}")
        return ""


# ------------------------------------------------------------------------------
# Prompt + Schemas
# ------------------------------------------------------------------------------

# UPDATED: System prompt to mention location capabilities
SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant.

You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area

You have access to:
1. Web search to find current information from the UC Davis Reddit community (r/UCDavis)
2. Google Maps API to find campus locations, buildings, and nearby places

When search results are provided:
- Use the actual content from Reddit posts to answer questions
- Cite specific opinions or information from the posts
- Mention that the information comes from UC Davis Reddit or Google Maps
- Summarize multiple perspectives if available
- For locations, provide specific addresses and directions when available

Always be enthusiastic about UC Davis and provide accurate, helpful information.
"""

class HistoryMessage(BaseModel):
    role: str = Field(..., description='Either "user" or "assistant"')
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[HistoryMessage] = []


# ------------------------------------------------------------------------------
# Chat endpoint
# ------------------------------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        # Decide if we should do a reddit search
        search_keywords = [
            "reddit", "recent", "latest", "current", "today",
            "this year", "right now", "people say", "students think",
            "opinions", "reviews", "experiences", "what's it like",
            "best", "worst", "recommend", "class",
        ]
        needs_web_search = any(k in req.message.lower() for k in search_keywords)

        # NEW: Check for location-related queries
        location_keywords = [
            "where", "location", "address", "directions", "find",
            "building", "place", "near", "close", "map", "how to get"
        ]
        needs_maps = any(k in req.message.lower() for k in location_keywords)

        # NEW: Collect results from multiple sources
        web_results = ""
        
        # Search Reddit if needed
        if needs_web_search:
            print(f"Searching Reddit for: {req.message}")
            reddit_data = await search_reddit(req.message)
            if reddit_data:
                web_results += f"\n=== Reddit Posts ===\n{reddit_data}\n"
                print("Found Reddit results")

        # NEW: Search Google Maps if needed
        if needs_maps:
            print(f"Searching Google Maps for: {req.message}")
            maps_data = await search_campus_location(req.message)
            if maps_data:
                web_results += f"\n=== Campus Locations (Google Maps) ===\n{maps_data}\n"
                print("Found Google Maps results")

        # Build the final user prompt
        if web_results:
            current_message = (
                f"{web_results}\n\n"
                f"User question: {req.message}\n\n"
                "Please use the above information to provide an informed answer."
            )
        else:
            current_message = req.message

        # Build LangChain message list
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        for m in req.conversation_history:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages.append(AIMessage(content=m.content))

        messages.append(HumanMessage(content=current_message))

        # Invoke LLM (in a thread so we don't block event loop)
        response = await asyncio.to_thread(llm.invoke, messages)

        return {"response": response.content}

    except Exception as e:
        print("Error generating response:", str(e))
        raise HTTPException(status_code=500, detail=str(e))