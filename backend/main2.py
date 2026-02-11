from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
  message: str




@app.post("/chat")
def chat(req: ChatRequest):
  if "uc davis" in req.message.lower():
      reply = "UC Davis is a great campus 🌳 "
  else:
      reply = "I’m still learning, but I got your message!"

  return {"reply": reply}