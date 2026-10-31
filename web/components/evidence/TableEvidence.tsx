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
    return <pre className="p-3 text-xs font-mono bg-black/40 rounded">{markdownTable}</pre>;
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
    <div className="overflow-x-auto rounded-lg border border-surfaceBorder bg-black/30 shadow-inner">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="bg-surface/90 border-b border-surfaceBorder text-slate-300 font-semibold">
            {headerCells.map((h, idx) => (
              <th key={idx} className="py-2.5 px-3 border-r border-surfaceBorder/40 last:border-none">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-surfaceBorder/30 font-mono tabular-nums">
          {dataLines.map((line, rIdx) => {
            const cells = parseRow(line);
            const isHighlight = isLineHighlighted(line);

            return (
              <tr
                key={rIdx}
                className={`transition-colors ${
                  isHighlight
                    ? "bg-amber-400/20 text-amber-200 font-semibold border-y-2 border-amber-400/60"
                    : "hover:bg-white/5 text-slate-300"
                }`}
              >
                {cells.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    className="py-2 px-3 border-r border-surfaceBorder/30 last:border-none"
                  >
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

