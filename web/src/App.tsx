import React, { useEffect, useState } from 'react';
import {
  actOnApproval,
  advanceClock,
  fetchAlerts,
  fetchApprovals,
  fetchClock,
  fetchEvalResults,
  fetchInvestigation,
  fetchInvestigations,
  fetchScenarios,
  fetchSubgraph,
  fetchTasks,
  fetchWatches,
  resetClock,
  runScenario,
  seedWorld,
} from './api';
import { ApprovalsView } from './components/ApprovalsView';
import { ErrorBoundary } from './components/ErrorBoundary';
import { EvalView } from './components/EvalView';
import { GraphExplorerView } from './components/GraphExplorerView';
import { InboxView } from './components/InboxView';
import { InvestigationStoryView } from './components/InvestigationStoryView';
import { Navbar } from './components/Navbar';
import { WatchesView } from './components/WatchesView';
import {
  Alert,
  ApprovalRequest,
  EvalMetrics,
  Investigation,
  Scenario,
  ScheduledTask,
  SubgraphData,
  Watch,
} from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('inbox');
  const [clockTime, setClockTime] = useState<string>('');
  const [isClockLoading, setIsClockLoading] = useState<boolean>(false);

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedInvId, setSelectedInvId] = useState<string | null>(null);
  const [selectedInv, setSelectedInv] = useState<Investigation | null>(null);

  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [watches, setWatches] = useState<Watch[]>([]);
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [subgraph, setSubgraph] = useState<SubgraphData | null>(null);
  const [evalResults, setEvalResults] = useState<Record<string, EvalMetrics> | null>(null);

  const [isActionRunning, setIsActionRunning] = useState<boolean>(false);

  // Initial load
  const loadAllData = async () => {
    try {
      const [cRes, scRes, aRes, invRes, apprRes, wRes, tRes, subRes] = await Promise.all([
        fetchClock().catch(() => ({ now: 1700000000, formatted: '2023-11-14 22:13:20' })),
        fetchScenarios().catch(() => []),
        fetchAlerts().catch(() => []),
        fetchInvestigations().catch(() => []),
        fetchApprovals().catch(() => []),
        fetchWatches().catch(() => []),
        fetchTasks().catch(() => []),
        fetchSubgraph(undefined, 2).catch(() => ({ nodes: [], edges: [] })),
      ]);

      setClockTime(cRes.formatted || `Epoch: ${cRes.now}`);
      setScenarios(scRes);
      setAlerts(aRes);
      setInvestigations(invRes);
      setApprovals(apprRes);
      setWatches(wRes);
      setTasks(tRes);
      setSubgraph(subRes);

      if (invRes.length > 0 && !selectedInvId) {
        setSelectedInvId(invRes[0].id);
      }
    } catch (e) {
      console.error('Error loading initial data:', e);
    }
  };

  useEffect(() => {
    loadAllData();
    // Load eval results in background
    fetchEvalResults()
      .then(setEvalResults)
      .catch(() => {});
  }, []);

  // When selectedInvId changes, fetch full investigation details
  useEffect(() => {
    if (selectedInvId) {
      fetchInvestigation(selectedInvId)
        .then(setSelectedInv)
        .catch(console.error);
    }
  }, [selectedInvId]);

  // Clock Actions
  const handleAdvanceClock = async (seconds: number) => {
    setIsClockLoading(true);
    try {
      const res = await advanceClock(seconds);
      setClockTime(res.formatted);
      await loadAllData();
    } finally {
      setIsClockLoading(false);
    }
  };

  const handleResetWorld = async () => {
    setIsClockLoading(true);
    try {
      await seedWorld(42);
      await resetClock();
      await loadAllData();
    } finally {
      setIsClockLoading(false);
    }
  };

  // Run Scenario -> jump directly to investigation story
  const handleRunScenario = async (scenarioId: string) => {
    setIsActionRunning(true);
    try {
      const res = await runScenario(scenarioId);
      await loadAllData();
      if (res.investigation_id) {
        setSelectedInvId(res.investigation_id);
        setCurrentTab('story');
      }
    } finally {
      setIsActionRunning(false);
    }
  };

  // Act on Approval
  const handleActApproval = async (apprId: string, decision: string) => {
    setIsActionRunning(true);
    try {
      const res = await actOnApproval(apprId, decision);
      await loadAllData();
      if (selectedInvId) {
        const updated = await fetchInvestigation(selectedInvId);
        setSelectedInv(updated);
      }
      return res;
    } finally {
      setIsActionRunning(false);
    }
  };

  // Subgraph Search
  const handleSearchNode = async (nodeId: string, depth: number) => {
    setIsActionRunning(true);
    try {
      const data = await fetchSubgraph(nodeId, depth);
      setSubgraph(data);
    } finally {
      setIsActionRunning(false);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        clockTime={clockTime}
        onAdvanceClock={handleAdvanceClock}
        onResetWorld={handleResetWorld}
        isClockLoading={isClockLoading}
      />

      <main className="main-content">
        {currentTab === 'inbox' && (
          <ErrorBoundary tabName="Inbox & Scenarios">
            <InboxView
              scenarios={scenarios}
              alerts={alerts}
              onRunScenario={handleRunScenario}
              isRunning={isActionRunning}
              onSelectAlert={(id) => {
                if (id.startsWith('inv-')) {
                  setSelectedInvId(id);
                  setCurrentTab('story');
                }
              }}
            />
          </ErrorBoundary>
        )}

        {currentTab === 'story' && (
          <ErrorBoundary tabName="Investigation Story">
            <InvestigationStoryView
              investigation={selectedInv}
              investigations={investigations}
              onSelectInvestigation={setSelectedInvId}
              onNavigateToApprovals={() => setCurrentTab('approvals')}
            />
          </ErrorBoundary>
        )}

        {currentTab === 'approvals' && (
          <ErrorBoundary tabName="Approvals & Actions">
            <ApprovalsView
              approvals={approvals}
              onActApproval={handleActApproval}
              isLoading={isActionRunning}
            />
          </ErrorBoundary>
        )}

        {currentTab === 'graph' && (
          <ErrorBoundary tabName="Graph Explorer">
            <GraphExplorerView
              subgraph={subgraph}
              onSearchNode={handleSearchNode}
              isLoading={isActionRunning}
            />
          </ErrorBoundary>
        )}

        {currentTab === 'watches' && (
          <ErrorBoundary tabName="Watches & Schedules">
            <WatchesView
              watches={watches}
              tasks={tasks}
              onAdvanceClock={handleAdvanceClock}
              isLoading={isClockLoading}
            />
          </ErrorBoundary>
        )}

        {currentTab === 'eval' && (
          <ErrorBoundary tabName="Evaluation Benchmark">
            <EvalView evalResults={evalResults} />
          </ErrorBoundary>
        )}
      </main>
    </div>
  );
};
