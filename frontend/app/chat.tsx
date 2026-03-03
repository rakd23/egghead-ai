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
  imagePreview?: string;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  timestamp: number;
};

function convertEmoticons(text: string): string {
  return text
    .replace(/:\)/g, "😊")
    .replace(/:\(/g, "😢")
    .replace(/;-?\)/g, "😉")
    .replace(/:-?D/g, "😄")
    .replace(/:-?O/gi, "😮")
    .replace(/:-?P/gi, "😛")
    .replace(/:b/gi, "😋")
    .replace(/:-?\//g, "😕")
    .replace(/<3/g, "❤️")
    .replace(/:\|/g, "😐")
    .replace(/XD/g, "😆")
    .replace(/B-?\)/g, "😎");
}

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

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
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) setIsDragging(true);
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

  async function handleSend() {
    const trimmed = input.trim();
    if ((!trimmed && !pendingImage) || loading) return;

    let convId = currentConvId;
    if (!convId) {
      convId = Date.now().toString();
      const title = trimmed
        ? trimmed.slice(0, 50) + (trimmed.length > 50 ? "..." : "")
        : `Image: ${pendingImage?.name?.slice(0, 40) ?? "upload"}`;
      const newConv: Conversation = {
        id: convId,
        title,
        messages: [],
        timestamp: Date.now(),
      };
      setConversations((prev) => [newConv, ...prev]);
      setCurrentConvId(convId);
    }

    const userMessageContent = trimmed || `[Image: ${pendingImage?.name}]`;
    const userMessage: Message = {
      role: "user",
      content: userMessageContent,
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
        const uploadRes = await fetch("http://127.0.0.1:8000/upload-image", {
          method: "POST",
          body: formData,
        });
        setUploadingImage(false);
        if (!uploadRes.ok) {
          const errText = await uploadRes.text();
          throw new Error(`Image upload failed: ${errText}`);
        }
        const uploadData = await uploadRes.json();
        image_content = uploadData.text;
      }

      // Step 2: Send chat
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed || "Please describe and analyze the uploaded image.",
          conversation_history,
          ...(image_content ? { image_content } : {}),
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = await res.json();
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
      setUploadingImage(false);
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
      setUploadingImage(false);
      if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    }
  }

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
    yesterday: conversations.filter(
      (c) => c.timestamp >= yesterday && c.timestamp < today
    ),
    lastWeek: conversations.filter(
      (c) => c.timestamp >= lastWeek && c.timestamp < yesterday
    ),
    older: conversations.filter((c) => c.timestamp < lastWeek),
  };

  return (
    <div
      className="flex h-screen bg-gradient-to-b from-[#0F2A54] via-[#0B1E3D] to-[#001426] text-white relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Full-screen drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0B1E3D]/80 border-4 border-dashed border-yellow-400 rounded-none pointer-events-none">
          <div className="flex flex-col items-center gap-3 text-yellow-400">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            <p className="text-xl font-semibold">Drop image here</p>
          </div>
        </div>
      )}
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

      <main
        className={`flex-1 flex flex-col ${
          !hasMessages ? "items-center justify-center" : ""
        } px-6`}
      >
        <div className="absolute top-4 left-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Toggle sidebar"
            title="Toggle sidebar"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {!hasMessages ? (
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
              <h1 className="text-6xl font-bold text-yellow-400 tracking-tight">
                Egghead.AI
              </h1>
              <p className="mt-4 text-white/50 text-base tracking-wide">
                Your UC Davis campus assistant 🐄
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
          <div className="flex flex-col h-full max-w-[720px] w-full mx-auto">
            <div className="py-4 border-b border-white/10 mb-4">
              <h1 className="text-xl font-semibold text-yellow-400">Egghead.AI</h1>
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

                    {/* Image thumbnail in message bubble */}
                    {m.imagePreview && (
                      <img
                        src={m.imagePreview}
                        alt="Uploaded"
                        className="mb-2 max-h-40 rounded-lg border border-white/20 object-contain"
                      />
                    )}

                    <div className="text-sm leading-relaxed">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          strong: ({ children }) => <strong className="font-bold text-yellow-300">{children}</strong>,
                          em: ({ children }) => <em className="italic text-white/90">{children}</em>,
                          ul: ({ children }) => <ul className="list-disc list-outside space-y-1 my-2 pl-5">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-outside space-y-1 my-2 pl-5">{children}</ol>,
                          li: ({ children }) => <li className="text-white/90 pl-1">{children}</li>,
                          h1: ({ children }) => <h1 className="text-xl font-bold text-yellow-300 mt-3 mb-1">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-lg font-bold text-yellow-300 mt-3 mb-1">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-base font-bold text-yellow-200 mt-2 mb-1">{children}</h3>,
                          code: ({ children }) => <code className="bg-white/10 text-yellow-200 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                          blockquote: ({ children }) => <blockquote className="border-l-4 border-yellow-400/50 pl-3 italic text-white/70 my-2">{children}</blockquote>,
                          a: ({ href, children }) => <a href={href} className="text-yellow-400 underline hover:text-yellow-300" target="_blank" rel="noopener noreferrer">{children}</a>,
                        }}
                      >
                        {convertEmoticons(m.content)}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {m.references && m.references.length > 0 && (
                    <div className="mt-2 ml-4 space-y-1">
                      <div className="text-xs text-yellow-400/70 mb-1">📚 UC Davis Resources:</div>
                      <div className="flex flex-wrap gap-2">
                        {m.references.map((ref, refIdx) => (
                          <span key={refIdx} className="text-sm text-white/70 px-3 py-1 bg-white/5 rounded-lg border border-white/10">
                            {ref.title}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="px-5 py-4 rounded-2xl bg-[#0E2A55]/60 border border-white/10 max-w-[85%] mr-auto shadow-md">
                  <div className="text-sm opacity-70 mb-2">Egghead</div>
                  <div className="flex items-center gap-1">
                    {uploadingImage ? (
                      <span className="text-xs text-yellow-400/70">Uploading image...</span>
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

        {/* Hidden file input — lives here so fileInputRef works */}
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

function Group({ label, children }: { label: string; children: React.ReactNode }) {
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
    <div className="flex flex-col w-full gap-2">
      {/* Pending image preview pill */}
      {pendingImagePreview && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[#0E2A55] border border-yellow-400/30 rounded-xl w-fit max-w-full">
          <img
            src={pendingImagePreview}
            alt="preview"
            className="w-8 h-8 rounded object-cover border border-white/20"
          />
          <span className="text-xs text-white/70 truncate max-w-[180px]">
            {pendingImageName}
          </span>
          <button
            onClick={onRemoveImage}
            className="text-white/40 hover:text-red-400 transition-colors text-sm ml-1"
            title="Remove image"
            type="button"
          >
            ×
          </button>
        </div>
      )}

      <div className="flex items-center w-full bg-[#0E2A55] border border-white/20 rounded-full px-4 py-3">
        {/* Image attach button */}
        <button
          onClick={onImageClick}
          disabled={loading}
          className="mr-3 w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors disabled:opacity-40 text-white/60 hover:text-yellow-400"
          title="Attach image"
          type="button"
          aria-label="Attach image"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
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
  conv, isActive, onSelect, onDelete,
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
