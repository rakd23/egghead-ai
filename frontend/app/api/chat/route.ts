import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message, sessionId, preferences } = body;

    // Call FastAPI backend with full request structure
    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        preferences: preferences || {
          tone: "friendly",
          depth: "medium",
          use_ucd_sources: true,
          show_references: true,
          model: "hf:mistralai/Mistral-7B-Instruct",
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json({
      reply: data.reply,
      sessionId: data.session_id,
      references: data.references || [],
      usedModel: data.used_model,
      safety: data.safety,
    });
  } catch (error) {
    console.error("Error calling FastAPI backend:", error);
    
    return NextResponse.json({
      reply: "Sorry, I'm having trouble connecting to my backend. Make sure the FastAPI server is running on port 8000.",
    }, { status: 500 });
  }
}