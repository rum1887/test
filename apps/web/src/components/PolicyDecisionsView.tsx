import React, { useState, useEffect } from 'react';
import { Lock, ShieldCheck, ShieldAlert, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

export const PolicyDecisionsView: React.FC = () => {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDecisions();
  }, []);

  const loadDecisions = async () => {
    setLoading(true);
    try {
      const data = await api.getTimeline(30);
      // Filter for policy decision items
      const decisions = data.timeline?.filter((item: any) => item.category === 'POLICY_DECISION') || [];
      setTimeline(decisions);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <Lock className="w-5 h-5 text-emerald-400" />
          <span>Deterministic Policy Decisions & Enforcement Audit</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Auditable trace of every deterministic policy evaluation executed at the boundary before tool or pod access.
        </p>
      </div>

      <div className="space-y-4">
        {timeline.map((d) => {
          const isAllow = d.decision === 'ALLOW';
          const isApproval = d.decision === 'REQUIRE_APPROVAL';
          const isDeny = d.decision === 'DENY';

          return (
            <div
              key={d.id}
              className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-5 shadow-lg space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#1b253b]">
                <div className="flex items-center space-x-3">
                  <span
                    className={`text-xs font-mono font-bold px-2.5 py-1 rounded ${
                      isAllow
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : isApproval
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}
                  >
                    {d.decision}
                  </span>
                  <span className="font-mono text-xs text-slate-400">ID: {d.id}</span>
                </div>

                <div className="text-right text-xs text-slate-400">
                  <span className="block font-mono">
                    {d.timestamp ? new Date(d.timestamp * 1000).toLocaleString() : 'N/A'}
                  </span>
                  <span className="text-[11px] text-slate-500">Enforcement Point: {d.provenance}</span>
                </div>
              </div>

              {/* Rationale Box */}
              <div className="bg-[#12192b] border border-[#1e2a44] rounded p-3 text-xs text-slate-200">
                <span className="font-semibold text-slate-400 block text-[11px] uppercase mb-1">
                  Evaluation Rationale
                </span>
                <p className="leading-relaxed font-mono text-[11px]">{d.rationale}</p>
              </div>

              {/* Evaluated Rules Tags */}
              {d.rules && d.rules.length > 0 && (
                <div className="text-xs space-y-1">
                  <span className="text-slate-400 text-[11px] block">Triggered / Failed Rule Identifiers:</span>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                    {d.rules.map((ruleId: string, idx: number) => (
                      <span
                        key={idx}
                        className="bg-rose-950/60 border border-rose-800/60 text-rose-300 px-2 py-0.5 rounded"
                      >
                        {ruleId}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {timeline.length === 0 && (
          <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-12 text-center text-xs text-slate-500">
            No policy evaluations recorded yet. Run a tool invocation in the Agent Trust tab to generate audit decisions.
          </div>
        )}
      </div>
    </div>
  );
};
