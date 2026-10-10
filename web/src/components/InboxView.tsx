import React, { useState } from 'react';
import { Alert, Scenario } from '../types';

interface InboxViewProps {
  scenarios: Scenario[];
  alerts: Alert[];
  onRunScenario: (scenarioId: string) => Promise<void>;
  isRunning: boolean;
  onSelectAlert: (alertId: string) => void;
}

export const InboxView: React.FC<InboxViewProps> = ({
  scenarios,
  alerts,
  onRunScenario,
  isRunning,
  onSelectAlert,
}) => {
  const [selectedPair, setSelectedPair] = useState<string>('all');

  // Group scenarios into matched pairs
  const pairMap: Record<string, { title: string; benign?: Scenario; malicious?: Scenario }> = {};

  const pairTitles: Record<string, string> = {
    pair1_shell_metadata: 'Pair 1: Interactive Shell & Cloud IMDS Access',
    pair2_role_binding: 'Pair 2: Privileged Cluster RoleBinding Creation',
    pair3_destructive_tool: 'Pair 3: Production Database Drop / Destructive Tool',
    pair4_dormant_permission: 'Pair 4: Dormant Wildcard Permission Abuse',
    pair5_outbound_endpoint: 'Pair 5: External Network Egress to Unknown C2',
    pair6_zombie_delegation: 'Pair 6: Zombie Session & Offboarded Contractor Abuse',
    pair7_convergence_stubborn: 'Pair 7: Crown Jewel Convergence & Stubborn Exposure',
  };

  scenarios.forEach((sc) => {
    if (!pairMap[sc.pair_id]) {
      pairMap[sc.pair_id] = {
        title: pairTitles[sc.pair_id] || sc.pair_id,
      };
    }
    if (sc.variant === 'benign') {
      pairMap[sc.pair_id].benign = sc;
    } else {
      pairMap[sc.pair_id].malicious = sc;
    }
  });

  const pairEntries = Object.entries(pairMap).filter(
    ([pid]) => selectedPair === 'all' || selectedPair === pid
  );

  return (
    <div className="inbox-view">
      <div className="view-header">
        <h1 className="view-title">Scenario Playground & Security Inbox</h1>
        <p className="view-description">
          Pairs of alerts look identical on the surface but have opposite ground truths. Select any scenario
          to trigger the incident and watch Trust Analyst investigate autonomously.
        </p>
      </div>

      {/* Filter bar */}
      <div style={{ marginBottom: 20, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          className={`btn btn-sm ${selectedPair === 'all' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setSelectedPair('all')}
        >
          All Pairs (14 Scenarios)
        </button>
        {Object.entries(pairTitles).map(([pid, title]) => (
          <button
            key={pid}
            className={`btn btn-sm ${selectedPair === pid ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedPair(pid)}
          >
            {title.split(':')[0]}
          </button>
        ))}
      </div>

      {/* Matched Pairs Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginBottom: 36 }}>
        {pairEntries.map(([pairId, pairData]) => (
          <div key={pairId} className="card">
            <div className="card-header">
              <span className="card-title">{pairData.title}</span>
              <span className="badge badge-neutral">Matched Pair</span>
            </div>
            <div className="card-body">
              <div className="grid-2col">
                {/* Benign Operational Scenario */}
                {pairData.benign && (
                  <div
                    style={{
                      border: '1px solid var(--border-light)',
                      borderRadius: 10,
                      padding: 16,
                      backgroundColor: '#fafaf8',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span className="badge badge-benign">Benign Operational</span>
                        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {pairData.benign.id}
                        </span>
                      </div>
                      <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>{pairData.benign.title}</h4>
                      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
                        {pairData.benign.description}
                      </p>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
                        <strong>Target:</strong> <code>{pairData.benign.alert.target_id}</code> |{' '}
                        <strong>Severity:</strong> {pairData.benign.alert.severity}
                      </div>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onRunScenario(pairData.benign!.id)}
                      disabled={isRunning}
                    >
                      ▶ Run Benign Investigation
                    </button>
                  </div>
                )}

                {/* Malicious Attack Scenario */}
                {pairData.malicious && (
                  <div
                    style={{
                      border: '1px solid var(--border-light)',
                      borderRadius: 10,
                      padding: 16,
                      backgroundColor: '#fafaf8',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <span className="badge badge-malicious">Malicious Attack</span>
                          {pairData.malicious.inject && (
                            <span className="badge badge-pending" title="Contains prompt injection attack">
                              Prompt Injection
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {pairData.malicious.id}
                        </span>
                      </div>
                      <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>{pairData.malicious.title}</h4>
                      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
                        {pairData.malicious.description}
                      </p>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
                        <strong>Target:</strong> <code>{pairData.malicious.alert.target_id}</code> |{' '}
                        <strong>Severity:</strong> {pairData.malicious.alert.severity}
                      </div>
                    </div>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => onRunScenario(pairData.malicious!.id)}
                      disabled={isRunning}
                    >
                      ⚡ Run Attack Investigation
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Live Alerts Feed */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Live Security Alerts Feed ({alerts.length})</span>
          <span className="badge badge-neutral">FalkorDB Real-Time</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Alert Title</th>
                <th>Target Entity</th>
                <th>Kind</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Investigation</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                    No alerts currently recorded. Run a scenario above to raise a runtime alert.
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>{a.title}</td>
                    <td>
                      <code>{a.target_id}</code>
                    </td>
                    <td>{a.kind}</td>
                    <td>
                      <span className={`badge ${a.severity === 'critical' ? 'badge-malicious' : 'badge-pending'}`}>
                        {a.severity}
                      </span>
                    </td>
                    <td>{a.status}</td>
                    <td>
                      {a.investigation_id ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{a.investigation_id}</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>-</span>
                      )}
                    </td>
                    <td>
                      {a.investigation_id ? (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectAlert(a.investigation_id!)}
                        >
                          View Story →
                        </button>
                      ) : (
                        <button className="btn btn-primary btn-sm" onClick={() => onSelectAlert(a.id)}>
                          Investigate
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
