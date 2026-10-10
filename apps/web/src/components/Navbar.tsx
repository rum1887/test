import React, { useState } from 'react';
import {
  Shield,
  Layers,
  RotateCcw,
  ShieldCheck,
  Building,
  Play,
  FileText,
  SlidersHorizontal,
} from 'lucide-react';
import { HealthResponse } from '../api/client';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  currentScenario: string;
  onSelectScenario: (scenarioKey: string) => void;
  health: HealthResponse | null;
  onReset: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  currentScenario,
  onSelectScenario,
  health,
  onReset,
}) => {
  const [resetting, setResetting] = useState(false);

  const handleResetClick = async () => {
    setResetting(true);
    await onReset();
    setTimeout(() => setResetting(false), 600);
  };

  const isHealthy = health?.database?.healthy ?? true;

  const navItems = [
    { id: 'overview', label: 'Interactive Scenario Story', icon: Play },
    { id: 'graph', label: 'Security Trust Graph', icon: Layers },
    { id: 'containment', label: 'Containment & Remediation', icon: Shield },
    { id: 'compliance', label: 'CISO Compliance & Audit', icon: ShieldCheck },
  ];

  return (
    <header className="bg-[#090e1c] border-b border-[#18233c] sticky top-0 z-50">
      {/* Top Clean Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Left: Brand Identity */}
          <div className="flex items-center space-x-3 shrink-0">
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-sm">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-white">Runtime Trust Layer</span>
                <span className="text-[10px] font-mono uppercase bg-sky-950 text-sky-300 border border-sky-800 px-1.5 py-0.5 rounded font-semibold">
                  CONTROL PLANE
                </span>
              </div>
              <div className="flex items-center space-x-1.5 text-[11px] text-slate-400 mt-0.5">
                <Building className="w-3 h-3 text-slate-500" />
                <span className="text-slate-300 font-medium">Acme Corp</span>
                <span className="text-slate-500">&bull;</span>
                <span className="font-mono text-sky-400">aws-eks-production [us-east-1]</span>
              </div>
            </div>
          </div>

          {/* Center: Practice & Demo Scenario Selector */}
          <div className="flex items-center space-x-2 bg-[#0e162a] border border-[#1e2c4a] rounded-lg px-3 py-1.5 text-xs shadow-inner">
            <SlidersHorizontal className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span className="text-slate-400 font-medium hidden sm:inline">Active Demo Scenario:</span>
            <select
              value={currentScenario}
              onChange={(e) => onSelectScenario(e.target.value)}
              className="bg-transparent text-white font-semibold text-xs focus:outline-none cursor-pointer pr-1"
            >
              <option value="B" className="bg-[#0d1322] text-slate-100">
                Scenario B: Rogue AI Agent Unauthorized Tool Call (Pitch Demo)
              </option>
              <option value="A" className="bg-[#0d1322] text-slate-100">
                Scenario A: Kubernetes Pod Breach & eBPF Shell Interception
              </option>
              <option value="C" className="bg-[#0d1322] text-slate-100">
                Scenario C: Multi-Vector Graph Convergence on AWS Root Secrets
              </option>
              <option value="ALL" className="bg-[#0d1322] text-slate-100">
                All Scenarios (Full Infrastructure View)
              </option>
            </select>
          </div>

          {/* Right: Status, Reset, User Profile */}
          <div className="flex items-center space-x-3 shrink-0">
            {/* Connection Status Indicator */}
            <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#10192e] border border-[#1b2a47] text-xs">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="text-slate-300 font-mono text-[11px]">FalkorDB Online</span>
            </div>

            {/* Reset Scenario Button */}
            <button
              onClick={handleResetClick}
              disabled={resetting}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-[#151f33] hover:bg-[#1d2b47] border border-[#233557] text-slate-300 hover:text-white text-xs font-medium transition disabled:opacity-50 cursor-pointer"
              title="Reset scenario state"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Reset</span>
            </button>

            {/* User Avatar */}
            <div className="flex items-center space-x-2 pl-2 border-l border-[#1b253b]">
              <div className="w-7 h-7 rounded-full bg-sky-600/20 border border-sky-500/40 flex items-center justify-center text-[11px] font-bold text-sky-300">
                AV
              </div>
              <div className="hidden lg:block text-left text-[11px] leading-tight">
                <div className="font-semibold text-slate-200">Alex Vance</div>
                <div className="text-[10px] text-slate-400 font-mono">Okta SSO</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-[#141e33]">
        <nav className="flex space-x-2 py-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                  active
                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#10192e]'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
