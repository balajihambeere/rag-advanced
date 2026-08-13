"use client";

import { useChatBot } from "@/components/ChatBotContext";

export default function AskAIButton({ productName }: { productName: string }) {
  const { open } = useChatBot();
  return (
    <button
      onClick={() => open(`Tell me more about the ${productName}`)}
      className="w-full sm:w-auto bg-[#8B1A1A] text-white font-semibold px-6 py-3 rounded-full hover:bg-[#6B1414] transition-colors"
    >
      💬 Ask AI about this product
    </button>
  );
}
