"use client";

import React, { useState, useEffect } from "react";
import { Citation, RetrievalTrace } from "@/lib/types";
import { getPageImageUrl } from "@/lib/api";
import { TableEvidence } from "./TableEvidence";
import { TraceTimeline } from "./TraceTimeline";
import { PageMinimap } from "./PageMinimap";
import {
  FileText,
  Table,
  CheckCircle2,
  AlertCircle,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Layers,
  X,
} from "lucide-react";

interface EvidencePanelProps {
  citation: Citation | null;
  allCitations: Citation[];
  onSelectCitation: (cit: Citation) => void;
  totalPages: number;
  trace?: RetrievalTrace;
  onClose?: () => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  citation,
  allCitations,
  onSelectCitation,
  totalPages,
  trace,
  onClose,
}) => {
  const [tab, setTab] = useState<"page" | "passage" | "trace">("page");
  const [zoom, setZoom] = useState(1);
  const [imageLoading, setImageLoading] = useState(true);

  // When selected citation changes, reset zoom and switch to page view
  useEffect(() => {
    setImageLoading(true);
  }, [citation]);

  if (!citation && !trace) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500 bg-surface/40">
        <FileText className="w-10 h-10 mb-3 stroke-1 text-slate-600" />
        <h4 className="text-sm font-semibold text-slate-400">No Evidence Selected</h4>
        <p className="text-xs max-w-xs mt-1">
          Click on any citation chip in an answer (e.g. <span className="font-mono text-slate-400">[p.43]</span>) to view the original page with the exact highlighted passage.
        </p>
      </div>
    );
  }

  const currentIndex = allCitations.findIndex(
    (c) => c.page === citation?.page && c.quote === citation?.quote
  );

  const handlePrev = () => {
    if (currentIndex > 0) {
      onSelectCitation(allCitations[currentIndex - 1]);
    }
  };

  const handleNext = () => {
    if (currentIndex < allCitations.length - 1) {
      onSelectCitation(allCitations[currentIndex + 1]);
    }
  };

  const pageNumber = citation?.page || 1;
  const imageUrl = getPageImageUrl(
    pageNumber,
    citation?.quote,
    citation?.type === "table"
  );

  const citedPages = allCitations.map((c) => c.page);
  const retrievedPages = trace?.top_sources?.map((s) => s.page) || [];

  return (
    <div className="h-full flex flex-col bg-surface border-l border-surfaceBorder overflow-hidden">
      {/* Header Bar */}
      <div className="p-3.5 border-b border-surfaceBorder bg-[#141822]/90 backdrop-blur-md flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setTab("page")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              tab === "page"
                ? "bg-accent/20 text-indigo-300 border border-accent/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Original Page
          </button>
          <button
            onClick={() => setTab("passage")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              tab === "passage"
                ? "bg-accent/20 text-indigo-300 border border-accent/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {citation?.type === "table" ? "Table Row" : "Passage Text"}
          </button>
          <button
            onClick={() => setTab("trace")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              tab === "trace"
                ? "bg-accent/20 text-indigo-300 border border-accent/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Trace
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls for image view */}
          {tab === "page" && (
            <div className="flex items-center gap-1 bg-black/30 p-0.5 rounded border border-white/5 text-slate-400">
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
                className="p-1 hover:text-slate-200 transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono px-1 select-none">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
                className="p-1 hover:text-slate-200 transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="p-1 hover:text-slate-200 transition-colors"
                title="Reset Zoom"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            onClick={() =>
              window.open(
                `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/pdf#page=${pageNumber}`,
                "_blank"
              )
            }
            className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded bg-black/30 hover:bg-black/50 border border-white/5 text-[11px] text-slate-300 hover:text-white transition-colors"
            title="Open original PDF in browser"
          >
            <ExternalLink className="w-3 h-3 text-accent" />
            <span>Full PDF</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-200 lg:hidden"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4">
          {/* TAB 1: Highlighted Page View */}
          {tab === "page" && (
            <div className="space-y-4">
              {/* Citation header bar */}
              {citation && (
                <div className="p-3 rounded-lg bg-black/40 border border-surfaceBorder flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-200">
                      Page {citation.label} (PDF p.{citation.page})
                    </span>
                    <span className="text-slate-500">•</span>
                    <span className="text-slate-400 truncate max-w-[200px]">
                      {citation.section}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {citation.verified ? (
                      <span className="flex items-center gap-1 text-[11px] text-verified font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Verified Quote
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[11px] text-amber-400 font-medium">
                        <AlertCircle className="w-3.5 h-3.5" /> Approximate
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Render Page Image with Warm Yellow Highlight */}
              <div className="relative rounded-xl overflow-hidden border border-surfaceBorder/80 bg-black/60 shadow-2xl flex justify-center items-center min-h-[420px]">
                {imageLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                    <span className="text-xs text-slate-400 animate-pulse">
                      Rendering page evidence at 1.6x...
                    </span>
                  </div>
                )}
                <div
                  style={{ transform: `scale(${zoom})`, transformOrigin: "top center" }}
                  className="transition-transform duration-150"
                >
                  <img
                    src={imageUrl}
                    alt={`Page ${pageNumber} Highlight`}
                    onLoad={() => setImageLoading(false)}
                    onError={() => setImageLoading(false)}
                    className="max-w-full h-auto rounded shadow-lg pulse-evidence"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Text / Table Structured Passage */}
          {tab === "passage" && citation && (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-black/30 border border-surfaceBorder text-xs space-y-1">
                <span className="text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
                  Cited Snippet
                </span>
                <p className="font-mono text-indigo-300 p-2 rounded bg-black/40 border border-white/5">
                  &ldquo;{citation.quote}&rdquo;
                </p>
              </div>

              {citation.type === "table" ? (
                <div>
                  <h5 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                    <Table className="w-3.5 h-3.5 text-indigo-400" />
                    Structured Table (Cited row highlighted)
                  </h5>
                  <TableEvidence
                    markdownTable={citation.full_text || ""}
                    highlightQuote={citation.quote}
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-emerald-400" />
                    Full Chunk Context
                  </h5>
                  <div className="p-3.5 rounded-lg bg-black/30 border border-surfaceBorder text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                    {citation.full_text}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Retrieval Trace */}
          {tab === "trace" && <TraceTimeline trace={trace} />}
        </div>

        {/* Needle-in-a-Haystack Page Minimap Strip */}
        <div className="w-12 border-l border-surfaceBorder/50 flex flex-col items-center justify-center p-1 shrink-0 bg-black/20">
          <PageMinimap
            totalPages={totalPages}
            citedPages={citedPages}
            retrievedPages={retrievedPages}
            currentPage={pageNumber}
            onSelectPage={(p) => {
              const matched = allCitations.find((c) => c.page === p);
              if (matched) onSelectCitation(matched);
            }}
          />
        </div>
      </div>

      {/* Footer Navigation Strip */}
      {allCitations.length > 1 && (
        <div className="p-2.5 border-t border-surfaceBorder bg-[#141822] flex items-center justify-between text-xs text-slate-400 shrink-0">
          <button
            onClick={handlePrev}
            disabled={currentIndex <= 0}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface hover:bg-surfaceHover border border-surfaceBorder disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Prev Citation</span>
          </button>

          <span className="font-mono text-[11px] text-slate-400">
            {currentIndex + 1} of {allCitations.length} Citations
          </span>

          <button
            onClick={handleNext}
            disabled={currentIndex >= allCitations.length - 1}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface hover:bg-surfaceHover border border-surfaceBorder disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            <span>Next Citation</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};



