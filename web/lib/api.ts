/**
 * API client functions for Report Navigator.
 */

import {
  DocumentMetadata,
  PipelineStep,
  AnswerResponse,
  IndexStatus,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

/**
 * Fetch document metadata for active report.
 */
export async function fetchDocMetadata(): Promise<DocumentMetadata> {
  try {
    const res = await fetch(`${API_BASE}/api/doc`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Failed to fetch document metadata: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error("fetchDocMetadata error:", error);
    return {
      title: "Error Connecting to Server",
      filename: "",
      page_count: 0,
      table_count: 0,
      starter_questions: [
        "What is the overall unemployment rate in the latest period?",
        "Which state recorded the highest female labour force participation?",
        "What are the key findings in Chapter 3?",
        "Compare the youth unemployment rate between 2023 and 2024.",
      ],
    };
  }
}

/**
 * Construct URL to render a page image with optional citation highlight.
 */
export function getPageImageUrl(
  page: number,
  quote?: string,
  isTable: boolean = false,
  zoom: number = 1.6,
  chunkId?: string
): string {
  const params = new URLSearchParams();
  if (quote) params.set("quote", quote);
  if (isTable) params.set("is_table", "true");
  if (zoom !== 1.6) params.set("zoom", String(zoom));
  if (chunkId) params.set("chunk", chunkId);

  const qs = params.toString();
  return `${API_BASE}/api/page/${page}/image${qs ? `?${qs}` : ""}`;
}

/**
 * Stream chat endpoint using Server-Sent Events over POST /api/chat.
 */
export async function streamChat(
  query: string,
  history: Array<{ role: string; content: string }>,
  useRerank: boolean,
  onStatus: (step: PipelineStep) => void,
  onAnswer: (answer: AnswerResponse) => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        history,
        use_rerank: useRerank,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat API request failed: HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error("No response body received from chat stream");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;

        let eventType = "message";
        let dataStr = "";

        const lines = block.split("\n");
        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataStr = line.slice(5).trim();
          }
        }

        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          if (eventType === "status") {
            onStatus(parsed as PipelineStep);
          } else if (eventType === "answer") {
            onAnswer(parsed as AnswerResponse);
          } else if (eventType === "error") {
            onError(new Error(parsed.detail || "Error received from chat pipeline"));
          }
        } catch (e) {
          console.error("Failed to parse SSE payload:", dataStr, e);
        }
      }
    }
  } catch (err: any) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

/**
 * Upload a new PDF report to be indexed.
 */
export async function uploadPdf(file: File): Promise<{ message: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/index`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || "Failed to upload and index PDF");
  }

  return await res.json();
}

/**
 * Poll indexing progress.
 */
export async function fetchIndexStatus(): Promise<IndexStatus> {
  const res = await fetch(`${API_BASE}/api/index/status`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch index status: ${res.statusText}`);
  }
  return await res.json();
}
