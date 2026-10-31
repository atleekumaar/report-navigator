"use client";

import React, { useState } from "react";
import { AnswerResponse, Citation } from "@/lib/types";
import { CitationChip } from "./CitationChip";
import {
  ShieldCheck,
  AlertTriangle,
  Calculator,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Layers,
  Sparkles,
} from "lucide-react";

interface AnswerCardProps {
  answer: AnswerResponse;
  onSelectCitation: (citation: Citation) => void;
  selectedCitation?: Citation | null;
  onOpenTrace?: () => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  answer,
  onSelectCitation,
  selectedCitation,
  onOpenTrace,
}) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = () => {
    let textToCopy = answer.answer;
    if (answer.calculation) {
      textToCopy += `\n\nCalculation: ${answer.calculation}`;
    }
    if (answer.citations?.length) {
      textToCopy += "\n\nSources:\n";
      answer.citations.forEach((c) => {
        textToCopy += `- Page ${c.label} (PDF p.${c.page}): "${c.quote}"\n`;
      });
    }
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render answer text with embedded citation buttons
  const renderFormattedAnswer = () => {
    // Splits by [p.XX] tags
    const parts = answer.answer.split(/(\[p\.\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/\[p\.(\d+)\]/);
      if (match) {
        const pageLabel = match[1];
        const cit = answer.citations?.find(
          (c) => String(c.label) === pageLabel || String(c.page) === pageLabel
        );
        if (cit) {
          return (
            <CitationChip
              key={index}
              citation={cit}
              onClick={onSelectCitation}
              isActive={selectedCitation?.page === cit.page && selectedCitation?.quote === cit.quote}
            />
          );
        }
      }
      return <span key={index}>{part}</span>;
    });
  };

  const allVerified = answer.citations?.length > 0 && answer.citations.every((c) => c.verified);

  return (
    <div className="rounded-2xl bg-[#320620]/75 border border-[#7D1B4D]/50 p-5 shadow-[0_10px_30px_rgba(15,0,10,0.5)] space-y-4 transition-all duration-200 hover:border-[#FF6EA7]/50 backdrop-blur-xl">
      {/* Top badges bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#6B1442]/40 text-xs">
        <div className="flex items-center gap-2">
          {allVerified ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-950/40 text-emerald-300 font-semibold border border-emerald-500/40">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Verified Quotes
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#45092C] text-[#FFA8C7] font-semibold border border-[#FF7AA8]/40">
              <Sparkles className="w-3.5 h-3.5 text-[#FF6EA7]" />
              Grounded Answer
            </span>
          )}

          {/* Confidence Badge */}
          <span
            className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] uppercase tracking-wider font-bold ${
              answer.confidence === "high"
                ? "bg-emerald-950/50 text-emerald-300 border border-emerald-500/30"
                : answer.confidence === "medium"
                ? "bg-[#520B33] text-[#FFA3C5] border border-[#FF7AA8]/40"
                : "bg-amber-950/50 text-amber-300 border border-amber-500/30"
            }`}
          >
            {answer.confidence} Confidence
          </span>
        </div>

        {/* Trace link */}
        {onOpenTrace && (
          <button
            onClick={onOpenTrace}
            className="flex items-center gap-1 text-[11px] text-[#FFA8C7] hover:text-white transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-[#FF7AA8]" />
            <span>View Retrieval Trace</span>
          </button>
        )}
      </div>

      {/* Main answer text */}
      <div className="text-[#FFF0F5] leading-relaxed text-sm md:text-[15px] selection:bg-[#FF6EA7]/40">
        {renderFormattedAnswer()}
      </div>

      {/* Calculation Block */}
      {answer.calculation && (
        <div className="p-3 rounded-xl bg-[#1C0212]/90 border border-[#7D1B4D]/50 font-mono text-xs text-[#FFC4D8] space-y-1">
          <div className="flex items-center gap-1.5 text-[#FF7AA8] font-bold text-[11px] uppercase tracking-wider">
            <Calculator className="w-3.5 h-3.5" />
            <span>Calculation</span>
          </div>
          <p className="whitespace-pre-wrap">{answer.calculation}</p>
        </div>
      )}

      {/* Number Warning Check */}
      {answer.has_number_warning && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-300 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
          <span>
            Please double-check numerical figures against the cited original page.
          </span>
        </div>
      )}

      {/* Bottom utilities toolbar */}
      <div className="pt-2 flex items-center justify-between border-t border-[#6B1442]/40 text-xs text-[#D89AB3]">
        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-[#45092C] text-[#FFA8C7] hover:text-white transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          <div className="flex items-center gap-1 border-l border-[#6B1442]/50 pl-3">
            <button
              onClick={() => setFeedback(feedback === "up" ? null : "up")}
              className={`p-1.5 rounded-lg hover:bg-[#45092C] transition-colors ${
                feedback === "up" ? "text-emerald-400 bg-emerald-950/50" : "text-[#D89AB3]"
              }`}
              title="Helpful answer"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setFeedback(feedback === "down" ? null : "down")}
              className={`p-1.5 rounded-lg hover:bg-[#45092C] transition-colors ${
                feedback === "down" ? "text-rose-400 bg-rose-950/50" : "text-[#D89AB3]"
              }`}
              title="Incorrect or unverified"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Quick jump to primary citation */}
        {answer.citations?.length > 0 && (
          <button
            onClick={() => onSelectCitation(answer.citations[0])}
            className="text-xs text-[#FF6EA7] hover:text-[#FFA3C5] font-semibold underline underline-offset-4 decoration-[#FF6EA7]/50"
          >
            Inspect Evidence Page →
          </button>
        )}
      </div>
    </div>
  );
};
