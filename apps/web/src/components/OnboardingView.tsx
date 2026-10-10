import React, { useState, useEffect } from 'react';
import {
  Code2,
  Terminal,
  Cpu,
  Database,
  Layers,
  Server,
  Key,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  Zap,
  Building,
  Plus,
  ArrowRight,
  GitBranch,
  Gauge,
  Lock,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';

export const OnboardingView: React.FC = () => {
  const [selectedSdkTab, setSelectedSdkTab] = useState<'python' | 'mcp' | 'openai' | 'k8s'>('python');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<string>('workload-checkout');
  const [showRegisterModal, setShowRegisterModal] = useState<boolean>(false);
  const [newAppName, setNewAppName] = useState<string>('');
  const [newAppFramework, setNewAppFramework] = useState<string>('LangChain');
  const [newAppCluster, setNewAppCluster] = useState<string>('aws-eks-production-us-east-1');
  const [liveWorkloads, setLiveWorkloads] = useState<any[]>([]);
  const [liveAgents, setLiveAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [creating, setCreating] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadInventory();
  }, []);

  const loadInventory = async () => {
    setLoading(true);
    try {
      const [wList, aList] = await Promise.all([
        api.getWorkloads().catch(() => []),
        api.getAgents().catch(() => []),
      ]);
      setLiveWorkloads(wList || []);
      setLiveAgents(aList || []);
      if (wList && wList.length > 0) {
        if (!wList.some((w: any) => w.id === selectedApp)) {
          setSelectedApp(wList[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load inventory in OnboardingView:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const defaultWorkloads = [
    {
      id: 'workload-checkout',
      name: 'checkout-service',
      kind: 'Deployment',
      namespace: 'trust-lab',
      status: 'DEGRADED',
      replicas: 2,
      pods: [{ id: 'pod-checkout-7f89b', name: 'checkout-service-7f89b-xk42' }],
      service_account: { id: 'sa-checkout-service', name: 'checkout-sa' },
      total_events: 2,
    },
    {
      id: 'workload-proxy',
      name: 'frontend-proxy',
      kind: 'Deployment',
      namespace: 'trust-lab',
      status: 'ACTIVE',
      replicas: 3,
      pods: [{ id: 'pod-proxy-99aa1', name: 'frontend-proxy-99aa1-abc' }],
      service_account: { id: 'sa-frontend-proxy', name: 'proxy-sa' },
      total_events: 0,
    },
    {
      id: 'workload-order-processor',
      name: 'order-processor',
      kind: 'StatefulSet',
      namespace: 'trust-lab',
      status: 'DEGRADED',
      replicas: 1,
      pods: [{ id: 'pod-order-proc-01', name: 'order-processor-0' }],
      service_account: null,
      total_events: 1,
    },
  ];

  const applications = liveWorkloads.length > 0 ? liveWorkloads : defaultWorkloads;

  const activeWorkload = applications.find((w: any) => w.id === selectedApp) || applications[0];

  const activeAgent = liveAgents[0] || {
    id: 'agent-autodev',
    name: 'AutoDev-Agent',
    model: 'gemini-2.5-pro',
    capabilities: ['lookup_customer_balance', 'get_transaction_history', 'audit_read'],
  };

  const allowedScopes = Array.isArray(activeAgent.capabilities) && activeAgent.capabilities.length > 0
    ? activeAgent.capabilities.filter((c: string) => !['export_customer_vault', 'db_drop_table'].includes(c))
    : ['lookup_customer_balance', 'get_transaction_history', 'audit_read'];

  const codeSnippets = {
    python: `# 1. Install SDK
pip install runtime-trust-sdk langchain-core

# 2. Connect Your Agent to the Runtime Trust Layer
from runtime_trust import TrustGatewayProxy, GuardedAgent
from langchain_community.chat_models import ChatOpenAI

# Configure pre-execution enforcement gateway bound to workload '${activeWorkload.name || 'checkout-service'}'
trust_proxy = TrustGatewayProxy(
    gateway_url="http://localhost:8000",
    session_id="session-alice-dev-01",
    workload_id="${activeWorkload.id || 'workload-checkout'}",
    fail_closed=True  # Rejects all actions if graph is unreachable
)

# Guard tools for agent '${activeAgent.name || 'AutoDev-Agent'}'
guarded_tools = [trust_proxy.guard(t) for t in [${allowedScopes.slice(0, 3).join(', ')}]]

# Tool invocations are evaluated in FalkorDB in <15ms before execution
agent = GuardedAgent(tools=guarded_tools, model=ChatOpenAI(model="${activeAgent.model || 'gemini-2.5-pro'}"))
agent.run("Check customer account balance")`,

    mcp: `// Model Context Protocol (MCP) Configuration (~/.claude/mcp_config.json)
{
  "mcpServers": {
    "${activeWorkload.name || 'production-database'}": {
      "command": "trust-mcp-gateway-proxy",
      "args": [
        "--upstream-server", "http://localhost:8443",
        "--control-plane", "http://localhost:8000",
        "--workload-id", "${activeWorkload.id || 'workload-checkout'}",
        "--session-id", "session-alice-dev-01"
      ],
      "env": {
        "RUNTIME_TRUST_FAIL_CLOSED": "true"
      }
    }
  }
}`,

    openai: `# OpenAI API Direct Function Calling Proxy (1-Line Base URL Override)
import openai

# Route all model function calls through Trust Layer Gateway proxy
client = openai.OpenAI(
    base_url="http://localhost:8000/api/target-app",
    api_key="trust-session-token-dev",
    default_headers={
        "X-Workload-Id": "${activeWorkload.id || 'workload-checkout'}",
        "X-Session-Id": "session-alice-dev-01"
    }
)

# Requests route through FalkorDB authorization intersection before invoking downstream models
response = client.chat.completions.create(
    model="${activeAgent.model || 'gemini-2.5-pro'}",
    messages=[{"role": "user", "content": "Verify compliance audit ledger"}],
    tools=[{"type": "function", "function": {"name": "audit_read"}}]
)`,

    k8s: `# Kubernetes Deployment Manifest with Transparent Sidecar (Zero Code Changes)
apiVersion: apps/v1
kind: ${activeWorkload.kind || 'Deployment'}
metadata:
  name: ${activeWorkload.name || 'checkout-service'}
  namespace: ${activeWorkload.namespace || 'trust-lab'}
spec:
  replicas: ${activeWorkload.replicas || 1}
  template:
    metadata:
      labels:
        app: ${activeWorkload.name || 'checkout-service'}
        trust.layer/guarded: "true"
    spec:
      serviceAccountName: ${activeWorkload.service_account?.name || activeWorkload.name + '-sa'}
      containers:
        # Target workload container
        - name: app-container
          image: internal-registry.io/apps/${activeWorkload.name || 'checkout-service'}:v1.2.0
          env:
            - name: MCP_SERVER_URL
              value: "http://127.0.0.1:8080" # Routes locally into sidecar
            - name: WORKLOAD_ID
              value: "${activeWorkload.id || 'workload-checkout'}"

        # Runtime Trust Layer Enforcement Sidecar
        - name: trust-enforcer-sidecar
          image: runtime-trust/enforcer-sidecar:v1.0.0
          ports:
            - containerPort: 8080
          env:
            - name: TRUST_CONTROL_PLANE
              value: "http://trust-api.trust-system.svc:8000"
            - name: UPSTREAM_MCP
              value: "http://localhost:8443"`,
  };

  const yamlManifest = `# Runtime Trust Layer: Agent Delegation & Scope Grant
apiVersion: trust.layer/v1alpha1
kind: AgentDelegationGrant
metadata:
  name: grant-${activeWorkload.name || 'checkout-service'}
  namespace: ${activeWorkload.namespace || 'trust-lab'}
spec:
  principal:
    id: "principal-alice"
    email: "alice.henderson@apexfintech.com"
    authProvider: "okta_oidc"
    role: "Operations & Compliance Lead"
  agent:
    id: "${activeAgent.id || 'agent-autodev'}"
    model: "${activeAgent.model || 'gemini-2.5-pro'}"
  workloadBinding:
    workloadId: "${activeWorkload.id || 'workload-checkout'}"
    serviceAccount: "${activeWorkload.service_account?.name || activeWorkload.name + '-sa'}"
  session:
    ttlSeconds: 3600
    audience: "mcp-data-server"
  bounds:
    allowedScopes:
${allowedScopes.map((s: string) => `      - "${s}"`).join('\n')}
    explicitlyProhibited:
      - "export_customer_vault"
      - "db_drop_table"
  guardrails:
    failClosedOnOutage: true
    destructiveOperationsRequireMfa: true
    maxBlastRadiusDepth: 3`;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      {/* Top Header */}
      <div className="bg-white border border-[#e8e5de] rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-stone-900 tracking-tight">Onboarding & Architecture Guide</h1>
            <span className="text-[10px] font-mono uppercase bg-[#faf8f5] text-stone-700 border border-[#e8e5de] px-2 py-0.5 rounded-full font-semibold">
              PRODUCTION INTEGRATION
            </span>
          </div>
          <p className="text-xs text-stone-500 mt-1 max-w-2xl">
            How enterprise teams connect AI agents and applications to Runtime Trust Layer. Covers multi-app onboarding, graph algorithms, ingestion pipelines, and pre-execution latency optimizations.
          </p>
        </div>

        <button
          onClick={() => setShowRegisterModal(true)}
          className="px-4 py-2.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white font-semibold text-xs flex items-center space-x-2 cursor-pointer shadow-sm transition self-start md:self-auto shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Application</span>
        </button>
      </div>

      {/* Live Standalone External App Banner */}
      <div className="bg-[#faf8f5] border border-[#ede9df] rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700 font-bold text-sm shrink-0">
            3001
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm text-stone-900">Live External Agent Application Running</span>
              <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 rounded font-semibold">
                ONLINE ON PORT 3001
              </span>
            </div>
            <p className="text-xs text-stone-600 mt-0.5">
              Experience the Runtime Trust Layer as a standalone security tool protecting an independent CRM agent. Test prompt injection with Guard ON vs Guard OFF.
            </p>
          </div>
        </div>

        <a
          href="http://localhost:3001"
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 rounded-lg bg-purple-700 hover:bg-purple-800 text-white font-semibold text-xs flex items-center space-x-1.5 transition cursor-pointer shadow-sm shrink-0"
        >
          <span>Open Standalone App (Port 3001)</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Action feedback toast */}
      {feedback && (
        <div
          className={`p-3 rounded-lg border text-xs font-semibold flex items-center justify-between shadow-sm ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} className="text-stone-400 hover:text-stone-800 cursor-pointer ml-3">
            ✕
          </button>
        </div>
      )}

      {/* Section 1: Multi-Application Registry */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span className="text-xs font-bold text-stone-700 uppercase tracking-wider flex items-center space-x-2">
            <Building className="w-4 h-4 text-stone-700" />
            <span>Discovered Kubernetes Workloads & AI Agents</span>
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadInventory}
              disabled={loading}
              className="text-xs text-stone-500 hover:text-stone-800 flex items-center space-x-1 cursor-pointer transition"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Inventory</span>
            </button>
            <span className="text-xs text-stone-300 hidden sm:inline">•</span>
            <span className="text-xs text-stone-500 hidden sm:inline">Select a workload to inspect delegation topology</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {applications.map((app) => {
            const isSelected = selectedApp === app.id;
            const podCount = app.pods ? app.pods.length : (app.workloads || 1);
            const statusStr = app.status || 'ACTIVE';
            const isDegraded = statusStr === 'DEGRADED';

            return (
              <div
                key={app.id}
                onClick={() => setSelectedApp(app.id)}
                className={`p-4 rounded-xl border transition cursor-pointer relative ${
                  isSelected
                    ? 'bg-[#faf8f5] border-stone-800 shadow-sm ring-1 ring-stone-800/20'
                    : 'bg-white border-[#e8e5de] hover:border-stone-400 hover:bg-[#faf8f5]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-sm text-stone-900 truncate max-w-[130px]" title={app.name}>
                    {app.name}
                  </span>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      statusStr === 'ACTIVE'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : isDegraded
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-stone-100 text-stone-700 border border-stone-200'
                    }`}
                  >
                    {statusStr}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-stone-500">
                  <div className="flex items-center justify-between">
                    <span>Kind:</span>
                    <span className="text-stone-800 font-mono text-[11px]">{app.kind || app.framework || 'Deployment'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Namespace:</span>
                    <span className="text-stone-800 font-mono text-[11px]">{app.namespace || 'trust-lab'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Pods:</span>
                    <span className="text-emerald-700 font-mono font-bold">{podCount} Pod(s)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Observed Events:</span>
                    <span className="text-purple-700 font-mono text-[11px] font-medium">{app.total_events || 0}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 2: Step-by-Step Onboarding Walkthrough */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Step 1 & 2: Integration & Code Snippets (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Step 1: Manifest */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 rounded-full bg-stone-100 text-stone-700 font-bold text-xs flex items-center justify-center border border-stone-300">
                  1
                </span>
                <span className="font-bold text-sm text-stone-900">Define Identity & Delegation Bounds (YAML / JSON)</span>
              </div>
              <button
                onClick={() => copyToClipboard(yamlManifest, 'manifest')}
                className="px-2.5 py-1 rounded bg-stone-100 hover:bg-stone-200 border border-stone-300 text-[11px] text-stone-700 flex items-center space-x-1 cursor-pointer transition"
              >
                {copiedKey === 'manifest' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'manifest' ? 'Copied' : 'Copy Spec'}</span>
              </button>
            </div>
            <p className="text-xs text-stone-500">
              Every agent session requires an explicit delegation grant bound to a verified human principal SSO token. Tools outside allowed scopes are rejected deterministically before running.
            </p>
            <div className="bg-[#faf8f5] rounded-lg p-3.5 border border-[#ede9df] font-mono text-[11px] text-stone-800 overflow-x-auto max-h-56">
              <pre>{yamlManifest}</pre>
            </div>
          </div>

          {/* Step 2: SDK / Gateway Hookup */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 rounded-full bg-stone-100 text-stone-700 font-bold text-xs flex items-center justify-center border border-stone-300">
                  2
                </span>
                <span className="font-bold text-sm text-stone-900">Connect Agent Tool Gateway (1-Line Wrapper)</span>
              </div>
              <button
                onClick={() => copyToClipboard(codeSnippets[selectedSdkTab], 'code')}
                className="px-2.5 py-1 rounded bg-stone-100 hover:bg-stone-200 border border-stone-300 text-[11px] text-stone-700 flex items-center space-x-1 cursor-pointer transition"
              >
                {copiedKey === 'code' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'code' ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>

            {/* SDK Language Selector */}
            <div className="flex space-x-2 border-b border-[#e8e5de] pb-2">
              {[
                { id: 'python', label: 'Python / LangChain / CrewAI' },
                { id: 'mcp', label: 'Anthropic Claude (MCP JSON)' },
                { id: 'openai', label: 'OpenAI REST Proxy' },
                { id: 'k8s', label: 'Kubernetes Sidecar' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedSdkTab(t.id as any)}
                  className={`px-3 py-1.5 rounded text-xs font-semibold transition cursor-pointer ${
                    selectedSdkTab === t.id
                      ? 'bg-stone-900 text-white'
                      : 'text-stone-500 hover:text-stone-900'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="bg-[#faf8f5] rounded-lg p-3.5 border border-[#ede9df] font-mono text-[11px] text-stone-800 overflow-x-auto max-h-72">
              <pre>{codeSnippets[selectedSdkTab]}</pre>
            </div>
          </div>
        </div>

        {/* Step 3 & 4: Ingestion & Graph Architecture (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Step 3: How Workloads & Tools Are Populated */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-full bg-stone-100 text-stone-700 font-bold text-xs flex items-center justify-center border border-stone-300">
                3
              </span>
              <span className="font-bold text-sm text-stone-900">How Workloads & Tools Are Populated</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-stone-900">
                  <GitBranch className="w-3.5 h-3.5 text-stone-700" />
                  <span>Pipeline A: Static Manifest Ingestion (GitOps)</span>
                </div>
                <p className="text-stone-600 leading-relaxed text-[11px]">
                  Scans OpenAPI schemas, MCP manifests, Helm values, and Kubernetes ServiceAccount RBAC configs on git push to build the static authorized permission graph.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-stone-900">
                  <Key className="w-3.5 h-3.5 text-stone-700" />
                  <span>Pipeline B: SSO & Identity Token Mapping</span>
                </div>
                <p className="text-stone-600 leading-relaxed text-[11px]">
                  Synchronizes Okta OIDC and AWS IAM tokens into <code className="text-stone-900 font-semibold">Principal</code> and <code className="text-stone-900 font-semibold">AgentSession</code> nodes with cryptographic expiry and audience bindings.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-stone-900">
                  <Cpu className="w-3.5 h-3.5 text-stone-700" />
                  <span>Pipeline C: Dynamic eBPF & Gateway Discovery</span>
                </div>
                <p className="text-stone-600 leading-relaxed text-[11px]">
                  Linux eBPF probes (<code className="text-stone-900 font-semibold">sys_enter_connect</code>) and the MCP Gateway dynamically capture live socket calls, continually adding verified <code className="text-stone-900 font-semibold">OBSERVED_ACCESS</code> edges.
                </p>
              </div>
            </div>
          </div>

          {/* Step 4: Graph Engine Algorithms & Optimizations */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-full bg-stone-100 text-stone-700 font-bold text-xs flex items-center justify-center border border-stone-300">
                4
              </span>
              <span className="font-bold text-sm text-stone-900">Graph Engine, Algorithm & Latency</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1.5">
                <span className="font-bold text-amber-800 flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5 text-amber-700" />
                  <span>Why Graph vs Relational Database?</span>
                </span>
                <p className="text-stone-600 text-[11px] leading-relaxed">
                  Delegation chains, tool invocations, and cloud reachability form an arbitrary directed mesh. Relational SQL queries require recursive CTE joins that take hundreds of milliseconds; FalkorDB native graph pointers traverse multi-hop paths in single-digit milliseconds.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1.5">
                <span className="font-bold text-stone-900 flex items-center space-x-1.5">
                  <Gauge className="w-3.5 h-3.5 text-stone-700" />
                  <span>The Traversal Algorithm: Bounded BFS</span>
                </span>
                <p className="text-stone-600 text-[11px] leading-relaxed">
                  Uses bounded Breadth-First Search (BFS) in Cypher:
                  <code className="block mt-1 p-1 bg-white border border-[#e8e5de] rounded text-stone-800 font-mono text-[10px]">
                    MATCH (p)-[:OWNS]-&gt;(s)-[:DELEGATES_TO*1..3]-&gt;(a)-[:CAN_INVOKE]-&gt;(t)
                  </code>
                  Bounds maximum depth to <code className="text-stone-900 font-semibold">k=4</code> to guarantee polynomial <code className="text-stone-900 font-semibold">O(V + E)</code> execution and avoid graph path explosion.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#faf8f5] border border-[#ede9df] space-y-1.5">
                <span className="font-bold text-emerald-800 flex items-center space-x-1.5">
                  <Zap className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Sub-15ms Latency Optimizations</span>
                </span>
                <ul className="text-stone-600 text-[11px] space-y-1 list-disc pl-4">
                  <li>In-memory Redis engine backing FalkorDB graph nodes.</li>
                  <li>Primary key hash indexes on <code className="text-stone-800 font-medium">AgentSession.id</code> and <code className="text-stone-800 font-medium">Tool.name</code>.</li>
                  <li>Compiled Cypher AST query plan caching.</li>
                  <li><strong className="text-stone-900">Deterministic Fail-Closed:</strong> Unreachable database defaults to HTTP 503 DENY immediately.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Register New Application Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#e8e5de] rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-stone-900">Register New Kubernetes Workload</h3>
            <p className="text-xs text-stone-500">
              Provision an active Workload node in the FalkorDB trust graph to bind autonomous agents, enforce delegations, and monitor telemetry.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-stone-700 font-semibold mb-1">Workload Name</label>
                <input
                  type="text"
                  value={newAppName}
                  onChange={(e) => setNewAppName(e.target.value)}
                  placeholder="e.g. settlement-engine"
                  className="w-full bg-[#faf8f5] border border-[#dedad2] rounded-lg px-3 py-2 text-stone-900 placeholder-stone-400 focus:outline-none focus:border-stone-500 font-mono text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-stone-700 font-semibold mb-1">Kind</label>
                  <select
                    value={newAppFramework}
                    onChange={(e) => setNewAppFramework(e.target.value)}
                    className="w-full bg-[#faf8f5] border border-[#dedad2] rounded-lg px-3 py-2 text-stone-900 focus:outline-none focus:border-stone-500 text-xs"
                  >
                    <option value="Deployment">Deployment</option>
                    <option value="StatefulSet">StatefulSet</option>
                    <option value="DaemonSet">DaemonSet</option>
                    <option value="Job">Job</option>
                  </select>
                </div>
                <div>
                  <label className="block text-stone-700 font-semibold mb-1">Namespace</label>
                  <input
                    type="text"
                    defaultValue="trust-lab"
                    className="w-full bg-[#faf8f5] border border-[#dedad2] rounded-lg px-3 py-2 text-stone-900 focus:outline-none focus:border-stone-500 font-mono text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-stone-700 font-semibold mb-1">Target Cluster</label>
                <input
                  type="text"
                  defaultValue="aws-eks-production-us-east-1"
                  className="w-full bg-[#faf8f5] border border-[#dedad2] rounded-lg px-3 py-2 text-stone-900 placeholder-stone-400 focus:outline-none focus:border-stone-500 font-mono text-[11px]"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-[#e8e5de]">
              <button
                onClick={() => setShowRegisterModal(false)}
                disabled={creating}
                className="px-3.5 py-2 rounded-lg bg-stone-100 text-stone-700 text-xs hover:bg-stone-200 cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={creating || !newAppName.trim()}
                onClick={async () => {
                  if (!newAppName.trim()) return;
                  setCreating(true);
                  try {
                    const res = await api.createWorkload({
                      name: newAppName.trim(),
                      namespace: 'trust-lab',
                      kind: newAppFramework || 'Deployment',
                      cluster: 'aws-eks-production-us-east-1',
                    });
                    setShowRegisterModal(false);
                    setNewAppName('');
                    setFeedback({
                      type: 'success',
                      message: `Workload "${res.workload.name}" (${res.workload.id}) provisioned into FalkorDB!`,
                    });
                    await loadInventory();
                    setSelectedApp(res.workload.id);
                  } catch (err: any) {
                    setFeedback({
                      type: 'error',
                      message: `Registration failed: ${err.message || 'Unknown error'}`,
                    });
                  } finally {
                    setCreating(false);
                  }
                }}
                className="px-4 py-2 rounded-lg bg-stone-900 hover:bg-stone-800 disabled:opacity-50 text-white font-semibold text-xs cursor-pointer shadow flex items-center space-x-1.5"
              >
                {creating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>{creating ? 'Provisioning...' : 'Provision Workload'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
