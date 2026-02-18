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


# ------------------------------------------------------------------------------
# Prompt + Schemas
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant.

You have extensive knowledge about:
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

        web_results = ""
        if needs_web_search:
            print(f"Searching Reddit for: {req.message}")
            web_results = await search_reddit(req.message)

        # Build the final user prompt
        if web_results:
            current_message = (
                "Here are recent posts from the UC Davis Reddit (r/UCDavis):\n\n"
                f"{web_results}\n\n"
                f"User question: {req.message}\n\n"
                "Please use the above Reddit posts to provide an informed answer."
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
