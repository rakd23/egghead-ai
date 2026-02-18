"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

type Reference = {
  title: string;
  type: string;
  id: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  references?: Reference[];
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  timestamp: number;
};

export default function Home() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("egghead-conversations");
    if (saved) setConversations(JSON.parse(saved));
  }, []);

  // Save conversations to localStorage (ALWAYS save, even if empty)
  useEffect(() => {
    localStorage.setItem("egghead-conversations", JSON.stringify(conversations));
  }, [conversations]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentConvId, conversations]);

  const currentConv = conversations.find((c) => c.id === currentConvId);
  const messages = currentConv?.messages || [];
  const hasMessages = messages.length > 0;

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    // Ensure we have a conversation id
    let convId = currentConvId;
    if (!convId) {
      convId = Date.now().toString();
      const newConv: Conversation = {
        id: convId,
        title: trimmed.slice(0, 50) + (trimmed.length > 50 ? "..." : ""),
        messages: [],
        timestamp: Date.now(),
      };
      setConversations((prev) => [newConv, ...prev]);
      setCurrentConvId(convId);
    }

    // Add user message immediately
    const userMessage: Message = { role: "user", content: trimmed };
    setConversations((prev) =>
      prev.map((c) =>
        c.id === convId ? { ...c, messages: [...c.messages, userMessage] } : c
      )
    );

    setInput("");
    setLoading(true);

    // Build conversation history (for backend context)
    const conversation_history = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      // HIT FASTAPI DIRECTLY
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          conversation_history,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = await res.json();

      // Backend returns: { "response": "..." }
      const replyText = data.response ?? data.reply ?? "No reply returned.";

      const assistantMessage: Message = {
        role: "assistant",
        content: replyText,
        references: Array.isArray(data.references) ? data.references : [],
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, assistantMessage] }
            : c
        )
      );
    } catch (error: any) {
      const assistantMessage: Message = {
        role: "assistant",
        content: `Error: ${error?.message || "could not reach backend."}`,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, assistantMessage] }
            : c
        )
      );
    } finally {
      setLoading(false);
    }
  }

  function createNewChat() {
    setCurrentConvId(null);
  }

  function deleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (currentConvId === id) setCurrentConvId(null);
  }

  // Group conversations by date
  const today = new Date().setHours(0, 0, 0, 0);
  const yesterday = today - 86400000;
  const lastWeek = today - 7 * 86400000;

  const groupedConvs = {
    today: conversations.filter((c) => c.timestamp >= today),
    yesterday: conversations.filter(
      (c) => c.timestamp >= yesterday && c.timestamp < today
    ),
    lastWeek: conversations.filter(
      (c) => c.timestamp >= lastWeek && c.timestamp < yesterday
    ),
    older: conversations.filter((c) => c.timestamp < lastWeek),
  };

  return (
    <div className="flex h-screen bg-gradient-to-b from-[#0F2A54] via-[#0B1E3D] to-[#001426] text-white">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-64 bg-[#071936] border-r border-white/10 flex flex-col">
          <div className="p-4">
            <button
              onClick={createNewChat}
              className="w-full px-4 py-2 bg-yellow-400 hover:bg-yellow-500 text-[#0B1E3D] rounded-lg font-semibold transition-colors"
            >
              + New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2">
            {groupedConvs.today.length > 0 && (
              <Group label="Today">
                {groupedConvs.today.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </Group>
            )}

            {groupedConvs.yesterday.length > 0 && (
              <Group label="Yesterday">
                {groupedConvs.yesterday.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </Group>
            )}

            {groupedConvs.lastWeek.length > 0 && (
              <Group label="Last 7 Days">
                {groupedConvs.lastWeek.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </Group>
            )}

            {groupedConvs.older.length > 0 && (
              <Group label="Older">
                {groupedConvs.older.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </Group>
            )}
          </div>
        </div>
      )}

      {/* Main */}
      <main
        className={`flex-1 flex flex-col ${
          !hasMessages ? "items-center justify-center" : ""
        } px-6`}
      >
        {/* Toggle sidebar */}
        <div className="absolute top-4 left-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Toggle sidebar"
            title="Toggle sidebar"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {!hasMessages ? (
          <div className="w-full max-w-[720px] flex flex-col items-center">
            <h1 className="text-5xl font-semibold mb-6 text-yellow-400">
              Egghead.AI
            </h1>

            <ChatInput
              input={input}
              setInput={setInput}
              loading={loading}
              onSend={handleSend}
            />
          </div>
        ) : (
          <div className="flex flex-col h-full max-w-[720px] w-full mx-auto">
            <div className="py-4 border-b border-white/10 mb-4">
              <h1 className="text-xl font-semibold text-yellow-400">
                Egghead.AI
              </h1>
            </div>

            <div className="flex-1 overflow-y-auto mb-6 space-y-3">
              {messages.map((m, idx) => (
                <div key={idx}>
                  <div
                    className={[
                      "px-5 py-4 rounded-2xl border border-white/10 max-w-[85%] shadow-md",
                      m.role === "user"
                        ? "bg-[#1C3F73] ml-auto"
                        : "bg-[#0E2A55]/60 mr-auto",
                    ].join(" ")}
                  >
                    <div className="text-sm opacity-70 mb-1">
                      {m.role === "user" ? "You" : "Egghead"}
                    </div>

                    <div className="prose prose-invert max-w-none text-sm leading-relaxed prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-strong:text-white">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </div>

                  {m.references && m.references.length > 0 && (
                    <div className="mt-2 ml-4 space-y-1">
                      <div className="text-xs text-yellow-400/70 mb-1">
                        📚 UC Davis Resources:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {m.references.map((ref, refIdx) => (
                          <span
                            key={refIdx}
                            className="text-sm text-white/70 px-3 py-1 bg-white/5 rounded-lg border border-white/10"
                          >
                            {ref.title}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="px-4 py-3 rounded-2xl bg-[#0E2A55]/60 border border-yellow-400/30 text-yellow-300">
                  Generating response...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <ChatInput
              input={input}
              setInput={setInput}
              loading={loading}
              onSend={handleSend}
            />
          </div>
        )}
      </main>
    </div>
  );
}

function Group({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-4">
      <div className="text-xs text-white/50 px-2 mb-2">{label}</div>
      {children}
    </div>
  );
}

function ChatInput({
  input,
  setInput,
  loading,
  onSend,
}: {
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
  onSend: () => void;
}) {
  return (
    <div className="flex items-center w-full bg-[#0E2A55] border border-white/20 rounded-full px-4 py-3">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask anything, Aggie..."
        className="flex-1 bg-transparent outline-none text-white placeholder-white/60"
        onKeyDown={(e) => {
          if (e.key === "Enter") onSend();
        }}
        disabled={loading}
      />

      <button
        onClick={onSend}
        disabled={loading}
        className="ml-3 w-10 h-10 rounded-full bg-yellow-400 disabled:opacity-60 flex items-center justify-center text-[#0B1E3D] font-bold"
        aria-label="Send"
        title="Send"
        type="button"
      >
        ↑
      </button>
    </div>
  );
}

function ConversationItem({
  conv,
  isActive,
  onSelect,
  onDelete,
}: {
  conv: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-left transition-colors mb-1 ${
        isActive
          ? "bg-yellow-400/20 text-yellow-300"
          : "text-white/80 hover:bg-white/10"
      }`}
      type="button"
    >
      <span className="flex-1 truncate">{conv.title}</span>

      {isHovered && (
        <button
          onClick={onDelete}
          className="text-red-400 hover:text-red-300 ml-2"
          title="Delete"
          type="button"
        >
          ×
        </button>
      )}
    </button>
  );
}
