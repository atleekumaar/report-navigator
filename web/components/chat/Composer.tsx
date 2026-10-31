"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, SlidersHorizontal, CornerDownLeft } from "lucide-react";

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
    <div className="relative rounded-2xl bg-surface border border-surfaceBorder shadow-xl p-2.5 space-y-2">
      <textarea
        ref={textareaRef}
        rows={2}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about the report (e.g. 'What was the female LFPR in 2024?')... [⌘K]"
        disabled={isLoading}
        className="w-full resize-none bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
      />

      <div className="flex items-center justify-between pt-1 border-t border-surfaceBorder/40 px-2 text-xs">
        {/* Toggle cross-encoder rerank */}
        <label className="flex items-center gap-2 text-slate-400 hover:text-slate-200 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={useRerank}
            onChange={(e) => onToggleRerank(e.target.checked)}
            className="rounded border-slate-700 bg-slate-900 text-accent focus:ring-0"
          />
          <SlidersHorizontal className="w-3 h-3 text-slate-500" />
          <span>Cross-Encoder Rerank</span>
        </label>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500 hidden sm:inline">
            Press <kbd className="px-1 py-0.5 rounded bg-black/40 border border-white/10 text-[10px]">Enter</kbd> to send
          </span>

          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              input.trim() && !isLoading
                ? "bg-accent hover:bg-accent-hover text-white shadow-md shadow-accent/20"
                : "bg-slate-800 text-slate-500 cursor-not-allowed"
            }`}
          >
            <span>Ask</span>
            <CornerDownLeft className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
