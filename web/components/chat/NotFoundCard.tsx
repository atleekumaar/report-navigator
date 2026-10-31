"use client";

import React from "react";
import { SearchX, FileText, ArrowRight } from "lucide-react";
import { AnswerResponse, Citation } from "@/lib/types";

interface NotFoundCardProps {
  answer: AnswerResponse;
  onSelectPage?: (page: number) => void;
}

export const NotFoundCard: React.FC<NotFoundCardProps> = ({
  answer,
  onSelectPage,
}) => {
  const topSources = answer.retrieval_trace?.top_sources || [];

  return (
    <div className="rounded-card bg-amber-950/20 border border-amber-500/30 p-5 shadow-lg space-y-3.5">
      <div className="flex items-center gap-2.5 text-amber-400 font-medium text-sm">
        <SearchX className="w-5 h-5 text-amber-400" />
        <span className="font-semibold">Not found in the report</span>
      </div>

      <p className="text-slate-300 text-sm leading-relaxed">
        {answer.answer ||
          "The provided statistical report does not contain verifiable evidence to answer this question. The system abides by strict anti-hallucination rules."}
      </p>

      {topSources.length > 0 && (
        <div className="pt-2 border-t border-amber-500/20">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Nearest matching pages found during retrieval:
          </p>
          <div className="flex flex-wrap gap-2">
            {topSources.slice(0, 4).map((s, idx) => (
              <button
                key={idx}
                onClick={() => onSelectPage && onSelectPage(s.page)}
                className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-surface border border-surfaceBorder hover:border-slate-500 text-xs text-slate-200 transition-all"
              >
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Page {s.label} (p.{s.page})</span>
                <ArrowRight className="w-3 h-3 text-slate-500" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
