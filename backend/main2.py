from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant. You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area

Always be enthusiastic about UC Davis and provide accurate, helpful information. If you're unsure about something specific, let the user know rather than guessing. Keep your responses focused on UC Davis-related topics."""

# Create LLM instance
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7
)

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=req.message),
        ]

        # llm.invoke is sync; run it in a worker thread
        response = await asyncio.to_thread(llm.invoke, messages)

        # IMPORTANT: return "reply" so frontend matches
        return {"reply": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
