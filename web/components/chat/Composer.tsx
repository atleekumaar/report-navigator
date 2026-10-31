"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, SlidersHorizontal, Send } from "lucide-react";

interface ComposerProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  useRerank: boolean;
  onToggleRerank: (val: boolean) => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  isLoading,
  useRerank,
  onToggleRerank,
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ⌘K focus hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="relative rounded-2xl bg-[#2D061E]/85 backdrop-blur-xl border border-[#801B4F]/50 shadow-[0_12px_40px_rgba(15,0,10,0.55)] p-3 space-y-2">
      <div className="flex items-start gap-2.5 px-1">
        <MessageSquare className="w-4 h-4 text-[#FFA8C7] mt-1 shrink-0 opacity-80" />
        <textarea
          ref={textareaRef}
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the report (e.g. 'What was the female LFPR in 2024?')... [⌘K]"
          disabled={isLoading}
          className="w-full resize-none bg-transparent text-sm text-white placeholder-[#E8A5BD]/60 focus:outline-none leading-relaxed"
        />
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-[#6B1442]/40 px-1 text-xs">
        {/* Modern Custom Pill Toggle Switch for Cross-Encoder */}
        <label className="flex items-center gap-2.5 text-[#F6C4D0] hover:text-white cursor-pointer select-none group">
          <div
            onClick={() => onToggleRerank(!useRerank)}
            className={`w-9 h-5 rounded-full transition-colors flex items-center p-0.5 cursor-pointer ${
              useRerank
                ? "bg-gradient-to-r from-[#FF6EA7] to-[#E02875] shadow-[0_0_10px_rgba(240,80,140,0.5)]"
                : "bg-[#45092C] border border-[#7D1B4D]/50"
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white shadow-md transform transition-transform duration-200 ${
                useRerank ? "translate-x-4" : "translate-x-0"
              }`}
            />
          </div>
          <div className="flex items-center gap-1.5 text-xs font-medium">
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#FFA3C5]" />
            <span>Cross-Encoder Rerank</span>
          </div>
        </label>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#D89AB3] hidden sm:inline">
            Press{" "}
            <kbd className="px-1.5 py-0.5 rounded-md bg-[#1C0212] border border-[#7D1B4D]/40 text-[10px] text-[#FFA3C5] font-mono">
              Enter
            </kbd>{" "}
            to send
          </span>

          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 ${
              input.trim() && !isLoading
                ? "bg-gradient-to-r from-[#FF6EA7] via-[#F43F85] to-[#D81B60] text-white shadow-[0_4px_16px_rgba(240,80,140,0.45)] hover:shadow-[0_6px_24px_rgba(240,80,140,0.65)] hover:-translate-y-0.5 active:translate-y-0"
                : "bg-[#45092C]/60 text-[#964265] border border-[#6B1442]/30 cursor-not-allowed"
            }`}
          >
            <span>Ask</span>
            <Send className="w-3 h-3 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
};
