"use client";

import { useState, useEffect, useRef } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
  references?: Array<{
    title: string;
    type: string;
    id: string;
  }>;
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
    if (saved) {
      setConversations(JSON.parse(saved));
    }
  }, []);

  // Save conversations to localStorage
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem("egghead-conversations", JSON.stringify(conversations));
    }
  }, [conversations]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentConvId, conversations]);

  const currentConv = conversations.find((c) => c.id === currentConvId);
  const messages = currentConv?.messages || [];
  const hasMessages = messages.length > 0;

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    let convId = currentConvId;

    // Create new conversation if none exists
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

    // Add user message
    const userMessage: Message = { role: "user", content: trimmed };
    setConversations((prev) =>
      prev.map((c) =>
        c.id === convId ? { ...c, messages: [...c.messages, userMessage] } : c
      )
    );
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: trimmed,
          sessionId: convId 
        }),
      });

      const data = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.reply ?? "No reply returned.",
        references: data.references || [],
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, assistantMessage] }
            : c
        )
      );
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: "Error: could not reach backend.",
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, errorMessage] }
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
    if (currentConvId === id) {
      setCurrentConvId(null);
    }
  }

  // Group conversations by date
  const today = new Date().setHours(0, 0, 0, 0);
  const yesterday = today - 86400000;
  const lastWeek = today - 7 * 86400000;

  const groupedConvs = {
    today: conversations.filter((c) => c.timestamp >= today),
    yesterday: conversations.filter((c) => c.timestamp >= yesterday && c.timestamp < today),
    lastWeek: conversations.filter((c) => c.timestamp >= lastWeek && c.timestamp < yesterday),
    older: conversations.filter((c) => c.timestamp < lastWeek),
  };

  return (
    <div className="flex h-screen bg-gradient-to-b from-[#200E57] to-[#3B1FA6] text-white">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-64 bg-[#1A0D4E] border-r border-white/10 flex flex-col">
          {/* New Chat Button */}
          <div className="p-4">
            <button
              onClick={createNewChat}
              className="w-full px-4 py-2 bg-yellow-400 hover:bg-yellow-500 text-[#200E57] rounded-lg font-semibold transition-colors"
            >
              + New Chat
            </button>
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto px-2">
            {/* Today */}
            {groupedConvs.today.length > 0 && (
              <div className="mb-4">
                <div className="text-xs text-white/50 px-2 mb-2">Today</div>
                {groupedConvs.today.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </div>
            )}

            {/* Yesterday */}
            {groupedConvs.yesterday.length > 0 && (
              <div className="mb-4">
                <div className="text-xs text-white/50 px-2 mb-2">Yesterday</div>
                {groupedConvs.yesterday.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </div>
            )}

            {/* Last 7 Days */}
            {groupedConvs.lastWeek.length > 0 && (
              <div className="mb-4">
                <div className="text-xs text-white/50 px-2 mb-2">Last 7 Days</div>
                {groupedConvs.lastWeek.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </div>
            )}

            {/* Older */}
            {groupedConvs.older.length > 0 && (
              <div className="mb-4">
                <div className="text-xs text-white/50 px-2 mb-2">Older</div>
                {groupedConvs.older.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className={`flex-1 flex flex-col ${!hasMessages ? 'items-center justify-center' : ''} px-6`}>
        {/* Toggle Sidebar Button */}
        <div className="absolute top-4 left-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {!hasMessages ? (
          // Centered layout when no messages
          <div className="w-full max-w-[720px] flex flex-col items-center">
            <h1 className="text-5xl font-semibold mb-6 text-yellow-400">
              Egghead.AI
            </h1>

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
        ) : (
          // Layout with messages (shifted to top-left)
          <div className="flex flex-col h-full max-w-[720px] w-full mx-auto">
            {/* Header with small title */}
            <div className="py-4 border-b border-white/10 mb-4">
              <h1 className="text-xl font-semibold text-yellow-400">
                Egghead.AI
              </h1>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto mb-6 space-y-3">
              {messages.map((m, idx) => (
                <div key={idx}>
                  <div
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
                  
                  {/* UC Davis Resources References */}
                  {m.references && m.references.length > 0 && (
                    <div className="mt-2 ml-4 space-y-1">
                      <div className="text-xs text-yellow-400/70 mb-1">📚 UC Davis Resources:</div>
                      {m.references.map((ref, refIdx) => (
                        <div
                          key={refIdx}
                          className="text-sm text-white/60 hover:text-white/80 px-3 py-1 bg-white/5 rounded-lg border border-white/10 inline-block mr-2"
                        >
                          {ref.title}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="px-4 py-3 rounded-2xl bg-[#2A176B]/60 border border-yellow-400/30 text-yellow-300">
                  Generating response...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input at bottom */}
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
        )}
      </main>
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
          ? "bg-yellow-400/20 text-yellow-400"
          : "text-white/80 hover:bg-white/10"
      }`}
    >
      <span className="flex-1 truncate">{conv.title}</span>
      {isHovered && (
        <span
          onClick={onDelete}
          className="text-red-400 hover:text-red-300 ml-2"
          title="Delete"
        >
          ×
        </span>
      )}
    </button>
  );
}