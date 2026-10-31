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
    <span className="relative inline-block mx-0.5 align-baseline">
      <button
        onClick={() => onClick(citation)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono font-medium transition-all duration-150 border cursor-pointer ${
          isActive
            ? "bg-gradient-to-r from-[#FF6EA7] to-[#E02875] border-[#FFA3C5] text-white shadow-[0_0_12px_rgba(255,110,167,0.6)]"
            : citation.verified
            ? "bg-emerald-950/40 hover:bg-emerald-900/50 border-emerald-500/40 text-emerald-300"
            : "bg-[#3B0725]/80 hover:bg-[#520F36] border-[#7D1B4D]/50 text-[#FFE4ED]"
        }`}
      >
        {citation.type === "table" ? (
          <Table className="w-3 h-3 text-[#FF7AA8]" />
        ) : (
          <FileText className="w-3 h-3 text-[#FFA8C7]" />
        )}
        <span>p.{citation.label || citation.page}</span>
        {citation.verified ? (
          <Check className="w-3 h-3 text-emerald-400" />
        ) : (
          <AlertCircle className="w-3 h-3 text-amber-400" />
        )}
      </button>

      {/* Hover preview tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 rounded-xl bg-[#220215] border border-[#7D1B4D]/60 shadow-[0_12px_32px_rgba(15,0,10,0.8)] z-50 text-left pointer-events-none animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl">
          <div className="flex items-center justify-between text-[11px] text-[#FFA8C7] mb-1.5 font-sans">
            <span className="font-bold text-white">
              Page {citation.label || citation.page} (PDF p.{citation.page})
            </span>
            <span className="capitalize text-[#D89AB3] text-[10px] bg-[#3B0725] px-1.5 py-0.5 rounded border border-[#7D1B4D]/40">
              {citation.type}
            </span>
          </div>
          <p className="text-xs text-[#FFF0F5] line-clamp-3 italic font-mono bg-[#16010D] p-2 rounded-lg border border-[#7D1B4D]/40 leading-relaxed">
            &ldquo;{citation.quote}&rdquo;
          </p>
          <div className="mt-2 flex items-center gap-1.5 text-[10px] font-sans">
            {citation.verified ? (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <Check className="w-3 h-3 text-emerald-400" /> Quote verified in document
              </span>
            ) : (
              <span className="text-amber-400 font-semibold flex items-center gap-1">
                <AlertCircle className="w-3 h-3 text-amber-400" /> Partial quote match
              </span>
            )}
          </div>
        </div>
      )}
    </span>
  );
};
