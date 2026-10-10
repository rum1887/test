import React from 'react';
import { ScheduledTask, Watch } from '../types';

interface WatchesViewProps {
  watches: Watch[];
  tasks: ScheduledTask[];
  onAdvanceClock: (seconds: number) => void;
  isLoading: boolean;
}

export const WatchesView: React.FC<WatchesViewProps> = ({
  watches,
  tasks,
  onAdvanceClock,
  isLoading,
}) => {
  return (
    <div className="watches-view">
      <div className="view-header">
        <h1 className="view-title">Active Graph Watches & Task Scheduler</h1>
        <p className="view-description">
          Trust Analyst registers long-running watches and scheduled tasks directly inside FalkorDB. Fast-forward
          the simulated clock to trigger watch wake events and execute post-containment verifications.
        </p>
      </div>

      {/* Clock Fast Forward Action Bar */}
      <div
        className="card"
        style={{
          marginBottom: 24,
          padding: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#fffdf9',
          border: '1px solid var(--border-medium)',
        }}
      >
        <div>
          <span style={{ fontWeight: 600, fontSize: 14 }}>Simulated Time Travel Controls</span>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Advance time to evaluate expiration windows and trigger scheduled follow-ups.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-primary btn-sm" onClick={() => onAdvanceClock(300)} disabled={isLoading}>
            Fast-Forward 5 Minutes (+300s)
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => onAdvanceClock(3600)} disabled={isLoading}>
            Fast-Forward 1 Hour (+3600s)
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => onAdvanceClock(86400)} disabled={isLoading}>
            Fast-Forward 24 Hours (+86400s)
          </button>
        </div>
      </div>

      <div className="grid-2col">
        {/* Active Watches Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Active FalkorDB Watches ({watches.length})</span>
            <span className="badge badge-neutral">Durable Triggers</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Watch ID</th>
                  <th>Kind</th>
                  <th>Status</th>
                  <th>Expires At</th>
                  <th>Triggered At</th>
                </tr>
              </thead>
              <tbody>
                {watches.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                      No active watches registered. Containment verifications register 24h watches.
                    </td>
                  </tr>
                ) : (
                  watches.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <code>{w.id}</code>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{w.kind}</span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            w.status === 'triggered'
                              ? 'badge-malicious'
                              : w.status === 'active'
                              ? 'badge-benign'
                              : 'badge-neutral'
                          }`}
                        >
                          {w.status}
                        </span>
                      </td>
                      <td>{w.expires_at}</td>
                      <td>{w.triggered_at || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Scheduled Tasks Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Scheduled Follow-Up Tasks ({tasks.length})</span>
            <span className="badge badge-neutral">Task Dispatcher</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Task ID</th>
                  <th>Action</th>
                  <th>Due Epoch</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                      No tasks currently scheduled.
                    </td>
                  </tr>
                ) : (
                  tasks.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <code>{t.id}</code>
                      </td>
                      <td>
                        <strong>{t.action}</strong>
                      </td>
                      <td>{t.due_at}</td>
                      <td>
                        <span
                          className={`badge ${
                            t.status === 'completed'
                              ? 'badge-benign'
                              : t.status === 'pending'
                              ? 'badge-pending'
                              : 'badge-neutral'
                          }`}
                        >
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
