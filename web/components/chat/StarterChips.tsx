"use client";

import React from "react";
import { Sparkles, ArrowRight } from "lucide-react";

interface StarterChipsProps {
  questions: string[];
  onSelect: (q: string) => void;
}

export const StarterChips: React.FC<StarterChipsProps> = ({ questions, onSelect }) => {
  return (
    <div className="space-y-3 max-w-2xl mx-auto py-8 text-center">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-medium">
        <Sparkles className="w-3.5 h-3.5" />
        <span>Try Asking Starter Questions</span>
      </div>
      <h3 className="text-xl font-semibold text-slate-100">
        Ask any statistical question from the report
      </h3>
      <p className="text-xs text-slate-400 max-w-md mx-auto">
        Answers cite the exact page, verify verbatim quotes, and highlight the original PDF document.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-4 text-left">
        {questions.map((q, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(q)}
            className="group flex items-start justify-between gap-3 p-3.5 rounded-xl bg-surface/80 hover:bg-surfaceHover border border-surfaceBorder hover:border-accent/40 text-xs text-slate-200 transition-all duration-150 shadow-sm"
          >
            <span className="leading-snug">{q}</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-accent transition-colors shrink-0 mt-0.5" />
          </button>
        ))}
      </div>
    </div>
  );
};

