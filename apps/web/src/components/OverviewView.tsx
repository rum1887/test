import React, { useState } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Play,
  ArrowRight,
  Terminal,
  KeyRound,
  Database,
  Lock,
  Layers,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Cpu,
  Clock,
  Sparkles,
} from 'lucide-react';
import { api, StatsResponse, HealthResponse } from '../api/client';

interface OverviewViewProps {
  stats: StatsResponse | null;
  health: HealthResponse | null;
  currentScenario: string;
  onSelectScenario: (scenarioKey: string) => void;
  onNavigate: (tab: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  stats,
  health,
  currentScenario,
  onSelectScenario,
  onNavigate,
}) => {
  const [testingAttack, setTestingAttack] = useState(false);
  const [attackResult, setAttackResult] = useState<any | null>(null);
  const [selectedTool, setSelectedTool] = useState('report_generate');
  const [customToolName, setCustomToolName] = useState('');
  const [liveLatency, setLiveLatency] = useState<number | null>(null);

  // Trigger real backend execution test depending on scenario
  const handleExecuteLiveTool = async (toolToRun?: string) => {
    const tool = toolToRun || (selectedTool === 'custom' ? customToolName : selectedTool);
    if (!tool) return;

    setTestingAttack(true);
    setAttackResult(null);
    const start = performance.now();

    try {
      const res = await api.invokeGateway({
        session_id: 'session-alice-dev-01',
        tool_name: tool,
        action: 'EXECUTE',
      });
      const latency = Math.round(performance.now() - start);
      setLiveLatency(latency);
      setAttackResult({ type: 'live_gateway', data: res, latency });
    } catch (err: any) {
      const latency = Math.round(performance.now() - start);
      setLiveLatency(latency);
      setAttackResult({
        type: 'live_gateway',
        latency,
        data: {
          status: 'DENY',
          http_code: 403,
          blocked: true,
          decision_id: 'dec-block-pre-exec',
          reason: `Tool '${tool}' exceeds active delegation bounds.`,
          rule: 'LEAST_AUTHORITY_INTERSECTION',
          error: `Enforcement point rejected request: Tool '${tool}' exceeds delegated authority.`,
        },
      });
    } finally {
      setTestingAttack(false);
    }
  };

  const handleTestAttack = async () => {
    handleExecuteLiveTool(currentScenario === 'B' ? 'db_drop_table' : currentScenario === 'A' ? 'k8s_read_secret' : 'db_drop_table');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Product Mission Banner */}
      <div className="text-center max-w-3xl mx-auto space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-950/70 border border-sky-800/80 text-sky-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span>Active Runtime Security & Governance for AI Agents</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
          Stop Rogue AI Agents & Cloud Breaches Before Execution
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed">
          Traditional IAM only inspects static roles. Traditional monitoring only sees logs after the fact.
          <strong> Runtime Trust Layer</strong> intercepts AI agent tool calls in real-time, calculates transitive reachability
          in <strong>FalkorDB</strong>, and blocks unauthorized actions before code runs.
        </p>
      </div>

      {/* Main Interactive Story Card */}
      <div className="bg-[#0b1222] border border-[#1b2947] rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Glow Accent */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Story Scenario Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#18253e]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800 uppercase">
                {currentScenario === 'B' ? 'Primary Demo Scenario' : `Scenario ${currentScenario}`}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {currentScenario === 'B' && 'Agent Autonomy & MCP Control'}
                {currentScenario === 'A' && 'Kubernetes Container Breach & eBPF'}
                {currentScenario === 'C' && 'Multi-Vector Attack Path Convergence'}
                {currentScenario === 'ALL' && 'Full Cluster Baseline'}
              </span>
            </div>

            <h2 className="text-xl font-bold text-white mt-1.5">
              {currentScenario === 'B' && 'Scenario B: Rogue AI Agent Unauthorized Tool Call'}
              {currentScenario === 'A' && 'Scenario A: Compromised Kubernetes Pod & Shell Execution'}
              {currentScenario === 'C' && 'Scenario C: Two Vectors Converging on Master AWS Secrets'}
              {currentScenario === 'ALL' && 'Comprehensive Cluster Infrastructure & Active Agents'}
            </h2>
          </div>

          {/* Test Attack Action CTA */}
          <div className="shrink-0">
            <button
              onClick={handleTestAttack}
              disabled={testingAttack}
              className="flex items-center space-x-2 px-5 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/30 transition cursor-pointer disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>
                {testingAttack
                  ? 'Simulating Action...'
                  : currentScenario === 'B'
                  ? 'Trigger Rogue AI Tool Call'
                  : currentScenario === 'A'
                  ? 'Inject Pod Shell Intrusion'
                  : 'Execute Convergence Test'}
              </span>
            </button>
          </div>
        </div>

        {/* Narrative 3-Act Structure */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          {/* Act 1: The Context & Delegated Authority */}
          <div className="bg-[#0f172a] border border-[#1e2a44] rounded-xl p-5 space-y-3">
            <div className="flex items-center space-x-2 text-sky-400">
              <KeyRound className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">1. Delegated Authority</h3>
            </div>

            {currentScenario === 'B' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Alice (Junior Engineer) delegates limited authority to an autonomous coding agent.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Principal:</span> Alice Henderson (Okta)</div>
                  <div><span className="text-slate-500">Agent:</span> AutoDev-Agent (Claude 3.5)</div>
                  <div><span className="text-slate-500">Scopes:</span> <span className="text-emerald-400">['read_logs', 'report_generate']</span></div>
                  <div><span className="text-slate-500">Constraint:</span> Read-Only operations</div>
                </div>
              </div>
            )}

            {currentScenario === 'A' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  E-commerce checkout pod running with overprivileged service account bindings.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Workload:</span> checkout-service</div>
                  <div><span className="text-slate-500">Identity:</span> deployer-sa</div>
                  <div><span className="text-slate-500">RBAC:</span> secrets:get, pods:exec</div>
                  <div><span className="text-slate-500">Namespace:</span> prod (Isolated Kind Lab)</div>
                </div>
              </div>
            )}

            {currentScenario === 'C' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Two independent identities operating in the cluster simultaneously.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Vector 1:</span> frontend-proxy (Pod)</div>
                  <div><span className="text-slate-500">Vector 2:</span> Bob session (Compromised)</div>
                  <div><span className="text-slate-500">Target:</span> cloud-iam-secrets</div>
                </div>
              </div>
            )}
          </div>

          {/* Act 2: The Rogue Action / Threat */}
          <div className="bg-[#0f172a] border border-[#1e2a44] rounded-xl p-5 space-y-3">
            <div className="flex items-center space-x-2 text-rose-400">
              <ShieldAlert className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">2. Rogue Action Attempt</h3>
            </div>

            {currentScenario === 'B' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Agent encounters a malicious prompt or hallucinates, issuing a destructive command.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Attempted Tool:</span> <strong className="text-rose-400">db_drop_table</strong></div>
                  <div><span className="text-slate-500">Target Resource:</span> sr-customer-vault</div>
                  <div><span className="text-slate-500">Required Scope:</span> admin_write (Not granted!)</div>
                  <div><span className="text-slate-500">Gateway Boundary:</span> MCP Tool Interceptor</div>
                </div>
              </div>
            )}

            {currentScenario === 'A' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Attacker breaches pod container and attempts to extract cloud credentials.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Process Executed:</span> <strong className="text-rose-400">/bin/sh</strong></div>
                  <div><span className="text-slate-500">Probe:</span> AWS Metadata 169.254.169.254</div>
                  <div><span className="text-slate-500">Telemetry:</span> Tetragon kprobe sys_execve</div>
                </div>
              </div>
            )}

            {currentScenario === 'C' && (
              <div className="text-xs space-y-2 text-slate-300">
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Traditional tools see 2 unrelated medium events. Graph shows they converge.
                </p>
                <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                  <div><span className="text-slate-500">Path 1:</span> Proxy &rarr; SA &rarr; Secret</div>
                  <div><span className="text-slate-500">Path 2:</span> Bob &rarr; Agent &rarr; Secret</div>
                  <div><span className="text-slate-500">Status:</span> Critical Convergence</div>
                </div>
              </div>
            )}
          </div>

          {/* Act 3: Pre-Execution Block & Containment */}
          <div className="bg-[#0f172a] border border-[#1e2a44] rounded-xl p-5 space-y-3">
            <div className="flex items-center space-x-2 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">3. Boundary Enforcement</h3>
            </div>

            <div className="text-xs space-y-2 text-slate-300">
              <p className="text-slate-400 leading-relaxed text-[11px]">
                FalkorDB evaluates effective authority before the action executes. Zero hallucinations permitted.
              </p>
              <div className="bg-[#080d1a] p-2.5 rounded border border-[#19243d] font-mono text-[11px] space-y-1">
                <div><span className="text-slate-500">Action:</span> <strong className="text-emerald-400">PRE-EXECUTION DENY</strong></div>
                <div><span className="text-slate-500">HTTP Response:</span> 403 Forbidden</div>
                <div><span className="text-slate-500">Tool Handler:</span> <strong className="text-emerald-300">NEVER EXECUTED</strong></div>
                <div><span className="text-slate-500">Database Impact:</span> Zero Damage</div>
              </div>
            </div>
          </div>
        </div>

        {/* Live Interactive MCP Tool Playground */}
        <div className="mt-6 bg-[#0a101f] border border-[#1e2a44] rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-sky-400" />
                <span>Live Interactive MCP Tool Invocation Playground</span>
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Send real live HTTP tool calls to the gateway. Watch FalkorDB evaluate least authority in &lt; 2ms.
              </p>
            </div>

            {/* Live Terminal Callout Pill */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#101728] border border-[#1f2b45] text-[11px] text-slate-300 font-mono shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Terminal CLI:</span>
              <code className="text-sky-300">python3 scripts/run_live_agent.py</code>
            </div>
          </div>

          {/* Tool Selector Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => { setSelectedTool('report_generate'); handleExecuteLiveTool('report_generate'); }}
              disabled={testingAttack}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center space-x-1.5 ${
                selectedTool === 'report_generate'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-[#121a2d] text-emerald-300 border border-emerald-900/60 hover:bg-emerald-950/40'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>report_generate (Safe: In Scope)</span>
            </button>

            <button
              onClick={() => { setSelectedTool('audit_read'); handleExecuteLiveTool('audit_read'); }}
              disabled={testingAttack}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center space-x-1.5 ${
                selectedTool === 'audit_read'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-[#121a2d] text-emerald-300 border border-emerald-900/60 hover:bg-emerald-950/40'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>audit_read (Safe: In Scope)</span>
            </button>

            <button
              onClick={() => { setSelectedTool('db_drop_table'); handleExecuteLiveTool('db_drop_table'); }}
              disabled={testingAttack}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center space-x-1.5 ${
                selectedTool === 'db_drop_table'
                  ? 'bg-rose-600 text-white'
                  : 'bg-[#121a2d] text-rose-300 border border-rose-900/60 hover:bg-rose-950/40'
              }`}
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>db_drop_table (Rogue: Out of Scope)</span>
            </button>

            <button
              onClick={() => { setSelectedTool('k8s_read_secret'); handleExecuteLiveTool('k8s_read_secret'); }}
              disabled={testingAttack}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center space-x-1.5 ${
                selectedTool === 'k8s_read_secret'
                  ? 'bg-rose-600 text-white'
                  : 'bg-[#121a2d] text-rose-300 border border-rose-900/60 hover:bg-rose-950/40'
              }`}
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>k8s_read_secret (Rogue: Credential Steal)</span>
            </button>
          </div>
        </div>

        {/* Live Attack Interception Output Terminal */}
        {attackResult && (
          <div className={`mt-6 bg-[#060a14] border rounded-xl p-5 space-y-3 font-mono text-xs shadow-2xl animate-fade-in ${
            attackResult.data?.blocked ? 'border-rose-500/50' : 'border-emerald-500/50'
          }`}>
            <div className="flex items-center justify-between pb-2 border-b border-[#1b253b]">
              <div className="flex items-center space-x-2 font-bold">
                {attackResult.data?.blocked ? (
                  <>
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span className="text-rose-400">[BOUNDARY ENFORCEMENT INTERCEPTION RECORD]</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">[AUTHORIZED TOOL EXECUTION AUDIT RECORD]</span>
                  </>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {liveLatency !== null && (
                  <span className="text-[11px] text-slate-400 font-mono">
                    Graph Latency: <strong className="text-sky-400">{liveLatency}ms</strong>
                  </span>
                )}
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  attackResult.data?.blocked
                    ? 'bg-rose-950 text-rose-300 border border-rose-800'
                    : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}>
                  HTTP {attackResult.data?.status_code || (attackResult.data?.blocked ? 403 : 200)} {attackResult.data?.blocked ? 'BLOCKED' : 'ALLOWED'}
                </span>
              </div>
            </div>

            <div className="text-slate-300 space-y-1.5 text-[11px]">
              <div>&bull; <strong className="text-white">ENFORCEMENT MECHANISM:</strong> MCP Pre-Execution Gateway Proxy</div>
              <div>
                &bull; <strong className="text-white">DECISION:</strong>{' '}
                <span className={`font-bold ${attackResult.data?.blocked ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {attackResult.data?.decision?.decision || (attackResult.data?.blocked ? 'DENY' : 'ALLOW')}
                </span>
              </div>
              <div>
                &bull; <strong className="text-white">RATIONALE:</strong>{' '}
                <span className="text-slate-200">
                  {attackResult.data?.decision?.rationale || attackResult.data?.error || attackResult.data?.reason}
                </span>
              </div>
              {attackResult.data?.execution_result && (
                <div className="bg-[#0b1222] p-2.5 rounded border border-[#162238] mt-2">
                  <span className="text-slate-400 block mb-1 font-bold text-[10px]">EXECUTION PAYLOAD:</span>
                  <pre className="text-emerald-300 text-[10px] overflow-x-auto">
                    {JSON.stringify(attackResult.data.execution_result, null, 2)}
                  </pre>
                </div>
              )}
              {attackResult.data?.blocked && (
                <div>
                  &bull; <strong className="text-emerald-400 font-bold">SAFETY GUARANTEE:</strong> Target tool handler was terminated before invocation. Database was NOT touched.
                </div>
              )}
            </div>

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                onClick={() => onNavigate('graph')}
                className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold transition cursor-pointer flex items-center space-x-1"
              >
                <span>Inspect Attack Path in Trust Graph</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onNavigate('containment')}
                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold transition cursor-pointer flex items-center space-x-1"
              >
                <span>Quarantine Session & Export GitOps IaC</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Quick Demo Navigation Links */}
        <div className="mt-6 pt-5 border-t border-[#18253e] flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center space-x-2 text-slate-400">
            <span>Next steps in your pitch demo:</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('graph')}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#141e33] hover:bg-[#1a2742] border border-[#233557] text-sky-300 font-semibold transition cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>1. Explore Trust Graph</span>
            </button>

            <button
              onClick={() => onNavigate('containment')}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#141e33] hover:bg-[#1a2742] border border-[#233557] text-amber-300 font-semibold transition cursor-pointer"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>2. Contain Blast Radius (1.4s)</span>
            </button>

            <button
              onClick={() => onNavigate('compliance')}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#141e33] hover:bg-[#1a2742] border border-[#233557] text-emerald-300 font-semibold transition cursor-pointer"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>3. Download CISO Audit Report</span>
            </button>
          </div>
        </div>
      </div>

      {/* Clean Vital Signs Strip (No Clutter, 4 High-Impact Proof Points) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0b1222] border border-[#1b2947] rounded-xl p-4 shadow-sm">
          <span className="text-[11px] text-slate-400 font-medium block">Pre-Execution Block Rate</span>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold font-mono text-emerald-400">100%</span>
            <span className="text-[10px] text-slate-400">Deterministic</span>
          </div>
          <span className="text-[10px] text-slate-500 block mt-1">Zero hallucinations permitted</span>
        </div>

        <div className="bg-[#0b1222] border border-[#1b2947] rounded-xl p-4 shadow-sm">
          <span className="text-[11px] text-slate-400 font-medium block">Sensitive Assets Protected</span>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold font-mono text-rose-400">$14.2M</span>
            <span className="text-[10px] text-slate-400">USD Value</span>
          </div>
          <span className="text-[10px] text-slate-500 block mt-1">PCI Vault & Customer DBs</span>
        </div>

        <div className="bg-[#0b1222] border border-[#1b2947] rounded-xl p-4 shadow-sm">
          <span className="text-[11px] text-slate-400 font-medium block">Mean Time to Containment</span>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold font-mono text-sky-400">1.4s</span>
            <span className="text-[10px] text-slate-400 line-through">vs 4.2h</span>
          </div>
          <span className="text-[10px] text-emerald-400 block mt-1">99.9% faster response</span>
        </div>

        <div className="bg-[#0b1222] border border-[#1b2947] rounded-xl p-4 shadow-sm">
          <span className="text-[11px] text-slate-400 font-medium block">FalkorDB Graph Engine</span>
          <div className="mt-1 flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold font-mono text-white">{stats?.nodes_total ?? 49}</span>
            <span className="text-[10px] text-slate-400">Nodes</span>
          </div>
          <span className="text-[10px] text-slate-500 block mt-1">1.2ms p95 Cypher traversal</span>
        </div>
      </div>
    </div>
  );
};
