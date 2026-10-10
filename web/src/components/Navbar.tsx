import React from 'react';

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  clockTime: string;
  onAdvanceClock: (seconds: number) => void;
  onResetWorld: () => void;
  isClockLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  clockTime,
  onAdvanceClock,
  onResetWorld,
  isClockLoading,
}) => {
  const tabs = [
    { id: 'inbox', label: 'Inbox & Scenarios' },
    { id: 'story', label: 'Investigation Story' },
    { id: 'approvals', label: 'Approvals & Actions' },
    { id: 'graph', label: 'Graph Explorer' },
    { id: 'watches', label: 'Watches & Schedules' },
    { id: 'eval', label: 'Evaluation Benchmark' },
  ];

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <div className="brand-icon">T</div>
        <div>
          <div className="brand-title">Trust Analyst</div>
          <div className="brand-subtitle">Autonomous Security on FalkorDB</div>
        </div>
      </div>

      <div className="nav-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`nav-tab-btn ${currentTab === t.id ? 'active' : ''}`}
            onClick={() => onSelectTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="nav-controls">
        <div className="clock-pill" title="Simulated Clock Time">
          <div className="clock-indicator" />
          <span>{clockTime || 'Sim Time: 1700000000'}</span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onAdvanceClock(300)}
          disabled={isClockLoading}
          title="Advance clock by 5 minutes to trigger watches & telemetry observation"
        >
          +5m
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onAdvanceClock(3600)}
          disabled={isClockLoading}
          title="Advance clock by 1 hour"
        >
          +1h
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onResetWorld}
          disabled={isClockLoading}
          title="Re-seed synthetic environment and reset simulated clock"
        >
          Reset World
        </button>
      </div>
    </nav>
  );
};
