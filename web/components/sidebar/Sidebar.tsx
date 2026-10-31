"use client";

import React, { useRef } from "react";
import { DocumentMetadata } from "@/lib/types";
import {
  Compass,
  FileText,
  Table,
  Upload,
  Plus,
  Github,
  BookOpen,
  Sparkles,
} from "lucide-react";

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
    <aside className="w-64 h-full flex flex-col bg-[#0D1017] border-r border-surfaceBorder shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-surfaceBorder flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-accent to-accent-purple flex items-center justify-center shadow-lg shadow-accent/20">
            <Compass className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-sm tracking-tight text-white flex items-center gap-1.5">
              Report Navigator
            </h1>
            <p className="text-[10px] text-slate-500 font-medium">Grounded Statistics QA</p>
          </div>
        </div>
      </div>

      {/* New Query / Chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-surface hover:bg-surfaceHover border border-surfaceBorder hover:border-slate-700 text-xs font-medium text-slate-200 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4 text-accent" />
          <span>New Query</span>
        </button>
      </div>

      {/* Active Document Card */}
      <div className="px-3 py-2 flex-1 overflow-y-auto space-y-4">
        <div className="p-3.5 rounded-xl bg-surface/90 border border-surfaceBorder space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-400">
              Active Report
            </span>
            <span className="w-2 h-2 rounded-full bg-verified animate-pulse" />
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-semibold text-slate-100 line-clamp-2 leading-snug">
              {metadata.title || "Government Statistics Report"}
            </h4>
            <p className="text-[11px] text-slate-500 font-mono truncate">
              {metadata.filename || "report.pdf"}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-surfaceBorder/40">
            <div className="p-2 rounded-lg bg-black/30 border border-white/5">
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <FileText className="w-3 h-3 text-indigo-400" />
                <span>Pages</span>
              </div>
              <span className="text-sm font-semibold font-mono text-slate-200">
                {metadata.page_count}
              </span>
            </div>

            <div className="p-2 rounded-lg bg-black/30 border border-white/5">
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <Table className="w-3 h-3 text-emerald-400" />
                <span>Tables</span>
              </div>
              <span className="text-sm font-semibold font-mono text-slate-200">
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
            className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/5 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Upload className="w-3 h-3" />
            <span>Upload Another PDF</span>
          </button>
        </div>

        {/* Feature Highlights */}
        <div className="p-3 rounded-xl bg-surface/50 border border-surfaceBorder text-[11px] space-y-2 text-slate-400">
          <span className="font-semibold text-slate-300 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-accent" />
            Judge Verification
          </span>
          <ul className="space-y-1.5 list-disc list-inside text-[10px] text-slate-400">
            <li>Exact page bounded chunks</li>
            <li>Direct table markdown parsing</li>
            <li>Quote verification engine</li>
            <li>Highlight burned onto PDF page</li>
          </ul>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-surfaceBorder text-slate-500 text-[11px] flex items-center justify-between">
        <span>Report Navigator v1.0</span>
        <span className="font-mono text-[10px]">BM25 + BGE</span>
      </div>
    </aside>
  );
};
