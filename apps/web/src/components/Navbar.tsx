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
  const isHealthy = health?.status === 'HEALTHY';
  const isStale = health?.sensor?.is_stale ?? false;

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Shield },
    { id: 'graph', label: 'Trust Graph', icon: Layers },
    { id: 'workloads', label: 'Workloads', icon: Cpu },
    { id: 'agents', label: 'Agent Trust', icon: Activity },
    { id: 'blast-radius', label: 'Blast Radius', icon: GitBranch },
    { id: 'events', label: 'Runtime Events', icon: Terminal },
    { id: 'policies', label: 'Policy Engine', icon: Lock },
    { id: 'containment', label: 'Containment', icon: AlertTriangle },
  ];

  return (
    <header className="bg-[#0a0f1d] border-b border-[#1b253b] sticky top-0 z-50">
      {/* Top Banner Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-inner">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">Runtime Trust Layer</span>
                <span className="text-[10px] font-mono uppercase bg-sky-950 text-sky-300 border border-sky-800 px-1.5 py-0.5 rounded">
                  FalkorDB Graph Native
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Kubernetes & AI-Agent Security Control Plane
              </p>
            </div>
          </div>

          {/* Center Status Indicators */}
          <div className="hidden md:flex items-center space-x-3">
            {/* FalkorDB Status */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#101728] border border-[#1e2a44] text-xs">
              <Database className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-400">FalkorDB:</span>
              <span className={`font-mono font-medium ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
                {isHealthy ? 'ONLINE' : 'DEGRADED'}
              </span>
            </div>

            {/* Sensor Telemetry Mode */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#101728] border border-[#1e2a44] text-xs">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse-live' : 'bg-amber-400'}`} />
              <span className="text-slate-400">Sensor:</span>
              <span className="font-mono font-semibold text-slate-200">
                {isLive ? 'LIVE eBPF' : 'REPLAY MODE'}
              </span>
              {isStale && (
                <span className="text-[10px] font-mono bg-amber-950 text-amber-300 border border-amber-800 px-1 rounded">
                  STALE
                </span>
              )}
            </div>

            {/* Replay stream trigger button */}
            <button
              onClick={onTriggerReplay}
              title="Inject synthetic telemetry event stream"
              className="flex items-center space-x-1 px-2.5 py-1 rounded-md bg-sky-950 hover:bg-sky-900 border border-sky-800/80 text-sky-300 text-xs font-medium transition cursor-pointer"
            >
              <Play className="w-3 h-3 fill-sky-400" />
              <span>Inject Event</span>
            </button>
          </div>

          {/* Right Action Controls: Scenario Selector & Reset */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 text-xs">
              <label htmlFor="scenario-select" className="text-slate-400 hidden lg:inline">Scenario:</label>
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

            <button
              onClick={handleResetClick}
              disabled={resetting}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800/60 text-rose-300 text-xs font-medium transition disabled:opacity-50 cursor-pointer"
              title="Reset graph state and reload synthetic baseline"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
              <span>Reset</span>
            </button>
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
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition cursor-pointer ${
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
