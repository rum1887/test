import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { OverviewView } from './components/OverviewView';
import { GraphView } from './components/GraphView';
import { WorkloadsView } from './components/WorkloadsView';
import { AgentsView } from './components/AgentsView';
import { BlastRadiusView } from './components/BlastRadiusView';
import { EventsView } from './components/EventsView';
import { PolicyDecisionsView } from './components/PolicyDecisionsView';
import { ContainmentView } from './components/ContainmentView';
import { ComplianceView } from './components/ComplianceView';
import { api, HealthResponse, StatsResponse, CytoscapeNode, CytoscapeEdge } from './api/client';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [nodes, setNodes] = useState<CytoscapeNode[]>([]);
  const [edges, setEdges] = useState<CytoscapeEdge[]>([]);

  // Selected entities for cross-tab drill-down
  const [blastTargetId, setBlastTargetId] = useState<string>('workload-checkout');
  const [containmentTargetId, setContainmentTargetId] = useState<string>('workload-checkout');

  // Notification Toast state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    loadPlatformData();
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const loadPlatformData = async () => {
    try {
      const [h, s, g] = await Promise.all([
        api.getHealth(),
        api.getStats(),
        api.getGraph(),
      ]);
      setHealth(h);
      setStats(s);
      setNodes(g.elements?.nodes || []);
      setEdges(g.elements?.edges || []);
    } catch (err) {
      console.error('Failed to load initial platform data:', err);
    }
  };

  const handleReset = async () => {
    try {
      await api.resetGraph();
      await loadPlatformData();
      showToast('Graph cleared & baseline scenarios re-seeded successfully.');
    } catch (err) {
      console.error(err);
      showToast('Error resetting graph state.');
    }
  };

  const handleLoadScenario = async (scenarioKey: string) => {
    try {
      await api.loadScenario(scenarioKey);
      await loadPlatformData();
      showToast(`Scenario ${scenarioKey} loaded successfully.`);
    } catch (err) {
      console.error(err);
      showToast(`Failed to load scenario ${scenarioKey}.`);
    }
  };

  const handleTriggerReplay = async () => {
    try {
      const res = await api.triggerReplay(3);
      await loadPlatformData();
      showToast(`Injected ${res.generated_count} synthetic replay events into graph.`);
    } catch (err) {
      console.error(err);
      showToast('Failed to trigger replay stream.');
    }
  };

  const handleTestAgentBlock = () => {
    setCurrentTab('agents');
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-200 flex flex-col font-sans">
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        health={health}
        onReset={handleReset}
        onLoadScenario={handleLoadScenario}
        onTriggerReplay={handleTriggerReplay}
      />

      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0d1322] border border-sky-500/80 text-sky-200 text-xs px-4 py-2.5 rounded-lg shadow-2xl flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main View Area */}
      <main className="flex-1">
        {currentTab === 'overview' && (
          <OverviewView
            stats={stats}
            health={health}
            onNavigate={(tab) => setCurrentTab(tab)}
            onTriggerReplay={handleTriggerReplay}
            onTestAgentBlock={handleTestAgentBlock}
          />
        )}

        {currentTab === 'compliance' && <ComplianceView />}

        {currentTab === 'graph' && (
          <GraphView
            nodes={nodes}
            edges={edges}
            onSelectNodeForBlastRadius={(id) => {
              setBlastTargetId(id);
              setCurrentTab('blast-radius');
            }}
            onSelectNodeForContainment={(id) => {
              setContainmentTargetId(id);
              setCurrentTab('containment');
            }}
          />
        )}

        {currentTab === 'workloads' && (
          <WorkloadsView
            onAnalyzeBlastRadius={(id) => {
              setBlastTargetId(id);
              setCurrentTab('blast-radius');
            }}
          />
        )}

        {currentTab === 'agents' && <AgentsView />}

        {currentTab === 'blast-radius' && (
          <BlastRadiusView
            initialSourceId={blastTargetId}
            onNavigateToContainment={(id) => {
              setContainmentTargetId(id);
              setCurrentTab('containment');
            }}
          />
        )}

        {currentTab === 'events' && <EventsView />}

        {currentTab === 'policies' && <PolicyDecisionsView />}

        {currentTab === 'containment' && (
          <ContainmentView initialSourceId={containmentTargetId} />
        )}
      </main>
    </div>
  );
}

export default App;
