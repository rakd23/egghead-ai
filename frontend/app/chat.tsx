"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type {
  Message,
  Conversation,
  ChatAPIResponse,
  SourceAttribution,
  ProfessorCard,
  DirectoryContact,
  CampusResource,
  QueryIntent,
} from "./types";

// ── Helpers ─────────────────────────────────────────────────────────────

const INTENT_LABELS: Record<QueryIntent, string> = {
  professor: "Professor Lookup",
  course: "Course Info",
  housing: "Housing",
  dining: "Dining",
  campus_resource: "Campus Resource",
  location: "Location",
  general: "General",
};

const SOURCE_ICONS: Record<string, string> = {
  vector_db: "📚",
  rate_my_professor: "⭐",
  reddit: "💬",
  web: "🌐",
  google_maps: "📍",
  ucd_directory: "📇",
  curated: "🏫",
};

function RelevanceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "bg-green-400" : pct >= 60 ? "bg-yellow-400" : "bg-orange-400";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-white/40">{pct}%</span>
    </div>
  );
}

// ── Professor Card Component ────────────────────────────────────────────

function ProfessorCardView({ card }: { card: ProfessorCard }) {
  return (
    <div className="mt-3 p-4 bg-gradient-to-br from-[#1a3a6b] to-[#0d2240] rounded-xl border border-yellow-400/20">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">👨‍🏫</span>
        <h3 className="font-semibold text-yellow-300 text-sm">{card.name}</h3>
        <span className="text-xs text-white/40 ml-auto">{card.department}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="bg-white/5 rounded-lg p-2 text-center">
          <div className="text-yellow-400 text-lg font-bold">
            {card.overall_rating ?? "N/A"}
          </div>
          <div className="text-white/50">Rating /5.0</div>
        </div>
        <div className="bg-white/5 rounded-lg p-2 text-center">
          <div className="text-orange-300 text-lg font-bold">
            {card.difficulty ?? "N/A"}
          </div>
          <div className="text-white/50">Difficulty /5.0</div>
        </div>
        <div className="bg-white/5 rounded-lg p-2 text-center">
          <div className="text-green-300 text-lg font-bold">
            {card.would_take_again != null
              ? `${Math.round(card.would_take_again)}%`
              : "N/A"}
          </div>
          <div className="text-white/50">Take Again</div>
        </div>
        <div className="bg-white/5 rounded-lg p-2 text-center">
          <div className="text-blue-300 text-lg font-bold">{card.num_ratings}</div>
          <div className="text-white/50">Reviews</div>
        </div>
      </div>
      {card.profile_url && (
        <a
          href={card.profile_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 block text-center text-xs text-yellow-400/70 hover:text-yellow-300 underline"
        >
          View on RateMyProfessor →
        </a>
      )}
    </div>
  );
}

// ── Source Card Component ────────────────────────────────────────────────

function DirectoryContactCard({ contact }: { contact: DirectoryContact }) {
  return (
    <div className="p-3 bg-gradient-to-br from-[#1a3a6b] to-[#0d2240] rounded-xl border border-blue-400/20">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm">📇</span>
        <h3 className="font-semibold text-blue-300 text-sm">{contact.full_name}</h3>
      </div>
      <div className="space-y-1 text-xs text-white/60">
        {contact.title && (
          <div className="flex items-center gap-2">
            <span className="text-white/30 w-12 shrink-0">Title</span>
            <span className="text-white/80">{contact.title}</span>
          </div>
        )}
        {contact.department && (
          <div className="flex items-center gap-2">
            <span className="text-white/30 w-12 shrink-0">Dept</span>
            <span className="text-white/80">{contact.department}</span>
          </div>
        )}
        {contact.email && (
          <div className="flex items-center gap-2">
            <span className="text-white/30 w-12 shrink-0">Email</span>
            <a href={`mailto:${contact.email}`} className="text-yellow-400/80 hover:text-yellow-300 underline">
              {contact.email}
            </a>
          </div>
        )}
        {contact.phone && (
          <div className="flex items-center gap-2">
            <span className="text-white/30 w-12 shrink-0">Phone</span>
            <span className="text-white/80">{contact.phone}</span>
          </div>
        )}
        {contact.address && (
          <div className="flex items-center gap-2">
            <span className="text-white/30 w-12 shrink-0">Office</span>
            <span className="text-white/80">{contact.address}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Source Attribution Card ─────────────────────────────────────────────

function SourceCard({ source }: { source: SourceAttribution }) {
  return (
    <div className="bg-white/5 rounded-lg p-2.5 border border-white/10 hover:border-white/20 transition-colors">
      <div className="flex items-start gap-2">
        <span className="text-sm shrink-0">{SOURCE_ICONS[source.source_type] || "📄"}</span>
        <div className="min-w-0 flex-1">
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-yellow-300/90 hover:text-yellow-200 line-clamp-1"
            >
              {source.title}
            </a>
          ) : (
            <div className="text-xs font-medium text-white/80 line-clamp-1">
              {source.title}
            </div>
          )}
          <p className="text-[11px] text-white/40 mt-0.5 line-clamp-2">{source.snippet}</p>
          <RelevanceBar score={source.relevance_score} />
        </div>
      </div>
    </div>
  );
}

// ── Campus Resource Pill ────────────────────────────────────────────────

function ResourcePill({ resource }: { resource: CampusResource }) {
  const inner = (
    <>
      <span className="text-xs">🏫</span>
      <span className="text-xs text-white/70">{resource.name}</span>
    </>
  );

  if (resource.url) {
    return (
      <a
        href={resource.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg border border-white/10 hover:border-yellow-400/30 transition-colors"
        title={resource.description}
      >
        {inner}
      </a>
    );
  }

  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 rounded-lg border border-white/10">
      {inner}
    </div>
  );
}

// ── Main Chat Component ─────────────────────────────────────────────────

export default function Chat() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pendingImage, setPendingImage] = useState<File | null>(null);
  const [pendingImagePreview, setPendingImagePreview] = useState<string | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  // Persist conversations to localStorage
  useEffect(() => {
    const saved = localStorage.getItem("egghead-conversations");
    if (saved) setConversations(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem("egghead-conversations", JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentConvId, conversations]);

  const currentConv = conversations.find((c) => c.id === currentConvId);
  const messages = currentConv?.messages || [];
  const hasMessages = messages.length > 0;

  // ── Image Handling ────────────────────────────────────────────────

  function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingImage(file);
    setPendingImagePreview(URL.createObjectURL(file));
    e.target.value = "";
  }

  function removePendingImage() {
    setPendingImage(null);
    if (pendingImagePreview) URL.revokeObjectURL(pendingImagePreview);
    setPendingImagePreview(null);
  }

  function handleDragEnter(e: React.DragEvent) {
    e.preventDefault();
    dragCounterRef.current++;
    if (e.dataTransfer.items?.length) setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setIsDragging(false);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    dragCounterRef.current = 0;
    const file = e.dataTransfer.files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    setPendingImage(file);
    setPendingImagePreview(URL.createObjectURL(file));
  }

  // ── Send Message ──────────────────────────────────────────────────

  async function handleSend() {
    const trimmed = input.trim();
    if ((!trimmed && !pendingImage) || loading) return;

    let convId = currentConvId;
    if (!convId) {
      convId = Date.now().toString();
      const title = trimmed
        ? trimmed.slice(0, 50) + (trimmed.length > 50 ? "..." : "")
        : `Image: ${pendingImage?.name?.slice(0, 40) ?? "upload"}`;
      setConversations((prev) => [
        { id: convId!, title, messages: [], timestamp: Date.now() },
        ...prev,
      ]);
      setCurrentConvId(convId);
    }

    const userMessage: Message = {
      role: "user",
      content: trimmed || `[Image: ${pendingImage?.name}]`,
      imagePreview: pendingImagePreview ?? undefined,
    };

    setConversations((prev) =>
      prev.map((c) =>
        c.id === convId ? { ...c, messages: [...c.messages, userMessage] } : c
      )
    );

    const imageFile = pendingImage;
    const imagePreviewUrl = pendingImagePreview;
    setInput("");
    setPendingImage(null);
    setPendingImagePreview(null);
    setLoading(true);

    const conversation_history = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      // Step 1: Upload image if present
      let image_content: string | undefined;
      if (imageFile) {
        setUploadingImage(true);
        const formData = new FormData();
        formData.append("file", imageFile);
        const uploadRes = await fetch("/api/chat/upload-image", {
          method: "POST",
          body: formData,
        }).catch(() => null);

        // Fallback to direct backend call if API route doesn't exist
        if (!uploadRes || !uploadRes.ok) {
          const directRes = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/upload-image`,
            { method: "POST", body: formData }
          );
          if (!directRes.ok) throw new Error("Image upload failed");
          const data = await directRes.json();
          image_content = data.text;
        } else {
          const data = await uploadRes.json();
          image_content = data.text;
        }
        setUploadingImage(false);
      }

      // Step 2: Send chat through Next.js API route
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed || "Please describe and analyze the uploaded image.",
          conversation_history,
          ...(image_content ? { image_content } : {}),
        }),
      });

      if (res.status === 429) {
        throw new Error("Too many requests. Please wait a moment and try again.");
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Request failed (${res.status})`);
      }

      const data: ChatAPIResponse = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.summary,
        sources: data.sources,
        professorCard: data.professor_card ?? undefined,
        directoryContacts: data.directory_contacts?.length ? data.directory_contacts : undefined,
        campusResources: data.campus_resources,
        intent: data.intent,
        cached: data.cached,
        queryTimeMs: data.query_time_ms,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, assistantMessage] }
            : c
        )
      );
      setRetryCount(0);

    } catch (error: unknown) {
      setUploadingImage(false);
      const errorMsg = error instanceof Error ? error.message : "Could not reach backend.";
      const assistantMessage: Message = {
        role: "assistant",
        content: `Something went wrong: ${errorMsg}`,
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
      setUploadingImage(false);
      if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    }
  }

  // ── Conversation Management ───────────────────────────────────────

  function createNewChat() {
    setCurrentConvId(null);
    removePendingImage();
  }

  function deleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (currentConvId === id) setCurrentConvId(null);
  }

  const today = new Date().setHours(0, 0, 0, 0);
  const yesterday = today - 86400000;
  const lastWeek = today - 7 * 86400000;

  const groupedConvs = {
    today: conversations.filter((c) => c.timestamp >= today),
    yesterday: conversations.filter((c) => c.timestamp >= yesterday && c.timestamp < today),
    lastWeek: conversations.filter((c) => c.timestamp >= lastWeek && c.timestamp < yesterday),
    older: conversations.filter((c) => c.timestamp < lastWeek),
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div
      className="flex h-screen bg-gradient-to-b from-[#0F2A54] via-[#0B1E3D] to-[#001426] text-white relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0B1E3D]/80 border-4 border-dashed border-yellow-400 pointer-events-none">
          <div className="flex flex-col items-center gap-3 text-yellow-400">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <p className="text-xl font-semibold">Drop image here</p>
          </div>
        </div>
      )}

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
              <SidebarGroup label="Today">
                {groupedConvs.today.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </SidebarGroup>
            )}
            {groupedConvs.yesterday.length > 0 && (
              <SidebarGroup label="Yesterday">
                {groupedConvs.yesterday.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </SidebarGroup>
            )}
            {groupedConvs.lastWeek.length > 0 && (
              <SidebarGroup label="Last 7 Days">
                {groupedConvs.lastWeek.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </SidebarGroup>
            )}
            {groupedConvs.older.length > 0 && (
              <SidebarGroup label="Older">
                {groupedConvs.older.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={currentConvId === conv.id}
                    onSelect={() => setCurrentConvId(conv.id)}
                    onDelete={(e) => deleteConversation(conv.id, e)}
                  />
                ))}
              </SidebarGroup>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className={`flex-1 flex flex-col ${!hasMessages ? "items-center justify-center" : ""} px-6`}>
        <div className="absolute top-4 left-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Toggle sidebar"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {!hasMessages ? (
          /* Landing state */
          <div className="w-full max-w-[680px] flex flex-col items-center text-center gap-4">
            <div className="relative flex items-center justify-center">
              <div className="absolute w-52 h-52 rounded-full bg-yellow-400/10 blur-2xl" />
              <img
                src="/Egghead Logo.png"
                alt="Egghead logo"
                className="relative w-52 h-52 object-contain mix-blend-screen drop-shadow-2xl"
              />
            </div>
            <div>
              <h1 className="text-6xl font-bold text-yellow-400 tracking-tight">Egghead.AI</h1>
              <p className="mt-4 text-white/50 text-base tracking-wide">
                Your UC Davis campus assistant
              </p>
            </div>
            <div className="w-full mt-2">
              <ChatInput
                input={input}
                setInput={setInput}
                loading={loading}
                uploadingImage={uploadingImage}
                onSend={handleSend}
                onImageClick={() => fileInputRef.current?.click()}
                pendingImagePreview={pendingImagePreview}
                pendingImageName={pendingImage?.name ?? null}
                onRemoveImage={removePendingImage}
              />
            </div>
          </div>
        ) : (
          /* Chat state */
          <div className="flex flex-col h-full max-w-[720px] w-full mx-auto">
            <div className="py-4 border-b border-white/10 mb-4">
              <h1 className="text-xl font-semibold text-yellow-400">Egghead.AI</h1>
            </div>

            <div className="flex-1 overflow-y-auto mb-6 space-y-3">
              {messages.map((m, idx) => (
                <div key={idx}>
                  {/* Message bubble */}
                  <div
                    className={[
                      "px-5 py-4 rounded-2xl border border-white/10 max-w-[85%] shadow-md",
                      m.role === "user" ? "bg-[#1C3F73] ml-auto" : "bg-[#0E2A55]/60 mr-auto",
                    ].join(" ")}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm opacity-70">
                        {m.role === "user" ? "You" : "Egghead"}
                      </span>
                      {/* Intent badge + metadata for assistant messages */}
                      {m.role === "assistant" && m.intent && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-400/10 text-yellow-400/70 border border-yellow-400/20">
                          {INTENT_LABELS[m.intent]}
                        </span>
                      )}
                      {m.role === "assistant" && m.cached && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-400/10 text-green-400/70 border border-green-400/20">
                          cached
                        </span>
                      )}
                      {m.role === "assistant" && m.queryTimeMs != null && (
                        <span className="text-[10px] text-white/30 ml-auto">
                          {m.queryTimeMs}ms
                        </span>
                      )}
                    </div>

                    {/* Image preview */}
                    {m.imagePreview && (
                      <img
                        src={m.imagePreview}
                        alt="Uploaded"
                        className="mb-2 max-h-40 rounded-lg border border-white/20 object-contain"
                      />
                    )}

                    {/* Message text */}
                    <div className="text-sm leading-relaxed">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          strong: ({ children }) => <strong className="font-bold text-yellow-300">{children}</strong>,
                          em: ({ children }) => <em className="italic text-white/90">{children}</em>,
                          ul: ({ children }) => <ul className="list-disc list-outside space-y-1 my-2 pl-5">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-outside space-y-1 my-2 pl-5">{children}</ol>,
                          li: ({ children }) => <li className="text-white/90 pl-1">{children}</li>,
                          h2: ({ children }) => <h2 className="text-lg font-bold text-yellow-300 mt-3 mb-1">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-base font-bold text-yellow-200 mt-2 mb-1">{children}</h3>,
                          code: ({ children }) => <code className="bg-white/10 text-yellow-200 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                          blockquote: ({ children }) => <blockquote className="border-l-4 border-yellow-400/50 pl-3 italic text-white/70 my-2">{children}</blockquote>,
                          a: ({ href, children }) => (
                            <a href={href} className="text-yellow-400 underline hover:text-yellow-300" target="_blank" rel="noopener noreferrer">
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {m.content}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {/* Professor Card */}
                  {m.professorCard && (
                    <div className="max-w-[85%] mr-auto">
                      <ProfessorCardView card={m.professorCard} />
                    </div>
                  )}

                  {/* Directory Contact Cards */}
                  {m.directoryContacts && m.directoryContacts.length > 0 && (
                    <div className="mt-2 max-w-[85%] mr-auto">
                      <div className="text-[10px] text-white/30 mb-1.5 px-1">
                        UC Davis Directory
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {m.directoryContacts.map((contact, cIdx) => (
                          <DirectoryContactCard key={cIdx} contact={contact} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Source attribution cards */}
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-2 max-w-[85%] mr-auto">
                      <div className="text-[10px] text-white/30 mb-1.5 px-1">
                        Sources ({m.sources.length})
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {m.sources.map((src, srcIdx) => (
                          <SourceCard key={srcIdx} source={src} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Campus resources */}
                  {m.campusResources && m.campusResources.length > 0 && (
                    <div className="mt-2 max-w-[85%] mr-auto">
                      <div className="text-[10px] text-white/30 mb-1.5 px-1">
                        UC Davis Resources
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.campusResources.map((r, rIdx) => (
                          <ResourcePill key={rIdx} resource={r} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Loading indicator */}
              {loading && (
                <div className="px-5 py-4 rounded-2xl bg-[#0E2A55]/60 border border-white/10 max-w-[85%] mr-auto shadow-md">
                  <div className="text-sm opacity-70 mb-2">Egghead</div>
                  <div className="flex items-center gap-1">
                    {uploadingImage ? (
                      <span className="text-xs text-yellow-400/70">Processing image...</span>
                    ) : (
                      <>
                        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-bounce [animation-delay:0ms]" />
                        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-bounce [animation-delay:150ms]" />
                        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-bounce [animation-delay:300ms]" />
                      </>
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <ChatInput
              input={input}
              setInput={setInput}
              loading={loading}
              uploadingImage={uploadingImage}
              onSend={handleSend}
              onImageClick={() => fileInputRef.current?.click()}
              pendingImagePreview={pendingImagePreview}
              pendingImageName={pendingImage?.name ?? null}
              onRemoveImage={removePendingImage}
            />
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
          className="hidden"
          onChange={handleImageSelect}
        />
      </main>
    </div>
  );
}

// ── Subcomponents ───────────────────────────────────────────────────────

function SidebarGroup({ label, children }: { label: string; children: React.ReactNode }) {
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
  uploadingImage,
  onSend,
  onImageClick,
  pendingImagePreview,
  pendingImageName,
  onRemoveImage,
}: {
  input: string;
  setInput: (v: string) => void;
  loading: boolean;
  uploadingImage: boolean;
  onSend: () => void;
  onImageClick: () => void;
  pendingImagePreview: string | null;
  pendingImageName: string | null;
  onRemoveImage: () => void;
}) {
  return (
    <div className="flex flex-col w-full gap-2 pb-4">
      {pendingImagePreview && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[#0E2A55] border border-yellow-400/30 rounded-xl w-fit max-w-full">
          <img src={pendingImagePreview} alt="preview" className="w-8 h-8 rounded object-cover border border-white/20" />
          <span className="text-xs text-white/70 truncate max-w-[180px]">{pendingImageName}</span>
          <button onClick={onRemoveImage} className="text-white/40 hover:text-red-400 transition-colors text-sm ml-1" title="Remove image" type="button">
            ×
          </button>
        </div>
      )}
      <div className="flex items-center w-full bg-[#0E2A55] border border-white/20 rounded-full px-4 py-3">
        <button
          onClick={onImageClick}
          disabled={loading}
          className="mr-3 w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors disabled:opacity-40 text-white/60 hover:text-yellow-400"
          title="Attach image"
          type="button"
          aria-label="Attach image"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={pendingImagePreview ? "Ask about the image..." : "Ask anything, Aggie..."}
          className="flex-1 bg-transparent outline-none text-white placeholder-white/60"
          onKeyDown={(e) => { if (e.key === "Enter") onSend(); }}
          disabled={loading}
        />
        <button
          onClick={onSend}
          disabled={loading || (!input.trim() && !pendingImagePreview)}
          className="ml-3 w-10 h-10 rounded-full bg-yellow-400 disabled:opacity-60 flex items-center justify-center text-[#0B1E3D] font-bold"
          aria-label="Send"
          title="Send"
          type="button"
        >
          ↑
        </button>
      </div>
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
        isActive ? "bg-yellow-400/20 text-yellow-300" : "text-white/80 hover:bg-white/10"
      }`}
      type="button"
    >
      <span className="flex-1 truncate">{conv.title}</span>
      {isHovered && (
        <button onClick={onDelete} className="text-red-400 hover:text-red-300 ml-2" title="Delete" type="button">
          ×
        </button>
      )}
    </button>
  );
}
