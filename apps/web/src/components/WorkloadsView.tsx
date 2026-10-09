import React, { useState, useEffect } from 'react';
import { Cpu, ShieldAlert, ArrowRight, ShieldCheck, KeyRound } from 'lucide-react';
import { api } from '../api/client';

interface WorkloadsViewProps {
  onAnalyzeBlastRadius: (workloadId: string) => void;
}

export const WorkloadsView: React.FC<WorkloadsViewProps> = ({ onAnalyzeBlastRadius }) => {
  const [workloads, setWorkloads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkload, setSelectedWorkload] = useState<any | null>(null);

  useEffect(() => {
    loadWorkloads();
  }, []);

  const loadWorkloads = async () => {
    setLoading(true);
    try {
      const data = await api.getWorkloads();
      setWorkloads(data);
      if (data.length > 0 && !selectedWorkload) {
        loadDetail(data[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    try {
      const detail = await api.getWorkloadDetail(id);
      setSelectedWorkload(detail);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <Cpu className="w-5 h-5 text-sky-400" />
          <span>Kubernetes Workload Trust & Inventory</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Correlates Kubernetes workloads, pods, service accounts, RBAC bindings, and observed runtime behavior.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Workloads Table / List */}
        <div className="lg:col-span-2 bg-[#0d1322] border border-[#1e2942] rounded-xl overflow-hidden shadow-lg">
          <div className="px-5 py-3.5 border-b border-[#1b253b] flex justify-between items-center bg-[#101728]">
            <span className="text-xs font-semibold text-slate-300">Cluster Workloads ({workloads.length})</span>
            <span className="text-[11px] font-mono text-slate-500">Namespace: trust-lab</span>
          </div>

          <div className="divide-y divide-[#151f33]">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading workloads...</div>
            ) : (
              workloads.map((w) => {
                const isSelected = selectedWorkload?.id === w.id;
                const isDegraded = w.status === 'DEGRADED';
                return (
                  <div
                    key={w.id}
                    onClick={() => loadDetail(w.id)}
                    className={`p-4 flex items-center justify-between hover:bg-[#121a2d] transition cursor-pointer ${
                      isSelected ? 'bg-[#151f33] border-l-4 border-sky-500' : ''
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-white">{w.name}</span>
                        <span className="text-[10px] font-mono uppercase bg-[#1a253e] text-slate-300 px-1.5 py-0.5 rounded">
                          {w.kind}
                        </span>
                        {isDegraded && (
                          <span className="text-[10px] font-mono uppercase bg-rose-950 text-rose-300 border border-rose-800 px-1.5 py-0.5 rounded flex items-center space-x-1">
                            <ShieldAlert className="w-2.5 h-2.5" />
                            <span>Overprivileged / Threat</span>
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 flex items-center space-x-3">
                        <span>Pods: {w.pods?.length ?? 0}</span>
                        <span>•</span>
                        <span>SA: {w.service_account?.name ?? 'default'}</span>
                        <span>•</span>
                        <span>Events: {w.total_events}</span>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onAnalyzeBlastRadius(w.id);
                      }}
                      className="flex items-center space-x-1 px-2.5 py-1.5 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded text-xs font-medium transition cursor-pointer"
                    >
                      <span>Blast Radius</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Selected Workload Granular Security Detail */}
        <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-5 shadow-lg">
          {selectedWorkload ? (
            <div className="space-y-5">
              <div className="pb-3 border-b border-[#1b253b]">
                <span className="text-[10px] font-mono uppercase text-sky-400">Selected Workload</span>
                <h3 className="text-base font-bold text-white mt-1">{selectedWorkload.name}</h3>
                <span className="text-xs text-slate-400 font-mono">{selectedWorkload.id}</span>
              </div>

              {/* RBAC Permissions Box */}
              <div>
                <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1 mb-2">
                  <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                  <span>Configured RBAC Permissions</span>
                </span>
                <div className="space-y-1.5">
                  {selectedWorkload.permissions?.map((perm: any) => (
                    <div
                      key={perm.id}
                      className="bg-[#121a2d] border border-[#1e2942] rounded p-2 text-xs font-mono text-slate-300"
                    >
                      <div className="flex justify-between">
                        <span className="text-sky-300 font-semibold">{perm.action}</span>
                        <span className="text-emerald-400">{perm.effect}</span>
                      </div>
                      <span className="text-[11px] text-slate-400 block mt-0.5">{perm.resource_pattern}</span>
                    </div>
                  ))}
                  {(!selectedWorkload.permissions || selectedWorkload.permissions.length === 0) && (
                    <div className="text-xs text-slate-500 italic">No direct secret/RBAC permissions granted.</div>
                  )}
                </div>
              </div>

              {/* Reachable Sensitive Resources Box */}
              <div>
                <span className="text-xs font-semibold text-slate-300 flex items-center space-x-1 mb-2">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                  <span>Reachable Sensitive Targets</span>
                </span>
                <div className="space-y-1.5">
                  {selectedWorkload.blast_radius?.sensitive_targets?.map((tgt: any) => (
                    <div
                      key={tgt.id}
                      className="bg-rose-950/20 border border-rose-900/40 rounded p-2 text-xs flex justify-between items-center"
                    >
                      <div>
                        <span className="font-semibold text-white block">{tgt.name}</span>
                        <span className="text-[11px] text-slate-400 font-mono">Min depth: {tgt.min_path_length} hops</span>
                      </div>
                      <span className="text-[10px] font-mono uppercase bg-rose-950 text-rose-300 border border-rose-800 px-1.5 py-0.5 rounded font-bold">
                        {tgt.sensitivity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => onAnalyzeBlastRadius(selectedWorkload.id)}
                  className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold transition cursor-pointer"
                >
                  Open Full Blast Radius Graph Analysis
                </button>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-400 text-center py-12">
              Select a workload to inspect its security posture.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
