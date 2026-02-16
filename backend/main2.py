from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from ddgs import DDGS
from typing import List, Dict

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)

async def search_reddit(query: str) -> str:
    """Search UC Davis subreddit"""
    try:
        def do_search():
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{query} site:reddit.com/r/ucdavis",
                    max_results=5
                ))
                return results
        
        results = await asyncio.to_thread(do_search)
        
        if not results:
            return ""
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"Result {i}:\n"
                f"Title: {result.get('title', 'N/A')}\n"
                f"Content: {result.get('body', 'N/A')}\n"
                f"URL: {result.get('href', 'N/A')}\n"
            )
        
        return "\n---\n".join(formatted_results)
    
    except Exception as e:
        print(f"Search error: {e}")
        return ""

SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant. You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments  
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area

You have access to web search to find current information from the UC Davis Reddit community (r/UCDavis).

When search results are provided:
- Use the actual content from Reddit posts to answer questions
- Cite specific opinions or information from the posts
- Mention that the information comes from UC Davis Reddit
- Summarize multiple perspectives if available

Always be enthusiastic about UC Davis and provide accurate, helpful information."""

# UPDATED Request schema to include conversation history
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message] = []  # Optional conversation history

@app.post("/chat")
async def chat(req: ChatRequest):
    print("Received message:", req.message)
    print("Conversation history length:", len(req.conversation_history))
    
    try:
        # Check if needs web search
        search_keywords = [
            "reddit", "recent", "latest", "current", "today", 
            "this year", "right now", "people say", "students think",
            "opinions", "reviews", "experiences", "what's it like",
            "best", "worst", "recommend", "class"
        ]
        
        needs_web_search = any(keyword in req.message.lower() for keyword in search_keywords)
        
        # Perform web search if needed
        web_results = ""
        if needs_web_search:
            try:
                print(f"Searching Reddit for: {req.message}")
                web_results = await search_reddit(req.message)
                if web_results:
                    print(f"Found {len(web_results)} characters of results")
            except Exception as search_error:
                print(f"Web search error: {search_error}")
                web_results = ""
        
        # Build the current user message
        if web_results:
            current_message = f"""Here are recent posts from the UC Davis Reddit (r/UCDavis):

{web_results}

User question: {req.message}

Please use the above Reddit posts to provide an informed answer."""
        else:
            current_message = req.message
        
        # Build full conversation with history
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # Add conversation history
        for msg in req.conversation_history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Add current message
        messages.append(HumanMessage(content=current_message))
        
        # Invoke LLM
        response = await asyncio.to_thread(llm.invoke, messages)
        print("Response:", response.content)
        return {"response": response.content}
    except Exception as e:
        print("Error generating response:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
