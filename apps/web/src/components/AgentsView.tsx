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
        <h2 className="text-xl font-bold text-stone-900 flex items-center space-x-2">
          <Activity className="w-5 h-5 text-stone-700" />
          <span>AI Agent Trust & Delegation Inspector</span>
        </h2>
        <p className="text-xs text-stone-500 mt-1">
          Traces delegated human authority, agent sessions, MCP tools, and pre-execution policy enforcement.
        </p>
      </div>

      {/* Grid: Sessions & Delegations vs Interactive Tool Gateway Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Active Agent Sessions & Delegations */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Sessions Card */}
          <div className="bg-white border border-[#e8e5de] rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-3.5 border-b border-[#e8e5de] bg-[#faf8f5] flex justify-between items-center">
              <span className="text-xs font-semibold text-stone-700">Active Delegated Sessions</span>
              <span className="text-[11px] font-mono text-stone-500">Effective Authority Bounded</span>
            </div>

            <div className="divide-y divide-[#f0ede6]">
              {sessions.map((s) => (
                <div key={s.session_id} className="p-4 space-y-2 hover:bg-[#faf8f5] transition">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-stone-900">{s.principal?.name}</span>
                        <span className="text-[10px] font-mono uppercase bg-[#f0ede6] text-stone-700 px-1.5 py-0.5 rounded font-medium">
                          {s.principal?.role}
                        </span>
                      </div>
                      <span className="text-xs text-stone-500 font-mono block mt-0.5">
                        Session: {s.session_id}
                      </span>
                    </div>

                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                      s.status === 'ACTIVE'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-rose-50 text-rose-800 border border-rose-200'
                    }`}>
                      {s.status}
                    </span>
                  </div>

                  <div className="bg-[#faf8f5] border border-[#ede9df] rounded p-3 text-xs space-y-1.5">
                    <div className="flex justify-between text-stone-700">
                      <span className="text-stone-400">Agent:</span>
                      <span className="font-mono text-stone-900 font-semibold">{s.agent?.name ?? 'AutoDev-Agent'}</span>
                    </div>
                    <div className="flex justify-between text-stone-700">
                      <span className="text-stone-400">Delegated Scopes:</span>
                      <span className="font-mono text-stone-800">
                        {JSON.stringify(s.delegation?.scopes ?? [])}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* MCP Tools Catalog */}
          <div className="bg-white border border-[#e8e5de] rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-3.5 border-b border-[#e8e5de] bg-[#faf8f5]">
              <span className="text-xs font-semibold text-stone-700">MCP Tool Catalog & Downstream Targets</span>
            </div>

            <div className="divide-y divide-[#f0ede6]">
              {tools.map((t) => (
                <div key={t.id} className="p-3.5 flex items-center justify-between text-xs hover:bg-[#faf8f5] transition">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-semibold text-stone-900">{t.name}</span>
                      {t.is_destructive && (
                        <span className="text-[10px] font-mono uppercase bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.5 rounded font-bold">
                          Destructive
                        </span>
                      )}
                    </div>
                    <span className="text-stone-500 text-[11px] block">{t.description}</span>
                  </div>

                  <div className="text-right">
                    <span className="font-mono text-[11px] text-stone-500 block">
                      Target: {t.downstream_target?.name ?? 'Internal'}
                    </span>
                    <span className="text-[10px] font-mono text-amber-700 uppercase font-semibold">
                      Risk: {t.risk_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Interactive Pre-Execution Tool Gateway Test Console */}
        <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-[#e8e5de]">
              <Lock className="w-4 h-4 text-stone-700" />
              <h3 className="text-sm font-bold text-stone-900">Live Tool Gateway Test Console</h3>
            </div>
            <p className="text-xs text-stone-500 mt-2">
              Sends an actual invocation through the controlled MCP Gateway to verify deterministic pre-execution blocking.
            </p>

            <div className="mt-4 space-y-4 text-xs">
              <div>
                <label className="text-stone-600 block font-medium mb-1">Select Active Session</label>
                <select
                  value={testSessionId}
                  onChange={(e) => setTestSessionId(e.target.value)}
                  className="w-full bg-[#faf8f5] border border-[#dedad2] rounded p-2 text-stone-800 focus:outline-none focus:border-stone-500 font-mono text-xs"
                >
                  {sessions.map((s) => (
                    <option key={s.session_id} value={s.session_id}>
                      {s.principal?.name} ({s.session_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-stone-600 block font-medium mb-1">Select Tool to Invoke</label>
                <select
                  value={testToolName}
                  onChange={(e) => setTestToolName(e.target.value)}
                  className="w-full bg-[#faf8f5] border border-[#dedad2] rounded p-2 text-stone-800 focus:outline-none focus:border-stone-500 font-mono text-xs"
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
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-stone-900 hover:bg-stone-800 text-white rounded font-semibold text-xs transition disabled:opacity-50 cursor-pointer shadow-sm"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{invoking ? 'Evaluating...' : 'Invoke via MCP Gateway'}</span>
              </button>
            </div>

            {/* Test Invocation Result Output */}
            {invocationResult && (
              <div className="mt-5 p-3.5 rounded-lg border text-xs space-y-2 bg-[#faf8f5] border-[#e8e5de]">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-stone-800">Gateway Decision</span>
                  <span
                    className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                      invocationResult.decision?.decision === 'ALLOW'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : invocationResult.decision?.decision === 'REQUIRE_APPROVAL'
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-rose-50 text-rose-800 border border-rose-200'
                    }`}
                  >
                    {invocationResult.decision?.decision ?? 'ERROR'}
                  </span>
                </div>

                <p className="text-stone-700 text-[11px] leading-relaxed">
                  {invocationResult.decision?.rationale ?? invocationResult.error}
                </p>

                {invocationResult.blocked && (
                  <div className="p-2 bg-rose-50 border border-rose-200 rounded text-rose-800 text-[11px] flex items-start space-x-1.5">
                    <ShieldX className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
                    <span>
                      CONFIRMED: Execution BLOCKED at gateway boundary. Tool never executed. Violation evidence saved to FalkorDB.
                    </span>
                  </div>
                )}

                {invocationResult.success && (
                  <div className="p-2 bg-emerald-50 border border-emerald-200 rounded text-emerald-800 text-[11px] flex items-start space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
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
