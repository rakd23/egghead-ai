from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
import asyncio
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()


# Create LLM instance using your OpenAI API key
llm = ChatOpenAI(
   model="gpt-3.5-turbo",
   temperature=0
)


# Request schema
class ChatRequest(BaseModel):
   message: str


# Chat endpoint
@app.post("/chat")
async def chat(req: ChatRequest):
   print("Received message:", req.message)
   try:
       # Make sure we await the response
       response = await asyncio.to_thread(llm.invoke, req.message)
       print("Response:", response.content)
       return {"response": response.content}
   except Exception as e:
       print("Error generating response:", str(e))
       raise HTTPException(status_code=500, detail=str(e))
