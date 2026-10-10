import {
  Alert,
  ApprovalRequest,
  EvalMetrics,
  Investigation,
  Scenario,
  ScheduledTask,
  SubgraphData,
  Watch,
} from './types';

const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function fetchClock(): Promise<{ now: number; formatted: string }> {
  const res = await fetch(`${API_BASE}/api/clock`);
  return res.json();
}

export async function advanceClock(seconds: number = 300) {
  const res = await fetch(`${API_BASE}/api/clock/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seconds }),
  });
  return res.json();
}

export async function resetClock() {
  const res = await fetch(`${API_BASE}/api/clock/reset`, { method: 'POST' });
  return res.json();
}

export async function seedWorld(seed: number = 42) {
  const res = await fetch(`${API_BASE}/api/world/seed?seed=${seed}`, { method: 'POST' });
  return res.json();
}

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/api/scenarios`);
  return res.json();
}

export async function runScenario(scenarioId: string) {
  const res = await fetch(`${API_BASE}/api/scenarios/${scenarioId}/run`, { method: 'POST' });
  return res.json();
}

export async function fetchAlerts(): Promise<Alert[]> {
  const res = await fetch(`${API_BASE}/api/alerts`);
  return res.json();
}

export async function fetchInvestigations(): Promise<Investigation[]> {
  const res = await fetch(`${API_BASE}/api/investigations`);
  return res.json();
}

export async function fetchInvestigation(id: string): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/api/investigations/${id}`);
  return res.json();
}

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const res = await fetch(`${API_BASE}/api/approvals`);
  return res.json();
}

export async function actOnApproval(apprId: string, actionDecision: string = 'approved') {
  const res = await fetch(`${API_BASE}/api/approvals/${apprId}/act`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action_decision: actionDecision, approver: 'alice_secops_lead' }),
  });
  return res.json();
}

export async function fetchSubgraph(centerId?: string, depth: number = 2): Promise<SubgraphData> {
  const url = centerId
    ? `${API_BASE}/api/graph/subgraph?center_id=${encodeURIComponent(centerId)}&depth=${depth}`
    : `${API_BASE}/api/graph/subgraph?depth=${depth}`;
  const res = await fetch(url);
  return res.json();
}

export async function fetchWatches(): Promise<Watch[]> {
  const res = await fetch(`${API_BASE}/api/watches`);
  return res.json();
}

export async function fetchTasks(): Promise<ScheduledTask[]> {
  const res = await fetch(`${API_BASE}/api/tasks`);
  return res.json();
}

export async function fetchEvalResults(): Promise<Record<string, EvalMetrics>> {
  const res = await fetch(`${API_BASE}/api/eval/results`);
  if (!res.ok) {
    throw new Error(`Eval results failed: ${res.status}`);
  }
  return res.json();
}
