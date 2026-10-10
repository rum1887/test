import React, { useState } from 'react';
import {
  Shield,
  Activity,
  Layers,
  Terminal,
  Cpu,
  RotateCcw,
  AlertTriangle,
  Play,
  Database,
  Lock,
  GitBranch,
  ShieldCheck,
  Building,
  User,
  ChevronDown,
} from 'lucide-react';
import { HealthResponse } from '../api/client';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  health: HealthResponse | null;
  onReset: () => void;
  onLoadScenario: (scenario: string) => void;
  onTriggerReplay: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  health,
  onReset,
  onLoadScenario,
  onTriggerReplay,
}) => {
  const [resetting, setResetting] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState('ALL');
  const [selectedCluster, setSelectedCluster] = useState('prod-us-east-1');

  const handleResetClick = async () => {
    setResetting(true);
    await onReset();
    setTimeout(() => setResetting(false), 600);
  };

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedScenario(val);
    onLoadScenario(val);
  };

  const isLive = health?.sensor?.is_live ?? false;
  const isHealthy = health?.database?.healthy ?? true;
  const isStale = health?.sensor?.is_stale ?? false;

  const navItems = [
    { id: 'overview', label: 'CISO Overview', icon: Shield },
    { id: 'compliance', label: 'Compliance & Audit', icon: ShieldCheck },
    { id: 'graph', label: 'Trust Graph', icon: Layers },
    { id: 'workloads', label: 'Workloads', icon: Cpu },
    { id: 'agents', label: 'Agent Trust (MCP)', icon: Activity },
    { id: 'blast-radius', label: 'Blast Radius', icon: GitBranch },
    { id: 'events', label: 'Runtime Events', icon: Terminal },
    { id: 'policies', label: 'Policy Engine', icon: Lock },
    { id: 'containment', label: 'Containment Simulator', icon: AlertTriangle },
  ];

  return (
    <header className="bg-[#0a0f1d] border-b border-[#1b253b] sticky top-0 z-50">
      {/* Top Enterprise Banner Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Left: Brand & Cluster Context */}
          <div className="flex items-center space-x-3 shrink-0">
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-inner">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-white">Runtime Trust Layer</span>
                <span className="text-[10px] font-mono uppercase bg-sky-950 text-sky-300 border border-sky-800 px-1.5 py-0.5 rounded">
                  ENTERPRISE v1.0
                </span>
              </div>
              {/* Tenant / Cluster Switcher */}
              <div className="flex items-center space-x-1.5 text-xs text-slate-400 mt-0.5">
                <Building className="w-3 h-3 text-slate-500" />
                <span className="text-slate-300 font-medium hidden sm:inline">Acme Corp:</span>
                <select
                  value={selectedCluster}
                  onChange={(e) => setSelectedCluster(e.target.value)}
                  className="bg-transparent text-sky-400 text-[11px] font-mono focus:outline-none cursor-pointer border-b border-transparent hover:border-sky-500 transition"
                >
                  <option value="prod-us-east-1" className="bg-[#0d1322] text-slate-200">
                    aws-eks-production [us-east-1]
                  </option>
                  <option value="staging-eu-central-1" className="bg-[#0d1322] text-slate-200">
                    aws-eks-staging [eu-central-1]
                  </option>
                  <option value="fintech-gke-core" className="bg-[#0d1322] text-slate-200">
                    gcp-gke-fintech [us-central1]
                  </option>
                </select>
              </div>
            </div>
          </div>

          {/* Center Status Indicators */}
          <div className="hidden lg:flex items-center space-x-3">
            {/* FalkorDB Engine Status */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#101728] border border-[#1e2a44] text-xs">
              <Database className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-400">Graph:</span>
              <span className={`font-mono font-medium ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
                {isHealthy ? 'FalkorDB ONLINE' : 'DEGRADED'}
              </span>
            </div>

            {/* Sensor Telemetry Mode */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#101728] border border-[#1e2a44] text-xs">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse-live' : 'bg-amber-400'}`} />
              <span className="text-slate-400">Sensor:</span>
              <span className="font-mono font-semibold text-slate-200">
                {isLive ? 'eBPF Live (48 nodes)' : 'Replay Stream'}
              </span>
              {isStale && (
                <span className="text-[10px] font-mono bg-amber-950 text-amber-300 border border-amber-800 px-1 rounded">
                  STALE
                </span>
              )}
            </div>

            {/* CISO Security Posture Pill */}
            <button
              onClick={() => setCurrentTab('compliance')}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/80 text-amber-300 text-xs font-medium transition cursor-pointer"
              title="Click to view full CISO Regulatory Compliance Posture"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              <span>Posture: 75/100</span>
            </button>
          </div>

          {/* Right Controls: User Profile + Scenarios + Reset */}
          <div className="flex items-center space-x-3 shrink-0">
            {/* Replay event trigger */}
            <button
              onClick={onTriggerReplay}
              title="Inject synthetic telemetry event stream into graph"
              className="hidden sm:flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-sky-950 hover:bg-sky-900 border border-sky-800/80 text-sky-300 text-xs font-medium transition cursor-pointer"
            >
              <Play className="w-3 h-3 fill-sky-400" />
              <span>Replay Event</span>
            </button>

            {/* Scenario selector */}
            <div className="flex items-center space-x-1.5 text-xs">
              <select
                id="scenario-select"
                value={selectedScenario}
                onChange={handleScenarioChange}
                className="bg-[#101728] border border-[#1e2a44] text-slate-200 text-xs rounded-md px-2.5 py-1.5 focus:outline-none focus:border-sky-500 cursor-pointer"
              >
                <option value="ALL">All Baseline Scenarios</option>
                <option value="A">Scenario A: K8s Shell Breach</option>
                <option value="B">Scenario B: Agent Delegation Block</option>
                <option value="C">Scenario C: Shared Attack Path</option>
                <option value="D">Scenario D: Stale Telemetry</option>
                <option value="E">Scenario E: Control Plane Fail-Closed</option>
              </select>
            </div>

            {/* Reset Graph */}
            <button
              onClick={handleResetClick}
              disabled={resetting}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-rose-950/50 hover:bg-rose-900/80 border border-rose-800/60 text-rose-300 text-xs font-medium transition disabled:opacity-50 cursor-pointer"
              title="Reset graph state and reload synthetic baseline"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Reset</span>
            </button>

            {/* Enterprise User Profile Chip */}
            <div className="hidden xl:flex items-center space-x-2 pl-2 border-l border-[#1b253b]">
              <div className="w-7 h-7 rounded-full bg-sky-600/20 border border-sky-500/40 flex items-center justify-center text-[11px] font-bold text-sky-300">
                AV
              </div>
              <div className="text-left text-[11px] leading-tight">
                <div className="font-semibold text-slate-200">Alex Vance</div>
                <div className="text-[10px] text-slate-400 font-mono">Okta SSO</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-[#141d30]">
        <nav className="flex space-x-1 overflow-x-auto py-1.5 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                  active
                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#101728]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${active ? 'text-sky-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
