"use client";

import { useChatBot } from "./ChatBotContext";

export default function OpenChatButton() {
  const { open } = useChatBot();
  return (
    <button
      onClick={() => open()}
      className="border border-red-300 text-red-100 px-8 py-3 rounded-full hover:bg-white/10 transition-colors"
    >
      Ask our AI Stylist 💬
    </button>
  );
}
