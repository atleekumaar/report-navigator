"use client";

import React from "react";
import { RetrievalTrace } from "@/lib/types";
import { Sparkles, Layers, FileText, Table } from "lucide-react";

interface TraceTimelineProps {
  trace?: RetrievalTrace;
}

export const TraceTimeline: React.FC<TraceTimelineProps> = ({ trace }) => {
  if (!trace) {
    return (
      <div className="p-8 text-center text-xs text-[#FFA8C7]/60">
        No retrieval trace available for this query.
      </div>
    );
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Rewritten Queries */}
      <div className="p-3.5 rounded-2xl bg-[#320620]/80 border border-[#7D1B4D]/45 space-y-2.5 backdrop-blur-md">
        <div className="flex items-center gap-1.5 font-bold text-white">
          <Sparkles className="w-3.5 h-3.5 text-[#FF6EA7]" />
          <span>Stage 3: Query Rewriting</span>
        </div>
        <div className="text-[#FFF0F5]">
          <span className="text-[#D89AB3]">Standalone query:</span>{" "}
          <span className="text-white font-medium">&ldquo;{trace.standalone_query}&rdquo;</span>
        </div>
        {trace.keywords?.length > 0 && (
          <div>
            <span className="text-[#D89AB3]">Search keywords:</span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {trace.keywords.map((k, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-lg bg-[#200315] border border-[#7D1B4D]/40 font-mono text-[11px] text-[#FFA8C7]"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Top Retrieved Chunks */}
      <div className="p-3.5 rounded-2xl bg-[#320620]/80 border border-[#7D1B4D]/45 space-y-2.5 backdrop-blur-md">
        <div className="flex items-center justify-between font-bold text-white">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#FF7AA8]" />
            <span>Stages 4 & 5: Fused Candidates ({trace.num_retrieved})</span>
          </div>
          <span className="text-[10px] text-[#FFA8C7] font-mono">Score</span>
        </div>

        <div className="space-y-2">
          {trace.top_sources?.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-[#200315] border border-[#7D1B4D]/35 text-[#FFF0F5]"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono text-[#FF6EA7] font-bold text-[11px] shrink-0">
                  {s.source_id}
                </span>
                {s.type === "table" ? (
                  <Table className="w-3.5 h-3.5 text-[#FF7AA8] shrink-0" />
                ) : (
                  <FileText className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                )}
                <span className="font-medium text-xs shrink-0">
                  Page {s.label || s.page} (p.{s.page})
                </span>
                {s.section && (
                  <span className="text-[#D89AB3] text-[11px] truncate max-w-[140px]">
                    {s.section}
                  </span>
                )}
              </div>
              <span className="font-mono text-[#FFA8C7] tabular-nums font-semibold shrink-0">
                {s.score !== undefined ? s.score.toFixed(3) : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
