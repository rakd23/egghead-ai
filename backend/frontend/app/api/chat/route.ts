import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const { message } = body;

  // Fake AI response for now
  return NextResponse.json({
    reply: `Egghead says: I received "${message}"`,
  });
}
