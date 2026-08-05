export type AgentFileUploadResponse = {
  session_id: string;
  file_id: string;
  original_filename: string;
  expires_at: string;
  validated_for_agent: boolean;
  rag_indexable: boolean;
  sheet_names: string[];
};

export type AgentSidebarConversation = {
  run_id: string;
  session_id: string | null;
  file_id: string | null;
  title: string;
  status: string;
  created_at: string;
};

export type AgentSidebarConversationListResponse = {
  items: AgentSidebarConversation[];
};

export type AgentConversationHistoryMessage = {
  message_id: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
};

export type AgentConversationDetailResponse = {
  run_id: string;
  session_id: string | null;
  file_id: string | null;
  messages: AgentConversationHistoryMessage[];
};

export type AgentSidebarFile = {
  session_id: string;
  file_id: string;
  original_filename: string;
  file_size_bytes: number | null;
  sheet_names: string[];
  created_at: string;
  expires_at: string;
  status: string;
};

export type AgentSidebarFileListResponse = {
  items: AgentSidebarFile[];
};

export type AgentDashboardChart = {
  chart_id: string;
  title: string;
  kind: string;
  metric: string;
  labels: string[];
  values: Array<number>;
  series: Array<{
    name: string;
    values: Array<number>;
  }>;
  metadata: Record<string, unknown>;
};

export type AgentFileDashboard = {
  file_id: string;
  sheet_name: string;
  summary: Record<string, unknown>;
  schema_overview: Record<string, unknown>;
  metrics: Record<string, unknown>;
  amount_metrics_by_currency: Record<string, Record<string, number>>;
  charts: AgentDashboardChart[];
  quality: Record<string, unknown>;
};

export type AgentDataQualityIssue = {
  issue_type: string;
  severity: string;
  canonical_field: string | null;
  source_column: string | null;
  affected_count: number;
  affected_ratio: number;
  message: string;
  affected_accounts?: Array<{
    account: string;
    affected_count: number;
  }>;
};

export type AgentSessionContextEvent = AgentRunEvent & {
  created_at: string;
};

export type AgentSessionContextResponse = {
  state: "empty" | "ready" | string;
  session_id: string;
  active_file: AgentSidebarFile | null;
  files: AgentSidebarFile[];
  dashboard: AgentFileDashboard | null;
  last_agent_events: AgentSessionContextEvent[];
};

export type AgentAttachedFile = {
  sessionId: string;
  fileId: string;
  filename: string;
  sizeBytes: number;
  previewUrl: string | null;
  expiresAt: string;
  sheetNames: string[];
  selectedSheetName: string;
};

export type AgentErrorResponse = {
  error: {
    code: string;
    message: string;
  };
};

export type AgentRunEvent = {
  event_type: string;
  title: string;
  message: string;
  status: "completed" | "running" | "streaming" | "error" | string;
  tool_name: string | null;
  provider_name: string | null;
  model_name: string | null;
};

export type AgentRunResponse = {
  answer: string;
  provider_name: string;
  model_name: string;
  execution_events: AgentRunEvent[];
  tool_results: Array<{
    tool_name: string;
    ok: boolean;
    output: Record<string, unknown>;
    error_code: string | null;
    error_message: string | null;
  }>;
};

export type AgentRunRequest = {
  message: string;
  sessionId?: string;
  fileId?: string;
  sheetName?: string;
};

export type AgentRunStreamMessage =
  | {
      type: "event";
      data: AgentRunEvent;
    }
  | {
      type: "result";
      data: AgentRunResponse;
    };

export type LedgerAnalysisSchema = {
  is_valid: boolean;
  present_columns: string[];
  missing_required_columns: string[];
  optional_columns: string[];
};

export type LedgerAnalysisColumn = {
  name: string;
  position: number;
  detected_type: string;
  non_empty_count: number;
  missing_count: number;
  missing_ratio: number;
};

export type LedgerPreAnalysis = {
  sheetName: string;
  rowCount: number;
  columnCount: number;
  schema: LedgerAnalysisSchema;
  columns: LedgerAnalysisColumn[];
};

export type LedgerQueryResult = {
  sheetName: string;
  totalMatches: number;
  page: number;
  pageSize: number;
  filters: Record<string, unknown>;
  returnedColumns: string[];
  entries: Array<Record<string, unknown>>;
  signConvention: string | null;
};

export type RasCandidateDetectionResult = {
  sheetName: string;
  rowCount: number;
  evaluatedPieceCount: number;
  candidatePieceCount: number;
  excludedPieceCount: number;
  rejectedRowCount: number;
  statusCounts: Record<string, number>;
  signalCounts: Record<string, number>;
  operationHintCounts: Record<string, number>;
  candidateAmountsByCurrency: Record<string, string>;
  missingFactCounts: Record<string, number>;
  issueCounts: Record<string, number>;
  rasReview: RasReviewSummary | null;
  decisionStatus: string;
  semanticModel: Record<string, unknown> | null;
};

export type RasReviewPeriod = {
  period: string;
  evaluatedEntryCount: number;
  candidateEntryCount: number;
  candidateAmount: number;
  cumulativeCandidateAmount: number;
  candidateRate: number;
  currency: string | null;
};

export type RasReviewSummary = {
  periods: RasReviewPeriod[];
};

export type AgentConversationMessage =
  | {
      id: string;
      role: "user";
      content: string;
      attachedFile: AgentAttachedFile | null;
    }
  | {
      id: string;
      role: "assistant";
      content: string | null;
      status: "loading" | "done" | "error";
      hasFileContext: boolean;
      preAnalysis: LedgerPreAnalysis | null;
      ledgerQuery: LedgerQueryResult | null;
      executionEvents: AgentRunEvent[];
      providerName: string | null;
      modelName: string | null;
    };
