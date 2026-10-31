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
  Sparkles,
} from "lucide-react";
import {
  EvidenceFolderIllustration,
  PagodaLandscapeSilhouette,
  CelestialCompassWatermark,
} from "@/components/ui/Illustrations";

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

  // Empty state when no citation and no trace is selected
  if (!citation && !trace) {
    return (
      <div className="h-full flex flex-col justify-between bg-[#240417]/90 backdrop-blur-xl border-l border-[#6B1442]/40 relative overflow-hidden select-none">
        {/* Subtle Celestial Compass Rose Watermark */}
        <CelestialCompassWatermark className="absolute top-6 right-6 w-56 h-56 opacity-25" />

        {/* Header Bar */}
        <div className="p-4 border-b border-[#6B1442]/35 flex items-center justify-between shrink-0 relative z-10">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#45092C] border border-[#FF7AA8]/30 flex items-center justify-center">
              <Layers className="w-4 h-4 text-[#FF7AA8]" />
            </div>
            <h3 className="font-bold text-sm text-white">Evidence</h3>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#3B0725] border border-[#FF7AA8]/30 text-[10px] font-mono text-[#FFA3C5] font-semibold">
              0 Selected
            </span>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 rounded-lg text-[#D89AB3] hover:text-white hover:bg-[#45092C] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Center Empty State Illustration */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center relative z-10 space-y-3">
          <EvidenceFolderIllustration className="w-40 h-40 mx-auto" />
          <h4 className="text-base font-bold text-white tracking-tight">
            No Evidence Selected
          </h4>
          <p className="text-xs text-[#E8B6C7] max-w-xs leading-relaxed">
            Click on any citation chip in an answer (e.g.{" "}
            <span className="font-mono text-white bg-[#420A2B] px-1.5 py-0.5 rounded border border-[#FF7AA8]/30 font-semibold">
              [p.43]
            </span>
            ) to view the original page with the exact highlighted passage.
          </p>
        </div>

        {/* Bottom Pagoda Landscape */}
        <div className="relative z-10 pt-4">
          <PagodaLandscapeSilhouette className="w-full h-24 opacity-75" />
        </div>
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
    <div className="h-full flex flex-col bg-[#240417]/90 backdrop-blur-xl border-l border-[#6B1442]/40 overflow-hidden relative">
      {/* Subtle Background Watermark */}
      <CelestialCompassWatermark className="absolute top-8 right-8 w-60 h-60 opacity-15" />

      {/* Header Bar */}
      <div className="p-3 border-b border-[#6B1442]/35 bg-[#2B051D]/90 backdrop-blur-md flex items-center justify-between shrink-0 relative z-10">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setTab("page")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
              tab === "page"
                ? "bg-gradient-to-r from-[#FF6EA7] to-[#E02875] text-white shadow-[0_0_12px_rgba(240,80,140,0.4)]"
                : "text-[#D89AB3] hover:text-white hover:bg-[#3D0828]"
            }`}
          >
            Original Page
          </button>
          <button
            onClick={() => setTab("passage")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
              tab === "passage"
                ? "bg-gradient-to-r from-[#FF6EA7] to-[#E02875] text-white shadow-[0_0_12px_rgba(240,80,140,0.4)]"
                : "text-[#D89AB3] hover:text-white hover:bg-[#3D0828]"
            }`}
          >
            {citation?.type === "table" ? "Table Row" : "Passage Text"}
          </button>
          <button
            onClick={() => setTab("trace")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
              tab === "trace"
                ? "bg-gradient-to-r from-[#FF6EA7] to-[#E02875] text-white shadow-[0_0_12px_rgba(240,80,140,0.4)]"
                : "text-[#D89AB3] hover:text-white hover:bg-[#3D0828]"
            }`}
          >
            Trace
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls for image view */}
          {tab === "page" && (
            <div className="flex items-center gap-1 bg-[#1A0210]/80 p-0.5 rounded-lg border border-[#7D1B4D]/40 text-[#FFA3C5]">
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
                className="p-1 hover:text-white transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono px-1 select-none text-white font-medium">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
                className="p-1 hover:text-white transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="p-1 hover:text-white transition-colors"
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
            className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#370824]/80 hover:bg-[#520F36] border border-[#7D1B4D]/40 text-[11px] text-[#FFE4ED] font-medium transition-colors"
            title="Open original PDF in browser"
          >
            <ExternalLink className="w-3 h-3 text-[#FF7AA8]" />
            <span>Full PDF</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-[#D89AB3] hover:text-white hover:bg-[#45092C] lg:hidden"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden relative z-10">
        <div className="flex-1 overflow-y-auto p-4">
          {/* TAB 1: Highlighted Page View */}
          {tab === "page" && (
            <div className="space-y-3.5">
              {/* Citation header bar */}
              {citation && (
                <div className="p-3 rounded-xl bg-[#350723]/80 border border-[#7D1B4D]/45 flex items-center justify-between text-xs backdrop-blur-md">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">
                      Page {citation.label || citation.page} (PDF p.{citation.page})
                    </span>
                    {citation.section && (
                      <>
                        <span className="text-[#8E3258]">•</span>
                        <span className="text-[#FFA8C7] truncate max-w-[200px]">
                          {citation.section}
                        </span>
                      </>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    {citation.verified ? (
                      <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-semibold px-2 py-0.5 rounded-full bg-emerald-950/40 border border-emerald-500/30">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Verified Quote
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[11px] text-amber-400 font-semibold px-2 py-0.5 rounded-full bg-amber-950/40 border border-amber-500/30">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                        Approximate
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Render Page Image with Luminous Highlight */}
              <div className="relative rounded-2xl overflow-hidden border border-[#851E52]/50 bg-[#16020E]/90 shadow-2xl flex justify-center items-center min-h-[420px]">
                {imageLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-[#1F0314]/80 z-10">
                    <span className="text-xs text-[#FFA8C7] font-medium animate-pulse flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#FF6EA7] animate-spin" />
                      Rendering high-resolution evidence page...
                    </span>
                  </div>
                )}
                <div
                  style={{ transform: `scale(${zoom})`, transformOrigin: "top center" }}
                  className="transition-transform duration-150 p-2"
                >
                  <img
                    src={imageUrl}
                    alt={`Page ${pageNumber} Highlight`}
                    onLoad={() => setImageLoading(false)}
                    onError={() => setImageLoading(false)}
                    className="max-w-full h-auto rounded-lg shadow-xl pulse-evidence"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Text / Table Structured Passage */}
          {tab === "passage" && citation && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-2xl bg-[#320620]/80 border border-[#7D1B4D]/45 text-xs space-y-1.5">
                <span className="text-[#FFB3CE] uppercase tracking-wider font-bold text-[10px]">
                  Cited Snippet
                </span>
                <p className="font-mono text-white p-2.5 rounded-xl bg-[#200315] border border-[#7D1B4D]/35 leading-relaxed">
                  &ldquo;{citation.quote}&rdquo;
                </p>
              </div>

              {citation.type === "table" ? (
                <div>
                  <h5 className="text-xs font-bold text-white mb-2 flex items-center gap-1.5">
                    <Table className="w-4 h-4 text-[#FF7AA8]" />
                    Structured Table (Cited row highlighted)
                  </h5>
                  <TableEvidence
                    markdownTable={citation.full_text || ""}
                    highlightQuote={citation.quote}
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-[#FF7AA8]" />
                    Full Chunk Context
                  </h5>
                  <div className="p-3.5 rounded-2xl bg-[#200315] border border-[#7D1B4D]/40 text-xs text-[#FFF0F5] leading-relaxed whitespace-pre-wrap font-sans">
                    {citation.full_text || citation.quote}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Retrieval Pipeline Trace */}
          {tab === "trace" && <TraceTimeline trace={trace} />}
        </div>

        {/* Right side page minimap scrubber */}
        {totalPages > 0 && (
          <div className="p-2 border-l border-[#6B1442]/30 flex flex-col justify-center shrink-0 bg-[#1D0212]/60">
            <PageMinimap
              totalPages={totalPages}
              citedPages={citedPages}
              retrievedPages={retrievedPages}
              currentPage={pageNumber}
              onSelectPage={(p) => {
                const foundCit = allCitations.find((c) => c.page === p);
                if (foundCit) {
                  onSelectCitation(foundCit);
                } else {
                  onSelectCitation({
                    page: p,
                    label: p,
                    quote: "",
                  });
                }
              }}
            />
          </div>
        )}
      </div>

      {/* Bottom Citation Switcher Bar (when multiple citations exist) */}
      {allCitations.length > 1 && (
        <div className="p-2.5 border-t border-[#6B1442]/35 bg-[#2B051D]/90 backdrop-blur-md flex items-center justify-between text-xs text-[#FFA8C7] shrink-0 relative z-10">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-white">Citation:</span>
            <span className="font-mono text-white">
              {currentIndex + 1} of {allCitations.length}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handlePrev}
              disabled={currentIndex <= 0}
              className={`p-1 rounded-lg border transition-colors ${
                currentIndex > 0
                  ? "bg-[#370824] hover:bg-[#520F36] text-white border-[#7D1B4D]/40"
                  : "text-[#6B2446] border-transparent cursor-not-allowed"
              }`}
              title="Previous Citation"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleNext}
              disabled={currentIndex >= allCitations.length - 1}
              className={`p-1 rounded-lg border transition-colors ${
                currentIndex < allCitations.length - 1
                  ? "bg-[#370824] hover:bg-[#520F36] text-white border-[#7D1B4D]/40"
                  : "text-[#6B2446] border-transparent cursor-not-allowed"
              }`}
              title="Next Citation"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
