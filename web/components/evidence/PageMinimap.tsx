"use client";

import React from "react";

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
    <div className="flex flex-col items-center py-2 px-1 bg-[#200315]/80 rounded-xl border border-[#7D1B4D]/40 select-none">
      <span className="text-[9px] font-mono text-[#D89AB3] mb-1">p.1</span>
      <div className="relative w-3.5 h-48 bg-[#16020E] rounded-full overflow-hidden border border-[#7D1B4D]/30 cursor-pointer">
        {/* Render retrieved page tick marks */}
        {retrievedPages.map((p, idx) => {
          const topPercent = ((p - 1) / Math.max(1, totalPages - 1)) * 100;
          return (
            <div
              key={`ret-${idx}`}
              onClick={() => onSelectPage(p)}
              style={{ top: `${topPercent}%` }}
              className="absolute left-0 w-full h-[2px] bg-[#FF7AA8]/50"
              title={`Retrieved Page ${p}`}
            />
          );
        })}

        {/* Render cited page tick marks (bright green/emerald) */}
        {citedPages.map((p, idx) => {
          const topPercent = ((p - 1) / Math.max(1, totalPages - 1)) * 100;
          return (
            <div
              key={`cit-${idx}`}
              onClick={() => onSelectPage(p)}
              style={{ top: `${topPercent}%` }}
              className="absolute left-0 w-full h-[3px] bg-[#10B981] shadow-[0_0_8px_#10B981]"
              title={`Cited Page ${p}`}
            />
          );
        })}

        {/* Current active page indicator */}
        <div
          style={{
            top: `${((currentPage - 1) / Math.max(1, totalPages - 1)) * 100}%`,
          }}
          className="absolute left-[-2px] w-4.5 h-1.5 bg-white rounded-full shadow-[0_0_8px_#FF6EA7] pointer-events-none transition-all duration-150"
        />
      </div>
      <span className="text-[9px] font-mono text-[#D89AB3] mt-1">p.{totalPages}</span>
    </div>
  );
};
