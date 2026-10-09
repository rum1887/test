import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle2, Play, ArrowRight, Activity, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

interface ContainmentViewProps {
  initialSourceId?: string;
}

export const ContainmentView: React.FC<ContainmentViewProps> = ({
  initialSourceId = 'workload-checkout',
}) => {
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [recommended, setRecommended] = useState<any | null>(null);
  const [simulationResult, setSimulationResult] = useState<any | null>(null);
  const [appliedAction, setAppliedAction] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    loadCandidates();
  }, [sourceId]);

  const loadCandidates = async () => {
    setLoading(true);
    setSimulationResult(null);
    setAppliedAction(null);
    try {
      const data = await api.getContainmentCandidates(sourceId);
      setCandidates(data.candidates || []);
      setRecommended(data.recommended_candidate || null);
      if (data.recommended_candidate) {
        // Automatically run baseline simulation on the recommended candidate
        handleSimulate(data.recommended_candidate.candidate_id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async (candidateId: string) => {
    setSimulating(true);
    try {
      const sim = await api.simulateContainment(sourceId, candidateId);
      setSimulationResult(sim);
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  };

  const handleApply = async (candidate: any) => {
    setApplying(true);
    try {
      const applied = await api.applyContainment(
        candidate.candidate_id,
        candidate.action_type,
        candidate.enforcement_mechanism
      );
      setAppliedAction(applied);

      // Verify action after 500ms
      setTimeout(async () => {
        try {
          const verified = await api.verifyContainment(applied.action_id);
          setAppliedAction(verified);
        } catch (err) {
          console.error(err);
        }
      }, 500);
    } catch (e) {
      console.error(e);
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Shield className="w-5 h-5 text-amber-400" />
            <span>Containment Simulator & Boundary Enforcement</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulates hypothetical node & edge removals to calculate exposure reduction, disruption risk, and remaining attack paths.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-[#0d1322] border border-[#1e2942] rounded-lg p-2 text-xs">
          <span className="text-slate-400">Threat Source:</span>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="bg-[#12192b] border border-[#1e2a44] rounded px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-sky-500"
          >
            <option value="workload-checkout">checkout-service (Workload)</option>
            <option value="pod-checkout-7f89b">checkout-service-7f89b (Pod)</option>
            <option value="workload-proxy">frontend-proxy (Workload)</option>
          </select>
        </div>
      </div>

      {/* Grid: Ranked Candidate Actions vs Before/After Simulation Diff */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Candidate Actions Table */}
        <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl overflow-hidden shadow-lg">
          <div className="px-5 py-3.5 border-b border-[#1b253b] bg-[#101728] flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-300">
              Evaluated Containment Candidates ({candidates.length})
            </span>
            <span className="text-[11px] font-mono text-slate-500">Ranked by Net Security Score</span>
          </div>

          <div className="divide-y divide-[#151f33]">
            {candidates.map((c, idx) => {
              const isTop = idx === 0;
              return (
                <div key={c.candidate_id} className="p-4 space-y-3 hover:bg-[#121a2d] transition">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-white">{c.action_type}</span>
                        {isTop && (
                          <span className="text-[10px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800 px-1.5 py-0.5 rounded font-bold">
                            Recommended
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 font-mono block mt-0.5">
                        Target: {c.node_name} ({c.node_label})
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-sm font-mono font-bold text-sky-400 block">
                        Net: {c.net_score}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        Exposure -{c.exposure_reduction_pct}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-[#12192b] p-2 rounded border border-[#1e2942]">
                      <span className="text-slate-500 block text-[10px]">Exposure Cut</span>
                      <span className="font-mono text-emerald-400 font-bold">{c.exposure_reduction_pct}%</span>
                    </div>
                    <div className="bg-[#12192b] p-2 rounded border border-[#1e2942]">
                      <span className="text-slate-500 block text-[10px]">Disruption Risk</span>
                      <span className="font-mono text-amber-400 font-bold">{c.disruption_score}</span>
                    </div>
                    <div className="bg-[#12192b] p-2 rounded border border-[#1e2942]">
                      <span className="text-slate-500 block text-[10px]">Remaining Paths</span>
                      <span className="font-mono text-slate-300 font-bold">{c.remaining_paths_count}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] font-mono text-slate-400 truncate max-w-[200px]">
                      Mech: {c.enforcement_mechanism}
                    </span>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleSimulate(c.candidate_id)}
                        className="px-2.5 py-1 bg-[#192540] hover:bg-[#223154] text-slate-200 border border-[#2b3c66] rounded text-xs font-medium transition cursor-pointer"
                      >
                        Simulate
                      </button>

                      <button
                        onClick={() => handleApply(c)}
                        disabled={applying}
                        className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-bold transition cursor-pointer"
                      >
                        Apply Containment
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Simulation Before / After Diff */}
        <div className="space-y-6">
          <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-5 shadow-lg space-y-4">
            <div className="pb-3 border-b border-[#1b253b] flex justify-between items-center">
              <div>
                <span className="text-[10px] font-mono uppercase text-sky-400">Hypothetical Simulation</span>
                <h3 className="text-sm font-bold text-white mt-0.5">Before vs After Reachability Diff</h3>
              </div>
              <span className="text-[10px] font-mono bg-sky-950 text-sky-300 border border-sky-800 px-2 py-0.5 rounded">
                Read-Only Traversal
              </span>
            </div>

            {simulationResult ? (
              <div className="space-y-4 text-xs">
                {/* Metric Diff Comparison */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-[#12192b] border border-[#1e2942] rounded-lg p-3 space-y-1">
                    <span className="text-slate-400 block text-[11px]">Baseline State</span>
                    <div className="text-lg font-bold font-mono text-white">
                      {simulationResult.baseline?.paths_count} paths
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Reaching {simulationResult.baseline?.reachable_targets_count} sensitive resources
                    </span>
                  </div>

                  <div className="bg-[#12192b] border border-[#1e2942] rounded-lg p-3 space-y-1">
                    <span className="text-slate-400 block text-[11px]">Post-Containment State</span>
                    <div className="text-lg font-bold font-mono text-emerald-400">
                      {simulationResult.post_containment?.remaining_paths_count} paths
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Remaining targets: {simulationResult.post_containment?.remaining_targets_count}
                    </span>
                  </div>
                </div>

                {/* Exposure Reduction Highlight */}
                <div className="p-3 bg-emerald-950/30 border border-emerald-900/50 rounded-lg flex items-center justify-between">
                  <span className="text-emerald-300 font-semibold">Net Exposure Reduction:</span>
                  <span className="font-mono text-lg font-extrabold text-emerald-400">
                    -{simulationResult.impact?.exposure_reduction_pct}%
                  </span>
                </div>

                {/* Eliminated Targets */}
                <div>
                  <span className="text-slate-400 block text-[11px] font-medium mb-1">
                    Eliminated Attack Targets:
                  </span>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                    {simulationResult.impact?.eliminated_targets?.map((t: string) => (
                      <span
                        key={t}
                        className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 px-2 py-0.5 rounded"
                      >
                        {t}
                      </span>
                    ))}
                    {(!simulationResult.impact?.eliminated_targets || simulationResult.impact.eliminated_targets.length === 0) && (
                      <span className="text-slate-500 italic">None eliminated</span>
                    )}
                  </div>
                </div>

                {/* Remaining Alternative Paths */}
                {simulationResult.post_containment?.remaining_paths_count > 0 && (
                  <div className="p-3 bg-amber-950/30 border border-amber-900/50 rounded-lg space-y-1 text-amber-200">
                    <div className="flex items-center space-x-1.5 font-semibold text-xs">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <span>Warning: Alternative Paths Remain</span>
                    </div>
                    <p className="text-[11px] text-amber-300/80 leading-relaxed">
                      This intervention does not fully isolate all sensitive assets. Consider secondary containment or network egress restriction.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                Click "Simulate" on any candidate to compute hypothetical exposure diff.
              </div>
            )}
          </div>

          {/* Applied Containment Action Confirmation Card */}
          {appliedAction && (
            <div className="bg-[#0d1322] border border-emerald-800/80 rounded-xl p-5 shadow-lg space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#1b253b]">
                <div className="flex items-center space-x-2 text-emerald-400">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="text-sm font-bold">Containment Action Confirmed</span>
                </div>
                <span className="font-mono text-xs px-2 py-0.5 rounded font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  {appliedAction.status}
                </span>
              </div>

              <div className="text-xs space-y-1 text-slate-300">
                <div>Action ID: <span className="font-mono text-slate-200">{appliedAction.action_id}</span></div>
                <div>Target ID: <span className="font-mono text-slate-200">{appliedAction.target_id}</span></div>
                <div>Mechanism: <span className="font-mono text-slate-200">{appliedAction.enforcement_mechanism}</span></div>
                <div className="pt-2 text-emerald-300 text-[11px]">
                  State confirmed by cluster enforcement boundary. Target node quarantined.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
