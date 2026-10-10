import React, { useState } from 'react';
import { ApprovalRequest } from '../types';

interface ApprovalsViewProps {
  approvals: ApprovalRequest[];
  onActApproval: (apprId: string, decision: string) => Promise<any>;
  isLoading: boolean;
}

export const ApprovalsView: React.FC<ApprovalsViewProps> = ({
  approvals,
  onActApproval,
  isLoading,
}) => {
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [escalationDetails, setEscalationDetails] = useState<any | null>(null);

  const handleAction = async (apprId: string, decision: string) => {
    setActionMessage(null);
    setEscalationDetails(null);
    try {
      const res = await onActApproval(apprId, decision);
      if (res.status === 'escalated') {
        setActionMessage(
          `⚠️ Post-containment verification detected stubborn exposure! Escalated to secondary action: ${res.next_action} on ${res.target_id}`
        );
        setEscalationDetails(res);
      } else if (res.status === 'contained') {
        setActionMessage(
          `✅ Containment verified successfully! Zero egress events observed and graph access eliminated. Follow-up watch and scheduled verification task registered.`
        );
      } else if (res.status === 'rejected') {
        setActionMessage(`Action request ${apprId} was rejected by human operator.`);
      }
    } catch (e: any) {
      setActionMessage(`Error executing action: ${e.message}`);
    }
  };

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const historyApprovals = approvals.filter((a) => a.status !== 'pending');

  return (
    <div className="approvals-view">
      <div className="view-header">
        <h1 className="view-title">Human-in-the-Loop Approvals & Containment</h1>
        <p className="view-description">
          Trust Analyst proposes surgical containment actions under a fail-closed policy gateway. Humans approve
          disruptive remediations, followed by automated verification and multi-path escalation.
        </p>
      </div>

      {actionMessage && (
        <div
          style={{
            marginBottom: 20,
            padding: 16,
            borderRadius: 8,
            backgroundColor: escalationDetails ? '#fef3e2' : '#eaf4ed',
            border: `1px solid ${escalationDetails ? '#e8be88' : '#a2cfb0'}`,
            fontSize: 14,
            fontWeight: 500,
            color: escalationDetails ? '#8a5314' : '#1e5e36',
          }}
        >
          {actionMessage}
        </div>
      )}

      {/* Pending Approvals Section */}
      <div className="card" style={{ marginBottom: 28 }}>
        <div className="card-header">
          <span className="card-title">Pending Action Requests ({pendingApprovals.length})</span>
          <span className="badge badge-pending">Awaiting Human Review</span>
        </div>
        <div className="card-body">
          {pendingApprovals.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 28, color: 'var(--text-muted)' }}>
              No pending approval requests. When an investigation confirms malicious activity, proposed actions will
              appear here.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {pendingApprovals.map((appr) => (
                <div
                  key={appr.id}
                  style={{
                    border: '1px solid var(--border-medium)',
                    borderRadius: 10,
                    padding: 20,
                    backgroundColor: '#fffdf9',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ maxWidth: '75%' }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                      <span className="badge badge-malicious">{appr.action}</span>
                      <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        Target: {appr.target_id}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>({appr.id})</span>
                    </div>
                    <p style={{ fontSize: 14, color: 'var(--text-main)', marginBottom: 8 }}>
                      <strong>Rationale:</strong> {appr.rationale}
                    </p>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Investigation: <code>{appr.investigation_id}</code> | Created at epoch{' '}
                      <code>{appr.created_at}</code>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleAction(appr.id, 'rejected')}
                      disabled={isLoading}
                    >
                      Reject
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleAction(appr.id, 'approved')}
                      disabled={isLoading}
                    >
                      ✓ Approve & Remediate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Historical Approvals */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Approval & Verification History ({historyApprovals.length})</span>
          <span className="badge badge-neutral">Audit Trail</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Action</th>
                <th>Target</th>
                <th>Status</th>
                <th>Approver</th>
                <th>Approved At</th>
                <th>Investigation</th>
              </tr>
            </thead>
            <tbody>
              {historyApprovals.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                    No historical approvals recorded yet.
                  </td>
                </tr>
              ) : (
                historyApprovals.map((h) => (
                  <tr key={h.id}>
                    <td>
                      <code>{h.id}</code>
                    </td>
                    <td>
                      <strong>{h.action}</strong>
                    </td>
                    <td>
                      <code>{h.target_id}</code>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          h.status === 'approved'
                            ? 'badge-benign'
                            : h.status === 'rejected'
                            ? 'badge-malicious'
                            : 'badge-neutral'
                        }`}
                      >
                        {h.status}
                      </span>
                    </td>
                    <td>{h.approver || '-'}</td>
                    <td>{h.approved_at || '-'}</td>
                    <td>
                      <code>{h.investigation_id}</code>
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
