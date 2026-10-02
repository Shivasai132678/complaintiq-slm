export interface Complaint {
  id: string;
  text: string;
  product: string;
  issue: string;
  priority: string;
  priority_reason: string;
  department: string;
  action: string;
  summary: string;
  summary_method?: string;
  status: string;
  backend: string;
  model_version: string;
  latency_ms: number;
  created_at: string;
  explanation: { token: string; weight: number }[];
  explanation_method?: string;
}
export interface Analytics {
  total: number;
  by_product: Record<string, number>;
  by_priority: Record<string, number>;
  by_department: Record<string, number>;
  by_backend: Record<string, number>;
  needs_review: number;
  average_latency_ms: number;
}
export interface Scores {
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  labels: string[];
  confusion_matrix: number[][];
}
export interface Evaluation {
  model: string;
  backend: string;
  test_size: number;
  status: string;
  product: Scores;
  issue: Scores;
  joint_accuracy: number;
  latency_ms_mean: number;
  review_rate: number;
  limitations: string | string[];
}
export interface BatchResult {
  items: (Complaint | { text: string; error: string })[];
  saved: number;
}
