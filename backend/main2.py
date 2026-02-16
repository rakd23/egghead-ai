from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage  # USE THIS
import asyncio
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

# Create LLM instance
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7  # Changed from 0 to make it more conversational
)

# ADD THIS: Define your system prompt
SYSTEM_PROMPT = """You are a helpful and friendly UC Davis campus assistant. You have extensive knowledge about:
- UC Davis campus locations, buildings, and facilities
- Academic programs, majors, and departments  
- Campus life, clubs, and student organizations
- Admissions and enrollment information
- Campus events and UC Davis traditions (like Picnic Day!)
- The local Davis area

Always be enthusiastic about UC Davis and provide accurate, helpful information. If you're unsure about something specific, let the user know rather than guessing. Keep your responses focused on UC Davis-related topics."""

# Request schema
class ChatRequest(BaseModel):
    message: str

# Chat endpoint
@app.post("/chat")
async def chat(req: ChatRequest):
    print("Received message:", req.message)
    try:
        # CHANGE THIS PART: Create messages with system prompt
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=req.message)
        ]
        
        # Invoke with the messages list
        response = await asyncio.to_thread(llm.invoke, messages)
        print("Response:", response.content)
        return {"response": response.content}
    except Exception as e:
        print("Error generating response:", str(e))
        raise HTTPException(status_code=500, detail=str(e))   print("Received message:", req.message)
   try:
       # Make sure we await the response
       response = await asyncio.to_thread(llm.invoke, req.message)
       print("Response:", response.content)
       return {"response": response.content}
   except Exception as e:
       print("Error generating response:", str(e))
       raise HTTPException(status_code=500, detail=str(e))
