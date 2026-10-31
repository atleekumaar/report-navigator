"use client";

import React from "react";
import {
  Sparkles,
  ArrowRight,
  TrendingUp,
  Users,
  Key,
  Calendar,
} from "lucide-react";
import { HeroDocMagnifierIllustration } from "@/components/ui/Illustrations";

interface StarterChipsProps {
  questions: string[];
  onSelect: (q: string) => void;
}

const DEFAULT_ICONS = [TrendingUp, Users, Key, Calendar];

export const StarterChips: React.FC<StarterChipsProps> = ({ questions, onSelect }) => {
  return (
    <div className="space-y-4 max-w-2xl mx-auto py-6 text-center select-none">
      {/* 3D-styled Document & Magnifier Hero Graphic */}
      <HeroDocMagnifierIllustration className="w-32 h-32 mx-auto" />

      {/* Pill Badge */}
      <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-[#420A2B]/80 border border-[#FF6EA7]/40 text-[#FFA8C7] text-xs font-semibold shadow-[0_0_12px_rgba(240,80,140,0.25)] backdrop-blur-md">
        <Sparkles className="w-3.5 h-3.5 text-[#FF6EA7]" />
        <span>Try Asking Starter Questions</span>
      </div>

      {/* Main Hero Heading */}
      <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight leading-snug">
        Ask any{" "}
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF7AA8] via-[#FF508E] to-[#FFA3C5]">
          statistical question
        </span>{" "}
        from the report
      </h2>

      {/* Subtitle */}
      <p className="text-xs md:text-[13px] text-[#E8B6C7] max-w-lg mx-auto leading-relaxed">
        Answers cite the exact page, verify verbatim quotes, and highlight the original PDF document.
      </p>

      {/* 2x2 Grid of Starter Question Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 text-left">
        {questions.slice(0, 4).map((q, idx) => {
          const Icon = DEFAULT_ICONS[idx % DEFAULT_ICONS.length];
          return (
            <button
              key={idx}
              onClick={() => onSelect(q)}
              className="group flex items-center justify-between gap-3 p-4 rounded-2xl bg-[#370824]/65 hover:bg-[#520F36]/85 border border-[#7D1B4D]/45 hover:border-[#FF6EA7]/70 text-xs text-[#FFF0F5] transition-all duration-200 shadow-lg hover:shadow-[0_8px_24px_rgba(240,80,140,0.25)] hover:-translate-y-0.5 active:translate-y-0 backdrop-blur-md"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-[#520B33]/80 border border-[#FF7AA8]/30 flex items-center justify-center shrink-0 group-hover:border-[#FF6EA7] group-hover:bg-[#680F41] transition-colors shadow-sm">
                  <Icon className="w-4 h-4 text-[#FFA8C7] group-hover:text-white transition-colors" />
                </div>
                <span className="font-medium leading-snug line-clamp-2 text-white">
                  {q}
                </span>
              </div>

              <div className="w-6 h-6 rounded-full bg-[#520B33]/70 border border-[#FF7AA8]/40 flex items-center justify-center shrink-0 group-hover:border-[#FF6EA7] group-hover:bg-[#FF6EA7] transition-all">
                <ArrowRight className="w-3 h-3 text-[#FFA8C7] group-hover:text-white transition-colors" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
