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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 font-sans">
      <div className="space-y-1">
        <h2 className="text-xl font-bold text-stone-900 flex items-center space-x-2">
          <Lock className="w-5 h-5 text-stone-700" />
          <span>Deterministic Policy Decisions & Enforcement Audit</span>
        </h2>
        <p className="text-xs text-stone-600">
          Auditable trace of every deterministic graph policy evaluation executed at the gateway boundary before tool or pod access.
        </p>
      </div>

      <div className="space-y-3.5">
        {timeline.map((d) => {
          const isAllow = d.decision === 'ALLOW';
          const isApproval = d.decision === 'REQUIRE_APPROVAL';
          const isDeny = d.decision === 'DENY';

          return (
            <div
              key={d.id}
              className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-3 text-stone-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[#f0ece2]">
                <div className="flex items-center space-x-3">
                  <span
                    className={`text-xs font-mono font-bold px-2.5 py-1 rounded border ${
                      isAllow
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : isApproval
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-rose-50 text-rose-800 border-rose-200'
                    }`}
                  >
                    {d.decision}
                  </span>
                  <span className="font-mono text-xs text-stone-500">ID: {d.id}</span>
                </div>

                <div className="text-right text-xs text-stone-500">
                  <span className="block font-mono text-stone-700">
                    {d.timestamp ? new Date(d.timestamp * 1000).toLocaleString() : 'N/A'}
                  </span>
                  <span className="text-[11px] text-stone-500">Enforcement Point: {d.provenance}</span>
                </div>
              </div>

              {/* Rationale Box */}
              <div className="bg-[#faf8f5] border border-[#ede9df] rounded-lg p-3 text-xs text-stone-800">
                <span className="font-semibold text-stone-500 block text-[11px] uppercase mb-1">
                  Evaluation Rationale
                </span>
                <p className="leading-relaxed font-mono text-[11px] text-stone-900">{d.rationale}</p>
              </div>

              {/* Evaluated Rules Tags */}
              {d.rules && d.rules.length > 0 && (
                <div className="text-xs space-y-1">
                  <span className="text-stone-500 text-[11px] block">Triggered / Failed Rule Identifiers:</span>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                    {d.rules.map((ruleId: string, idx: number) => (
                      <span
                        key={idx}
                        className="bg-rose-50 border border-rose-200 text-rose-800 px-2 py-0.5 rounded font-medium"
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

        {timeline.length === 0 && !loading && (
          <div className="bg-white border border-[#e8e5de] rounded-xl p-12 text-center text-xs text-stone-500 shadow-sm">
            No policy evaluations recorded yet. Run a tool invocation or test action to view live gateway decisions.
          </div>
        )}
      </div>
    </div>
  );
};
