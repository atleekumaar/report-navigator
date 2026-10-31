"use client";

import React, { useState } from "react";
import { Citation } from "@/lib/types";
import { FileText, Table, Check, AlertCircle } from "lucide-react";

interface CitationChipProps {
  citation: Citation;
  onClick: (citation: Citation) => void;
  isActive?: boolean;
}

export const CitationChip: React.FC<CitationChipProps> = ({
  citation,
  onClick,
  isActive = false,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span className="relative inline-block mx-0.5">
      <button
        onClick={() => onClick(citation)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono font-medium transition-all duration-150 border cursor-pointer ${
          isActive
            ? "bg-accent/25 border-accent text-accent-hover shadow-sm"
            : citation.verified
            ? "bg-verified/10 hover:bg-verified/20 border-verified/30 text-emerald-300"
            : "bg-surface hover:bg-surfaceHover border-surfaceBorder text-slate-300"
        }`}
      >
        {citation.type === "table" ? (
          <Table className="w-3 h-3 text-indigo-400" />
        ) : (
          <FileText className="w-3 h-3 text-emerald-400" />
        )}
        <span>p.{citation.label || citation.page}</span>
        {citation.verified ? (
          <Check className="w-3 h-3 text-verified" />
        ) : (
          <AlertCircle className="w-3 h-3 text-amber-400" />
        )}
      </button>

      {/* Hover preview tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-2.5 rounded-lg bg-[#181C26] border border-white/10 shadow-2xl z-50 text-left pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
            <span className="font-semibold text-slate-200">
              Page {citation.label} (PDF p.{citation.page})
            </span>
            <span className="capitalize text-slate-500">{citation.type}</span>
          </div>
          <p className="text-xs text-slate-300 line-clamp-3 italic font-mono bg-black/30 p-1.5 rounded border border-white/5">
            "{citation.quote}"
          </p>
          <div className="mt-1.5 flex items-center gap-1 text-[10px]">
            {citation.verified ? (
              <span className="text-verified font-medium flex items-center gap-1">
                <Check className="w-2.5 h-2.5" /> Quote verified in document
              </span>
            ) : (
              <span className="text-amber-400 font-medium flex items-center gap-1">
                <AlertCircle className="w-2.5 h-2.5" /> Partial quote match
              </span>
            )}
          </div>
        </div>
      )}
    </span>
  );
};

