"use client";

import React from "react";
import { RetrievalTrace } from "@/lib/types";
import { Sparkles, Search, Layers, FileText, Table } from "lucide-react";

interface TraceTimelineProps {
  trace?: RetrievalTrace;
}

export const TraceTimeline: React.FC<TraceTimelineProps> = ({ trace }) => {
  if (!trace) {
    return (
      <div className="p-8 text-center text-xs text-slate-500">
        No retrieval trace available for this query.
      </div>
    );
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Rewritten Queries */}
      <div className="p-3 rounded-lg bg-surface border border-surfaceBorder space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Stage 3: Query Rewriting</span>
        </div>
        <div className="text-slate-400">
          <span className="text-slate-500">Standalone query:</span>{" "}
          <span className="text-slate-200 font-medium">"{trace.standalone_query}"</span>
        </div>
        {trace.keywords?.length > 0 && (
          <div>
            <span className="text-slate-500">Search keywords:</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {trace.keywords.map((k, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded bg-black/40 border border-white/5 font-mono text-[11px] text-slate-300"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Top Retrieved Chunks */}
      <div className="p-3 rounded-lg bg-surface border border-surfaceBorder space-y-2.5">
        <div className="flex items-center justify-between font-semibold text-slate-300">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>Stages 4 & 5: Fused Candidates ({trace.num_retrieved})</span>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">Cross-encoder Score</span>
        </div>

        <div className="space-y-2">
          {trace.top_sources?.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded bg-black/25 border border-white/5 text-slate-300"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-accent font-semibold">{s.source_id}</span>
                {s.type === "table" ? (
                  <Table className="w-3.5 h-3.5 text-indigo-400" />
                ) : (
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                )}
                <span>
                  Page {s.label} (PDF p.{s.page})
                </span>
                <span className="text-slate-500 truncate max-w-[120px]">
                  {s.section}
                </span>
              </div>
              <span className="font-mono text-slate-400 tabular-nums">
                {s.score !== undefined ? s.score.toFixed(3) : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
