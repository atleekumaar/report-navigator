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
    <div className="rounded-card bg-surface border border-surfaceBorder p-5 shadow-lg space-y-4 transition-all duration-200 hover:border-slate-700/60">
      {/* Top badges bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-surfaceBorder/50 text-xs">
        <div className="flex items-center gap-2">
          {allVerified ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-verified/15 text-emerald-400 font-medium border border-verified/30">
              <ShieldCheck className="w-3.5 h-3.5 text-verified" />
              Verified Quotes
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium border border-slate-700">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              Grounded Answer
            </span>
          )}

          {/* Confidence Badge */}
          <span
            className={`px-2 py-0.5 rounded-full font-mono text-[11px] uppercase tracking-wider font-semibold ${
              answer.confidence === "high"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : answer.confidence === "medium"
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
          >
            {answer.confidence} Confidence
          </span>
        </div>

        {/* Trace link */}
        {onOpenTrace && (
          <button
            onClick={onOpenTrace}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-accent transition-colors"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>View Retrieval Trace</span>
          </button>
        )}
      </div>

      {/* Main answer text */}
      <div className="text-slate-100 leading-relaxed text-sm md:text-[15px] selection:bg-accent/30">
        {renderFormattedAnswer()}
      </div>

      {/* Calculation Block */}
      {answer.calculation && (
        <div className="p-3 rounded-lg bg-black/40 border border-surfaceBorder/80 font-mono text-xs text-indigo-300 space-y-1">
          <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-[11px] uppercase tracking-wider">
            <Calculator className="w-3.5 h-3.5" />
            <span>Calculation</span>
          </div>
          <p className="whitespace-pre-wrap">{answer.calculation}</p>
        </div>
      )}

      {/* Number Warning Check */}
      {answer.has_number_warning && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
          <span>
            Please double-check numerical figures against the cited original page.
          </span>
        </div>
      )}

      {/* Bottom utilities toolbar */}
      <div className="pt-2 flex items-center justify-between border-t border-surfaceBorder/40 text-xs text-slate-400">
        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md hover:bg-surfaceHover text-slate-400 hover:text-slate-200 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-verified" />
                <span className="text-verified">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          <div className="flex items-center gap-1 border-l border-surfaceBorder pl-3">
            <button
              onClick={() => setFeedback(feedback === "up" ? null : "up")}
              className={`p-1.5 rounded-md hover:bg-surfaceHover transition-colors ${
                feedback === "up" ? "text-verified bg-verified/10" : "text-slate-400"
              }`}
              title="Helpful answer"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setFeedback(feedback === "down" ? null : "down")}
              className={`p-1.5 rounded-md hover:bg-surfaceHover transition-colors ${
                feedback === "down" ? "text-danger bg-danger/10" : "text-slate-400"
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
            className="text-xs text-accent hover:text-accent-hover font-medium underline underline-offset-4 decoration-accent/40"
          >
            Inspect Evidence Page →
          </button>
        )}
      </div>
    </div>
  );
};
