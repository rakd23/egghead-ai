import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message, conversation_history, image_content } = body;

    if (!message || typeof message !== "string" || message.trim().length === 0) {
      return NextResponse.json(
        { error: "Message is required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message.trim(),
        conversation_history: conversation_history || [],
        ...(image_content ? { image_content } : {}),
      }),
    });

    if (response.status === 429) {
      const detail = await response.json();
      return NextResponse.json(
        { error: "rate_limited", detail },
        { status: 429 }
      );
    }

    if (!response.ok) {
      const text = await response.text();
      console.error(`Backend error (${response.status}): ${text}`);
      return NextResponse.json(
        { error: `Backend returned ${response.status}` },
        { status: 502 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error("API route error:", error);
    return NextResponse.json(
      { error: "Failed to reach backend. Is the server running?" },
      { status: 502 }
    );
  }
}
