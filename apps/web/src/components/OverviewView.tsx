import React from 'react';
import {
  ShieldAlert,
  Cpu,
  KeyRound,
  Database,
  Terminal,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Play,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { StatsResponse, HealthResponse } from '../api/client';

interface OverviewViewProps {
  stats: StatsResponse | null;
  health: HealthResponse | null;
  onNavigate: (tab: string) => void;
  onTriggerReplay: () => void;
  onTestAgentBlock: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  stats,
  health,
  onNavigate,
  onTriggerReplay,
  onTestAgentBlock,
}) => {
  const isLive = health?.sensor?.is_live ?? false;
  const isStale = health?.sensor?.is_stale ?? false;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Threat Banner (if critical violations or stale telemetry detected) */}
      {isStale && (
        <div className="bg-amber-950/40 border border-amber-800/80 rounded-lg p-4 flex items-start space-x-3 text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs">
            <span className="font-semibold block text-sm">Degraded Telemetry Visibility Warning</span>
            Sensor telemetry stream is stale ({health?.sensor?.stale_warning}). Security trust scores have been degraded to UNKNOWN / DEGRADED. System does NOT assume safe status in absence of telemetry.
          </div>
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Workloads */}
        <div
          onClick={() => onNavigate('workloads')}
          className="bg-[#0d1322] border border-[#1e2942] hover:border-sky-500/50 rounded-xl p-5 transition cursor-pointer group shadow-lg"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400">Monitored Workloads</span>
            <div className="p-2 bg-sky-500/10 rounded-lg text-sky-400 group-hover:bg-sky-500/20 transition">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-white">
              {stats?.workloads_count ?? 4}
            </span>
            <span className="text-xs text-slate-400">({stats?.pods_count ?? 4} pods active)</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">Kind isolated Kubernetes lab</p>
        </div>

        {/* KPI 2: Agent Delegations */}
        <div
          onClick={() => onNavigate('agents')}
          className="bg-[#0d1322] border border-[#1e2942] hover:border-sky-500/50 rounded-xl p-5 transition cursor-pointer group shadow-lg"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400">Agents & Delegations</span>
            <div className="p-2 bg-pink-500/10 rounded-lg text-pink-400 group-hover:bg-pink-500/20 transition">
              <KeyRound className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-white">
              {stats?.agents_count ?? 1}
            </span>
            <span className="text-xs text-slate-400">({stats?.principals_count ?? 2} principals)</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">Autonomous tool invocation gateways</p>
        </div>

        {/* KPI 3: Sensitive Targets */}
        <div
          onClick={() => onNavigate('blast-radius')}
          className="bg-[#0d1322] border border-[#1e2942] hover:border-rose-500/50 rounded-xl p-5 transition cursor-pointer group shadow-lg"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400">Sensitive Target Jewels</span>
            <div className="p-2 bg-rose-500/10 rounded-lg text-rose-400 group-hover:bg-rose-500/20 transition">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-rose-400">
              {stats?.sensitive_resources_count ?? 4}
            </span>
            <span className="text-xs text-slate-400">Critical resources</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">PCI-DSS vault & customer databases</p>
        </div>

        {/* KPI 4: Policy Decisions */}
        <div
          onClick={() => onNavigate('policies')}
          className="bg-[#0d1322] border border-[#1e2942] hover:border-emerald-500/50 rounded-xl p-5 transition cursor-pointer group shadow-lg"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-medium text-slate-400">Policy Decisions Enforced</span>
            <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400 group-hover:bg-emerald-500/20 transition">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-white">
              {stats?.decisions_count ?? 1}
            </span>
            <span className="text-xs text-emerald-400 font-medium">100% Deterministic</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">Pre-execution boundary protection</p>
        </div>
      </div>

      {/* Control Plane & Telemetry Provenance Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Security Architecture Summary */}
        <div className="lg:col-span-2 bg-[#0d1322] border border-[#1e2942] rounded-xl p-6 shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-[#1b253b]">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-white">Security Control Plane Architecture</h3>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Graph Schema v1.0.0</span>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-[#12192b] border border-[#1e2a44] rounded-lg p-3.5 space-y-2">
              <span className="font-semibold text-sky-300 block">1. Workload Trust</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Tracks Kubernetes service accounts, RBAC bindings, secret mounts, and Calico/Kind network reachability.
              </p>
              <div className="pt-2 text-[10px] font-mono text-slate-400 border-t border-[#1e2942]">
                Traversal: Pod &rarr; SA &rarr; Perm &rarr; Resource
              </div>
            </div>

            <div className="bg-[#12192b] border border-[#1e2a44] rounded-lg p-3.5 space-y-2">
              <span className="font-semibold text-pink-300 block">2. Agent Delegation</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Calculates effective authority: Principal Auth &cap; Agent Caps &cap; Delegation Scopes &cap; Resource Constraints.
              </p>
              <div className="pt-2 text-[10px] font-mono text-slate-400 border-t border-[#1e2942]">
                Boundary: MCP Gateway Pre-execution
              </div>
            </div>

            <div className="bg-[#12192b] border border-[#1e2a44] rounded-lg p-3.5 space-y-2">
              <span className="font-semibold text-emerald-300 block">3. Runtime Enforcement</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Correlates eBPF telemetry with FalkorDB graph paths. Proposes containment and simulates before/after exposure.
              </p>
              <div className="pt-2 text-[10px] font-mono text-slate-400 border-t border-[#1e2942]">
                State: Simulated &rarr; Applied &rarr; Verified
              </div>
            </div>
          </div>

          {/* Quick Actions Bar */}
          <div className="mt-6 pt-4 border-t border-[#1b253b] flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigate('blast-radius')}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold transition cursor-pointer"
            >
              <span>Explore Workload Blast Radius</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onTestAgentBlock}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-950 hover:bg-rose-900 border border-rose-800 text-rose-200 rounded text-xs font-semibold transition cursor-pointer"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Test Pre-Execution Agent Block</span>
            </button>

            <button
              onClick={() => onNavigate('containment')}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#192540] hover:bg-[#223154] border border-[#2b3c66] text-slate-300 rounded text-xs font-semibold transition cursor-pointer"
            >
              <span>Simulate Containment</span>
            </button>
          </div>
        </div>

        {/* Right: Data Provenance & Sensor Health */}
        <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl p-6 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#1b253b]">
              <div className="flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Telemetry & Data Provenance</h3>
              </div>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between items-center py-1.5 border-b border-[#162035]">
                <span className="text-slate-400">Sensor Mode</span>
                <span className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                  isLive ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}>
                  {isLive ? 'Live Linux eBPF' : 'Synthetic Replay'}
                </span>
              </div>

              <div className="flex justify-between items-center py-1.5 border-b border-[#162035]">
                <span className="text-slate-400">Sensor Driver</span>
                <span className="font-mono text-slate-200">Cilium Tetragon / kprobe</span>
              </div>

              <div className="flex justify-between items-center py-1.5 border-b border-[#162035]">
                <span className="text-slate-400">Primary Graph Store</span>
                <span className="font-mono text-sky-400">FalkorDB v4 / Cypher</span>
              </div>

              <div className="flex justify-between items-center py-1.5 border-b border-[#162035]">
                <span className="text-slate-400">Events Ingested</span>
                <span className="font-mono text-slate-200">
                  {health?.sensor?.total_events_ingested ?? stats?.events_count ?? 0}
                </span>
              </div>

              <div className="flex justify-between items-center py-1.5 border-b border-[#162035]">
                <span className="text-slate-400">Dropped Events</span>
                <span className="font-mono text-slate-200">
                  {health?.sensor?.dropped_events_count ?? 0}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#1b253b]">
            <button
              onClick={onTriggerReplay}
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-[#131c31] hover:bg-[#1a2642] border border-sky-900/60 text-sky-300 rounded text-xs font-semibold transition cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-sky-400" />
              <span>Inject Telemetry Event Stream</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
