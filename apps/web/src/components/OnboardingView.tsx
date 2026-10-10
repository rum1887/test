import React, { useState } from 'react';
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
} from 'lucide-react';

export const OnboardingView: React.FC = () => {
  const [selectedSdkTab, setSelectedSdkTab] = useState<'python' | 'mcp' | 'openai' | 'k8s'>('python');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<string>('apex-fintech');
  const [showRegisterModal, setShowRegisterModal] = useState<boolean>(false);
  const [newAppName, setNewAppName] = useState<string>('');
  const [newAppFramework, setNewAppFramework] = useState<string>('LangChain');

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const applications = [
    {
      id: 'apex-fintech',
      name: 'Apex FinTech Banking Core',
      framework: 'LangChain + Gemini',
      environment: 'aws-eks-production',
      status: 'ACTIVE & GUARDED',
      agent: 'agent-apex-ops',
      workloads: 4,
      toolsGuarded: 6,
    },
    {
      id: 'healthcore-ehr',
      name: 'HealthCore Clinical Records',
      framework: 'Claude Desktop MCP',
      environment: 'gcp-gke-hipaa',
      status: 'READY TO CONNECT',
      agent: 'agent-clinical-triage',
      workloads: 3,
      toolsGuarded: 4,
    },
    {
      id: 'logiflow-ops',
      name: 'LogiFlow Supply Chain Fleet',
      framework: 'CrewAI Multi-Agent',
      environment: 'azure-aks-westus',
      status: 'READY TO CONNECT',
      agent: 'agent-dispatcher-fleet',
      workloads: 8,
      toolsGuarded: 12,
    },
  ];

  const codeSnippets = {
    python: `# 1. Install SDK
pip install runtime-trust-sdk langchain-core

# 2. Connect Your Agent to the Runtime Trust Layer
from runtime_trust import TrustGatewayProxy, GuardedAgent
from langchain_community.chat_models import ChatOpenAI
from my_tools import lookup_customer_balance, export_customer_vault

# Configure pre-execution enforcement gateway
trust_proxy = TrustGatewayProxy(
    gateway_url="https://trust-api.internal.cluster.local:8000",
    session_id="session-alice-dev-01",
    fail_closed=True  # Rejects all actions if graph is unreachable
)

# Wrap tools with deterministic graph guard
guarded_tools = [trust_proxy.guard(t) for t in [lookup_customer_balance, export_customer_vault]]

# All tool invocations are evaluated in FalkorDB in <15ms before execution
agent = GuardedAgent(tools=guarded_tools, model=ChatOpenAI(model="gpt-4o"))
agent.run("Check balance for customer #104")`,

    mcp: `// Model Context Protocol (MCP) Configuration (~/.claude/mcp_config.json)
{
  "mcpServers": {
    "apex-database-service": {
      "command": "trust-mcp-gateway-proxy",
      "args": [
        "--upstream-server", "http://database-mcp.internal:8443",
        "--control-plane", "http://trust-api.internal:8000",
        "--session-token", "env:TRUST_SESSION_TOKEN",
        "--enforce-delegation", "true"
      ],
      "env": {
        "TRUST_SESSION_TOKEN": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae"
      }
    }
  }
}`,

    openai: `# OpenAI API Direct Function Calling Proxy (1-Line Base URL Override)
import openai

# Route all model function calls through Trust Layer Gateway proxy
client = openai.OpenAI(
    base_url="http://trust-api.internal:8000/v1/proxy",
    api_key="your-openai-api-key",
    default_headers={
        "X-Trust-Session-ID": "session-alice-dev-01",
        "X-Principal-ID": "principal-alice",
        "X-Enforcement-Mode": "STRICT_BLOCK"
    }
)

# If model attempts unauthorized tool, Gateway halts with HTTP 403 Forbidden
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Export customer vault keys"}],
    tools=my_function_definitions
)`,

    k8s: `# Kubernetes Deployment Manifest with Transparent Sidecar (Zero Code Changes)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-support-agent
  namespace: trust-lab
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: apex-support-agent
    spec:
      serviceAccountName: apex-agent-sa
      containers:
        # Your unmodified AI Agent Container
        - name: agent-app
          image: apex/support-agent:v1.4.2
          env:
            - name: MCP_SERVER_URL
              value: "http://127.0.0.1:8080" # Routes locally into sidecar

        # Runtime Trust Layer Enforcement Sidecar
        - name: trust-enforcer-sidecar
          image: runtime-trust/enforcer-sidecar:v1.0.0
          ports:
            - containerPort: 8080
          env:
            - name: TRUST_CONTROL_PLANE
              value: "http://trust-api.trust-system.svc:8000"
            - name: UPSTREAM_MCP
              value: "http://production-mcp.internal:8443"`,
  };

  const yamlManifest = `# Runtime Trust Layer: Agent Delegation & Scope Grant
apiVersion: trust.layer/v1alpha1
kind: AgentDelegationGrant
metadata:
  name: grant-apex-customer-ops
  namespace: trust-lab
spec:
  principal:
    id: "principal-alice"
    email: "alice.henderson@apexfintech.com"
    authProvider: "okta_oidc"
    role: "Operations & Compliance Lead"
  agent:
    id: "agent-apex-ops"
    model: "gemini-2.5-pro"
  session:
    ttlSeconds: 3600
    audience: "mcp-data-server"
  bounds:
    allowedScopes:
      - "lookup_customer_balance"
      - "get_transaction_history"
      - "audit_read"
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
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-white tracking-tight">Onboarding & Architecture Guide</h1>
            <span className="text-[10px] font-mono uppercase bg-sky-950 text-sky-300 border border-sky-800 px-2 py-0.5 rounded-full font-semibold">
              PRODUCTION INTEGRATION
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            How enterprise teams connect AI agents and applications to Runtime Trust Layer. Covers multi-app onboarding, graph algorithms, ingestion pipelines, and pre-execution latency optimizations.
          </p>
        </div>

        <button
          onClick={() => setShowRegisterModal(true)}
          className="px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs flex items-center space-x-2 cursor-pointer shadow-lg transition self-start md:self-auto shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Application</span>
        </button>
      </div>

      {/* Section 1: Multi-Application Registry */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Building className="w-4 h-4 text-sky-400" />
            <span>Connected Applications & Enterprise Tenants</span>
          </span>
          <span className="text-xs text-slate-400">Select an application to view its security topology</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {applications.map((app) => (
            <div
              key={app.id}
              onClick={() => setSelectedApp(app.id)}
              className={`p-4 rounded-xl border transition cursor-pointer relative ${
                selectedApp === app.id
                  ? 'bg-[#101b33] border-sky-500/80 shadow-md ring-1 ring-sky-500/40'
                  : 'bg-[#0b1120] border-[#1e293b] hover:border-[#2d3f66] hover:bg-[#0e162a]'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-sm text-white">{app.name}</span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                    app.status.includes('ACTIVE')
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}
                >
                  {app.status}
                </span>
              </div>
              <div className="space-y-1 text-xs text-slate-400">
                <div className="flex items-center justify-between">
                  <span>Framework:</span>
                  <span className="text-slate-200 font-mono text-[11px]">{app.framework}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Cluster:</span>
                  <span className="text-sky-300 font-mono text-[11px]">{app.environment}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Guarded Tools:</span>
                  <span className="text-emerald-400 font-mono font-bold">{app.toolsGuarded} MCP Tools</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Step-by-Step Onboarding Walkthrough */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Step 1 & 2: Integration & Code Snippets (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Step 1: Manifest */}
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 rounded-full bg-sky-500/20 text-sky-400 font-bold text-xs flex items-center justify-center border border-sky-500/40">
                  1
                </span>
                <span className="font-bold text-sm text-white">Define Identity & Delegation Bounds (YAML / JSON)</span>
              </div>
              <button
                onClick={() => copyToClipboard(yamlManifest, 'manifest')}
                className="px-2.5 py-1 rounded bg-[#16223b] hover:bg-[#1e2f52] border border-[#233557] text-[11px] text-slate-300 flex items-center space-x-1 cursor-pointer transition"
              >
                {copiedKey === 'manifest' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'manifest' ? 'Copied' : 'Copy Spec'}</span>
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Every agent session requires an explicit delegation grant bound to a verified human principal SSO token. Tools outside allowed scopes are rejected deterministically before running.
            </p>
            <div className="bg-black/60 rounded-lg p-3.5 border border-white/5 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-56">
              <pre>{yamlManifest}</pre>
            </div>
          </div>

          {/* Step 2: SDK / Gateway Hookup */}
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 rounded-full bg-sky-500/20 text-sky-400 font-bold text-xs flex items-center justify-center border border-sky-500/40">
                  2
                </span>
                <span className="font-bold text-sm text-white">Connect Agent Tool Gateway (1-Line Wrapper)</span>
              </div>
              <button
                onClick={() => copyToClipboard(codeSnippets[selectedSdkTab], 'code')}
                className="px-2.5 py-1 rounded bg-[#16223b] hover:bg-[#1e2f52] border border-[#233557] text-[11px] text-slate-300 flex items-center space-x-1 cursor-pointer transition"
              >
                {copiedKey === 'code' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'code' ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>

            {/* SDK Language Selector */}
            <div className="flex space-x-2 border-b border-[#18233c] pb-2">
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
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="bg-black/60 rounded-lg p-3.5 border border-white/5 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-72">
              <pre>{codeSnippets[selectedSdkTab]}</pre>
            </div>
          </div>
        </div>

        {/* Step 3 & 4: Ingestion & Graph Architecture (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Step 3: How Workloads & Tools Are Populated */}
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-full bg-sky-500/20 text-sky-400 font-bold text-xs flex items-center justify-center border border-sky-500/40">
                3
              </span>
              <span className="font-bold text-sm text-white">How Workloads & Tools Are Populated</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-sky-400">
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>Pipeline A: Static Manifest Ingestion (GitOps)</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Scans OpenAPI schemas, MCP manifests, Helm values, and Kubernetes ServiceAccount RBAC configs on git push to build the static authorized permission graph.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-purple-400">
                  <Key className="w-3.5 h-3.5" />
                  <span>Pipeline B: SSO & Identity Token Mapping</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Synchronizes Okta OIDC and AWS IAM tokens into <code className="text-slate-200">Principal</code> and <code className="text-slate-200">AgentSession</code> nodes with cryptographic expiry and audience bindings.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-emerald-400">
                  <Cpu className="w-3.5 h-3.5" />
                  <span>Pipeline C: Dynamic eBPF & Gateway Discovery</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Linux eBPF probes (<code className="text-slate-200">sys_enter_connect</code>) and the MCP Gateway dynamically capture live socket calls, continually adding verified <code className="text-slate-200">OBSERVED_ACCESS</code> edges.
                </p>
              </div>
            </div>
          </div>

          {/* Step 4: Graph Engine Algorithms & Optimizations */}
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded-full bg-sky-500/20 text-sky-400 font-bold text-xs flex items-center justify-center border border-sky-500/40">
                4
              </span>
              <span className="font-bold text-sm text-white">Graph Engine, Algorithm & Latency</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1.5">
                <span className="font-bold text-amber-400 flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  <span>Why Graph vs Relational Database?</span>
                </span>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Delegation chains, tool invocations, and cloud reachability form an arbitrary directed mesh. Relational SQL queries require recursive CTE joins that take hundreds of milliseconds; FalkorDB native graph pointers traverse multi-hop paths in single-digit milliseconds.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1.5">
                <span className="font-bold text-sky-400 flex items-center space-x-1.5">
                  <Gauge className="w-3.5 h-3.5" />
                  <span>The Traversal Algorithm: Bounded BFS</span>
                </span>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Uses bounded Breadth-First Search (BFS) in Cypher:
                  <code className="block mt-1 p-1 bg-black/40 rounded text-slate-300 font-mono text-[10px]">
                    MATCH (p)-[:OWNS]-&gt;(s)-[:DELEGATES_TO*1..3]-&gt;(a)-[:CAN_INVOKE]-&gt;(t)
                  </code>
                  Bounds maximum depth to <code className="text-slate-200">k=4</code> to guarantee polynomial <code className="text-slate-200">O(V + E)</code> execution and avoid graph path explosion.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#0e162a] border border-[#1c2944] space-y-1.5">
                <span className="font-bold text-emerald-400 flex items-center space-x-1.5">
                  <Zap className="w-3.5 h-3.5" />
                  <span>Sub-15ms Latency Optimizations</span>
                </span>
                <ul className="text-slate-400 text-[11px] space-y-1 list-disc pl-4">
                  <li>In-memory Redis engine backing FalkorDB graph nodes.</li>
                  <li>Primary key hash indexes on <code className="text-slate-300">AgentSession.id</code> and <code className="text-slate-300">Tool.name</code>.</li>
                  <li>Compiled Cypher AST query plan caching.</li>
                  <li><strong className="text-white">Deterministic Fail-Closed:</strong> Unreachable database defaults to HTTP 503 DENY immediately.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Register New Application Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-[#203154] rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Register New Enterprise Application</h3>
            <p className="text-xs text-slate-400">
              Provide application details to provision an isolated FalkorDB graph namespace and mint an initial trust gateway token.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Application Name</label>
                <input
                  type="text"
                  value={newAppName}
                  onChange={(e) => setNewAppName(e.target.value)}
                  placeholder="e.g. Apex Settlement Engine"
                  className="w-full bg-[#080d1a] border border-[#1e2a44] rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Agent Framework</label>
                <select
                  value={newAppFramework}
                  onChange={(e) => setNewAppFramework(e.target.value)}
                  className="w-full bg-[#080d1a] border border-[#1e2a44] rounded-lg px-3 py-2 text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="LangChain">LangChain / LangGraph</option>
                  <option value="Claude-MCP">Anthropic Claude Desktop (MCP)</option>
                  <option value="CrewAI">CrewAI / AutoGen Multi-Agent</option>
                  <option value="OpenAI-SDK">Direct OpenAI Function Calling</option>
                  <option value="Custom">Custom Proprietary LLM Engine</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Deployment Cluster</label>
                <input
                  type="text"
                  placeholder="e.g. aws-eks-production-us-east-1"
                  defaultValue="aws-eks-production-us-east-1"
                  className="w-full bg-[#080d1a] border border-[#1e2a44] rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 font-mono text-[11px]"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-[#1a253d]">
              <button
                onClick={() => setShowRegisterModal(false)}
                className="px-3.5 py-2 rounded-lg bg-[#141d30] text-slate-300 text-xs hover:text-white cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowRegisterModal(false);
                  alert(`Application '${newAppName || 'New App'}' registered! Ingestion token provisioned.`);
                }}
                className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs cursor-pointer shadow"
              >
                Create App & Provision Token
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
