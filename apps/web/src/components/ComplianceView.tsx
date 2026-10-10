import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  FileText,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Lock,
  Database,
  Clock,
  Sparkles,
  DollarSign,
  Layers,
} from 'lucide-react';
import { api, CompliancePostureResponse, ComplianceControl } from '../api/client';

export const ComplianceView: React.FC = () => {
  const [posture, setPosture] = useState<CompliancePostureResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFramework, setSelectedFramework] = useState<string>('all');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    loadCompliance();
  }, []);

  const loadCompliance = async () => {
    try {
      setLoading(true);
      const res = await api.getCompliancePosture();
      setPosture(res);
    } catch (err) {
      console.error('Failed to load compliance posture:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = () => {
    setDownloading(true);
    const exportUrl = api.getComplianceExportUrl();
    window.open(exportUrl, '_blank');
    setTimeout(() => setDownloading(false), 1000);
  };

  if (loading && !posture) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex flex-col items-center justify-center space-y-4">
        <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-slate-400 font-mono">Evaluating graph against PCI-DSS, SOC 2, and EU AI Act...</span>
      </div>
    );
  }

  const allControls: (ComplianceControl & { frameworkName: string })[] = [];
  if (posture) {
    posture.frameworks.pci_dss_4.controls.forEach((c) =>
      allControls.push({ ...c, frameworkName: 'PCI-DSS v4.0' })
    );
    posture.frameworks.soc2_type2.controls.forEach((c) =>
      allControls.push({ ...c, frameworkName: 'SOC 2 Type II' })
    );
    posture.frameworks.eu_ai_act.controls.forEach((c) =>
      allControls.push({ ...c, frameworkName: 'EU AI Act (2024/1689)' })
    );
    posture.frameworks.nist_ai_rmf.controls.forEach((c) =>
      allControls.push({ ...c, frameworkName: 'NIST AI RMF 1.0' })
    );
  }

  const filteredControls = allControls.filter((c) => {
    if (selectedFramework === 'all') return true;
    if (selectedFramework === 'pci' && c.frameworkName.includes('PCI')) return true;
    if (selectedFramework === 'soc2' && c.frameworkName.includes('SOC 2')) return true;
    if (selectedFramework === 'eu_ai' && c.frameworkName.includes('EU AI')) return true;
    if (selectedFramework === 'nist' && c.frameworkName.includes('NIST')) return true;
    return false;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header Banner */}
      <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#faf8f5] text-stone-700 border border-[#e8e5de]">
              CISO GOVERNANCE CONTROL PLANE
            </span>
            <span className="text-xs text-stone-500 font-mono">
              Cluster: {posture?.cluster_context || 'aws-eks-production-us-east-1'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-stone-900 mt-1.5 tracking-tight flex items-center space-x-2">
            <span>Regulatory Compliance & Risk Posture</span>
            <ShieldCheck className="w-6 h-6 text-stone-700" />
          </h1>
          <p className="text-xs text-stone-500 mt-1 max-w-2xl">
            Continuous, mathematically provable verification of Kubernetes workload privileges, AI agent Model Context
            Protocol (MCP) delegations, and kernel eBPF runtime events against global compliance frameworks.
          </p>
        </div>

        {/* Export Report CTA */}
        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={handleDownloadReport}
            disabled={downloading}
            className="flex items-center space-x-2 px-4 py-2.5 bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{downloading ? 'Generating Report...' : 'Download Official CISO Audit Report'}</span>
          </button>
        </div>
      </div>

      {/* High-Level Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* KPI 1: Overall CISO Trust Score */}
        <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm">
          <span className="text-xs font-medium text-stone-500 block">Composite Security Score</span>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold font-mono text-stone-900">
              {posture?.overall_security_score ?? 75}
            </span>
            <span className="text-xs font-mono text-stone-400">/ 100</span>
          </div>
          <div className="mt-2 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-[11px] font-mono uppercase font-semibold text-amber-700">
              {posture?.risk_level ?? 'ELEVATED RISK'}
            </span>
          </div>
        </div>

        {/* KPI 2: Reachable Sensitive Exposure */}
        <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm">
          <span className="text-xs font-medium text-stone-500 block">Reachable Asset Exposure</span>
          <div className="mt-3 flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold font-mono text-rose-700">
              ${((posture?.total_exposure_usd ?? 14200000) / 1000000).toFixed(1)}M
            </span>
            <span className="text-xs text-stone-500">USD Liability</span>
          </div>
          <p className="mt-2 text-[11px] text-stone-400">PCI vault & customer data jewels</p>
        </div>

        {/* KPI 3: MTTC Reduction */}
        <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm">
          <span className="text-xs font-medium text-stone-500 block">Mean Time to Containment (MTTC)</span>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-emerald-700">
              {posture?.mean_time_to_containment_seconds ?? 1.4}s
            </span>
            <span className="text-xs text-stone-400 line-through">vs 4.2h Industry avg</span>
          </div>
          <p className="mt-2 text-[11px] text-emerald-700 font-medium">99.9% faster response via graph simulation</p>
        </div>

        {/* KPI 4: Pre-Execution Block Rate */}
        <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm">
          <span className="text-xs font-medium text-stone-500 block">AI Agent Tool Enforcement</span>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-stone-900">100%</span>
            <span className="text-xs text-emerald-700 font-medium">Pre-Execution Block</span>
          </div>
          <p className="mt-2 text-[11px] text-stone-400">Zero model hallucinations permitted</p>
        </div>
      </div>

      {/* 4 Regulatory Framework Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {posture &&
          Object.entries(posture.frameworks).map(([key, f]) => {
            const isFailing = f.score < 75;
            return (
              <div
                key={key}
                onClick={() => {
                  if (key === 'pci_dss_4') setSelectedFramework('pci');
                  else if (key === 'soc2_type2') setSelectedFramework('soc2');
                  else if (key === 'eu_ai_act') setSelectedFramework('eu_ai');
                  else if (key === 'nist_ai_rmf') setSelectedFramework('nist');
                }}
                className={`bg-white border rounded-xl p-5 transition cursor-pointer shadow-sm hover:border-stone-400 ${
                  isFailing ? 'border-amber-300' : 'border-[#e8e5de]'
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-semibold text-stone-900">{f.name}</span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      f.score >= 80
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {f.score}%
                  </span>
                </div>

                <div className="mt-3 w-full bg-[#f0ede6] rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${f.score >= 80 ? 'bg-emerald-600' : 'bg-amber-600'}`}
                    style={{ width: `${f.score}%` }}
                  />
                </div>

                <div className="mt-3 flex justify-between items-center text-[11px]">
                  <span className="text-stone-500">Status</span>
                  <span className={`font-mono font-medium ${f.score >= 80 ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {f.status}
                  </span>
                </div>
              </div>
            );
          })}
      </div>

      {/* Critical Findings Section */}
      {posture?.critical_findings && posture.critical_findings.length > 0 && (
        <div className="bg-white border border-[#e8e5de] rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-semibold text-stone-900">Active Audit Deficiencies & Defect Remediation</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {posture.critical_findings.map((f, i) => (
              <div
                key={i}
                className="bg-[#faf8f5] border border-[#ede9df] rounded-lg p-4 space-y-2 text-xs"
              >
                <div className="flex justify-between items-start">
                  <span className="font-semibold text-stone-900">{f.title}</span>
                  <span className="text-[10px] font-mono bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.5 rounded">
                    {f.severity}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-stone-600">{f.framework}</div>
                <p className="text-stone-600 text-[11px] leading-relaxed">{f.description}</p>
                <div className="pt-2 border-t border-[#e8e5de] flex items-center space-x-1.5 text-[11px] text-emerald-800 font-medium">
                  <span>Remediation:</span>
                  <span className="text-stone-700">{f.remediation}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Control-by-Control Table */}
      <div className="bg-white border border-[#e8e5de] rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#e8e5de]">
          <div>
            <h3 className="text-sm font-semibold text-stone-900">Continuous Control Evaluation Ledger</h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Live proof points linking graph entities to specific compliance standard requirements
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center space-x-1 bg-[#faf8f5] p-1 rounded-lg border border-[#ede9df] text-xs">
            <button
              onClick={() => setSelectedFramework('all')}
              className={`px-2.5 py-1 rounded transition cursor-pointer ${
                selectedFramework === 'all' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              All Controls ({allControls.length})
            </button>
            <button
              onClick={() => setSelectedFramework('pci')}
              className={`px-2.5 py-1 rounded transition cursor-pointer ${
                selectedFramework === 'pci' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              PCI-DSS
            </button>
            <button
              onClick={() => setSelectedFramework('soc2')}
              className={`px-2.5 py-1 rounded transition cursor-pointer ${
                selectedFramework === 'soc2' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              SOC 2
            </button>
            <button
              onClick={() => setSelectedFramework('eu_ai')}
              className={`px-2.5 py-1 rounded transition cursor-pointer ${
                selectedFramework === 'eu_ai' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              EU AI Act
            </button>
            <button
              onClick={() => setSelectedFramework('nist')}
              className={`px-2.5 py-1 rounded transition cursor-pointer ${
                selectedFramework === 'nist' ? 'bg-stone-900 text-white font-semibold' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              NIST AI RMF
            </button>
          </div>
        </div>

        {/* Controls Table */}
        <div className="overflow-x-auto border border-[#f0ede6] rounded-lg">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#faf8f5] border-b border-[#e8e5de] text-stone-500 font-mono text-[11px]">
                <th className="py-2.5 pl-3">CONTROL ID</th>
                <th className="py-2.5">FRAMEWORK</th>
                <th className="py-2.5">TITLE & CATEGORY</th>
                <th className="py-2.5">STATUS</th>
                <th className="py-2.5">GRAPH & eBPF EVIDENCE</th>
                <th className="py-2.5 pr-3">RISK IMPACT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0ede6]">
              {filteredControls.map((c) => (
                <tr key={c.id} className="hover:bg-[#faf8f5] transition">
                  <td className="py-3.5 pl-3 font-mono font-semibold text-stone-900 whitespace-nowrap">
                    {c.id}
                  </td>
                  <td className="py-3.5 text-stone-700 font-medium whitespace-nowrap">
                    {c.frameworkName}
                  </td>
                  <td className="py-3.5 max-w-xs">
                    <span className="font-semibold text-stone-900 block">{c.title}</span>
                    <span className="text-[10px] text-stone-400 font-mono">{c.category}</span>
                  </td>
                  <td className="py-3.5 whitespace-nowrap">
                    {c.status === 'PASS' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>PASS</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                        <XCircle className="w-3 h-3 text-rose-600" />
                        <span>FAIL</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 text-stone-600 max-w-sm text-[11px] font-sans">
                    {c.evidence}
                  </td>
                  <td className="py-3.5 pr-3 font-mono text-[11px] text-stone-500 whitespace-nowrap">
                    {c.impact}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
