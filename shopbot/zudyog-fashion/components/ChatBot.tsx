"use client";

import { useState, useRef, useEffect } from "react";
import { useChatBot } from "./ChatBotContext";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatBot() {
  const { isOpen, pendingPrefill, open, close } = useChatBot();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Namaste! I'm your zUdyog Fashion assistant. Ask me anything about our collection — fabrics, sizing, occasions, or care tips.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => {
    const stored = localStorage.getItem("shopbot_session_id");
    if (stored) return stored;
    const id = `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem("shopbot_session_id", id);
    return id;
  });
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom and focus input when drawer opens
  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      const t = setTimeout(() => inputRef.current?.focus(), 320);
      return () => clearTimeout(t);
    }
  }, [isOpen, messages]);

  // Apply prefill to input when drawer opens with one
  useEffect(() => {
    if (isOpen && pendingPrefill) {
      setInput(pendingPrefill);
    }
  }, [isOpen]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't connect to the assistant right now. Please try again or contact support@zudyog.com",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => open()}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-[#8B1A1A] text-white shadow-xl hover:bg-[#6B1414] active:scale-95 transition-all flex items-center justify-center text-2xl"
        aria-label="Open AI stylist"
      >
        💬
      </button>

      {/* Backdrop */}
      <div
        onClick={close}
        className={`fixed inset-0 bg-black/40 z-50 transition-opacity duration-300 ${isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          }`}
      />

      {/* Right-side drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-[420px] max-w-full bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 ease-in-out ${isOpen ? "translate-x-0" : "translate-x-full"
          }`}
        aria-modal="true"
        role="dialog"
        aria-label="zUdyog AI Stylist"
      >
        {/* Header */}
        <div className="bg-[#8B1A1A] text-white px-5 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛍️</span>
            <div>
              <p className="font-semibold leading-tight">zUdyog AI Stylist</p>
              <p className="text-[11px] text-red-200 mt-0.5">
                Ask about fabrics, sizes &amp; occasions
              </p>
            </div>
          </div>
          <button
            onClick={close}
            className="w-8 h-8 rounded-full hover:bg-white/20 flex items-center justify-center text-lg transition-colors"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user"
                    ? "bg-[#8B1A1A] text-white rounded-br-sm"
                    : "bg-stone-100 text-stone-800 rounded-bl-sm"
                  }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-stone-100 rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-stone-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-stone-200 px-4 py-4 flex gap-2 flex-shrink-0 bg-white">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask anything about our collection…"
            className="flex-1 text-sm border border-stone-300 rounded-xl px-4 py-2.5 outline-none focus:border-[#8B1A1A] transition-colors"
            disabled={loading}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="bg-[#8B1A1A] text-white text-sm px-4 py-2.5 rounded-xl hover:bg-[#6B1414] disabled:opacity-40 transition-colors font-medium flex-shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </>
  );
}
