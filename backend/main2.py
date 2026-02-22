from __future__ import annotations

import asyncio
import os
from typing import List

from ddgs import DDGS
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel, Field
import googlemaps


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
    return {"ok": True, "routes": ["/docs", "/redoc", "/chat"]}


# ------------------------------------------------------------------------------
# Env + LLM + Vector Store
# ------------------------------------------------------------------------------

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY is not set. /chat will fail until it's set.")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

# Load the UC Davis knowledge base vector store
print("Loading UC Davis knowledge base...")
embeddings = OpenAIEmbeddings()
vectorstore = None
try:
    vectorstore = FAISS.load_local(
    "faiss_db",
    embeddings,
    allow_dangerous_deserialization=True
)
    print("✓ UC Davis knowledge base loaded!")
except Exception as e:
    print(f"WARNING: Could not load vector store: {e}")
    print("Make sure you've run build_vectorstore.py first!")

# Initialize Google Maps client
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
                f"Result {i}:\n"
                f"Title: {r.get('title', 'N/A')}\n"
                f"Content: {r.get('body', 'N/A')}\n"
                f"URL: {r.get('href', 'N/A')}\n"
            )

        return "\n---\n".join(formatted)

    except Exception as e:
        print(f"Search error: {e}")
        return ""


# ------------------------------------------------------------------------------
# Google Maps search helper
# ------------------------------------------------------------------------------

async def search_campus_location(query: str) -> str:
    """Search for UC Davis campus locations using Google Maps API."""
    if not gmaps:
        return ""
    
    try:
        def do_maps_search():
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
            
            location = place.get('geometry', {}).get('location', {})
            lat = location.get('lat', 'N/A')
            lng = location.get('lng', 'N/A')
            
            formatted.append(
                f"Location {i}:\n"
                f"Name: {name}\n"
                f"Address: {address}\n"
                f"Rating: {rating}\n"
                f"Coordinates: {lat}, {lng}\n"
            )
        
        return "\n---\n".join(formatted)
    
    except Exception as e:
        print(f"Google Maps API error: {e}")
        return ""


# ------------------------------------------------------------------------------
# Prompt + Schemas
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant.

IMPORTANT: When information is provided to you from the UC Davis knowledge base, Reddit, or Google Maps, you MUST use it to answer questions. This information is REAL and CURRENT.

You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area

You have access to:
1. UC Davis knowledge base (campus info, dining, housing, buildings, etc.)
2. Reddit search for current student opinions and experiences
3. Google Maps for precise location and address information

When information is provided:
- Use the UC Davis knowledge base as your primary source
- Reference Reddit posts when discussing student opinions: "According to recent Reddit posts..."
- Cite Google Maps data for locations and addresses
- Be specific and detailed using the provided information

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
        # STEP 1: Search UC Davis knowledge base
        uc_davis_context = ""
        if vectorstore:
            print("Searching UC Davis knowledge base...")
            relevant_docs = await asyncio.to_thread(
                vectorstore.similarity_search,
                req.message,
                k=3  # Get top 3 most relevant chunks
            )
            
            if relevant_docs:
                uc_davis_context = "\n\n".join([doc.page_content for doc in relevant_docs])
                print(f"Found {len(relevant_docs)} relevant documents from knowledge base")
        
        # STEP 2: Check if we should search Reddit
        search_keywords = [
            "reddit", "recent", "latest", "current", "today",
            "this year", "right now", "people say", "students think",
            "opinions", "reviews", "experiences", "what's it like",
            "best", "worst", "recommend"
        ]
        needs_web_search = any(k in req.message.lower() for k in search_keywords)

        # STEP 3: Check for location-related queries
        location_keywords = [
            "where", "location", "address", "directions", "find",
            "building", "place", "near", "close", "map", "how to get"
        ]
        needs_maps = any(k in req.message.lower() for k in location_keywords)

        # STEP 4: Collect results from multiple sources
        web_results = ""
        
        # Search Reddit if needed
        if needs_web_search:
            print(f"Searching Reddit for: {req.message}")
            reddit_data = await search_reddit(req.message)
            if reddit_data:
                web_results += f"\n=== Reddit Posts ===\n{reddit_data}\n"
                print("Found Reddit results")

        # Search Google Maps if needed
        if needs_maps:
            print(f"Searching Google Maps for: {req.message}")
            maps_data = await search_campus_location(req.message)
            if maps_data:
                web_results += f"\n=== Campus Locations (Google Maps) ===\n{maps_data}\n"
                print("Found Google Maps results")

        # STEP 5: Build the final user prompt with all context
        context_parts = []
        
        if uc_davis_context:
            context_parts.append(f"=== UC Davis Knowledge Base ===\n{uc_davis_context}")
        
        if web_results:
            context_parts.append(web_results.strip())
        
        if context_parts:
            current_message = "\n\n".join(context_parts) + f"\n\n---\n\nUser question: {req.message}"
        else:
            current_message = req.message

        # STEP 6: Build LangChain message list
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        for m in req.conversation_history:
            if m.role == "user":
                messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages.append(AIMessage(content=m.content))

        messages.append(HumanMessage(content=current_message))

        print(f"Sending {len(messages)} messages to LLM")

        # Invoke LLM
        response = await asyncio.to_thread(llm.invoke, messages)
        print("Response generated")

        return {"response": response.content}

    except Exception as e:
        print("Error generating response:", str(e))
        raise HTTPException(status_code=500, detail=str(e))