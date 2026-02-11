"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply ?? "No reply returned.",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: could not reach backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-[#200E57] to-[#3B1FA6] text-white px-6">
      <div className="w-full max-w-[720px] flex flex-col items-center">
        <h1 className="text-5xl font-semibold mb-6 text-yellow-400">
          Egghead.AI
        </h1>

        {/* Messages */}
        <div className="w-full mb-6 space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={[
                "px-4 py-3 rounded-2xl border border-white/15 max-w-[85%]",
                m.role === "user"
                  ? "bg-white/10 ml-auto"
                  : "bg-[#2A176B]/60 mr-auto",
              ].join(" ")}
            >
              <div className="text-sm opacity-70 mb-1">
                {m.role === "user" ? "You" : "Egghead"}
              </div>
              <div className="text-base whitespace-pre-wrap">
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="px-4 py-3 rounded-2xl bg-[#2A176B]/60 border border-yellow-400/30 text-yellow-300">
              Generating response...
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex items-center w-full bg-[#2A176B] border border-white/30 rounded-full px-4 py-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything, Aggie..."
            className="flex-1 bg-transparent outline-none text-white placeholder-yellow-300"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />

          <button
            onClick={handleSend}
            className="ml-3 w-10 h-10 rounded-full bg-yellow-400 flex items-center justify-center text-[#200E57] font-bold"
            aria-label="Send"
            title="Send"
          >
            ↑
          </button>
        </div>
      </div>
    </main>
  );
}
