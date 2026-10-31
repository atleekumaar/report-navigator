"use client";

import React from "react";

interface TableEvidenceProps {
  markdownTable: string;
  highlightQuote?: string;
}

export const TableEvidence: React.FC<TableEvidenceProps> = ({
  markdownTable,
  highlightQuote,
}) => {
  const lines = markdownTable.split("\n").filter((l) => l.trim().startsWith("|"));
  if (lines.length < 2) {
    return <pre className="p-3 text-xs font-mono bg-[#1E0313] text-[#FFE4ED] rounded-xl">{markdownTable}</pre>;
  }

  const parseRow = (line: string) => {
    return line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());
  };

  const headerCells = parseRow(lines[0]);
  const dataLines = lines.slice(2); // Skip separator

  // Check if a line matches the highlighted quote
  const isLineHighlighted = (line: string) => {
    if (!highlightQuote) return false;
    const cleanLine = line.replace(/\|/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
    const cleanQuote = highlightQuote.replace(/\|/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
    return cleanLine.includes(cleanQuote) || cleanQuote.includes(cleanLine);
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-[#7D1B4D]/50 bg-[#1A0210] shadow-inner">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="bg-[#350723] border-b border-[#7D1B4D]/60 text-white font-bold">
            {headerCells.map((h, idx) => (
              <th key={idx} className="py-2.5 px-3 border-r border-[#7D1B4D]/40 last:border-none">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#6B1442]/30 font-mono tabular-nums">
          {dataLines.map((line, rIdx) => {
            const cells = parseRow(line);
            const isHighlight = isLineHighlighted(line);

            return (
              <tr
                key={rIdx}
                className={`transition-colors ${
                  isHighlight
                    ? "bg-[#FF5C93]/25 text-white font-bold border-y-2 border-[#FF5C93]"
                    : "hover:bg-[#3D0828]/50 text-[#FFF0F5]"
                }`}
              >
                {cells.map((cell, cIdx) => (
                  <td key={cIdx} className="py-2 px-3 border-r border-[#6B1442]/20 last:border-none">
                    {cell}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
