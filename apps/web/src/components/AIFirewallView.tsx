import React, { useState } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  ArrowRight,
  Database,
  Lock,
  Layers,
  Cpu,
  Hash,
  Terminal,
  Activity,
  User,
  Bot,
  Wrench,
  ToggleLeft,
  ToggleRight,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';

interface AIFirewallViewProps {
  initialTool?: string;
  initialCaller?: string;
}

export const AIFirewallView: React.FC<AIFirewallViewProps> = ({
  initialTool = 'lookup_customer_balance',
  initialCaller = 'principal-alice',
}) => {
  const [caller, setCaller] = useState<string>(initialCaller);
  const [agentId, setAgentId] = useState<string>('agent-autodev');
  const [selectedTool, setSelectedTool] = useState<string>(initialTool);
  const [enforceMode, setEnforceMode] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);

  const presets = [
    {
      id: 'legit-read',
      label: 'Legitimate Customer Balance Lookup',
      caller: 'principal-alice',
      agent: 'agent-autodev',
      tool: 'lookup_customer_balance',
      description: 'Authorized read within Alice’s delegated Support & Compliance scopes.',
      expected: 'ALLOW',
    },
    {
      id: 'priv-esc',
      label: 'Privilege Escalation Attack (Vault Export)',
      caller: 'principal-alice',
      agent: 'agent-autodev',
      tool: 'export_customer_vault',
      description: 'Unauthorized attempt to extract KMS keys from customer vault. Destructive & un-scoped.',
      expected: 'DENY',
    },
    {
      id: 'treasury-payout',
      label: 'Treasury Settlement Payout ($75k)',
      caller: 'principal-marcus',
      agent: 'agent-nexus-settlement',
      tool: 'process_settlement_payout',
      description: 'Authorized disbursement executed by Treasury Director Marcus Vance.',
      expected: 'ALLOW',
    },
    {
      id: 'destructive-drop',
      label: 'Destructive Table Drop (SQL Injection)',
      caller: 'principal-bob',
      agent: 'agent-autodev',
      tool: 'db_drop_table',
      description: 'Catastrophic operation blocked at MCP pre-execution boundary.',
      expected: 'DENY',
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setCaller(p.caller);
    setAgentId(p.agent);
    setSelectedTool(p.tool);
    setResult(null);
  };

  const handleIntercept = async () => {
    setEvaluating(true);
    try {
      const res = await api.firewallIntercept({
        caller_identity: caller,
        agent_id: agentId,
        tool_name: selectedTool,
        parameters: { account_id: 'acc-104' },
        enforce_mode: enforceMode,
      });
      setResult(res);
    } catch (err: any) {
      console.error('Firewall intercept error:', err);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center space-x-2.5 mb-2">
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-[#ede7da] text-stone-800 border border-[#ded7c8]">
                <Shield className="w-3 h-3 text-stone-900" />
                <span>AI FIREWALL & TRUST LAYER</span>
              </span>
              <span className="text-stone-400">&bull;</span>
              <span className="text-xs text-stone-500 font-mono">Multi-Layer Interceptor</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900">
              Agentic Runtime Interception & Graph Reasoning
            </h1>
            <p className="mt-1.5 text-sm text-stone-600 max-w-2xl">
              Intercepts incoming agent tool requests across 4 defensive planes, explores the latest
              FalkorDB storage graph in real-time, validates delegation scopes, and implements deterministic enforcement.
            </p>
          </div>

          {/* Enforce Mode Toggle */}
          <div className="flex items-center space-x-3 bg-white border border-[#ded7c8] rounded-xl px-4 py-2.5 shadow-2xs">
            <div className="text-right">
              <div className="text-xs font-semibold text-stone-900">
                {enforceMode ? 'ENFORCE MODE' : 'AUDIT / BYPASS'}
              </div>
              <div className="text-[10px] text-stone-500">
                {enforceMode ? 'Blocks unauthorized requests' : 'Permits execution, logs violation'}
              </div>
            </div>
            <button
              onClick={() => setEnforceMode(!enforceMode)}
              className="text-stone-800 hover:text-stone-900 transition cursor-pointer"
            >
              {enforceMode ? (
                <ToggleRight className="w-8 h-8 text-emerald-600" />
              ) : (
                <ToggleLeft className="w-8 h-8 text-stone-400" />
              )}
            </button>
          </div>
        </div>

        {/* 4 Defense Layers Pipeline Architecture */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-8 pt-6 border-t border-[#ded7c8]">
          <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold text-stone-900">
              <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center text-[10px] font-mono">
                L1
              </span>
              <span>Ingress Identity</span>
            </div>
            <p className="text-[11px] text-stone-500 leading-snug">
              Verifies caller principal exists in graph, has active status, and is not locked or quarantined.
            </p>
          </div>

          <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold text-stone-900">
              <span className="w-5 h-5 rounded-full bg-violet-100 text-violet-800 flex items-center justify-center text-[10px] font-mono">
                L2
              </span>
              <span>Delegation & RBAC</span>
            </div>
            <p className="text-[11px] text-stone-500 leading-snug">
              Validates that the active delegation grant explicitly covers the requested tool operation.
            </p>
          </div>

          <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold text-stone-900">
              <span className="w-5 h-5 rounded-full bg-rose-100 text-rose-800 flex items-center justify-center text-[10px] font-mono">
                L3
              </span>
              <span>MCP Tool Catalog</span>
            </div>
            <p className="text-[11px] text-stone-500 leading-snug">
              Pre-execution guard checking tool risk level, destructive flags, and registered parameters.
            </p>
          </div>

          <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold text-stone-900">
              <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center text-[10px] font-mono">
                L4
              </span>
              <span>Data Egress Blast Radius</span>
            </div>
            <p className="text-[11px] text-stone-500 leading-snug">
              Cross-checks blast radius against Crown Jewels (Vault secrets, SQLite database, KMS keys).
            </p>
          </div>
        </div>
      </div>

      {/* Preset Scenarios */}
      <div className="space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
          Quick Evaluation Scenarios:
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {presets.map((p) => (
            <div
              key={p.id}
              onClick={() => handleApplyPreset(p)}
              className="bg-[#faf7f0] border border-[#ded7c8] hover:border-stone-400 rounded-xl p-3.5 transition cursor-pointer space-y-2 hover:bg-white"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-stone-900">{p.label}</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                  p.expected === 'ALLOW' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                }`}>
                  {p.expected}
                </span>
              </div>
              <p className="text-[11px] text-stone-500 leading-tight">{p.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Interception Sandbox */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Interception Controls */}
        <div className="lg:col-span-5 bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center space-x-2 pb-3 border-b border-[#ded7c8]">
            <Terminal className="w-4 h-4 text-stone-800" />
            <h2 className="text-sm font-semibold text-stone-900">
              Live Interceptor Request Builder
            </h2>
          </div>

          <div className="space-y-4 text-xs">
            {/* Caller Identity */}
            <div>
              <label className="block text-stone-700 font-medium mb-1">
                Caller Principal (Layer 1)
              </label>
              <select
                value={caller}
                onChange={(e) => setCaller(e.target.value)}
                className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 font-mono focus:outline-hidden focus:border-stone-800"
              >
                <option value="principal-alice">principal-alice (Alice Henderson — Operations & Compliance)</option>
                <option value="principal-marcus">principal-marcus (Marcus Vance — Treasury Operations)</option>
                <option value="principal-bob">principal-bob (Bob Martinez — DevOps)</option>
                <option value="principal-untrusted-hacker">principal-untrusted-hacker (External Unauthenticated)</option>
              </select>
            </div>

            {/* Target Agent */}
            <div>
              <label className="block text-stone-700 font-medium mb-1">
                Autonomous Agent (Layer 2)
              </label>
              <select
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 font-mono focus:outline-hidden focus:border-stone-800"
              >
                <option value="agent-autodev">agent-autodev (Orbit Support Agent :3001)</option>
                <option value="agent-nexus-settlement">agent-nexus-settlement (Nexus FinOps Agent :3002)</option>
              </select>
            </div>

            {/* Requested Tool */}
            <div>
              <label className="block text-stone-700 font-medium mb-1">
                Requested MCP Tool (Layer 3)
              </label>
              <select
                value={selectedTool}
                onChange={(e) => setSelectedTool(e.target.value)}
                className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 font-mono focus:outline-hidden focus:border-stone-800"
              >
                <option value="lookup_customer_balance">lookup_customer_balance (READ_ONLY / LOW)</option>
                <option value="get_transaction_history">get_transaction_history (READ_ONLY / LOW)</option>
                <option value="audit_read">audit_read (READ_ONLY / LOW)</option>
                <option value="process_settlement_payout">process_settlement_payout (MUTATION / HIGH)</option>
                <option value="verify_treasury_ledger">verify_treasury_ledger (READ_ONLY / LOW)</option>
                <option value="export_customer_vault">export_customer_vault (EXFILTRATION / CRITICAL)</option>
                <option value="db_drop_table">db_drop_table (DESTRUCTIVE / CRITICAL)</option>
                <option value="rotate_kms_key">rotate_kms_key (Newly Registered Tool)</option>
              </select>
            </div>

            {/* Payload preview */}
            <div>
              <label className="block text-stone-700 font-medium mb-1">
                Execution Parameters
              </label>
              <div className="bg-white border border-[#ded7c8] rounded-xl p-3 font-mono text-[11px] text-stone-700">
                {'{ "account_id": "acc-104", "currency": "USD" }'}
              </div>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleIntercept}
              disabled={evaluating}
              className="w-full mt-2 inline-flex items-center justify-center space-x-2 py-2.5 rounded-xl bg-stone-900 hover:bg-stone-800 text-stone-50 font-semibold transition cursor-pointer shadow-sm disabled:opacity-60"
            >
              <Play className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
              <span>{evaluating ? 'Evaluating Graph in Real-Time...' : 'Intercept & Validate Event'}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Multi-Layer Evaluation & Enforced Result */}
        <div className="lg:col-span-7 space-y-6">
          {result ? (
            <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-6 animate-in fade-in">
              {/* Decision Header */}
              <div className="flex items-start justify-between pb-4 border-b border-[#ded7c8]">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                      result.decision === 'ALLOW'
                        ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                        : 'bg-rose-100 text-rose-900 border border-rose-300'
                    }`}>
                      DECISION: {result.decision} ({result.status_code})
                    </span>
                    <span className="text-[11px] font-mono text-stone-500">
                      Trace: {result.trace_id}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-stone-700 font-medium leading-relaxed">
                    {result.rationale}
                  </p>
                </div>

                <div className="text-right shrink-0">
                  {result.decision === 'ALLOW' ? (
                    <div className="w-10 h-10 rounded-full bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-rose-100 border border-rose-300 flex items-center justify-center text-rose-800">
                      <XCircle className="w-6 h-6" />
                    </div>
                  )}
                </div>
              </div>

              {/* Layer-by-Layer Interception Breakdown */}
              <div className="space-y-3">
                <div className="text-xs font-semibold text-stone-800 uppercase tracking-wider">
                  Multi-Layer Defensive Evaluation:
                </div>
                <div className="space-y-2">
                  {result.layers_evaluated?.map((l: any, idx: number) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border flex items-start justify-between gap-3 text-xs ${
                        l.passed
                          ? 'bg-white border-[#ded7c8]'
                          : 'bg-rose-50/50 border-rose-200'
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-stone-900 flex items-center space-x-1.5">
                          <span>{l.layer}</span>
                        </div>
                        <div className="text-[11px] text-stone-600">{l.checked}</div>
                        <div className="text-[10px] font-mono text-stone-500 mt-1">
                          Evidence: {l.evidence}
                        </div>
                      </div>

                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${
                        l.passed
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}>
                        {l.passed ? 'PASSED' : 'BLOCKED'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Real-Time Graph Traversal Path */}
              {result.graph_path_explored && (
                <div className="space-y-3 pt-2">
                  <div className="text-xs font-semibold text-stone-800 uppercase tracking-wider">
                    FalkorDB Multi-Hop Path Explored:
                  </div>
                  <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 overflow-x-auto">
                    <div className="flex items-center space-x-2 text-xs font-mono min-w-max">
                      {result.graph_path_explored.map((item: any, idx: number) => {
                        if (item.node) {
                          return (
                            <span
                              key={idx}
                              className={`px-2.5 py-1 rounded-lg border font-semibold ${
                                item.label === 'Principal'
                                  ? 'bg-blue-50 border-blue-200 text-blue-900'
                                  : item.label === 'AgentSession'
                                  ? 'bg-stone-50 border-stone-200 text-stone-800'
                                  : item.label === 'Agent'
                                  ? 'bg-amber-50 border-amber-200 text-amber-900'
                                  : item.label === 'Tool'
                                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                                  : 'bg-emerald-50 border-emerald-200 text-emerald-900'
                              }`}
                            >
                              ({item.label}: {item.name || item.node})
                            </span>
                          );
                        } else {
                          return (
                            <span key={idx} className="text-stone-400 font-sans text-xs">
                              --[{item.edge}]&rarr;
                            </span>
                          );
                        }
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Enforced Result Payload */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs font-semibold text-stone-800 uppercase tracking-wider">
                  <span>Enforced Execution Output:</span>
                  {result.evidence_hash && (
                    <span className="font-mono text-[10px] text-stone-500 font-normal">
                      SHA256: {result.evidence_hash.slice(0, 16)}...
                    </span>
                  )}
                </div>

                {result.execution_result ? (
                  <div className="bg-white border border-[#ded7c8] rounded-xl p-3.5 font-mono text-xs text-stone-800 overflow-x-auto">
                    <pre>{JSON.stringify(result.execution_result, null, 2)}</pre>
                  </div>
                ) : (
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 text-xs text-rose-900 space-y-1">
                    <div className="font-semibold flex items-center space-x-1.5">
                      <ShieldAlert className="w-4 h-4 text-rose-700" />
                      <span>Execution Blocked at Boundary</span>
                    </div>
                    <p className="text-[11px] text-rose-700">
                      The tool was intercepted before invoking MCP gateway or database. A security violation event was recorded in FalkorDB with SHA256 evidence.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-[#faf7f0] border border-[#ded7c8] border-dashed rounded-2xl p-12 text-center space-y-3">
              <Shield className="w-10 h-10 text-stone-400 mx-auto" />
              <div className="font-semibold text-sm text-stone-800">
                Ready to Intercept Runtime Event
              </div>
              <p className="text-xs text-stone-500 max-w-sm mx-auto">
                Select a preset or customize the caller, agent, and requested tool on the left, then click "Intercept & Validate Event" to observe multi-layer enforcement.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
