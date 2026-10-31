"use client";

import React from "react";
import { Citation, RetrievalSource } from "@/lib/types";

interface PageMinimapProps {
  totalPages: number;
  citedPages: number[];
  retrievedPages: number[];
  currentPage: number;
  onSelectPage: (page: number) => void;
}

export const PageMinimap: React.FC<PageMinimapProps> = ({
  totalPages = 100,
  citedPages = [],
  retrievedPages = [],
  currentPage = 1,
  onSelectPage,
}) => {
  if (totalPages <= 0) return null;

  return (
    <div className="flex flex-col items-center py-2 px-1 bg-black/40 rounded-lg border border-surfaceBorder select-none">
      <span className="text-[9px] font-mono text-slate-500 mb-1">p.1</span>
      <div className="relative w-3 h-48 bg-slate-900 rounded-full overflow-hidden border border-white/5 cursor-pointer">
        {/* Render retrieved page tick marks */}
        {retrievedPages.map((p, idx) => {
          const topPercent = ((p - 1) / Math.max(1, totalPages - 1)) * 100;
          return (
            <div
              key={`ret-${idx}`}
              onClick={() => onSelectPage(p)}
              style={{ top: `${topPercent}%` }}
              className="absolute left-0 w-full h-[2px] bg-indigo-500/60"
              title={`Retrieved Page ${p}`}
            />
          );
        })}

        {/* Render cited page tick marks (bright green/amber) */}
        {citedPages.map((p, idx) => {
          const topPercent = ((p - 1) / Math.max(1, totalPages - 1)) * 100;
          return (
            <div
              key={`cit-${idx}`}
              onClick={() => onSelectPage(p)}
              style={{ top: `${topPercent}%` }}
              className="absolute left-0 w-full h-[3px] bg-verified shadow-[0_0_8px_#22C55E]"
              title={`Cited Page ${p}`}
            />
          );
        })}

        {/* Current active page indicator indicator */}
        <div
          style={{
            top: `${((currentPage - 1) / Math.max(1, totalPages - 1)) * 100}%`,
          }}
          className="absolute left-[-2px] w-4 h-1 bg-white rounded-full shadow-md pointer-events-none transition-all duration-150"
        />
      </div>
      <span className="text-[9px] font-mono text-slate-500 mt-1">p.{totalPages}</span>
    </div>
  );
};
