export interface Health {
  backend: "baseline" | "slm";
  model_version: string;
  slm_status: string;
  training_status: string;
  training_size?: number;
}
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
  input_truncated?: boolean;
  input_chars_used?: number;
  cached?: boolean;
  scope_check?: {
    in_scope: boolean;
    score: number;
    reason: string;
    method?: string;
  } | null;
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
