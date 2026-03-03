from __future__ import annotations

from ratemyprof import RateMyProfScraper
ucdavis_rmp = RateMyProfScraper(1073)



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

if not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY is not set. /chat will fail until it's set.")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

# Vision model for image parsing
vision_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

# Connect to Supabase
print("Connecting to Supabase...")
embeddings = OpenAIEmbeddings()
supabase_client = None

try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if supabase_url and supabase_key:
        supabase_client: Client = create_client(supabase_url, supabase_key)
        print("✓ Connected to Supabase!")
    else:
        print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
except Exception as e:
    print(f"WARNING: Could not connect to Supabase: {e}")

# Initialize Google Maps client
gmaps = None
if os.getenv("GOOGLE_MAPS_API_KEY"):
    gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
else:
    print("WARNING: GOOGLE_MAPS_API_KEY is not set. Location search will be disabled.")

# Initialize RateMyProfessor scraper for UC Davis
ucdavis = RateMyProfScraper(1082)  # 1082 is UC Davis school ID


# ------------------------------------------------------------------------------
# Image Upload & Parsing Endpoint
# ------------------------------------------------------------------------------

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Parse text/content from uploaded images using GPT-4 Vision"""
    try:
        content = await file.read()
        
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            raise HTTPException(status_code=400, detail="File must be an image (png, jpg, jpeg, gif, webp)")
        
        base64_image = base64.b64encode(content).decode('utf-8')
        
        print(f"Processing image: {file.filename}")
        
        def parse_image():
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Extract all text from this image. If it's a document, transcribe it exactly. If it's a photo/diagram, describe what you see in detail. Be thorough and accurate."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            )
            
            response = vision_llm.invoke([message])
            return response.content
        
        extracted_text = await asyncio.to_thread(parse_image)
        
        print(f"Extracted {len(extracted_text)} characters from image")
        
        return {
            "text": extracted_text,
            "filename": file.filename,
            "length": len(extracted_text)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


# ------------------------------------------------------------------------------
# RateMyProfessor search
# ------------------------------------------------------------------------------

async def search_rate_my_professor(professor_name: str) -> str:
    """Search RateMyProfessor for UC Davis professors"""
    try:
        def do_search():
            result = ucdavis.SearchProfessor(professor_name)
            return result
        
        result = await asyncio.to_thread(do_search)
        
        if not result:
            return ""
        
        return f"""RateMyProfessor Results for {professor_name}:
Overall Rating: {result.get('overall_rating', 'N/A')}/5.0
Department: {result.get('tDept', 'N/A')}
Number of Ratings: {result.get('tNumRatings', 'N/A')}
Rating Class: {result.get('rating_class', 'N/A')}"""
    
    except Exception as e:
        print(f"RateMyProfessor error: {e}")
        return ""


# ------------------------------------------------------------------------------
# Web search helpers
# ------------------------------------------------------------------------------

async def search_web_general(query: str) -> str:
    """Search the entire web using DuckDuckGo"""
    try:
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=5))
        
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
        print(f"Web search error: {e}")
        return ""

async def search_reddit(query: str) -> str:
    """Search UC Davis subreddit"""
    try:
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(f"{query} site:reddit.com/r/ucdavis", max_results=5))

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
    """Search for UC Davis campus locations"""
    if not gmaps:
        return ""
    
    try:
        def do_maps_search():
            places_result = gmaps.places(
                query=f"{query} UC Davis",
                location=(38.5382, -121.7617),
                radius=3000
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

IMPORTANT: When information is provided to you from the UC Davis knowledge base, web search, Reddit, RateMyProfessor, Google Maps, or uploaded images, you MUST use it to answer questions. This information is REAL and CURRENT.

You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area
- Professor ratings and reviews

You have access to:
1. UC Davis knowledge base (campus info, dining, housing, buildings, etc.)
2. Real-time web search for current information
3. Reddit search for current student opinions and experiences
4. Google Maps for precise location and address information
5. RateMyProfessor for professor ratings and reviews
6. Image parsing for uploaded photos/documents

When information is provided:
- Use the UC Davis knowledge base as your primary source
- Use web search results for current events
- Reference Reddit posts for student opinions
- Cite Google Maps data for locations
- Use RateMyProfessor data for professor ratings
- Use extracted image text/content when answering about uploaded images
- Be specific and detailed using the provided information

Always be enthusiastic about UC Davis and provide accurate, helpful information.
"""

class HistoryMessage(BaseModel):
    role: str = Field(..., description='Either "user" or "assistant"')
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
        # STEP 1: Search UC Davis knowledge base
        uc_davis_context = ""
        if supabase_client:
            print("Searching UC Davis knowledge base...")
            try:
                query_embedding = await asyncio.to_thread(embeddings.embed_query, req.message)
                
                def do_vector_search():
                    return supabase_client.rpc(
                        'match_documents',
                        {'query_embedding': query_embedding, 'match_count': 10}
                    ).execute()
                
                response = await asyncio.to_thread(do_vector_search)
                
                good_results = []
                if response.data:
                    good_results = [doc for doc in response.data if doc.get('similarity', 0) > 0.75]
                    print(f"Vector search: {len(response.data)} docs, {len(good_results)} with >0.75 similarity")
                
                if len(good_results) < 2:
                    print("Vector search weak, trying keyword search...")
                    keywords = [word for word in req.message.lower().split() 
                               if len(word) > 3 and word not in ['what', 'where', 'when', 'which', 'are', 'the', 'all']]
                    
                    if keywords:
                        def do_keyword_search():
                            all_docs = []
                            for kw in keywords[:3]:
                                result = supabase_client.table('documents').select('content').ilike('content', f'%{kw}%').limit(3).execute()
                                if result.data:
                                    all_docs.extend(result.data)
                            seen = set()
                            unique_docs = []
                            for doc in all_docs:
                                doc_str = doc['content']
                                if doc_str not in seen:
                                    seen.add(doc_str)
                                    unique_docs.append(doc)
                            return unique_docs[:5]
                        
                        keyword_results = await asyncio.to_thread(do_keyword_search)
                        if keyword_results:
                            print(f"Keyword search found {len(keyword_results)} documents")
                            uc_davis_context = "\n\n".join([doc['content'] for doc in keyword_results])
                        else:
                            if response.data:
                                uc_davis_context = "\n\n".join([doc['content'] for doc in response.data])
                    else:
                        if response.data:
                            uc_davis_context = "\n\n".join([doc['content'] for doc in response.data])
                else:
                    uc_davis_context = "\n\n".join([doc['content'] for doc in good_results])
                    
            except Exception as e:
                print(f"Error searching knowledge base: {e}")
        
        # STEP 2: Web search
        print(f"Searching web for: {req.message}")
        web_search_results = await search_web_general(f"{req.message} UC Davis")
        
        # STEP 3: Check for professor queries
        professor_keywords = ["professor", "prof", "instructor", "teacher", "rate my professor", "rmp", "rating"]
        needs_professor_search = any(k in req.message.lower() for k in professor_keywords)
        
        # STEP 4: Check for Reddit
        search_keywords = [
            "reddit", "recent", "latest", "current", "today",
            "this year", "right now", "people say", "students think",
            "opinions", "reviews", "experiences", "what's it like",
            "best", "worst", "recommend"
        ]
        needs_reddit_search = any(k in req.message.lower() for k in search_keywords)

        # STEP 5: Check for location
        location_keywords = [
            "where", "location", "address", "directions", "find",
            "building", "place", "near", "close", "map", "how to get"
        ]
        needs_maps = any(k in req.message.lower() for k in location_keywords)

        # STEP 6: Collect results
        web_results = ""
        
        if web_search_results:
            web_results += f"\n=== Web Search Results ===\n{web_search_results}\n"
            print("Found web search results")
        
        if needs_professor_search:
            words = req.message.split()
            for i, word in enumerate(words):
                if word.lower() in professor_keywords and i + 1 < len(words):
                    potential_name = " ".join(words[i+1:min(i+3, len(words))])
                    potential_name = re.sub(r'[^\w\s]', '', potential_name).strip()
                    if potential_name:
                        print(f"Searching RateMyProfessor for: {potential_name}")
                        rmp_data = await search_rate_my_professor(potential_name)
                        if rmp_data:
                            web_results += f"\n=== {rmp_data} ===\n"
                            print("Found RateMyProfessor results")
                        break
        
        if needs_reddit_search:
            print(f"Searching Reddit for: {req.message}")
            reddit_data = await search_reddit(req.message)
            if reddit_data:
                web_results += f"\n=== Reddit Posts ===\n{reddit_data}\n"
                print("Found Reddit results")

        if needs_maps:
            print(f"Searching Google Maps for: {req.message}")
            maps_data = await search_campus_location(req.message)
            if maps_data:
                web_results += f"\n=== Campus Locations (Google Maps) ===\n{maps_data}\n"
                print("Found Google Maps results")

        # STEP 7: Build final prompt
        context_parts = []
        
        if req.image_content:
            context_parts.append(f"=== Uploaded Image Content ===\n{req.image_content}")
            print(f"Using uploaded image content ({len(req.image_content)} chars)")
        
        if uc_davis_context:
            context_parts.append(f"=== UC Davis Knowledge Base ===\n{uc_davis_context}")
        
        if web_results:
            context_parts.append(web_results.strip())
        
        if context_parts:
            current_message = "\n\n".join(context_parts) + f"\n\n---\n\nUser question: {req.message}"
        else:
            current_message = req.message

        # STEP 8: Build messages
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