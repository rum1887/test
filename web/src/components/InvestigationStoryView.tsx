import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { Investigation } from '../types';

interface InvestigationStoryViewProps {
  investigation: Investigation | null;
  investigations: Investigation[];
  onSelectInvestigation: (id: string) => void;
  onNavigateToApprovals: () => void;
}

export const InvestigationStoryView: React.FC<InvestigationStoryViewProps> = ({
  investigation,
  investigations,
  onSelectInvestigation,
  onNavigateToApprovals,
}) => {
  const cyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!cyRef.current || !investigation) return;

    // Build Cytoscape graph from cited evidence and investigation context
    const cyElements: any[] = [];
    const addedNodes = new Set<string>();

    const addNode = (id: string, label: string, type: string) => {
      if (!addedNodes.has(id)) {
        addedNodes.add(id);
        cyElements.push({
          data: { id, label, type },
        });
      }
    };

    const addEdge = (source: string, target: string, label: string) => {
      cyElements.push({
        data: {
          id: `${source}->${target}`,
          source,
          target,
          label,
        },
      });
    };

    // Investigation node
    addNode(investigation.id, investigation.id, 'Investigation');

    // Hypotheses
    const hyps = investigation.hypotheses_from_graph || investigation.hypotheses || [];
    hyps.forEach((h) => {
      addNode(h.id, h.title.slice(0, 24) + '...', 'Hypothesis');
      addEdge(investigation.id, h.id, 'HYPOTHESIS');
    });

    // Evidence nodes
    if (investigation.evidence_store) {
      Object.keys(investigation.evidence_store).forEach((eid) => {
        const cleanName = eid.replace('ev:node:', '').replace('ev:action:', '');
        addNode(eid, cleanName, 'Evidence');
        addEdge(investigation.id, eid, 'EVIDENCE');
      });
    }

    const cy = cytoscape({
      container: cyRef.current,
      elements: cyElements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-size': '11px',
            'font-family': 'Plus Jakarta Sans, sans-serif',
            color: '#24211e',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'background-color': '#d8d0c0',
            width: 32,
            height: 32,
          },
        },
        {
          selector: 'node[type = "Investigation"]',
          style: {
            'background-color': '#8b5e34',
            width: 44,
            height: 44,
            color: '#8b5e34',
            'font-weight': 'bold',
          },
        },
        {
          selector: 'node[type = "Hypothesis"]',
          style: {
            'background-color': '#c07828',
            width: 32,
            height: 32,
          },
        },
        {
          selector: 'node[type = "Evidence"]',
          style: {
            'background-color': '#297a48',
            width: 28,
            height: 28,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#d8d0c0',
            'target-arrow-color': '#a39b91',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'font-size': '9px',
            label: 'data(label)',
            color: '#736b63',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 20,
      },
    });

    return () => {
      cy.destroy();
    };
  }, [investigation]);

  if (!investigation) {
    return (
      <div className="story-view">
        <div className="view-header">
          <h1 className="view-title">Autonomous Investigation Narrative</h1>
          <p className="view-description">Select an investigation to review its full forensic reasoning story.</p>
        </div>
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
            No investigation selected. Pick one from the list below or run a scenario in the Inbox tab.
            <div style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              {investigations.map((inv) => (
                <button
                  key={inv.id}
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSelectInvestigation(inv.id)}
                >
                  Investigation: {inv.id} ({inv.status})
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isMalicious = investigation.verdict === 'malicious';
  const isBenign = investigation.verdict === 'benign';
  const hyps = investigation.hypotheses_from_graph || investigation.hypotheses || [];

  return (
    <div className="story-view">
      {/* Top Header & Selector */}
      <div className="view-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <h1 className="view-title">Investigation: {investigation.id}</h1>
            <span
              className={`badge ${
                isMalicious ? 'badge-malicious' : isBenign ? 'badge-benign' : 'badge-pending'
              }`}
            >
              Status: {investigation.status}
            </span>
          </div>
          <p className="view-description">
            Alert: <strong>{investigation.alert_title || investigation.alert_id}</strong> | Started at sim epoch{' '}
            <code>{investigation.started_at}</code>
          </p>
        </div>

        {/* Switch dropdown */}
        <select
          value={investigation.id}
          onChange={(e) => onSelectInvestigation(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            border: '1px solid var(--border-medium)',
            backgroundColor: 'var(--bg-card)',
            fontSize: 13,
            color: 'var(--text-main)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {investigations.map((inv) => (
            <option key={inv.id} value={inv.id}>
              {inv.id} - {inv.status}
            </option>
          ))}
        </select>
      </div>

      <div className="grid-2col">
        {/* Left Column: Forensic Story Timeline */}
        <div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Investigation Narrative Timeline</span>
              <span className="badge badge-neutral">Autonomous Agent Trace</span>
            </div>
            <div className="card-body">
              <div className="story-timeline">
                {/* Step 1: Alert Ingestion */}
                <div className="story-step">
                  <div className="story-step-dot" />
                  <div className="story-step-header">
                    <span className="story-step-title">1. Alert Ingestion & Target Resolution</span>
                    <span className="badge badge-neutral">Sim Epoch {investigation.started_at}</span>
                  </div>
                  <div className="story-step-content">
                    Ingested alert <code>{investigation.alert_id}</code>. Target entity resolved in FalkorDB entity
                    graph with temporal filters applied. Initial severity flagged as {investigation.severity || 'high'}.
                  </div>
                </div>

                {/* Step 2: Competing Hypotheses */}
                <div className="story-step">
                  <div className="story-step-dot" />
                  <div className="story-step-header">
                    <span className="story-step-title">2. Competing Hypotheses Formulation</span>
                    <span className="badge badge-neutral">{hyps.length} Formulated</span>
                  </div>
                  <div className="story-step-content">
                    {hyps.map((h) => (
                      <div
                        key={h.id}
                        style={{
                          marginBottom: 6,
                          padding: 6,
                          borderRadius: 6,
                          backgroundColor: '#f7f4ed',
                          fontSize: 12,
                        }}
                      >
                        <strong>{h.title}</strong> — Status: <code>{h.status}</code> (conf: {h.confidence})
                      </div>
                    ))}
                  </div>
                </div>

                {/* Step 3: Graph Traversal & Tool Trace */}
                <div className="story-step">
                  <div className="story-step-dot" />
                  <div className="story-step-header">
                    <span className="story-step-title">3. Tool-Driven Forensic Walk</span>
                    <span className="badge badge-neutral">
                      {investigation.tool_call_count || 6} Graph & Telemetry Queries
                    </span>
                  </div>
                  <div className="story-step-content">
                    <ul style={{ paddingLeft: 18, marginTop: 4 }}>
                      <li>Executed <code>process_tree</code> to trace process ancestry and parent kubectl exec session.</li>
                      <li>Executed <code>search_documents</code> & <code>k8s_audit</code> via Quarantined Reader.</li>
                      <li>Evaluated <code>blast_radius</code> and <code>find_convergence</code> on FalkorDB topology.</li>
                      <li>Checked temporal ChangeSets and active authorization baselines.</li>
                    </ul>
                  </div>
                </div>

                {/* Step 4: Evidence-Cited Verdict */}
                <div className="story-step">
                  <div className="story-step-dot" style={{ backgroundColor: isMalicious ? '#b83432' : '#297a48' }} />
                  <div className="story-step-header">
                    <span className="story-step-title">4. Evidence-Cited Verdict</span>
                    <span className={`badge ${isMalicious ? 'badge-malicious' : 'badge-benign'}`}>
                      {investigation.verdict ? investigation.verdict.toUpperCase() : 'PENDING'}
                    </span>
                  </div>
                  <div className="story-step-content">
                    <p style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: 8 }}>
                      {investigation.summary || 'Investigation in progress.'}
                    </p>
                    {investigation.claims && investigation.claims.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <strong style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                          Verified Claims:
                        </strong>
                        {investigation.claims.map((cl, i) => (
                          <div key={i} style={{ fontSize: 12, marginTop: 4, paddingLeft: 8, borderLeft: '2px solid var(--border-medium)' }}>
                            "{cl.text}"
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              Evidence: {cl.evidence_ids.join(', ')}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Step 5: Containment & Approvals */}
                {investigation.status === 'awaiting_approval' && (
                  <div className="story-step" style={{ backgroundColor: '#fffcf7', borderColor: '#e8be88' }}>
                    <div className="story-step-dot" style={{ backgroundColor: '#c07828' }} />
                    <div className="story-step-header">
                      <span className="story-step-title">5. Containment Action Proposed</span>
                      <span className="badge badge-pending">Human Approval Required</span>
                    </div>
                    <div className="story-step-content">
                      <p style={{ marginBottom: 12 }}>
                        Autonomous investigation verified malicious attack. Disruptive containment action requires
                        human approval under policy gateway.
                      </p>
                      <button className="btn btn-primary btn-sm" onClick={onNavigateToApprovals}>
                        Review Approval Request →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Evidence Subgraph & Audit Metadata */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Evidence Subgraph Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Evidence Subgraph (Cytoscape)</span>
              <span className="badge badge-neutral">Graph Walk</span>
            </div>
            <div className="card-body">
              <div ref={cyRef} className="cytoscape-box" />
              <div
                style={{
                  display: 'flex',
                  gap: 16,
                  marginTop: 12,
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  justifyContent: 'center',
                }}
              >
                <span>● Brown: Investigation</span>
                <span>● Amber: Hypothesis</span>
                <span>● Green: Verified Evidence</span>
              </div>
            </div>
          </div>

          {/* Audit Metrics Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Audit Log & Efficiency Metrics</span>
              <span className="badge badge-neutral">Deterministic Replay</span>
            </div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, textAlign: 'center' }}>
                <div style={{ padding: 12, backgroundColor: '#faf8f5', borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>STEPS</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{investigation.step_count || 3}</div>
                </div>
                <div style={{ padding: 12, backgroundColor: '#faf8f5', borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>TOOL CALLS</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{investigation.tool_call_count || 6}</div>
                </div>
                <div style={{ padding: 12, backgroundColor: '#faf8f5', borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>TOTAL TOKENS</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>
                    {(investigation.input_tokens || 0) + (investigation.output_tokens || 0)}
                  </div>
                </div>
                <div style={{ padding: 12, backgroundColor: '#faf8f5', borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>COST (USD)</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>${(investigation.cost_usd || 0).toFixed(4)}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
