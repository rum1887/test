export interface Alert {
  id: string;
  title: string;
  kind: string;
  severity: string;
  status: string;
  at: number;
  target_id: string;
  target_type?: string;
  investigation_id?: string;
  investigation_status?: string;
}

export interface Hypothesis {
  id: string;
  title: string;
  status: 'open' | 'supported' | 'refuted';
  confidence: number;
}

export interface Claim {
  text: string;
  evidence_ids: string[];
}

export interface RecommendedAction {
  type: string;
  target_id: string;
  rationale: string;
}

export interface Verdict {
  verdict: 'benign' | 'malicious' | 'needs_human' | 'insufficient_evidence';
  confidence: number;
  severity: string;
  summary: string;
  claims: Claim[];
  recommended_actions: RecommendedAction[];
  open_questions?: string[];
}

export interface ApprovalRequest {
  id: string;
  investigation_id: string;
  action: string;
  target_id: string;
  status: 'pending' | 'approved' | 'rejected';
  rationale: string;
  created_at: number;
  approver?: string;
  approved_at?: number;
}

export interface Investigation {
  id: string;
  status: 'running' | 'awaiting_approval' | 'paused_watch' | 'done' | 'killed';
  started_at: number;
  updated_at: number;
  alert_id?: string;
  alert_title?: string;
  severity?: string;
  verdict?: any;
  confidence?: number;
  summary?: string;
  hypotheses?: Hypothesis[];
  hypotheses_from_graph?: Hypothesis[];
  claims?: Claim[];
  evidence_store?: Record<string, string>;
  approvals?: ApprovalRequest[];
  step_count?: number;
  tool_call_count?: number;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
}

export interface Scenario {
  id: string;
  pair_id: string;
  variant: 'benign' | 'malicious';
  title: string;
  description: string;
  inject: boolean;
  alert: {
    id: string;
    title: string;
    kind: string;
    severity: string;
    target_id: string;
    target_label: string;
  };
  ground_truth: {
    verdict: string;
    rationale: string;
    required_evidence: string[];
    correct_actions: string[];
  };
}

export interface Watch {
  id: string;
  investigation_id: string;
  kind: string;
  status: string;
  created_at: number;
  expires_at: number;
  triggered_at?: number;
  spec?: string | Record<string, any>;
}

export interface ScheduledTask {
  id: string;
  investigation_id: string;
  action: string;
  due_at: number;
  status: string;
  payload?: string | Record<string, any>;
}

export interface SubgraphElement {
  data: {
    id: string;
    label?: string;
    type?: string;
    source?: string;
    target?: string;
  };
}

export interface SubgraphData {
  nodes: SubgraphElement[];
  edges: SubgraphElement[];
}

export interface EvalMetricRecord {
  scenario_id: string;
  pair_id: string;
  variant: string;
  is_injected: boolean;
  predicted_verdict: string;
  ground_truth_verdict: string;
  is_correct: boolean;
  evidence_recall: number;
  resisted_injection: boolean;
}

export interface EvalMetrics {
  evaluator_name: string;
  total_scenarios: number;
  accuracy: number;
  fpr: number;
  fnr: number;
  precision: number;
  evidence_recall: number;
  injection_resistance_rate: number;
  avg_tokens_per_scenario: number;
  avg_cost_per_scenario: number;
  records: EvalMetricRecord[];
}
