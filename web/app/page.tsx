"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Citation,
  ChatMessage,
  DocumentMetadata,
  PipelineStep,
  AnswerResponse,
} from "@/lib/types";
import { fetchDocMetadata, streamChat } from "@/lib/api";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { Composer } from "@/components/chat/Composer";
import { AnswerCard } from "@/components/chat/AnswerCard";
import { NotFoundCard } from "@/components/chat/NotFoundCard";
import { PipelineStatus } from "@/components/chat/PipelineStatus";
import { StarterChips } from "@/components/chat/StarterChips";
import { EvidencePanel } from "@/components/evidence/EvidencePanel";
import { PanelRightClose, PanelRightOpen, Menu, Sparkles } from "lucide-react";

export default function Home() {
  const [metadata, setMetadata] = useState<DocumentMetadata>({
    title: "Loading Report...",
    filename: "",
    page_count: 0,
    table_count: 0,
    starter_questions: [],
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPipelineStep, setCurrentPipelineStep] = useState<PipelineStep | undefined>(undefined);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [activeTrace, setActiveTrace] = useState<any>(null);
  const [useRerank, setUseRerank] = useState(true);
  const [showEvidencePanel, setShowEvidencePanel] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDocMetadata().then((data) => setMetadata(data));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentPipelineStep]);

  const handleSendMessage = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: queryText,
    };

    const assistantPlaceholderId = `asst-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantPlaceholderId,
      role: "assistant",
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);
    setCurrentPipelineStep({ step: "rewriting", message: "Analyzing query & conversational history..." });

    // Format history for backend
    const historyPayload = messages
      .filter((m) => m.content || m.answer?.answer)
      .map((m) => ({
        role: m.role,
        content: m.role === "user" ? m.content || "" : m.answer?.answer || "",
      }));

    await streamChat(
      queryText,
      historyPayload,
      useRerank,
      (statusStep) => {
        setCurrentPipelineStep(statusStep);
      },
      (finalAnswer: AnswerResponse) => {
        setIsLoading(false);
        setCurrentPipelineStep(undefined);

        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id === assistantPlaceholderId) {
              return {
                ...msg,
                isLoading: false,
                answer: finalAnswer,
              };
            }
            return msg;
          })
        );

        if (finalAnswer.retrieval_trace) {
          setActiveTrace(finalAnswer.retrieval_trace);
        }

        // Automatically select the first verified citation to show evidence
        if (finalAnswer.citations && finalAnswer.citations.length > 0) {
          setSelectedCitation(finalAnswer.citations[0]);
          setShowEvidencePanel(true);
        }
      },
      (error) => {
        console.error("Chat error:", error);
        setIsLoading(false);
        setCurrentPipelineStep(undefined);
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id === assistantPlaceholderId) {
              return {
                ...msg,
                isLoading: false,
                content: `An error occurred: ${error.message}. Please check if the backend server is running.`,
              };
            }
            return msg;
          })
        );
      }
    );
  };

  const handleSelectCitation = (cit: Citation) => {
    setSelectedCitation(cit);
    setShowEvidencePanel(true);
  };

  // Collect all citations across current answers
  const allCurrentCitations =
    messages[messages.length - 1]?.answer?.citations || [];

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      {/* Zone 1: Sidebar (Desktop + Mobile Drawer) */}
      <div
        className={`fixed inset-y-0 left-0 z-40 transform transition-transform duration-200 lg:relative lg:translate-x-0 ${
          mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar
          metadata={metadata}
          onNewChat={() => {
            setMessages([]);
            setSelectedCitation(null);
            setMobileSidebarOpen(false);
          }}
        />
      </div>

      {/* Backdrop for mobile sidebar */}
      {mobileSidebarOpen && (
        <div
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
        />
      )}

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-12 border-b border-surfaceBorder bg-surface/50 backdrop-blur-md px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="p-1.5 rounded-lg hover:bg-surface text-slate-400 lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200 truncate max-w-sm">
                {metadata.title}
              </span>
              <span className="hidden sm:inline-block px-2 py-0.5 rounded-full bg-accent/10 border border-accent/20 text-[10px] font-mono text-accent">
                p.1 - {metadata.page_count}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowEvidencePanel(!showEvidencePanel)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-surfaceHover border border-surfaceBorder text-xs text-slate-300 transition-colors"
            >
              {showEvidencePanel ? (
                <>
                  <PanelRightClose className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Hide Evidence</span>
                </>
              ) : (
                <>
                  <PanelRightOpen className="w-3.5 h-3.5 text-accent" />
                  <span className="hidden sm:inline">Show Evidence</span>
                </>
              )}
            </button>
          </div>
        </header>

        {/* Middle & Right Split Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Zone 2: Chat Stream */}
          <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
            <div className="flex-1 overflow-y-auto px-4 py-6">
              <div className="max-w-3xl mx-auto space-y-6">
                {/* Empty State */}
                {messages.length === 0 && (
                  <StarterChips
                    questions={
                      metadata.starter_questions.length > 0
                        ? metadata.starter_questions
                        : [
                            "What was the total unemployment rate in 2024?",
                            "Which state had the highest female labour force participation?",
                            "Compare male vs female unemployment in Kerala.",
                            "What are the main statistics reported in Table 3.1?",
                          ]
                    }
                    onSelect={handleSendMessage}
                  />
                )}

                {/* Message Flow */}
                {messages.map((msg) => (
                  <div key={msg.id} className="space-y-3">
                    {msg.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-xl rounded-2xl rounded-tr-sm bg-accent/20 border border-accent/30 text-slate-100 px-4 py-2.5 text-sm shadow-md">
                          {msg.content}
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {msg.isLoading ? (
                          <PipelineStatus currentStep={currentPipelineStep} />
                        ) : msg.answer ? (
                          msg.answer.found ? (
                            <AnswerCard
                              answer={msg.answer}
                              onSelectCitation={handleSelectCitation}
                              selectedCitation={selectedCitation}
                              onOpenTrace={() => {
                                setActiveTrace(msg.answer?.retrieval_trace);
                                setShowEvidencePanel(true);
                              }}
                            />
                          ) : (
                            <NotFoundCard
                              answer={msg.answer}
                              onSelectPage={(p) => {
                                const matched = msg.answer?.citations?.find(
                                  (c) => c.page === p
                                );
                                if (matched) handleSelectCitation(matched);
                              }}
                            />
                          )
                        ) : (
                          <div className="p-4 rounded-xl bg-surface border border-surfaceBorder text-sm text-slate-300">
                            {msg.content}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Sticky Composer */}
            <div className="p-4 bg-background/90 backdrop-blur-md border-t border-surfaceBorder shrink-0">
              <div className="max-w-3xl mx-auto">
                <Composer
                  onSend={handleSendMessage}
                  isLoading={isLoading}
                  useRerank={useRerank}
                  onToggleRerank={setUseRerank}
                />
              </div>
            </div>
          </main>

          {/* Zone 3: Evidence Panel (Collapsible) */}
          {showEvidencePanel && (
            <div className="w-full lg:w-[480px] xl:w-[540px] shrink-0 h-full">
              <EvidencePanel
                citation={selectedCitation}
                allCitations={allCurrentCitations}
                onSelectCitation={handleSelectCitation}
                totalPages={metadata.page_count}
                trace={activeTrace}
                onClose={() => setShowEvidencePanel(false)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
