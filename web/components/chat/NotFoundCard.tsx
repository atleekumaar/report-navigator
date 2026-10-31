"use client";

import React from "react";
import { SearchX, FileText, ArrowRight } from "lucide-react";
import { AnswerResponse } from "@/lib/types";

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
    <div className="rounded-2xl bg-[#2D061E]/80 border border-amber-500/35 p-5 shadow-[0_10px_30px_rgba(15,0,10,0.5)] space-y-3.5 backdrop-blur-xl">
      <div className="flex items-center gap-2.5 text-amber-400 font-semibold text-sm">
        <div className="w-7 h-7 rounded-lg bg-amber-950/50 border border-amber-500/30 flex items-center justify-center">
          <SearchX className="w-4 h-4 text-amber-400" />
        </div>
        <span>Not found in the report</span>
      </div>

      <p className="text-[#FCE8F0] text-sm leading-relaxed">
        {answer.answer ||
          "The provided statistical report does not contain verifiable evidence to answer this question. The system abides by strict anti-hallucination rules."}
      </p>

      {topSources.length > 0 && (
        <div className="pt-2 border-t border-[#6B1442]/40">
          <p className="text-[11px] font-bold uppercase tracking-wider text-[#FFA8C7] mb-2.5">
            Nearest matching pages found during retrieval:
          </p>
          <div className="flex flex-wrap gap-2">
            {topSources.slice(0, 4).map((s, idx) => (
              <button
                key={idx}
                onClick={() => onSelectPage && onSelectPage(s.page)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#370824] border border-[#7D1B4D]/45 hover:border-[#FF7AA8] text-xs font-medium text-[#FFF0F5] transition-all shadow-sm"
              >
                <FileText className="w-3.5 h-3.5 text-[#FF7AA8]" />
                <span>Page {s.label || s.page} (p.{s.page})</span>
                <ArrowRight className="w-3 h-3 text-[#D89AB3]" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
