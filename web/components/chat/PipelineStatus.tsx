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
    <div className="my-3 p-4 rounded-xl bg-surface/90 border border-surfaceBorder shadow-lg backdrop-blur-md">
      <div className="flex items-center gap-2 mb-3 text-xs font-semibold tracking-wider uppercase text-accent">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
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
                  ? "text-slate-100 font-medium"
                  : isDone
                  ? "text-slate-400"
                  : "text-slate-600"
              }`}
            >
              <div className="w-4 h-4 flex items-center justify-center">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-verified" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-accent animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-slate-700" />
                )}
              </div>
              <Icon className="w-3.5 h-3.5" />
              <span>{s.label}</span>
              {isCurrent && currentStep?.message && (
                <span className="text-[11px] text-accent/90 italic truncate max-w-xs">
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

