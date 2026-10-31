/**
 * API client functions for Report Navigator.
 * Automatically resolves between production Render backend, Next.js proxy rewrites, and local dev.
 */

import {
  DocumentMetadata,
  PipelineStep,
  AnswerResponse,
  IndexStatus,
} from "./types";

export const PROD_BACKEND_URL = "https://report-navigator-api-4ei5.onrender.com";

export function getApiBase(): string {
  // 1. Explicit env var if defined
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  // 2. In browser on production (e.g. *.vercel.app or non-localhost)
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return PROD_BACKEND_URL;
    }
  }
  // 3. Local fallback
  return "http://127.0.0.1:8000";
}

/**
 * Fetch document metadata for active report.
 */
export async function fetchDocMetadata(): Promise<DocumentMetadata> {
  const base = getApiBase();
  let lastError: any = null;

  // Primary attempt
  try {
    const res = await fetch(`${base}/api/doc`, { cache: "no-store" });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    lastError = err;
  }

  // Fallback 1: Try relative path rewrite (handles Next.js vercel.json rewrites)
  if (typeof window !== "undefined" && base !== "") {
    try {
      const res = await fetch("/api/doc", { cache: "no-store" });
      if (res.ok) {
        return await res.json();
      }
    } catch (_) {}
  }

  // Fallback 2: Try explicit production Render backend URL directly
  if (base !== PROD_BACKEND_URL) {
    try {
      const res = await fetch(`${PROD_BACKEND_URL}/api/doc`, { cache: "no-store" });
      if (res.ok) {
        return await res.json();
      }
    } catch (_) {}
  }

  throw lastError || new Error("Failed to connect to backend server");
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
  const base = getApiBase();
  return `${base}/api/page/${page}/image${qs ? `?${qs}` : ""}`;
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
  const base = getApiBase();
  const endpoints = [
    `${base}/api/chat`,
    "/api/chat",
    `${PROD_BACKEND_URL}/api/chat`,
  ];

  let response: Response | null = null;
  let connectionError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
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

      if (res.ok) {
        response = res;
        break;
      }
    } catch (e: any) {
      connectionError = e;
    }
  }

  if (!response || !response.ok) {
    onError(
      connectionError ||
        new Error(
          "Failed to reach backend API. Please check your internet connection or backend status."
        )
    );
    return;
  }

  if (!response.body) {
    onError(new Error("No response body received from chat stream"));
    return;
  }

  try {
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

  const base = getApiBase();
  const res = await fetch(`${base}/api/index`, {
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
  const base = getApiBase();
  const res = await fetch(`${base}/api/index/status`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch index status: ${res.statusText}`);
  }
  return await res.json();
}
