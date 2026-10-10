/**
 * Typed API Client for Runtime Trust Layer.
 * Configured via import.meta.env.VITE_API_BASE_URL for static hosting.
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export interface HealthResponse {
  status: 'HEALTHY' | 'DEGRADED';
  database: {
    healthy: boolean;
    host: string;
    port: number;
    graph_name: string;
    last_error: string | null;
  };
  sensor: {
    sensor_name: string;
    mode: 'live_ebpf' | 'replay_synthetic';
    is_live: boolean;
    last_event_timestamp: number | null;
    total_events_ingested: number;
    dropped_events_count: number;
    is_stale: boolean;
    stale_warning: string | null;
  };
}

export interface StatsResponse {
  nodes_total: number;
  edges_total: number;
  workloads_count: number;
  pods_count: number;
  agents_count: number;
  principals_count: number;
  events_count: number;
  sensitive_resources_count: number;
  decisions_count: number;
  entities: Record<string, number>;
  relationships: Record<string, number>;
}

export interface CytoscapeNode {
  data: {
    id: string;
    label: string;
    name: string;
    category: string;
    status: string;
    sensitivity?: string;
    severity?: string;
    mode?: string;
    event_type?: string;
    process_name?: string;
    command_line?: string;
  };
}

export interface CytoscapeEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label: string;
    evidence: string;
    evidence_type: 'configured' | 'inferred' | 'observed' | 'simulated';
    confidence: number;
  };
}

export interface GraphResponse {
  elements: {
    nodes: CytoscapeNode[];
    edges: CytoscapeEdge[];
  };
  counts: {
    nodes: number;
    edges: number;
  };
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    return res.json();
  },

  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE_URL}/api/stats`);
    return res.json();
  },

  async getGraph(labels?: string, scenarioId?: string): Promise<GraphResponse> {
    const params = new URLSearchParams();
    if (labels) params.set('labels', labels);
    if (scenarioId) params.set('scenario_id', scenarioId);
    const res = await fetch(`${API_BASE_URL}/api/graph?${params.toString()}`);
    return res.json();
  },

  async getWorkloads(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/workloads`);
    return res.json();
  },

  async getWorkloadDetail(id: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/workloads/${encodeURIComponent(id)}`);
    return res.json();
  },

  async getAgents(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/agents`);
    return res.json();
  },

  async getSessions(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/agents/sessions`);
    return res.json();
  },

  async getTools(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/agents/tools`);
    return res.json();
  },

  async getEvents(severity?: string, mode?: string, limit = 50): Promise<any[]> {
    const params = new URLSearchParams();
    if (severity) params.set('severity', severity);
    if (mode) params.set('mode', mode);
    params.set('limit', String(limit));
    const res = await fetch(`${API_BASE_URL}/api/events?${params.toString()}`);
    return res.json();
  },

  async triggerReplay(count = 3): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/events/replay?count=${count}`, {
      method: 'POST',
    });
    return res.json();
  },

  async getBlastRadius(targetId: string, maxDepth = 5): Promise<any> {
    const res = await fetch(
      `${API_BASE_URL}/api/blast-radius?target_id=${encodeURIComponent(targetId)}&max_depth=${maxDepth}`
    );
    return res.json();
  },

  async traceDelegation(sessionId: string, tool?: string): Promise<any> {
    const params = new URLSearchParams({ session_id: sessionId });
    if (tool) params.set('tool', tool);
    const res = await fetch(`${API_BASE_URL}/api/delegation-chain?${params.toString()}`);
    return res.json();
  },

  async getAttackPaths(sources?: string): Promise<any> {
    const params = new URLSearchParams();
    if (sources) params.set('sources', sources);
    const res = await fetch(`${API_BASE_URL}/api/attack-paths?${params.toString()}`);
    return res.json();
  },

  async evaluatePolicy(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/policies/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  async invokeGateway(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/gateway/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  async getContainmentCandidates(sourceId: string): Promise<any> {
    const res = await fetch(
      `${API_BASE_URL}/api/containment/candidates?source_id=${encodeURIComponent(sourceId)}`
    );
    return res.json();
  },

  async simulateContainment(sourceId: string, excludedNodeId?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/containment/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, excluded_node_id: excludedNodeId }),
    });
    return res.json();
  },

  async applyContainment(targetId: string, actionType: string, mechanism: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/enforcement/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_id: targetId,
        action_type: actionType,
        enforcement_mechanism: mechanism,
      }),
    });
    return res.json();
  },

  async verifyContainment(actionId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/enforcement/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_id: actionId }),
    });
    return res.json();
  },

  async listContainmentActions(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/enforcement/actions`);
    return res.json();
  },

  async getScenarios(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/api/scenarios`);
    return res.json();
  },

  async resetGraph(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/scenarios/reset`, { method: 'POST' });
    return res.json();
  },

  async loadScenario(scenarioKey: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/scenarios/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_key: scenarioKey }),
    });
    return res.json();
  },

  async getTimeline(limit = 50): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/audit/timeline?limit=${limit}`);
    return res.json();
  },

  async getViolations(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/audit/violations`);
    return res.json();
  },

  async getTelemetryHealth(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/audit/telemetry-health`);
    return res.json();
  },

  async getIntegrity(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/audit/integrity`);
    return res.json();
  },

  async getCompliancePosture(): Promise<CompliancePostureResponse> {
    const res = await fetch(`${API_BASE_URL}/api/compliance/posture`);
    return res.json();
  },

  async getComplianceReport(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/compliance/report`);
    return res.json();
  },

  getComplianceExportUrl(): string {
    return `${API_BASE_URL}/api/compliance/report/export`;
  },

  async exportContainmentIaC(targetId: string, actionType = 'QUARANTINE_POD'): Promise<IaCExportResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/containment/export-iac?target_id=${encodeURIComponent(targetId)}&action_type=${encodeURIComponent(actionType)}`
    );
    return res.json();
  },

  async getTargetAppState(): Promise<TargetAppState> {
    const res = await fetch(`${API_BASE_URL}/api/target-app/state`);
    return res.json();
  },

  async sendTargetAppChat(req: { message: string; session_id?: string; account_id?: string }): Promise<TargetAppChatResponse> {
    const res = await fetch(`${API_BASE_URL}/api/target-app/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return res.json();
  },

  async resetTargetAppSession(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/target-app/reset-session`, { method: 'POST' });
    return res.json();
  },
};

export interface TargetAppState {
  application_name: string;
  app_id: string;
  environment: string;
  connected_agent: {
    id: string;
    name: string;
    model: string;
    session_id: string;
    principal: {
      name: string;
      role: string;
    };
    delegated_scopes: string[];
    session_status: string;
  };
  target_customer: {
    account_id: string;
    holder_name: string;
    company: string;
    tier: string;
    verified: boolean;
    ledger_balance: string;
    credit_limit: string;
  };
  protected_crown_jewels: {
    id: string;
    name: string;
    sensitivity: string;
    compliance: string[];
  }[];
}

export interface TargetAppChatResponse {
  message: string;
  attack_detected: boolean;
  attack_category: string;
  agent_thought: string;
  tool_called: {
    name: string;
    parameters: Record<string, any>;
  };
  gateway_intercepted: boolean;
  status_code: number;
  decision: {
    decision_id: string;
    decision: 'ALLOW' | 'DENY' | 'REQUIRE_APPROVAL' | 'RESTRICT';
    rationale: string;
    evaluated_rules: {
      rule_id: string;
      rule_name: string;
      passed: boolean;
      description: string;
      remediation: string;
    }[];
    enforcement_point: string;
    timestamp: number;
  };
  execution_result?: any;
  agent_reply: string;
  averted_consequence: string;
  latency_ms: number;
  evidence_hash: string;
  timestamp: number;
}

export interface ComplianceControl {
  id: string;
  title: string;
  category: string;
  status: 'PASS' | 'FAIL' | 'WARNING';
  evidence: string;
  impact: string;
}

export interface FrameworkData {
  name: string;
  score: number;
  status: string;
  controls: ComplianceControl[];
}

export interface ComplianceFinding {
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  framework: string;
  description: string;
  remediation: string;
}

export interface CompliancePostureResponse {
  timestamp: number;
  tenant_id: string;
  tenant_name: string;
  cluster_context: string;
  overall_security_score: number;
  risk_level: 'CRITICAL' | 'ELEVATED' | 'OPTIMAL';
  total_exposure_usd: number;
  mean_time_to_containment_seconds: number;
  industry_benchmark_mttc_hours: number;
  frameworks: {
    pci_dss_4: FrameworkData;
    soc2_type2: FrameworkData;
    eu_ai_act: FrameworkData;
    nist_ai_rmf: FrameworkData;
  };
  critical_findings: ComplianceFinding[];
  sensitive_resources: {
    id: string;
    name: string;
    type: string;
    sensitivity: string;
    reachers_count: number;
    exposure_value: number;
  }[];
}

export interface IaCExportResponse {
  target_id: string;
  action_type: string;
  artifacts: {
    kubernetes_network_policy_yaml: string;
    kyverno_cluster_policy_yaml: string;
    mcp_gateway_filter_json: string;
    terraform_aws_sg_hcl: string;
  };
}

