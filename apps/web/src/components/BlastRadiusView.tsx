import React, { useState, useEffect } from 'react';
import { GitBranch, ShieldAlert, Layers, ArrowRight, Shield } from 'lucide-react';
import { api } from '../api/client';

interface BlastRadiusViewProps {
  initialSourceId?: string;
  onNavigateToContainment?: (sourceId: string) => void;
}

export const BlastRadiusView: React.FC<BlastRadiusViewProps> = ({
  initialSourceId = 'workload-checkout',
  onNavigateToContainment,
}) => {
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [maxDepth, setMaxDepth] = useState(5);
  const [blastData, setBlastData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadBlastRadius();
  }, [sourceId, maxDepth]);

  const loadBlastRadius = async () => {
    setLoading(true);
    try {
      const data = await api.getBlastRadius(sourceId, maxDepth);
      setBlastData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-stone-900 flex items-center space-x-2">
            <GitBranch className="w-5 h-5 text-stone-700" />
            <span>Workload Blast-Radius Analysis</span>
          </h2>
          <p className="text-xs text-stone-500 mt-1">
            FalkorDB bounded traversal discovering reachable sensitive resources via identities, permissions, and network endpoints.
          </p>
        </div>

        {/* Source Selector & Depth Controls */}
        <div className="flex items-center space-x-3 bg-white border border-[#e8e5de] shadow-sm rounded-lg p-2 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="text-stone-500">Threat Source:</span>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="bg-[#faf8f5] border border-[#dedad2] rounded px-2 py-1 text-stone-800 font-mono text-xs focus:outline-none focus:border-stone-500"
            >
              <option value="workload-checkout">checkout-service (Workload)</option>
              <option value="pod-checkout-7f89b">checkout-service-7f89b (Pod)</option>
              <option value="workload-proxy">frontend-proxy (Workload)</option>
              <option value="workload-order-processor">order-processor (Workload)</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5 border-l border-[#e8e5de] pl-3">
            <span className="text-stone-500">Depth:</span>
            <input
              type="range"
              min={1}
              max={6}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-20 accent-stone-800 cursor-pointer"
            />
            <span className="font-mono text-stone-900 font-bold">{maxDepth}</span>
          </div>
        </div>
      </div>

      {/* KPI Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm">
          <span className="text-xs text-stone-500">Total Plausible Paths</span>
          <div className="mt-1 text-2xl font-bold font-mono text-stone-900">
            {blastData?.total_paths ?? 0}
          </div>
          <span className="text-[11px] text-stone-400">Traversed in real-time Cypher</span>
        </div>

        <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm">
          <span className="text-xs text-stone-500">Reachable Sensitive Targets</span>
          <div className="mt-1 text-2xl font-bold font-mono text-rose-700">
            {blastData?.sensitive_resources_count ?? 0}
          </div>
          <span className="text-[11px] text-stone-400">High & Critical sensitivity</span>
        </div>

        <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm">
          <span className="text-xs text-stone-500">Maximum Traversal Depth</span>
          <div className="mt-1 text-2xl font-bold font-mono text-stone-900">
            {blastData?.max_path_length ?? 0} hops
          </div>
          <span className="text-[11px] text-stone-400">Longest plausible chain</span>
        </div>
      </div>

      {/* Sensitive Targets List */}
      <div className="bg-white border border-[#e8e5de] rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-3.5 border-b border-[#e8e5de] bg-[#faf8f5] flex justify-between items-center">
          <span className="text-xs font-semibold text-stone-700">Target Resources Reached from {sourceId}</span>
          {onNavigateToContainment && (
            <button
              onClick={() => onNavigateToContainment(sourceId)}
              className="flex items-center space-x-1 px-2.5 py-1 bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-medium transition cursor-pointer shadow-sm"
            >
              <Shield className="w-3 h-3" />
              <span>Simulate Containment</span>
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-stone-700">
            <thead className="bg-[#faf8f5] text-[11px] text-stone-500 uppercase font-mono border-b border-[#e8e5de]">
              <tr>
                <th className="px-4 py-2.5">Resource Name</th>
                <th className="px-4 py-2.5">Entity Type</th>
                <th className="px-4 py-2.5">Sensitivity Level</th>
                <th className="px-4 py-2.5">Min Hop Distance</th>
                <th className="px-4 py-2.5">Path Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0ede6]">
              {blastData?.targets?.map((tgt: any) => (
                <tr key={tgt.id} className="hover:bg-[#faf8f5]">
                  <td className="px-4 py-3 font-semibold text-stone-900">{tgt.name}</td>
                  <td className="px-4 py-3 font-mono text-stone-500">{tgt.label}</td>
                  <td className="px-4 py-3">
                    <span className="text-[10px] font-mono uppercase bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.5 rounded font-bold">
                      {tgt.sensitivity}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-stone-800 font-medium">{tgt.min_path_length} hops</td>
                  <td className="px-4 py-3 font-mono text-stone-500">{tgt.path_count} independent paths</td>
                </tr>
              ))}
              {(!blastData?.targets || blastData.targets.length === 0) && (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-stone-400">
                    No sensitive resources reachable within {maxDepth} hops.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Path Breakdown Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-stone-700 flex items-center space-x-2">
          <Layers className="w-4 h-4 text-stone-700" />
          <span>Detailed Plausible Access Paths ({blastData?.paths?.length ?? 0})</span>
        </h3>

        <div className="space-y-2">
          {blastData?.paths?.slice(0, 10).map((p: any, idx: number) => (
            <div
              key={idx}
              className="bg-white border border-[#e8e5de] rounded-lg p-3.5 text-xs space-y-2 shadow-sm"
            >
              <div className="flex justify-between items-center text-[11px]">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-stone-500">Path #{idx + 1} ({p.length} hops)</span>
                  <span
                    className={`font-mono uppercase text-[10px] px-1.5 py-0.2 rounded font-bold ${
                      p.classification === 'observed'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : p.classification === 'inferred'
                        ? 'bg-sky-50 text-sky-800 border border-sky-200'
                        : 'bg-stone-100 text-stone-700'
                    }`}
                  >
                    {p.classification}
                  </span>
                </div>
                <span className="font-semibold text-rose-700">{p.target?.name}</span>
              </div>

              {/* Node Sequence Bar */}
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] pt-1">
                {p.nodes?.map((node: any, nIdx: number) => (
                  <React.Fragment key={nIdx}>
                    <span className="bg-[#faf8f5] border border-[#ede9df] px-2 py-0.5 rounded text-stone-800">
                      {node.name}
                    </span>
                    {nIdx < p.edges?.length && (
                      <span className="text-stone-400 text-[10px]">&rarr; {p.edges[nIdx]?.type} &rarr;</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
