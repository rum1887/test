import React, { useState, useEffect } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  Play,
  ArrowRight,
  Activity,
  ShieldCheck,
  Code,
  Copy,
  Check,
  Terminal,
  FileCode,
  Download,
} from 'lucide-react';
import { api, IaCExportResponse } from '../api/client';

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

  // IaC Export Modal State
  const [iacData, setIacData] = useState<IaCExportResponse | null>(null);
  const [iacTab, setIacTab] = useState<'k8s' | 'kyverno' | 'mcp' | 'terraform'>('k8s');
  const [copied, setCopied] = useState(false);
  const [loadingIac, setLoadingIac] = useState(false);

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

  const handleExportIaC = async (targetId: string, actionType: string) => {
    setLoadingIac(true);
    try {
      const data = await api.exportContainmentIaC(targetId, actionType);
      setIacData(data);
    } catch (e) {
      console.error('Failed to export IaC artifact:', e);
    } finally {
      setLoadingIac(false);
    }
  };

  const handleCopyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getActiveCode = () => {
    if (!iacData) return '';
    if (iacTab === 'k8s') return iacData.artifacts.kubernetes_network_policy_yaml;
    if (iacTab === 'kyverno') return iacData.artifacts.kyverno_cluster_policy_yaml;
    if (iacTab === 'mcp') return iacData.artifacts.mcp_gateway_filter_json;
    if (iacTab === 'terraform') return iacData.artifacts.terraform_aws_sg_hcl;
    return '';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-stone-900 flex items-center space-x-2">
            <Shield className="w-5 h-5 text-stone-700" />
            <span>Containment Simulator & Boundary Enforcement</span>
          </h2>
          <p className="text-xs text-stone-500 mt-1">
            Simulates hypothetical node & edge removals to calculate exposure reduction, disruption risk, and remaining attack paths.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-white border border-[#e8e5de] shadow-sm rounded-lg p-2 text-xs">
          <span className="text-stone-500">Threat Source:</span>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="bg-[#faf8f5] border border-[#dedad2] rounded px-2.5 py-1 text-stone-800 font-mono text-xs focus:outline-none focus:border-stone-500 cursor-pointer"
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
        <div className="bg-white border border-[#e8e5de] rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-3.5 border-b border-[#e8e5de] bg-[#faf8f5] flex justify-between items-center">
            <span className="text-xs font-semibold text-stone-700">
              Evaluated Containment Candidates ({candidates.length})
            </span>
            <span className="text-[11px] font-mono text-stone-500">Ranked by Net Security Score</span>
          </div>

          <div className="divide-y divide-[#f0ede6]">
            {candidates.map((c, idx) => {
              const isTop = idx === 0;
              return (
                <div key={c.candidate_id} className="p-4 space-y-3 hover:bg-[#faf8f5] transition">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-stone-900">{c.action_type}</span>
                        {isTop && (
                          <span className="text-[10px] font-mono uppercase bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 rounded font-bold">
                            Recommended
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-stone-500 font-mono block mt-0.5">
                        Target: {c.node_name} ({c.node_label})
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-sm font-mono font-bold text-stone-900 block">
                        Net: {c.net_score}
                      </span>
                      <span className="text-[10px] text-stone-500">
                        Exposure -{c.exposure_reduction_pct}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-[#faf8f5] p-2 rounded border border-[#ede9df]">
                      <span className="text-stone-500 block text-[10px]">Exposure Cut</span>
                      <span className="font-mono text-emerald-700 font-bold">{c.exposure_reduction_pct}%</span>
                    </div>
                    <div className="bg-[#faf8f5] p-2 rounded border border-[#ede9df]">
                      <span className="text-stone-500 block text-[10px]">Disruption Risk</span>
                      <span className="font-mono text-amber-700 font-bold">{c.disruption_score}</span>
                    </div>
                    <div className="bg-[#faf8f5] p-2 rounded border border-[#ede9df]">
                      <span className="text-stone-500 block text-[10px]">Remaining Paths</span>
                      <span className="font-mono text-stone-700 font-bold">{c.remaining_paths_count}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <span className="text-[11px] font-mono text-stone-500 truncate max-w-[180px]">
                      Mech: {c.enforcement_mechanism}
                    </span>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleExportIaC(c.candidate_id, c.action_type)}
                        className="px-2.5 py-1 bg-white hover:bg-stone-50 text-stone-700 border border-stone-300 rounded text-xs font-medium transition cursor-pointer flex items-center space-x-1 shadow-2xs"
                        title="Export Kubernetes NetworkPolicy YAML / Kyverno GitOps artifacts"
                      >
                        <FileCode className="w-3 h-3 text-stone-600" />
                        <span>IaC Playbook</span>
                      </button>

                      <button
                        onClick={() => handleSimulate(c.candidate_id)}
                        className="px-2.5 py-1 bg-stone-100 hover:bg-stone-200 text-stone-800 border border-stone-300 rounded text-xs font-medium transition cursor-pointer"
                      >
                        Simulate
                      </button>

                      <button
                        onClick={() => handleApply(c)}
                        disabled={applying}
                        className="px-3 py-1 bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-bold transition cursor-pointer"
                      >
                        Apply
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
          <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-4">
            <div className="pb-3 border-b border-[#e8e5de] flex justify-between items-center">
              <div>
                <span className="text-[10px] font-mono uppercase text-stone-500 font-semibold">Hypothetical Simulation</span>
                <h3 className="text-sm font-bold text-stone-900 mt-0.5">Before vs After Reachability Diff</h3>
              </div>
              <span className="text-[10px] font-mono bg-[#f4f1ea] text-stone-700 border border-[#e2ded5] px-2 py-0.5 rounded font-medium">
                Zero-Mutation Traversal
              </span>
            </div>

            {simulationResult ? (
              <div className="space-y-4 text-xs">
                {/* Metric Diff Comparison */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-[#faf8f5] border border-[#ede9df] rounded-lg p-3 space-y-1">
                    <span className="text-stone-500 block text-[11px]">Baseline State</span>
                    <div className="text-lg font-bold font-mono text-stone-900">
                      {simulationResult.baseline?.paths_count} paths
                    </div>
                    <span className="text-[11px] text-stone-500">
                      Reaching {simulationResult.baseline?.reachable_targets_count} sensitive resources
                    </span>
                  </div>

                  <div className="bg-emerald-50/40 border border-emerald-200/80 rounded-lg p-3 space-y-1">
                    <span className="text-emerald-800 block text-[11px]">Post-Containment State</span>
                    <div className="text-lg font-bold font-mono text-emerald-700">
                      {simulationResult.post_containment?.remaining_paths_count} paths
                    </div>
                    <span className="text-[11px] text-emerald-700/80">
                      Remaining targets: {simulationResult.post_containment?.remaining_targets_count}
                    </span>
                  </div>
                </div>

                {/* Exposure Reduction Highlight */}
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
                  <span className="text-emerald-800 font-semibold">Net Exposure Reduction:</span>
                  <span className="font-mono text-lg font-extrabold text-emerald-700">
                    -{simulationResult.impact?.exposure_reduction_pct}%
                  </span>
                </div>

                {/* Eliminated Targets */}
                <div>
                  <span className="text-stone-500 block text-[11px] font-medium mb-1">
                    Eliminated Attack Targets:
                  </span>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                    {simulationResult.impact?.eliminated_targets?.map((t: string) => (
                      <span
                        key={t}
                        className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-2 py-0.5 rounded"
                      >
                        {t}
                      </span>
                    ))}
                    {(!simulationResult.impact?.eliminated_targets || simulationResult.impact.eliminated_targets.length === 0) && (
                      <span className="text-stone-400 italic">None eliminated</span>
                    )}
                  </div>
                </div>

                {/* Remaining Alternative Paths */}
                {simulationResult.post_containment?.remaining_paths_count > 0 && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1 text-amber-900">
                    <div className="flex items-center space-x-1.5 font-semibold text-xs text-amber-800">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <span>Warning: Alternative Paths Remain</span>
                    </div>
                    <p className="text-[11px] text-amber-700 leading-relaxed">
                      This intervention does not fully isolate all sensitive assets. Consider secondary containment or network egress restriction.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-stone-400">
                Click "Simulate" on any candidate to compute hypothetical exposure diff.
              </div>
            )}
          </div>

          {/* Applied Containment Action Confirmation Card */}
          {appliedAction && (
            <div className="bg-emerald-50/40 border border-emerald-200 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-emerald-200">
                <div className="flex items-center space-x-2 text-emerald-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span className="text-sm font-bold">Containment Action Confirmed</span>
                </div>
                <span className="font-mono text-xs px-2 py-0.5 rounded font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {appliedAction.status}
                </span>
              </div>

              <div className="text-xs space-y-1 text-stone-700">
                <div>Action ID: <span className="font-mono text-stone-900">{appliedAction.action_id}</span></div>
                <div>Target ID: <span className="font-mono text-stone-900">{appliedAction.target_id}</span></div>
                <div>Mechanism: <span className="font-mono text-stone-900">{appliedAction.enforcement_mechanism}</span></div>
                <div className="pt-2 text-emerald-800 text-[11px] font-medium">
                  State confirmed by cluster enforcement boundary. Target node quarantined.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Production IaC Export Modal / Drawer */}
      {iacData && (
        <div className="bg-white border border-[#e8e5de] rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#e8e5de]">
            <div>
              <div className="flex items-center space-x-2">
                <FileCode className="w-5 h-5 text-stone-700" />
                <h3 className="text-sm font-bold text-stone-900">
                  GitOps Infrastructure as Code (IaC) Remediation Playbook
                </h3>
              </div>
              <p className="text-xs text-stone-500 mt-0.5 font-mono">
                Target: {iacData.target_id} | Action: {iacData.action_type}
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleCopyCode(getActiveCode())}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-semibold transition cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied to Clipboard!' : 'Copy Config'}</span>
              </button>
              <button
                onClick={() => setIacData(null)}
                className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded text-xs font-medium transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>

          {/* Format Tabs */}
          <div className="flex space-x-2 text-xs border-b border-[#e8e5de] pb-2">
            <button
              onClick={() => setIacTab('k8s')}
              className={`px-3 py-1.5 rounded transition cursor-pointer ${
                iacTab === 'k8s' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              Kubernetes NetworkPolicy (YAML)
            </button>
            <button
              onClick={() => setIacTab('kyverno')}
              className={`px-3 py-1.5 rounded transition cursor-pointer ${
                iacTab === 'kyverno' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              Kyverno / OPA ClusterPolicy (YAML)
            </button>
            <button
              onClick={() => setIacTab('mcp')}
              className={`px-3 py-1.5 rounded transition cursor-pointer ${
                iacTab === 'mcp' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              MCP Gateway Route Filter (JSON)
            </button>
            <button
              onClick={() => setIacTab('terraform')}
              className={`px-3 py-1.5 rounded transition cursor-pointer ${
                iacTab === 'terraform' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              Terraform AWS Security Group (HCL)
            </button>
          </div>

          {/* Code Viewer */}
          <div className="bg-[#faf8f5] border border-[#e8e5de] rounded-lg p-4 font-mono text-xs text-stone-800 overflow-x-auto max-h-80 select-all">
            <pre>{getActiveCode()}</pre>
          </div>
        </div>
      )}
    </div>
  );
};
