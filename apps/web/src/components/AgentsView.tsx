import React, { useState, useEffect } from 'react';
import { Activity, KeyRound, ShieldAlert, CheckCircle2, ShieldX, Play, Lock } from 'lucide-react';
import { api } from '../api/client';

export const AgentsView: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [tools, setTools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Tool Invocation Test State
  const [testSessionId, setTestSessionId] = useState('session-alice-dev-01');
  const [testToolName, setTestToolName] = useState('db_drop_table');
  const [invoking, setInvoking] = useState(false);
  const [invocationResult, setInvocationResult] = useState<any | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [a, s, t] = await Promise.all([
        api.getAgents(),
        api.getSessions(),
        api.getTools(),
      ]);
      setAgents(a);
      setSessions(s);
      setTools(t);
      if (s.length > 0) setTestSessionId(s[0].session_id);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTestInvoke = async () => {
    setInvoking(true);
    setInvocationResult(null);
    try {
      const res = await api.invokeGateway({
        session_id: testSessionId,
        tool_name: testToolName,
        action: 'EXECUTE',
        parameters: { target: 'production' },
      });
      setInvocationResult(res);
    } catch (e) {
      console.error(e);
      setInvocationResult({ error: String(e) });
    } finally {
      setInvoking(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <Activity className="w-5 h-5 text-pink-400" />
          <span>AI Agent Trust & Delegation Inspector</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Traces delegated human authority, agent sessions, MCP tools, and pre-execution policy enforcement.
        </p>
      </div>

      {/* Grid: Sessions & Delegations vs Interactive Tool Gateway Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Active Agent Sessions & Delegations */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Sessions Card */}
          <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl overflow-hidden shadow-lg">
            <div className="px-5 py-3.5 border-b border-[#1b253b] bg-[#101728] flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-300">Active Delegated Sessions</span>
              <span className="text-[11px] font-mono text-slate-500">Effective Authority Bounded</span>
            </div>

            <div className="divide-y divide-[#151f33]">
              {sessions.map((s) => (
                <div key={s.session_id} className="p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-white">{s.principal?.name}</span>
                        <span className="text-[10px] font-mono uppercase bg-[#1a253e] text-slate-300 px-1.5 py-0.5 rounded">
                          {s.principal?.role}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 font-mono block mt-0.5">
                        Session: {s.session_id}
                      </span>
                    </div>

                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                      s.status === 'ACTIVE'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}>
                      {s.status}
                    </span>
                  </div>

                  <div className="bg-[#12192b] border border-[#1c2740] rounded p-3 text-xs space-y-1.5">
                    <div className="flex justify-between text-slate-300">
                      <span className="text-slate-500">Agent:</span>
                      <span className="font-mono text-pink-300 font-medium">{s.agent?.name ?? 'AutoDev-Agent'}</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span className="text-slate-500">Delegated Scopes:</span>
                      <span className="font-mono text-sky-300">
                        {JSON.stringify(s.delegation?.scopes ?? [])}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* MCP Tools Catalog */}
          <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl overflow-hidden shadow-lg">
            <div className="px-5 py-3.5 border-b border-[#1b253b] bg-[#101728]">
              <span className="text-xs font-semibold text-slate-300">MCP Tool Catalog & Downstream Targets</span>
            </div>

            <div className="divide-y divide-[#151f33]">
              {tools.map((t) => (
                <div key={t.id} className="p-3.5 flex items-center justify-between text-xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-semibold text-white">{t.name}</span>
                      {t.is_destructive && (
                        <span className="text-[10px] font-mono uppercase bg-rose-950 text-rose-300 border border-rose-800 px-1 py-0.2 rounded font-bold">
                          Destructive
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 text-[11px] block">{t.description}</span>
                  </div>

                  <div className="text-right">
                    <span className="font-mono text-[11px] text-slate-400 block">
                      Target: {t.downstream_target?.name ?? 'Internal'}
                    </span>
                    <span className="text-[10px] font-mono text-amber-400 uppercase font-semibold">
                      Risk: {t.risk_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Interactive Pre-Execution Tool Gateway Test Console */}
        <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-[#1b253b]">
              <Lock className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-bold text-white">Live Tool Gateway Test Console</h3>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Sends an actual invocation through the controlled MCP Gateway to verify deterministic pre-execution blocking.
            </p>

            <div className="mt-4 space-y-4 text-xs">
              <div>
                <label className="text-slate-400 block font-medium mb-1">Select Active Session</label>
                <select
                  value={testSessionId}
                  onChange={(e) => setTestSessionId(e.target.value)}
                  className="w-full bg-[#12192b] border border-[#1e2a44] rounded p-2 text-slate-200 focus:outline-none focus:border-sky-500 font-mono text-xs"
                >
                  {sessions.map((s) => (
                    <option key={s.session_id} value={s.session_id}>
                      {s.principal?.name} ({s.session_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-400 block font-medium mb-1">Select Tool to Invoke</label>
                <select
                  value={testToolName}
                  onChange={(e) => setTestToolName(e.target.value)}
                  className="w-full bg-[#12192b] border border-[#1e2a44] rounded p-2 text-slate-200 focus:outline-none focus:border-sky-500 font-mono text-xs"
                >
                  <option value="audit_read">audit_read (Read-only compliance)</option>
                  <option value="report_generate">report_generate (Generate reports)</option>
                  <option value="db_query">db_query (Parameterized read)</option>
                  <option value="db_drop_table">db_drop_table (CRITICAL / Destructive)</option>
                </select>
              </div>

              <button
                onClick={handleTestInvoke}
                disabled={invoking}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white rounded font-semibold text-xs transition disabled:opacity-50 cursor-pointer shadow-md"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{invoking ? 'Evaluating...' : 'Invoke via MCP Gateway'}</span>
              </button>
            </div>

            {/* Test Invocation Result Output */}
            {invocationResult && (
              <div className="mt-5 p-3.5 rounded-lg border text-xs space-y-2 bg-[#090e1a] border-[#1e2942]">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-slate-300">Gateway Decision</span>
                  <span
                    className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                      invocationResult.decision?.decision === 'ALLOW'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : invocationResult.decision?.decision === 'REQUIRE_APPROVAL'
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}
                  >
                    {invocationResult.decision?.decision ?? 'ERROR'}
                  </span>
                </div>

                <p className="text-slate-300 text-[11px] leading-relaxed">
                  {invocationResult.decision?.rationale ?? invocationResult.error}
                </p>

                {invocationResult.blocked && (
                  <div className="p-2 bg-rose-950/40 border border-rose-900/60 rounded text-rose-300 text-[11px] flex items-start space-x-1.5">
                    <ShieldX className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      CONFIRMED: Execution BLOCKED at gateway boundary. Tool never executed. Violation evidence saved to FalkorDB.
                    </span>
                  </div>
                )}

                {invocationResult.success && (
                  <div className="p-2 bg-emerald-950/40 border border-emerald-900/60 rounded text-emerald-300 text-[11px] flex items-start space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>Tool executed successfully. Output hash recorded in graph.</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
