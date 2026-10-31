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
import { Eye, EyeOff, Menu } from "lucide-react";

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
    <div className="h-screen w-screen flex overflow-hidden bg-[#1A0312] relative select-none">
      {/* Wave Background Image Asset with Soft Blend */}
      <div
        className="absolute inset-0 bg-cover bg-center pointer-events-none opacity-70 mix-blend-screen z-0"
        style={{ backgroundImage: "url('/bg-wave.jpg')" }}
      />

      {/* Ambient Top-Right Radial Soft Pink Flare */}
      <div className="absolute top-0 right-0 w-[550px] h-[450px] bg-gradient-to-bl from-[#FF5C93]/25 via-[#E02875]/10 to-transparent blur-3xl pointer-events-none z-0" />

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
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        {/* Top Navbar */}
        <header className="h-13 border-b border-[#6B1442]/35 bg-[#260419]/70 backdrop-blur-xl px-5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="p-1.5 rounded-lg hover:bg-[#45092C] text-[#FFA8C7] lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-bold text-white tracking-wide truncate max-w-sm">
                {metadata.title || "Report Navigator"}
              </span>
              <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full bg-[#420A2B] border border-[#FF7AA8]/40 text-[10px] font-mono text-[#FFA8C7] font-semibold">
                p. 1 - {metadata.page_count}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowEvidencePanel(!showEvidencePanel)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#3B0725]/80 hover:bg-[#520F36] border border-[#FF7AA8]/35 text-xs text-white font-medium transition-all shadow-sm"
            >
              {showEvidencePanel ? (
                <>
                  <EyeOff className="w-3.5 h-3.5 text-[#FFA8C7]" />
                  <span className="hidden sm:inline">Hide Evidence</span>
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-[#FF6EA7]" />
                  <span className="hidden sm:inline">Show Evidence</span>
                </>
              )}
            </button>
          </div>
        </header>

        {/* Middle & Right Split Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Zone 2: Chat Stream */}
          <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
            <div className="flex-1 overflow-y-auto px-4 py-6">
              <div className="max-w-3xl mx-auto space-y-6">
                {/* Empty State Hero */}
                {messages.length === 0 && (
                  <StarterChips
                    questions={
                      metadata.starter_questions.length > 0
                        ? metadata.starter_questions
                        : [
                            "What is the overall unemployment rate in the latest period?",
                            "Which state recorded the highest female labour force participation?",
                            "What are the key findings in Chapter 3?",
                            "Compare the youth unemployment rate between 2023 and 2024.",
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
                        <div className="max-w-xl rounded-2xl rounded-tr-sm bg-gradient-to-r from-[#FF6EA7]/30 via-[#E02875]/35 to-[#8A0C43]/40 border border-[#FF7AA8]/50 text-white px-4 py-3 text-sm shadow-[0_4px_20px_rgba(240,80,140,0.2)] backdrop-blur-md">
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
                          <div className="p-4 rounded-2xl bg-[#320620]/80 border border-[#7D1B4D]/50 text-sm text-[#FFE4ED]">
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

            {/* Sticky Bottom Composer */}
            <div className="p-4 bg-transparent shrink-0">
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
            <div className="w-full lg:w-[460px] xl:w-[500px] shrink-0 h-full relative z-20">
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
