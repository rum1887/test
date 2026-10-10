import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Server,
  Cpu,
  Database,
  ExternalLink,
  RotateCcw,
  RefreshCw,
  Terminal,
  Lock,
  Layers,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Zap,
  Globe,
  Radio,
  Clock,
  ArrowRight,
  Share2,
  Network,
  Activity,
  Flame,
} from 'lucide-react';
import {
  api,
  GatewayGuardStateResponse,
  ConnectedServicesResponse,
  ConnectedServiceItem,
  RecentGatewayDecisionsResponse,
  BlastRadiusStatusResponse,
} from '../api/client';

export const ConnectedServicesView: React.FC = () => {
  const [guardState, setGuardState] = useState<GatewayGuardStateResponse | null>(null);
  const [fleetData, setFleetData] = useState<ConnectedServicesResponse | null>(null);
  const [decisions, setDecisions] = useState<RecentGatewayDecisionsResponse | null>(null);
  const [blastStatus, setBlastStatus] = useState<BlastRadiusStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [toggling, setToggling] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [contaminating, setContaminating] = useState<boolean>(false);
  const [testingNexus, setTestingNexus] = useState<boolean>(false);
  const [nexusTestResult, setNexusTestResult] = useState<any | null>(null);
  const [regUrl, setRegUrl] = useState<string>('http://localhost:8443');
  const [registering, setRegistering] = useState<boolean>(false);
  const [regResult, setRegResult] = useState<any | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 5000);
    return () => clearInterval(interval);
  }, []);

  const notify = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  const loadAllData = async () => {
    try {
      const [g, f, d, b] = await Promise.all([
        api.getGatewayGuardState(),
        api.getConnectedServices(),
        api.getRecentGatewayDecisions(10),
        api.getBlastRadiusStatus(),
      ]);
      setGuardState(g);
      setFleetData(f);
      setDecisions(d);
      setBlastStatus(b);
    } catch (e) {
      console.error('Failed to load connected services data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleGuard = async () => {
    setToggling(true);
    try {
      const res = await api.toggleGatewayGuard();
      await loadAllData();
      notify(`Runtime Security Guard switched to ${res.mode} mode.`);
    } catch (e) {
      console.error(e);
      notify('Failed to toggle central guard mode.');
    } finally {
      setToggling(false);
    }
  };

  const handleContaminateOrbit = async () => {
    setContaminating(true);
    try {
      await api.contaminateOrbit();
      await loadAllData();
      notify('Orbit Agent marked contaminated. Blast-radius containment rules active.');
    } catch (e) {
      console.error(e);
      notify('Failed to update Orbit contamination state.');
    } finally {
      setContaminating(false);
    }
  };

  const handleTestNexus = async () => {
    setTestingNexus(true);
    try {
      const res = await api.testNexusSettlement();
      setNexusTestResult(res);
      await loadAllData();
      if (res.blocked) {
        notify('Lateral movement blocked: Nexus settlement intercepted by policy gateway.');
      } else {
        notify('Nexus settlement payout executed on clean ledger.');
      }
    } catch (e) {
      console.error(e);
      notify('Failed to test Nexus settlement.');
    } finally {
      setTestingNexus(false);
    }
  };

  const handleResetQuarantine = async () => {
    setResetting(true);
    try {
      await api.resetGatewayQuarantine();
      setNexusTestResult(null);
      await loadAllData();
      notify('Quarantine cleared across all agent sessions and shared infrastructure.');
    } catch (e) {
      console.error(e);
      notify('Failed to reset quarantine.');
    } finally {
      setResetting(false);
    }
  };

  const handleRegisterService = async (targetUrl?: string) => {
    const urlToUse = targetUrl || regUrl;
    if (!urlToUse) return;
    setRegistering(true);
    try {
      const res = await api.registerLiveService(urlToUse);
      setRegResult(res);
      await loadAllData();
      notify(`Service registered: ${res.service_name} (${res.protocol_detected})`);
    } catch (e) {
      console.error(e);
      notify('Failed to register live service.');
    } finally {
      setRegistering(false);
    }
  };

  const isEnforcing = guardState?.guard_enabled ?? true;
  const isOrbitContaminated = blastStatus?.orbit_agent?.status === 'CONTAMINATED';
  const isSharedDbQuarantined = blastStatus?.shared_infrastructure?.status === 'QUARANTINED_BY_BLAST_RADIUS';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 font-sans">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d162a] border border-sky-500/80 text-sky-200 text-xs px-4 py-2.5 rounded-xl shadow-2xl flex items-center space-x-2 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
          <span>{notification}</span>
        </div>
      )}

      {/* Hero Control Bar: Central Runtime Security Guard Control */}
      <div className={`rounded-2xl p-6 border shadow-sm transition-all ${
        isEnforcing
          ? 'bg-white border-[#e8e5de]'
          : 'bg-rose-50/70 border-rose-200'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg shadow-sm ${
                isEnforcing ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-100 text-rose-800 border border-rose-200'
              }`}>
                {isEnforcing ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6 animate-pulse" />}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl font-bold text-stone-900 tracking-tight">Connected Fleet & Runtime Guard Hub</h1>
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-bold flex items-center space-x-1 border ${
                    isEnforcing
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-rose-50 text-rose-800 border-rose-200 animate-pulse'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isEnforcing ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                    <span>{isEnforcing ? 'ACTIVE ENFORCEMENT' : 'BYPASS / OBSERVATION'}</span>
                  </span>
                </div>
                <p className="text-xs text-stone-500">
                  SecOps Central Governance: Controls real-time pre-execution policy enforcement across all connected AI agents and MCP servers.
                </p>
              </div>
            </div>
          </div>

          {/* Central Guard Controls */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleToggleGuard}
              disabled={toggling}
              className={`px-4 py-2.5 rounded-xl font-bold text-xs transition cursor-pointer flex items-center space-x-2 shadow-sm disabled:opacity-50 ${
                isEnforcing
                  ? 'bg-stone-900 hover:bg-stone-800 text-white'
                  : 'bg-rose-600 hover:bg-rose-500 text-white'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>{isEnforcing ? 'Enforcement Mode: ON (Protected)' : 'Enforcement Mode: OFF (Bypassed)'}</span>
            </button>

            <button
              onClick={handleResetQuarantine}
              disabled={resetting}
              className="px-3.5 py-2.5 rounded-xl bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer disabled:opacity-50 shadow-sm"
              title="Clear active threat containment and session lockouts"
            >
              <RotateCcw className={`w-3.5 h-3.5 text-stone-500 ${resetting ? 'animate-spin' : ''}`} />
              <span>Reset Quarantine</span>
            </button>

            <a
              href="http://localhost:3001"
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 border border-stone-300 text-stone-800 text-xs font-semibold flex items-center space-x-1.5 transition"
            >
              <span>Orbit AI (:3001)</span>
              <ExternalLink className="w-3.5 h-3.5 text-stone-500" />
            </a>

            <a
              href="http://localhost:3002"
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 border border-stone-300 text-stone-800 text-xs font-semibold flex items-center space-x-1.5 transition"
            >
              <span>Nexus FinOps (:3002)</span>
              <ExternalLink className="w-3.5 h-3.5 text-stone-500" />
            </a>
          </div>
        </div>

        {/* Status Sub-bar */}
        <div className="mt-4 pt-3.5 border-t border-stone-100 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center space-x-6 text-[11px] font-mono text-stone-500">
            <div>
              Gateway SLA: <span className="text-emerald-700 font-semibold">&lt; 15 ms deterministic</span>
            </div>
            <div>
              Enforcement Boundary: <span className="text-stone-800 font-semibold">ep-mcp-gateway-01</span>
            </div>
            <div>
              Quarantine State: <span className={guardState?.is_quarantined ? 'text-amber-800 font-bold' : 'text-emerald-700 font-bold'}>
                {guardState?.is_quarantined ? 'QUARANTINED (Threat Active)' : 'CLEAN (No Lockouts)'}
              </span>
            </div>
          </div>
          <div className="text-[11px] text-stone-500">
            {isEnforcing
              ? 'Active enforcement: all tool calls from connected agents are intercepted and evaluated against the security graph before execution.'
              : 'Observation mode active: tool calls execute directly against destination servers for passive auditing.'}
          </div>
        </div>
      </div>

      {/* Studio: Live URL Registration & Dynamic Auto-Discovery */}
      <div className="bg-[#faf8f5] border border-[#e8e4dc] rounded-2xl p-6 shadow-sm space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#ece8de] pb-4">
          <div>
            <div className="flex items-center space-x-2.5">
              <Globe className="w-5 h-5 text-stone-700" />
              <h2 className="text-base font-bold text-stone-900 tracking-tight">
                Live URL Auto-Discovery & Zero-Touch Graph Registration
              </h2>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Provide any live endpoint URL (MCP Server, Google ADK Multi-Agent, or REST API). The platform probes it, detects the protocol, extracts all tools and privileges, and maps it dynamically into FalkorDB.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg bg-stone-200 text-stone-700 border border-stone-300">
              LIVE DYNAMIC INGESTION
            </span>
          </div>
        </div>

        {/* URL Input Form with Quick Preset Buttons */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
            <div className="relative flex-1">
              <input
                type="text"
                value={regUrl}
                onChange={(e) => setRegUrl(e.target.value)}
                placeholder="Enter live service URL (e.g. http://localhost:8443 or http://localhost:3002)"
                className="w-full bg-white border border-[#dcd7cb] focus:border-stone-500 rounded-xl px-4 py-2.5 text-xs text-stone-800 font-mono focus:outline-none placeholder-stone-400 shadow-sm"
              />
            </div>
            <button
              onClick={() => handleRegisterService()}
              disabled={registering || !regUrl.trim()}
              className="px-5 py-2.5 rounded-xl bg-stone-900 hover:bg-stone-800 text-white font-semibold text-xs flex items-center justify-center space-x-2 shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${registering ? 'animate-spin' : ''}`} />
              <span>{registering ? 'Probing & Registering...' : 'Auto-Discover & Register Live'}</span>
            </button>
          </div>

          {/* Quick Preset Chips */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-[11px] text-stone-500 font-mono font-semibold">Live Presets:</span>
            <button
              onClick={() => { setRegUrl('http://localhost:8443'); handleRegisterService('http://localhost:8443'); }}
              disabled={registering}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 text-[11px] font-mono flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
            >
              <span>Live MCP Server (:8443)</span>
            </button>
            <button
              onClick={() => { setRegUrl('http://localhost:3002'); handleRegisterService('http://localhost:3002'); }}
              disabled={registering}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 text-[11px] font-mono flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
            >
              <span>Nexus FinOps Agent (:3002)</span>
            </button>
            <button
              onClick={() => { setRegUrl('http://localhost:3001'); handleRegisterService('http://localhost:3001'); }}
              disabled={registering}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 text-[11px] font-mono flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
            >
              <span>Orbit Support Agent (:3001)</span>
            </button>
          </div>
        </div>

        {/* Live Registration Result Card */}
        {regResult && (
          <div className="bg-white border border-[#e8e4dc] rounded-xl p-4 space-y-3 shadow-sm text-xs font-mono">
            <div className="flex items-center justify-between border-b border-stone-100 pb-2.5">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span className="font-bold text-stone-900 uppercase text-[11px] tracking-wider">
                  Live Registration Successful: {regResult.service_name}
                </span>
              </div>
              <div className="flex items-center space-x-3 text-[10px]">
                <span className="bg-stone-100 text-stone-700 border border-stone-200 px-2 py-0.5 rounded font-bold">
                  {regResult.protocol_detected}
                </span>
                <span className="text-emerald-700 font-bold">
                  {regResult.registration_latency_ms} ms SLA
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
              <div className="bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df] space-y-1">
                <div className="text-stone-500 text-[10px] uppercase font-bold">Target URL:</div>
                <div className="text-stone-800 font-medium truncate">{regResult.service_url}</div>
                <div className="text-stone-400 text-[10px]">Probe: {regResult.probe_url_resolved}</div>
              </div>

              <div className="bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df] space-y-1">
                <div className="text-stone-500 text-[10px] uppercase font-bold">Discovered Tools & Actions:</div>
                <div className="text-emerald-700 font-bold">{regResult.discovered_tools_count} Tools Cataloged</div>
                <div className="text-stone-500 text-[10px] truncate">Auto-classified with risk boundaries</div>
              </div>

              <div className="bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df] space-y-1">
                <div className="text-stone-500 text-[10px] uppercase font-bold">FalkorDB Graph Sync:</div>
                <div className="text-purple-700 font-bold">{regResult.graph_nodes_merged} Nodes/Edges Merged</div>
                <div className="text-stone-500 text-[10px]">Linked to: {regResult.linked_infrastructure?.join(', ')}</div>
              </div>
            </div>

            {/* Discovered Tools Chips */}
            {regResult.tools_and_actions && regResult.tools_and_actions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-stone-100 space-y-1.5">
                <div className="text-[10px] text-stone-500 uppercase font-bold">Cataloged Tools & Risk Classification:</div>
                <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
                  {regResult.tools_and_actions.map((t: any, idx: number) => {
                    const isCrit = t.risk_level === 'CRITICAL';
                    const isHigh = t.risk_level === 'HIGH';
                    return (
                      <span
                        key={idx}
                        className={`text-[10px] px-2 py-0.5 rounded border font-mono flex items-center space-x-1.5 ${
                          isCrit
                            ? 'bg-rose-50 text-rose-800 border-rose-200'
                            : isHigh
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-stone-100 text-stone-700 border-stone-200'
                        }`}
                      >
                        <span className="font-bold">{t.name}</span>
                        <span className="text-[9px] opacity-75">({t.risk_level})</span>
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Multi-Agent Shared Infrastructure & Blast-Radius Lateral Containment */}
      <div className={`border rounded-2xl p-6 shadow-sm space-y-6 transition-all ${
        isOrbitContaminated
          ? 'bg-rose-50/60 border-rose-200'
          : 'bg-white border-[#e8e5de]'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#ece8de] pb-4">
          <div>
            <div className="flex items-center space-x-2.5">
              <Share2 className={`w-5 h-5 ${isOrbitContaminated ? 'text-rose-600' : 'text-stone-700'}`} />
              <h2 className="text-base font-bold text-stone-900 tracking-tight">
                Multi-Agent Shared Infrastructure & Blast-Radius Lateral Containment
              </h2>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Live simulation of lateral contamination spread across multi-agent systems sharing corporate data stores (<code className="text-stone-800 font-mono">sr-financial-db</code>).
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`text-[11px] font-mono font-bold px-3 py-1 rounded-lg border flex items-center space-x-1.5 ${
              isOrbitContaminated
                ? 'bg-rose-50 text-rose-800 border-rose-200 animate-pulse'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isOrbitContaminated ? 'bg-rose-500' : 'bg-emerald-500'}`} />
              <span>{isOrbitContaminated ? 'LATERAL CONTAINMENT ACTIVE' : 'MULTI-AGENT FLEET SECURE'}</span>
            </span>
          </div>
        </div>

        {/* 1-Click Interactive Demonstration Controls */}
        <div className="bg-[#faf8f5] border border-[#e8e4dc] rounded-xl p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-bold text-stone-900 uppercase tracking-wider">
                Lateral Contamination Verification Suite
              </span>
            </div>
            <div className="text-[11px] text-stone-500 font-mono">
              Deterministic Graph Rule: <span className="text-stone-800 font-bold">POL_BLAST_RADIUS_SHARED_CONTAINMENT</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Step 1 Button: Contaminate Orbit */}
            <button
              onClick={handleContaminateOrbit}
              disabled={contaminating}
              className={`p-3 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between space-y-2 ${
                isOrbitContaminated
                  ? 'bg-rose-100 border-rose-300 text-rose-950'
                  : 'bg-white hover:bg-stone-50 border-stone-200 text-stone-800 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase font-bold text-rose-700">Step 1 • Attack Vector</span>
                <Flame className={`w-4 h-4 ${isOrbitContaminated ? 'text-rose-600' : 'text-stone-400'}`} />
              </div>
              <div>
                <div className="text-xs font-bold">
                  {contaminating ? 'Simulating Compromise...' : isOrbitContaminated ? 'Orbit Agent Compromised' : 'Simulate Upstream Compromise (:3001)'}
                </div>
                <p className="text-[10px] text-stone-500 mt-0.5">
                  Flags session context with lateral threat indicator.
                </p>
              </div>
            </button>

            {/* Step 2 Button: Test Nexus Access */}
            <button
              onClick={handleTestNexus}
              disabled={testingNexus}
              className={`p-3 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between space-y-2 ${
                isOrbitContaminated
                  ? 'bg-white hover:bg-stone-50 border-stone-400 text-stone-900 ring-2 ring-stone-300 shadow-sm'
                  : 'bg-white hover:bg-stone-50 border-stone-200 text-stone-800 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase font-bold text-stone-700">Step 2 • Lateral Movement</span>
                <Activity className={`w-4 h-4 ${testingNexus ? 'animate-spin text-stone-700' : 'text-stone-400'}`} />
              </div>
              <div>
                <div className="text-xs font-bold">
                  {testingNexus ? 'Evaluating Gateway...' : 'Execute Downstream Settlement (:3002)'}
                </div>
                <p className="text-[10px] text-stone-500 mt-0.5">
                  Nexus requests $125k disbursement on shared financial ledger.
                </p>
              </div>
            </button>

            {/* Step 3 Button: Reset Quarantine */}
            <button
              onClick={handleResetQuarantine}
              disabled={resetting}
              className="p-3 rounded-xl border border-stone-200 bg-white hover:bg-stone-50 text-stone-800 text-left transition cursor-pointer flex flex-col justify-between space-y-2 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase font-bold text-emerald-700">Step 3 • Remediation</span>
                <RotateCcw className={`w-4 h-4 ${resetting ? 'animate-spin text-emerald-600' : 'text-stone-400'}`} />
              </div>
              <div>
                <div className="text-xs font-bold">
                  {resetting ? 'Resetting Fleet...' : 'Clear Quarantine & Restore Baseline'}
                </div>
                <p className="text-[10px] text-stone-500 mt-0.5">
                  Clears session threat events; unlocks shared database across all agents.
                </p>
              </div>
            </button>
          </div>
        </div>

        {/* Visual Graph Diagram: Multi-Agent Fleet Sharing Financial Infrastructure */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-center">
          {/* Node 1: Orbit Customer Support Agent */}
          <div className={`p-4 rounded-xl border transition shadow-sm space-y-2.5 ${
            isOrbitContaminated
              ? 'bg-rose-100/70 border-rose-300 text-rose-950'
              : 'bg-[#faf8f5] border-[#ede9df] text-stone-800'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-stone-200 flex items-center justify-center font-bold text-xs text-stone-700">
                  ✦
                </div>
                <div>
                  <h4 className="text-xs font-bold text-stone-900">Orbit AI Agent</h4>
                  <p className="text-[10px] font-mono text-stone-500">Port 3001 • Google ADK</p>
                </div>
              </div>
              <span className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold ${
                isOrbitContaminated
                  ? 'bg-rose-200 text-rose-900 border border-rose-300'
                  : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
              }`}>
                {isOrbitContaminated ? 'CONTAMINATED' : 'HEALTHY'}
              </span>
            </div>
            <div className="text-[11px] font-mono space-y-1 bg-white p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-500">Session ID:</span><span className="text-stone-800">session-alice-dev-01</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Principal:</span><span className="text-stone-800">Alice Smith (Customer Support)</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Active Threats:</span><span className={isOrbitContaminated ? 'text-rose-700 font-bold' : 'text-emerald-700'}>{blastStatus?.orbit_agent?.active_threats_count ?? 0}</span></div>
            </div>
            <div className="text-[10px] text-stone-500 flex items-center justify-between">
              <span>Upstream vector</span>
              <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="text-stone-800 hover:underline flex items-center space-x-1">
                <span>Inspect Agent</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>

          {/* Center Node: Shared Infrastructure (sr-financial-db) */}
          <div className={`p-4 rounded-xl border transition shadow-sm space-y-2.5 ${
            isSharedDbQuarantined
              ? 'bg-amber-100/70 border-amber-300 text-amber-950'
              : 'bg-[#faf8f5] border-[#ede9df] text-stone-800'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-stone-200 flex items-center justify-center font-bold text-xs text-stone-700">
                  <Database className="w-4 h-4 text-stone-600" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-stone-900">Shared Financial Ledger</h4>
                  <p className="text-[10px] font-mono text-stone-500">sr-financial-db • Core SQLite</p>
                </div>
              </div>
              <span className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold ${
                isSharedDbQuarantined
                  ? 'bg-amber-200 text-amber-900 border border-amber-300'
                  : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
              }`}>
                {isSharedDbQuarantined ? 'ISOLATED BY BLAST RADIUS' : 'SHARED ACTIVE'}
              </span>
            </div>
            <div className="text-[11px] font-mono space-y-1 bg-white p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-500">Shared By:</span><span className="text-stone-800">Orbit (:3001) + Nexus (:3002)</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Policy Guard:</span><span className="text-stone-800">POL_BLAST_RADIUS_SHARED_CONTAINMENT</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Access Mode:</span><span className={isSharedDbQuarantined ? 'text-amber-800 font-bold' : 'text-emerald-700'}>{isSharedDbQuarantined ? 'SUSPENDED (Zero Writes)' : 'NORMAL_DELEGATED'}</span></div>
            </div>
            <div className="text-[10px] text-stone-500">
              {isSharedDbQuarantined
                ? 'Ledger mutations suspended to prevent lateral spread from contaminated agent session.'
                : 'Clean baseline state. Payouts and balance queries authorized under active delegation grant.'}
            </div>
          </div>

          {/* Node 2: Nexus Settlement Multi-Agent */}
          <div className="p-4 rounded-xl border transition shadow-sm space-y-2.5 bg-[#faf8f5] border-[#ede9df] text-stone-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-stone-200 flex items-center justify-center font-bold text-xs text-stone-700">
                  <ShieldCheck className="w-4 h-4 text-stone-600" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-stone-900">Nexus Settlement Agent</h4>
                  <p className="text-[10px] font-mono text-stone-500">Port 3002 • Google ADK</p>
                </div>
              </div>
              <span className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold ${
                isOrbitContaminated
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-stone-100 text-stone-700 border border-stone-200'
              }`}>
                {isOrbitContaminated ? 'PROTECTED (ISOLATED)' : 'OPERATIONAL'}
              </span>
            </div>
            <div className="text-[11px] font-mono space-y-1 bg-white p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-500">Session ID:</span><span className="text-stone-800">session-nexus-settlement-01</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Principal:</span><span className="text-stone-800">Marcus Vance (Treasury Director)</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Sub-Agent:</span><span className="text-stone-800">TreasuryDisbursementAgent</span></div>
            </div>
            <div className="text-[10px] text-stone-500 flex items-center justify-between">
              <span>Downstream target</span>
              <a href="http://localhost:3002" target="_blank" rel="noreferrer" className="text-stone-800 hover:underline flex items-center space-x-1">
                <span>Inspect Agent</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Live Test Results Inspector (Interactive Real-Time Feedback) */}
        {nexusTestResult && (
          <div className="bg-[#faf8f5] border border-[#ede9df] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-stone-200 pb-2.5">
              <div className="flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-stone-700" />
                <span className="text-xs font-bold text-stone-900 uppercase tracking-wider">
                  Live MCP Gateway Interception Result (Nexus Settlement Execution)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  nexusTestResult.blocked
                    ? 'bg-rose-50 text-rose-800 border-rose-200'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}>
                  HTTP {nexusTestResult.status_code} • {nexusTestResult.blocked ? 'LATERAL SPREAD BLOCKED' : 'EXECUTED'}
                </span>
                <span className="text-[10px] font-mono text-emerald-700 font-semibold">
                  {nexusTestResult.gateway_latency_ms?.toFixed(2) ?? '19.20'} ms deterministic
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="bg-white p-3 rounded-lg border border-[#ede9df] space-y-1.5">
                <div className="text-stone-500 text-[10px] uppercase font-bold">Requested Operation:</div>
                <div className="text-stone-900 font-bold">{nexusTestResult.tool_called || 'process_settlement_payout'}</div>
                <div className="text-stone-600 text-[11px]">{nexusTestResult.message}</div>
                <div className="text-[10px] text-stone-500 mt-2">
                  Multi-Agent Chain: {nexusTestResult.multi_agent?.delegation_chain?.join(' ➔ ') || 'NexusSettlementOrchestrator ➔ TreasuryDisbursementAgent'}
                </div>
              </div>

              <div className={`p-3 rounded-lg border space-y-1.5 ${
                nexusTestResult.blocked
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-900'
              }`}>
                <div className="text-[10px] uppercase font-bold text-stone-700">Policy Gateway Enforcement:</div>
                <div className="text-[11px] leading-relaxed">
                  {nexusTestResult.decision_rationale}
                </div>
                <div className="text-[10px] font-bold mt-2">
                  {nexusTestResult.blocked
                    ? 'Blast-radius containment enforced: zero mutations permitted on shared database.'
                    : 'Execution verified: financial ledger updated safely.'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Fleet Topology Grid: 6 Core Live Architecture Components */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-stone-600" />
            <h2 className="text-xs font-bold text-stone-700 uppercase tracking-wider">Connected Services & Infrastructure Fleet</h2>
          </div>
          <span className="text-[10px] font-mono bg-[#f4f1ea] text-stone-700 border border-[#e2ded5] px-2.5 py-0.5 rounded-full font-semibold">
            6 ACTIVE SERVICES
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Service 1: Orbit Customer Support Agent (Google ADK Multi-Agent) */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-purple-300 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700 font-bold text-sm">
                  ✦
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Orbit Multi-Agent System</h3>
                  <p className="text-[10px] text-purple-700 font-mono font-medium">Google ADK v2.11 Framework</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE :3001
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Framework:</span><span className="text-purple-700 font-semibold">Google ADK v2.11</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Root Agent:</span><span className="text-stone-800">OrbitTriageOrchestrator</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Sub-Agents:</span><span className="text-stone-800">BillingOps, Compliance, Admin</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Local LLM:</span><span className="text-stone-800">Ollama qwen3:4b (GPU)</span></div>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1">
              <span className="text-stone-500 text-[10px]">Guard: {isEnforcing ? 'Enforcing Boundaries' : 'Bypassed'}</span>
              <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="text-stone-700 hover:text-stone-900 font-semibold flex items-center space-x-1 text-[11px]">
                <span>Open Orbit</span>
                <ArrowRight className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Service 2: Nexus Settlement Multi-Agent (Google ADK FinOps) */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-sky-300 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-700 font-bold text-sm">
                  ⚡
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Nexus FinOps Multi-Agent</h3>
                  <p className="text-[10px] text-sky-700 font-mono font-medium">Google ADK v2.11 Framework</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-sky-50 text-sky-700 border border-sky-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE :3002
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Framework:</span><span className="text-sky-700 font-semibold">Google ADK v2.11</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Root Agent:</span><span className="text-stone-800">NexusSettlementOrchestrator</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Sub-Agents:</span><span className="text-stone-800">TreasuryDisbursement, LedgerAudit</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Shared Infra:</span><span className="text-amber-700 font-semibold">sr-financial-db</span></div>
            </div>
            <div className="flex items-center justify-between text-[11px] pt-1">
              <span className="text-stone-500 text-[10px]">Guard: Blast-Radius Protected</span>
              <a href="http://localhost:3002" target="_blank" rel="noreferrer" className="text-stone-700 hover:text-stone-900 font-semibold flex items-center space-x-1 text-[11px]">
                <span>Open Nexus</span>
                <ArrowRight className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Service 3: Live CRM Database MCP Server */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-stone-400 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-700 font-bold text-sm">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Live CRM Database MCP</h3>
                  <p className="text-[10px] text-stone-500 font-mono">Tool Execution Server</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-stone-100 text-stone-700 border border-stone-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE :8443
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Protocol:</span><span className="text-stone-800 font-medium">Model Context Protocol</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Format:</span><span className="text-stone-800">JSON-RPC 2.0</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Transport:</span><span className="text-stone-800">HTTP + SSE (/sse)</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Live Tools:</span><span className="text-emerald-700 font-semibold">5 Registered</span></div>
            </div>
            <div className="text-[10px] text-stone-500 flex items-center space-x-1.5">
              <span>Tools:</span>
              <span className="text-stone-700 font-mono truncate">lookup, transactions, audit, vault, drop</span>
            </div>
          </div>

          {/* Service 4: Production Live SQLite Core Database */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-emerald-300 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-sm">
                  <Database className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Production Core Database</h3>
                  <p className="text-[10px] text-stone-500 font-mono">Protected Data Store</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE (SQL)
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Engine:</span><span className="text-stone-800">SQLite Persistent</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Database:</span><span className="text-stone-800">production_live.db</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Crown Jewels:</span><span className="text-rose-700 font-bold">KMS Vault & PII</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Compliance:</span><span className="text-stone-800 font-medium">SOC2, PCI-DSS, SOX</span></div>
            </div>
            <div className="text-[10px] text-stone-500 flex items-center space-x-1.5">
              <span>Status:</span>
              <span className="text-emerald-700 font-semibold">Zero Unmitigated Mutations Allowed</span>
            </div>
          </div>

          {/* Service 5: Local LLM Engine (Ollama) */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-stone-400 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-700 font-bold text-sm">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Ollama Local LLM Engine</h3>
                  <p className="text-[10px] text-stone-500 font-mono">Autonomous Inference</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-stone-100 text-stone-700 border border-stone-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE :11434
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Host:</span><span className="text-stone-800">localhost:11434</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Loaded Model:</span><span className="text-stone-800 font-semibold">qwen3:4b (GPU)</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Fast Model:</span><span className="text-stone-800">qwen3:0.6b</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Tool Format:</span><span className="text-stone-800">OpenAI / MCP Schemas</span></div>
            </div>
            <div className="text-[10px] text-stone-500">
              Inference runs locally on Apple Silicon GPU without cloud egress.
            </div>
          </div>

          {/* Service 6: FalkorDB Graph Control Plane */}
          <div className="bg-white border border-[#e8e5de] rounded-xl p-4 shadow-sm space-y-3 relative overflow-hidden group hover:border-stone-400 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-700 font-bold text-sm">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">Trust Layer Graph Engine</h3>
                  <p className="text-[10px] text-stone-500 font-mono">FalkorDB v2.5 Control Plane</p>
                </div>
              </div>
              <span className="text-[9px] font-mono bg-stone-100 text-stone-700 border border-stone-200 px-1.5 py-0.5 rounded font-bold">
                ONLINE :6379 / :8000
              </span>
            </div>
            <div className="text-[11px] space-y-1.5 text-stone-700 font-mono bg-[#faf8f5] p-2.5 rounded-lg border border-[#ede9df]">
              <div className="flex justify-between"><span className="text-stone-400">Graph DB:</span><span className="text-stone-800">FalkorDB Engine</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Policy:</span><span className="text-stone-800 font-medium">Cypher Directed Graphs</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Latency:</span><span className="text-emerald-700 font-semibold">&lt; 25 ms deterministic</span></div>
            </div>
            <div className="text-[10px] text-stone-500">
              Evaluates delegations, tool integrity, and runtime threat isolation.
            </div>
          </div>
        </div>
      </div>

      {/* Live Gateway Invocations & Policy Enforcement Feed */}
      <div className="bg-white border border-[#e8e5de] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-stone-600" />
            <h2 className="text-xs font-bold text-stone-700 uppercase tracking-wider">Real-Time Gateway Invocations & Enforcement Stream</h2>
          </div>
          <button
            onClick={loadAllData}
            className="flex items-center space-x-1 text-xs text-stone-500 hover:text-stone-800 transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Feed</span>
          </button>
        </div>

        {decisions && decisions.decisions.length > 0 ? (
          <div className="overflow-x-auto border border-[#f0ede6] rounded-lg">
            <table className="w-full text-left text-xs font-sans">
              <thead>
                <tr className="bg-[#faf8f5] border-b border-[#e8e5de] text-stone-500 font-mono text-[11px]">
                  <th className="py-2.5 px-3">Decision ID</th>
                  <th className="py-2.5 px-3">Action Result</th>
                  <th className="py-2.5 px-3">Enforcement Reason</th>
                  <th className="py-2.5 px-3">Failed Rules</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0ede6] font-mono text-[11px]">
                {decisions.decisions.map((d) => {
                  const isBlocked = d.decision !== 'ALLOW';
                  return (
                    <tr key={d.decision_id} className="hover:bg-[#faf8f5] transition">
                      <td className="py-3 px-3 text-stone-800 font-medium">{d.decision_id}</td>
                      <td className="py-3 px-3">
                        {isBlocked ? (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 text-[10px] font-bold">
                            <XCircle className="w-3 h-3 text-rose-600" />
                            <span>BLOCKED (403)</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>ALLOWED (200)</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-stone-700 max-w-md truncate" title={d.rationale}>
                        {d.rationale}
                      </td>
                      <td className="py-3 px-3">
                        {d.evaluated_rules.length > 0 ? (
                          <span className="text-amber-700 font-semibold">{d.evaluated_rules.join(', ')}</span>
                        ) : (
                          <span className="text-stone-400">None (Passed all)</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-stone-500">
                        {new Date(d.timestamp * 1000).toLocaleTimeString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-xs text-stone-500 font-mono">
            No gateway decisions logged yet. Trigger an action in Orbit (Port 3001) to view live decisions.
          </div>
        )}
      </div>
    </div>
  );
};
