/**
 * TypeScript type definitions for Report Navigator frontend.
 */

export interface Citation {
  page: number;
  label?: string | number;
  quote: string;
  verified?: boolean;
  reason?: string;
  type?: "text" | "table";
  chunk_id?: string;
  source_id?: string;
  section?: string;
  full_text?: string;
  table_context?: {
    row_label?: string;
    col_label?: string;
    cell_value?: string;
    sheet_name?: string;
  };
}

export interface RetrievalSource {
  source_id: string;
  type: "text" | "table";
  page: number;
  label?: string | number;
  section?: string;
  score?: number;
  text?: string;
  table_html?: string;
  table_markdown?: string;
  chunk_id?: string;
}

export interface RetrievalTrace {
  standalone_query: string;
  keywords: string[];
  num_retrieved: number;
  top_sources: RetrievalSource[];
  query_type?: string;
  elapsed_ms?: number;
}

export interface AnswerResponse {
  answer: string;
  found: boolean;
  confidence: "high" | "medium" | "low";
  citations: Citation[];
  retrieval_trace?: RetrievalTrace;
  calculation?: string;
  has_number_warning?: boolean;
  model?: string;
  source_count?: number;
}

export interface DocumentMetadata {
  title: string;
  filename: string;
  page_count: number;
  table_count: number;
  starter_questions: string[];
}

export interface PipelineStep {
  step: "rewriting" | "searching" | "reading" | "verifying" | string;
  message: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content?: string;
  isLoading?: boolean;
  answer?: AnswerResponse;
}

export interface IndexStatus {
  status: "idle" | "starting" | "ingesting" | "indexing" | "complete" | "error";
  progress: number;
  message: string;
}
