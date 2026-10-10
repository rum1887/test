import React, { useState, useEffect } from 'react';
import {
  Compass,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  RotateCcw,
  Layers,
  Database,
  Cpu,
  Terminal,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Play,
  Lock,
  ExternalLink,
  Zap,
} from 'lucide-react';
import {
  api,
  GatewayGuardStateResponse,
  BlastRadiusStatusResponse,
  RecentGatewayDecisionsResponse,
} from '../api/client';

interface StoryModeViewProps {
  onNavigateToTab: (tabId: string) => void;
}

export const StoryModeView: React.FC<StoryModeViewProps> = ({ onNavigateToTab }) => {
  const [activeStep, setActiveStep] = useState<number>(1);
  const [guardState, setGuardState] = useState<GatewayGuardStateResponse | null>(null);
  const [blastStatus, setBlastStatus] = useState<BlastRadiusStatusResponse | null>(null);
  const [recentDecisions, setRecentDecisions] = useState<RecentGatewayDecisionsResponse | null>(null);
  const [contaminating, setContaminating] = useState<boolean>(false);
  const [testingNexus, setTestingNexus] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [nexusResult, setNexusResult] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    loadLiveState();
    const timer = setInterval(loadLiveState, 4000);
    return () => clearInterval(timer);
  }, []);

  const showFeedback = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 3500);
  };

  const loadLiveState = async () => {
    try {
      const [g, b, d] = await Promise.all([
        api.getGatewayGuardState().catch(() => null),
        api.getBlastRadiusStatus().catch(() => null),
        api.getRecentGatewayDecisions(5).catch(() => null),
      ]);
      if (g) setGuardState(g);
      if (b) setBlastStatus(b);
      if (d) setRecentDecisions(d);
    } catch (e) {
      console.error('Failed to load story live state:', e);
    }
  };

  const isContaminated = blastStatus?.orbit_agent?.status === 'CONTAMINATED';
  const isQuarantined = blastStatus?.shared_infrastructure?.status === 'QUARANTINED_BY_BLAST_RADIUS';

  const handleSimulateAttack = async () => {
    setContaminating(true);
    try {
      await api.contaminateOrbit();
      await loadLiveState();
      setActiveStep(2);
      showFeedback('Upstream attack injected: Orbit Agent marked contaminated.');
    } catch (e) {
      console.error(e);
      showFeedback('Failed to contaminate Orbit Agent.');
    } finally {
      setContaminating(false);
    }
  };

  const handleTestLateralSettlement = async () => {
    setTestingNexus(true);
    try {
      const res = await api.testNexusSettlement();
      setNexusResult(res);
      await loadLiveState();
      setActiveStep(4);
      if (res.blocked) {
        showFeedback('Lateral movement halted: Nexus settlement blocked by blast-radius rule.');
      } else {
        showFeedback('Nexus payout executed on clean ledger.');
      }
    } catch (e) {
      console.error(e);
      showFeedback('Failed to execute settlement test.');
    } finally {
      setTestingNexus(false);
    }
  };

  const handleResetBaseline = async () => {
    setResetting(true);
    try {
      await api.resetGatewayQuarantine();
      setNexusResult(null);
      await loadLiveState();
      setActiveStep(1);
      showFeedback('Baseline restored: Quarantines cleared across all agents.');
    } catch (e) {
      console.error(e);
      showFeedback('Failed to reset baseline state.');
    } finally {
      setResetting(false);
    }
  };

  const storySteps = [
    {
      step: 1,
      title: 'Baseline Fleet & Topology',
      subtitle: 'Discovery & Graph Mapping',
      tag: isContaminated ? 'Threat Detected' : 'Healthy Baseline',
      tagColor: isContaminated ? 'bg-amber-50 text-amber-800 border-amber-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200',
    },
    {
      step: 2,
      title: 'Upstream Attack Vector',
      subtitle: 'Prompt Injection on Orbit (:3001)',
      tag: isContaminated ? 'Compromised' : 'Pending Simulation',
      tagColor: isContaminated ? 'bg-rose-50 text-rose-800 border-rose-200' : 'bg-stone-100 text-stone-600 border-stone-200',
    },
    {
      step: 3,
      title: 'Real-Time Interception',
      subtitle: 'Gateway Graph Evaluation (<15ms)',
      tag: 'Deterministic 403',
      tagColor: 'bg-stone-100 text-stone-700 border-stone-200',
    },
    {
      step: 4,
      title: 'Lateral Containment',
      subtitle: 'Multi-Agent Blast Radius Isolation',
      tag: isQuarantined ? 'Contained' : 'Clean Ledger',
      tagColor: isQuarantined ? 'bg-amber-50 text-amber-800 border-amber-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200',
    },
    {
      step: 5,
      title: 'Hardening & Compliance',
      subtitle: 'IaC Generation & Audit Evidence',
      tag: 'SOC2 / PCI / EU AI',
      tagColor: 'bg-stone-100 text-stone-700 border-stone-200',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-sans">
      {/* Toast Feedback */}
      {feedback && (
        <div className="fixed bottom-6 right-6 z-50 bg-stone-900 text-stone-100 text-xs px-4 py-2.5 rounded-lg shadow-lg flex items-center space-x-2 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Header Banner: Clean Editorial Beige */}
      <div className="bg-[#f7f5f0] border border-[#e8e4dc] rounded-2xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-stone-200/80 text-stone-700 border border-stone-300">
                Interactive Architecture Narrative
              </span>
              <span className="text-xs text-stone-500 font-mono">
                Acme Corp • aws-eks-production
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-stone-900 tracking-tight">
              The Runtime Trust Journey
            </h1>
            <p className="text-sm text-stone-600 max-w-2xl leading-relaxed">
              Step through the complete security lifecycle: from graph-native discovery to prompt injection, deterministic gateway interception, lateral spread containment, and auditable proof.
            </p>
          </div>

          <div className="flex items-center space-x-2.5 shrink-0">
            <button
              onClick={handleResetBaseline}
              disabled={resetting}
              className="px-3.5 py-2 rounded-xl bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer shadow-sm disabled:opacity-50"
              title="Reset all session states back to clean baseline"
            >
              <RotateCcw className={`w-3.5 h-3.5 text-stone-500 ${resetting ? 'animate-spin' : ''}`} />
              <span>Reset Baseline</span>
            </button>
            <button
              onClick={() => onNavigateToTab('graph')}
              className="px-3.5 py-2 rounded-xl bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
            >
              <span>Explore Graph Plane</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Story Stepper Progress Bar */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5 pt-4 border-t border-[#e5e1d7]">
          {storySteps.map((s) => {
            const isSelected = activeStep === s.step;
            return (
              <button
                key={s.step}
                onClick={() => setActiveStep(s.step)}
                className={`text-left p-3 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-white border-stone-400 shadow-sm'
                    : 'bg-white/60 hover:bg-white border-transparent text-stone-600'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] mb-1">
                  <span className={`font-mono font-bold ${isSelected ? 'text-stone-900' : 'text-stone-400'}`}>
                    0{s.step}
                  </span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${s.tagColor}`}>
                    {s.tag}
                  </span>
                </div>
                <div className={`text-xs font-semibold ${isSelected ? 'text-stone-900' : 'text-stone-700'}`}>
                  {s.title}
                </div>
                <div className="text-[11px] text-stone-500 truncate mt-0.5">
                  {s.subtitle}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chapter Content Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left 7 Columns: Story Explanation & Narrative */}
        <div className="lg:col-span-7 space-y-6">
          {activeStep === 1 && (
            <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-stone-500 uppercase font-semibold">
                  Chapter 1 • Foundation
                </span>
                <h2 className="text-xl font-bold text-stone-900">
                  Zero-Trust Baseline & Graph Discovery
                </h2>
              </div>
              <p className="text-sm text-stone-600 leading-relaxed">
                Modern enterprise applications combine autonomous AI agents and Kubernetes microservices. Instead of granting wide API keys or trusting perimeter network boundaries, the <strong>Runtime Trust Layer</strong> continuously indexes identities, RBAC roles, tools, and sensitive resources inside a live <strong>FalkorDB Knowledge Graph</strong>.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="p-3.5 rounded-xl bg-[#faf9f5] border border-[#ece8de] space-y-1.5">
                  <div className="flex items-center space-x-2 text-stone-800 font-semibold text-xs">
                    <Cpu className="w-4 h-4 text-stone-600" />
                    <span>Autonomous Agents</span>
                  </div>
                  <p className="text-xs text-stone-600 leading-relaxed">
                    Orbit (:3001) for Customer Support, Nexus (:3002) for Treasury FinOps. Each bounded by delegated human SSO credentials.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-[#faf9f5] border border-[#ece8de] space-y-1.5">
                  <div className="flex items-center space-x-2 text-stone-800 font-semibold text-xs">
                    <Database className="w-4 h-4 text-stone-600" />
                    <span>Shared Corporate Stores</span>
                  </div>
                  <p className="text-xs text-stone-600 leading-relaxed">
                    <code className="text-stone-800 font-mono text-[11px]">sr-financial-db</code> and KMS credential vaults shared across departments.
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">Next: See what happens when an agent is hijacked.</span>
                <button
                  onClick={() => setActiveStep(2)}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <span>Proceed to Chapter 2</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {activeStep === 2 && (
            <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-stone-500 uppercase font-semibold">
                  Chapter 2 • Attack Simulation
                </span>
                <h2 className="text-xl font-bold text-stone-900">
                  Upstream Attack: Prompt Injection & Goal Hijacking
                </h2>
              </div>
              <p className="text-sm text-stone-600 leading-relaxed">
                In this scenario, an external user submits an adversarial prompt to <strong>Orbit Customer Support Agent (:3001)</strong>. The LLM is tricked into attempting an out-of-scope administrative operation: exfiltrating AWS KMS keys or dropping the customer table.
              </p>

              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/80 space-y-2">
                <div className="flex items-center space-x-2 text-amber-900 font-semibold text-xs">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>The Risk of Implicit Tool Trust</span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  Without runtime interception, the AI agent would directly call the MCP server or database driver, leaking credentials or destroying production tables.
                </p>
              </div>

              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleSimulateAttack}
                  disabled={contaminating}
                  className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center space-x-2 shadow-sm transition cursor-pointer disabled:opacity-50"
                >
                  <Play className={`w-3.5 h-3.5 ${contaminating ? 'animate-spin' : ''}`} />
                  <span>{isContaminated ? 'Re-Inject Threat Indicator' : 'Simulate Upstream Compromise (:3001)'}</span>
                </button>
                <a
                  href="http://localhost:3001"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3.5 py-2.5 rounded-xl bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-medium flex items-center space-x-1.5 transition"
                >
                  <span>Open Orbit Agent Chat</span>
                  <ExternalLink className="w-3.5 h-3.5 text-stone-400" />
                </a>
              </div>

              <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">Next: Observe real-time gateway interception.</span>
                <button
                  onClick={() => setActiveStep(3)}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <span>Proceed to Chapter 3</span>
                  <ArrowRight className="w-3 3" />
                </button>
              </div>
            </div>
          )}

          {activeStep === 3 && (
            <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-stone-500 uppercase font-semibold">
                  Chapter 3 • Real-Time Enforcement
                </span>
                <h2 className="text-xl font-bold text-stone-900">
                  Gateway Interception: Graph Traversal in &lt;15ms
                </h2>
              </div>
              <p className="text-sm text-stone-600 leading-relaxed">
                Before any tool payload executes, the agent wrapper routes the invocation through the <strong>Runtime Trust Layer Gateway</strong>. The engine evaluates Cypher reachability rules in FalkorDB:
              </p>

              <div className="p-3.5 rounded-xl bg-[#faf9f5] border border-[#ece8de] font-mono text-[11px] text-stone-700 space-y-1">
                <div className="text-stone-400 text-[10px] uppercase font-bold">Evaluated Cypher Traversal:</div>
                <div className="text-stone-900 font-semibold">
                  MATCH (s:AgentSession)-[:HAS_GRANT]-&gt;(d:DelegationGrant)-[:ALLOWS_TOOL]-&gt;(t:Tool)
                </div>
                <div className="text-stone-600 text-[10px]">
                  Result: Tool outside delegation bounds $\rightarrow$ Action blocked (HTTP 403 Forbidden).
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200">
                  <div className="text-[10px] text-stone-500 uppercase font-bold">Deterministic Latency</div>
                  <div className="text-lg font-bold text-stone-900">&lt; 14.8 ms</div>
                  <div className="text-[10px] text-stone-500">Deterministic graph SLA</div>
                </div>
                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200">
                  <div className="text-[10px] text-stone-500 uppercase font-bold">Zero LLM in Guard Loop</div>
                  <div className="text-lg font-bold text-stone-900">Graph Only</div>
                  <div className="text-[10px] text-stone-500">Immune to jailbreaks</div>
                </div>
              </div>

              <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">Next: See how the platform prevents lateral movement.</span>
                <button
                  onClick={() => setActiveStep(4)}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <span>Proceed to Chapter 4</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {activeStep === 4 && (
            <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-stone-500 uppercase font-semibold">
                  Chapter 4 • Lateral Isolation
                </span>
                <h2 className="text-xl font-bold text-stone-900">
                  Blast Radius Containment Across Multi-Agent Fleets
                </h2>
              </div>
              <p className="text-sm text-stone-600 leading-relaxed">
                The biggest vulnerability in multi-agent architectures is <strong>lateral movement</strong> through shared databases. Even if Orbit cannot directly access the treasury, a secondary agent—like <strong>Nexus FinOps (:3002)</strong>—might interact with the same database (<code className="text-stone-800 font-mono text-xs">sr-financial-db</code>).
              </p>

              <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200 space-y-2">
                <div className="flex items-center space-x-2 text-amber-900 font-semibold text-xs">
                  <ShieldAlert className="w-4 h-4 text-amber-600" />
                  <span>Blast-Radius Protection Active</span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  Because Orbit is contaminated, the platform isolates <code className="font-mono">sr-financial-db</code>. Any downstream agent attempting financial disbursements on this database is halted immediately.
                </p>
              </div>

              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleTestLateralSettlement}
                  disabled={testingNexus}
                  className="px-4 py-2.5 rounded-xl bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold flex items-center space-x-2 shadow-sm transition cursor-pointer disabled:opacity-50"
                >
                  <Zap className={`w-3.5 h-3.5 ${testingNexus ? 'animate-spin' : ''}`} />
                  <span>Execute Downstream Settlement Test (:3002)</span>
                </button>
                <a
                  href="http://localhost:3002"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3.5 py-2.5 rounded-xl bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-medium flex items-center space-x-1.5 transition"
                >
                  <span>Open Nexus Agent</span>
                  <ExternalLink className="w-3.5 h-3.5 text-stone-400" />
                </a>
              </div>

              {nexusResult && (
                <div className="p-3.5 rounded-xl bg-[#faf9f5] border border-[#ece8de] text-xs font-mono space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold text-stone-800">
                      HTTP {nexusResult.status_code} • {nexusResult.blocked ? 'LATERAL SPREAD INTERCEPTED' : 'EXECUTED'}
                    </span>
                    <span className="text-emerald-700 font-semibold">
                      {nexusResult.gateway_latency_ms?.toFixed(1) || '14.2'} ms
                    </span>
                  </div>
                  <p className="text-stone-600 text-[11px] leading-relaxed">
                    {nexusResult.decision_rationale}
                  </p>
                </div>
              )}

              <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">Next: Review automated policy hardening & audit proofs.</span>
                <button
                  onClick={() => setActiveStep(5)}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <span>Proceed to Chapter 5</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {activeStep === 5 && (
            <div className="bg-white border border-[#e8e5de] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-stone-500 uppercase font-semibold">
                  Chapter 5 • Hardening & Proof
                </span>
                <h2 className="text-xl font-bold text-stone-900">
                  Infrastructure Hardening & Regulatory Compliance Proof
                </h2>
              </div>
              <p className="text-sm text-stone-600 leading-relaxed">
                Rather than stopping at runtime alerts, the platform compiles graph containment paths into persistent Infrastructure-as-Code (IaC) and generates auditable evidence for compliance bodies.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200 space-y-1">
                  <div className="text-[10px] text-stone-500 uppercase font-bold">Kubernetes Policy</div>
                  <div className="text-xs font-semibold text-stone-900">NetworkPolicy YAML</div>
                  <div className="text-[10px] text-stone-500">Automated egress cutoff</div>
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200 space-y-1">
                  <div className="text-[10px] text-stone-500 uppercase font-bold">Kyverno Admission</div>
                  <div className="text-xs font-semibold text-stone-900">ClusterPolicy YAML</div>
                  <div className="text-[10px] text-stone-500">Block pod re-admit</div>
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200 space-y-1">
                  <div className="text-[10px] text-stone-500 uppercase font-bold">Audit Standards</div>
                  <div className="text-xs font-semibold text-stone-900">SOC 2 / PCI / EU AI</div>
                  <div className="text-[10px] text-stone-500">Deterministic proof logs</div>
                </div>
              </div>

              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => onNavigateToTab('containment')}
                  className="px-4 py-2 rounded-xl bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>Inspect & Export IaC Policies</span>
                </button>
                <button
                  onClick={() => onNavigateToTab('compliance')}
                  className="px-3.5 py-2 rounded-xl bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-medium flex items-center space-x-1.5 transition"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-stone-500" />
                  <span>View Compliance Posture</span>
                </button>
              </div>

              <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">Story completed. Reset whenever you wish to demonstrate again.</span>
                <button
                  onClick={handleResetBaseline}
                  disabled={resetting}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset Story Baseline</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right 5 Columns: Live Architecture Status Card */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-[#e8e5de] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-stone-100 pb-3">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
                  Live Fleet State Machine
                </h3>
              </div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                isContaminated
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200'
              }`}>
                {isContaminated ? 'THREAT ACTIVE' : 'SECURE'}
              </span>
            </div>

            {/* Architecture Node 1: Orbit Agent */}
            <div className={`p-3.5 rounded-xl border transition-all space-y-1.5 ${
              isContaminated ? 'bg-rose-50/60 border-rose-200 text-rose-950' : 'bg-[#faf9f5] border-[#ece8de]'
            }`}>
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>Orbit Support Agent (:3001)</span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  isContaminated ? 'bg-rose-100 text-rose-800 border-rose-300' : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                }`}>
                  {isContaminated ? 'CONTAMINATED' : 'HEALTHY'}
                </span>
              </div>
              <p className="text-[11px] text-stone-600">
                Session: <code className="font-mono text-stone-800">session-alice-dev-01</code> (Okta Customer Support role)
              </p>
            </div>

            {/* Architecture Node 2: Shared Database */}
            <div className={`p-3.5 rounded-xl border transition-all space-y-1.5 ${
              isQuarantined ? 'bg-amber-50/70 border-amber-200 text-amber-950' : 'bg-[#faf9f5] border-[#ece8de]'
            }`}>
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>Shared Database (<code className="font-mono text-[11px]">sr-financial-db</code>)</span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  isQuarantined ? 'bg-amber-100 text-amber-800 border-amber-300' : 'bg-stone-100 text-stone-700 border-stone-300'
                }`}>
                  {isQuarantined ? 'ISOLATED' : 'SHARED READ/WRITE'}
                </span>
              </div>
              <p className="text-[11px] text-stone-600">
                {isQuarantined
                  ? 'Mutations suspended to protect corporate treasury from lateral spread.'
                  : 'Normal delegated operations authorized under strict graph bounds.'}
              </p>
            </div>

            {/* Architecture Node 3: Nexus FinOps Agent */}
            <div className="p-3.5 rounded-xl bg-[#faf9f5] border border-[#ece8de] space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>Nexus FinOps Agent (:3002)</span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  isQuarantined ? 'bg-emerald-100 text-emerald-800 border-emerald-300' : 'bg-stone-100 text-stone-700 border-stone-300'
                }`}>
                  {isQuarantined ? 'BLAST-CONTAINED' : 'OPERATIONAL'}
                </span>
              </div>
              <p className="text-[11px] text-stone-600">
                Principal: Marcus Vance (Treasury Director) • Sub-agent: TreasuryDisbursement
              </p>
            </div>

            {/* Recent Decisions Feed in Story Panel */}
            <div className="pt-2 border-t border-stone-100 space-y-2">
              <div className="text-[11px] font-bold text-stone-700 uppercase tracking-wider flex items-center justify-between">
                <span>Recent Gateway Decisions</span>
                <span className="text-[10px] font-mono text-stone-500">Live &lt; 15ms</span>
              </div>

              {recentDecisions && recentDecisions.decisions.length > 0 ? (
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {recentDecisions.decisions.slice(0, 3).map((d) => {
                    const isAllow = d.decision === 'ALLOW';
                    return (
                      <div
                        key={d.decision_id}
                        className="p-2 rounded-lg bg-stone-50 border border-stone-200 text-[11px] space-y-0.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className={`font-mono font-bold text-[10px] px-1.5 py-0.2 rounded border ${
                            isAllow
                              ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                              : 'bg-rose-100 text-rose-800 border-rose-300'
                          }`}>
                            {d.decision}
                          </span>
                          <span className="font-mono text-[10px] text-stone-400">
                            {new Date(d.timestamp * 1000).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-stone-700 truncate text-[11px]" title={d.rationale}>
                          {d.rationale}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-3 text-center text-xs text-stone-400 font-mono">
                  No gateway events logged yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
