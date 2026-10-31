"use client";

import React from "react";
import { CheckCircle2, Loader2, Sparkles, Search, BookOpen, ShieldCheck } from "lucide-react";
import { PipelineStep } from "@/lib/types";

interface PipelineStatusProps {
  currentStep?: PipelineStep;
}

const STEPS = [
  { id: "rewriting", label: "Rewriting & context", icon: Sparkles },
  { id: "searching", label: "Hybrid retrieval (BM25 + Dense)", icon: Search },
  { id: "reading", label: "Reading passages", icon: BookOpen },
  { id: "verifying", label: "Verifying citations & numbers", icon: ShieldCheck },
];

export const PipelineStatus: React.FC<PipelineStatusProps> = ({ currentStep }) => {
  const activeIdx = currentStep
    ? STEPS.findIndex((s) => s.id === currentStep.step)
    : 0;

  return (
    <div className="my-3 p-4 rounded-2xl bg-[#2D061E]/85 border border-[#801B4F]/50 shadow-[0_10px_30px_rgba(15,0,10,0.5)] backdrop-blur-xl">
      <div className="flex items-center gap-2 mb-3 text-xs font-bold tracking-wider uppercase text-[#FF7AA8]">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#FF6EA7]" />
        <span>Evidence Pipeline In Progress</span>
      </div>

      <div className="space-y-2.5">
        {STEPS.map((s, idx) => {
          const Icon = s.icon;
          const isDone = idx < activeIdx;
          const isCurrent = idx === activeIdx;
          const isPending = idx > activeIdx;

          return (
            <div
              key={s.id}
              className={`flex items-center gap-3 text-xs transition-all duration-200 ${
                isCurrent
                  ? "text-white font-semibold"
                  : isDone
                  ? "text-[#FFA8C7]"
                  : "text-[#853055]"
              }`}
            >
              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-[#FF6EA7] animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-[#45092C]" />
                )}
              </div>
              <Icon className="w-3.5 h-3.5 text-[#FFA8C7]" />
              <span>{s.label}</span>
              {isCurrent && currentStep?.message && (
                <span className="text-[11px] text-[#FFA3C5] italic truncate max-w-xs font-mono">
                  — {currentStep.message}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
