"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface ChatBotCtx {
  isOpen: boolean;
  pendingPrefill: string;
  open: (prefill?: string) => void;
  close: () => void;
}

const ChatBotContext = createContext<ChatBotCtx | null>(null);

export function ChatBotProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingPrefill, setPendingPrefill] = useState("");

  function open(prefill = "") {
    setPendingPrefill(prefill);
    setIsOpen(true);
  }

  function close() {
    setIsOpen(false);
    setPendingPrefill("");
  }

  return (
    <ChatBotContext.Provider value={{ isOpen, pendingPrefill, open, close }}>
      {children}
    </ChatBotContext.Provider>
  );
}

export function useChatBot() {
  const ctx = useContext(ChatBotContext);
  if (!ctx) throw new Error("useChatBot must be used inside ChatBotProvider");
  return ctx;
}
