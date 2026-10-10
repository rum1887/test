import React, { useState } from 'react';
import {
  Compass,
  Shield,
  Layers,
  RotateCcw,
  ShieldCheck,
  Building,
  Zap,
  Code2,
  Server,
  Network,
  Activity,
  CheckCircle2,
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
    { id: 'trust-store', label: 'Trust Store & Living Graph', icon: Layers, featured: true },
    { id: 'ai-firewall', label: 'AI Firewall (Runtime Interceptor)', icon: Shield, featured: true },
    { id: 'story', label: 'Story Walkthrough', icon: Compass },
    { id: 'graph', label: 'Raw Cytoscape Graph', icon: Network },
    { id: 'containment', label: 'Lateral Containment', icon: Zap },
    { id: 'compliance', label: 'Compliance Audit', icon: ShieldCheck },
  ];

  return (
    <header className="bg-[#faf7f0] border-b border-[#ded7c8] sticky top-0 z-50 shadow-2xs">
      {/* Top Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Left: Brand Identity */}
          <div className="flex items-center space-x-3 shrink-0">
            <div className="w-9 h-9 rounded-xl bg-stone-900 text-stone-100 flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-5 h-5 text-stone-100" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-base tracking-tight text-stone-900">
                  Runtime Trust Layer
                </span>
                <span className="text-[10px] font-mono uppercase bg-[#ede7da] text-stone-800 px-1.5 py-0.5 rounded font-semibold border border-[#ded7c8]">
                  CONTROL PLANE
                </span>
              </div>
              <div className="flex items-center space-x-1.5 text-[11px] text-stone-600 mt-0.5">
                <Building className="w-3 h-3 text-stone-500" />
                <span className="text-stone-800 font-medium">Acme Corp</span>
                <span className="text-stone-400">&bull;</span>
                <span className="font-mono text-stone-600">aws-eks-production [us-east-1]</span>
              </div>
            </div>
          </div>

          {/* Center: Live Enforcement Badge */}
          <div className="hidden lg:flex items-center space-x-2.5 bg-[#f5f0e8] border border-[#ded7c8] rounded-lg px-3.5 py-1.5 text-xs shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-stone-600 font-medium">Active Fleet:</span>
            <span className="text-stone-900 font-semibold">Orbit (:3001)</span>
            <span className="text-stone-400">&bull;</span>
            <span className="text-stone-800 font-mono text-[11px]">Nexus (:3002)</span>
            <span className="text-stone-400">&bull;</span>
            <span className="text-stone-800 font-mono text-[11px]">MCP (:8443)</span>
          </div>

          {/* Right: Status, Reset, User Profile */}
          <div className="flex items-center space-x-3 shrink-0">
            {/* Status Indicator */}
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-[#f5f0e8] border border-[#ded7c8] text-xs shadow-2xs">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-stone-800 font-mono text-[11px]">FalkorDB Online</span>
            </div>

            {/* Reset Button */}
            <button
              onClick={handleResetClick}
              disabled={resetting}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-[#f5f0e8] hover:bg-[#ede7da] border border-[#ded7c8] text-stone-800 hover:text-stone-900 text-xs font-medium transition disabled:opacity-50 cursor-pointer shadow-2xs"
              title="Reset graph baseline state"
            >
              <RotateCcw className={`w-3.5 h-3.5 text-stone-600 ${resetting ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Reset Baseline</span>
            </button>

            {/* User Avatar */}
            <div className="flex items-center space-x-2 pl-2 border-l border-[#ded7c8]">
              <div className="w-7 h-7 rounded-full bg-[#ede7da] border border-[#ded7c8] flex items-center justify-center text-[11px] font-bold text-stone-800">
                AH
              </div>
              <div className="hidden md:block text-left text-[11px] leading-tight">
                <div className="font-semibold text-stone-800">Alice Henderson</div>
                <div className="text-[10px] text-stone-500 font-mono">SecOps Director</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-[#ded7c8]">
        <nav className="flex space-x-1.5 py-2 overflow-x-auto no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              currentTab === item.id ||
              (item.id === 'control-plane' && currentTab === 'connected-services') ||
              (item.id === 'data-plane' && currentTab === 'policies');

            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                  active
                    ? 'bg-stone-900 text-white shadow-sm'
                    : item.featured
                    ? 'bg-[#ede7da] hover:bg-[#e4dcce] text-stone-900 border border-[#ded7c8] font-semibold'
                    : 'text-stone-700 hover:text-stone-900 hover:bg-[#ede7da] border border-transparent'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${active ? 'text-white' : 'text-stone-600'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
