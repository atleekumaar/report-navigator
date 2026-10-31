"use client";

import React, { useRef } from "react";
import { DocumentMetadata } from "@/lib/types";
import {
  FileText,
  Table,
  Upload,
  Plus,
  ShieldCheck,
  Check,
  Layers,
} from "lucide-react";
import { PagodaLandscapeSilhouette } from "@/components/ui/Illustrations";

interface SidebarProps {
  metadata: DocumentMetadata;
  onNewChat: () => void;
  onUploadFile?: (file: File) => void;
  onOpenDocModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  metadata,
  onNewChat,
  onUploadFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0] && onUploadFile) {
      onUploadFile(e.target.files[0]);
    }
  };

  return (
    <aside className="w-64 h-full flex flex-col bg-[#240417]/90 backdrop-blur-xl border-r border-[#6B1442]/40 shrink-0 select-none relative overflow-hidden">
      {/* Brand Header */}
      <div className="p-4 border-b border-[#6B1442]/35 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {/* Glowing Geometric Cube / Origami Icon */}
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#FF6EA7] via-[#F43F85] to-[#B8165B] flex items-center justify-center shadow-[0_0_15px_rgba(255,110,167,0.45)] border border-white/20">
            <Layers className="w-5 h-5 text-white drop-shadow" />
          </div>
          <div>
            <h1 className="font-bold text-[15px] tracking-tight text-white flex items-center gap-1.5">
              Report Navigator
            </h1>
            <p className="text-[10px] text-[#FFA8C7] font-medium tracking-wide">
              Grounded Statistics QA
            </p>
          </div>
        </div>
      </div>

      {/* New Query Pill Button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2 px-3.5 rounded-full bg-gradient-to-r from-[#FF6EA7]/25 via-[#E02875]/35 to-[#A31252]/40 hover:from-[#FF6EA7]/40 hover:to-[#E02875]/55 border border-[#FF7AA8]/50 hover:border-[#FF94BD] text-xs font-semibold text-white transition-all shadow-[0_4px_16px_rgba(240,80,140,0.25)] hover:shadow-[0_6px_22px_rgba(240,80,140,0.4)] active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5 text-[#FFB3CE]" />
          <span>New Query</span>
        </button>
      </div>

      {/* Middle Scrollable Section */}
      <div className="px-3 py-1 flex-1 overflow-y-auto space-y-3.5">
        {/* Active Document Card */}
        <div className="p-3.5 rounded-2xl bg-[#370824]/75 border border-[#7D1B4D]/45 space-y-3 shadow-lg backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#FFB3CE]/80">
              Active Report
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  metadata.page_count > 0
                    ? "bg-[#10B981] shadow-[0_0_8px_#10B981] animate-pulse"
                    : "bg-[#F59E0B] shadow-[0_0_8px_#F59E0B]"
                }`}
              />
              <span className="text-[9px] font-mono text-[#D89AB3]">
                {metadata.page_count > 0 ? "Live" : "Syncing"}
              </span>
            </span>
          </div>

          <div className="space-y-0.5">
            <h4 className="text-xs font-semibold text-white line-clamp-1 leading-snug">
              {metadata.title || "Report"}
            </h4>
            <p className="text-[10px] text-[#D89AB3] font-mono truncate">
              {metadata.filename || "report.pdf"}
            </p>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#7D1B4D]/35">
            <div className="p-2 rounded-xl bg-[#230416]/60 border border-[#7D1B4D]/35">
              <div className="flex items-center gap-1 text-[10px] text-[#FFA3C5]">
                <FileText className="w-3 h-3 text-[#FF7AA8]" />
                <span className="font-medium">Pages</span>
              </div>
              <span className="text-base font-bold font-mono text-white tabular-nums">
                {metadata.page_count}
              </span>
            </div>

            <div className="p-2 rounded-xl bg-[#230416]/60 border border-[#7D1B4D]/35">
              <div className="flex items-center gap-1 text-[10px] text-[#FFA3C5]">
                <Table className="w-3 h-3 text-[#FF7AA8]" />
                <span className="font-medium">Tables</span>
              </div>
              <span className="text-base font-bold font-mono text-white tabular-nums">
                {metadata.table_count}
              </span>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-[#4A0A30]/50 hover:bg-[#5E0D3E]/70 border border-[#FF7AA8]/30 hover:border-[#FF7AA8]/60 text-[11px] font-medium text-[#FFE4ED] transition-all shadow-sm"
          >
            <Upload className="w-3 h-3 text-[#FF7AA8]" />
            <span>Upload Another PDF</span>
          </button>
        </div>

        {/* Judge Verification Checklist */}
        <div className="p-3.5 rounded-2xl bg-[#320620]/60 border border-[#6B1442]/40 text-[11px] space-y-2.5 backdrop-blur-md">
          <div className="flex items-center gap-1.5 font-bold text-white text-xs">
            <ShieldCheck className="w-4 h-4 text-[#FF6EA7]" />
            <span>Judge Verification</span>
          </div>
          <ul className="space-y-1.5 text-[11px] text-[#F3CBD9]">
            <li className="flex items-center gap-2">
              <Check className="w-3 h-3 text-[#FF6EA7] shrink-0" />
              <span>Exact page bounded chunks</span>
            </li>
            <li className="flex items-center gap-2">
              <Check className="w-3 h-3 text-[#FF6EA7] shrink-0" />
              <span>Direct table markdown parsing</span>
            </li>
            <li className="flex items-center gap-2">
              <Check className="w-3 h-3 text-[#FF6EA7] shrink-0" />
              <span>Quote verification engine</span>
            </li>
            <li className="flex items-center gap-2">
              <Check className="w-3 h-3 text-[#FF6EA7] shrink-0" />
              <span>Highlight burned onto PDF page</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Decorative Pagoda Silhouette at Bottom */}
      <div className="px-1 pt-2 select-none pointer-events-none">
        <PagodaLandscapeSilhouette className="w-full h-20 opacity-80" />
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-[#6B1442]/40 text-[#D89AB3] text-[10px] font-medium flex items-center justify-between bg-[#1D0212]/80">
        <span>Report Navigator v1.0</span>
        <span className="font-mono text-[#FFA3C5]">BM25 + BGE</span>
      </div>
    </aside>
  );
};
