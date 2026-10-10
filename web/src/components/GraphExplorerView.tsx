import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { SubgraphData } from '../types';

interface GraphExplorerViewProps {
  subgraph: SubgraphData | null;
  onSearchNode: (nodeId: string, depth: number) => void;
  isLoading: boolean;
}

export const GraphExplorerView: React.FC<GraphExplorerViewProps> = ({
  subgraph,
  onSearchNode,
  isLoading,
}) => {
  const cyRef = useRef<HTMLDivElement>(null);
  const [searchInput, setSearchInput] = useState<string>('pod-checkout-1');
  const [depth, setDepth] = useState<number>(2);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  const presets = [
    { label: 'Checkout Pod', id: 'pod-checkout-1' },
    { label: 'Customer Vault Secret', id: 'sr-customer-vault' },
    { label: 'Billing SA', id: 'sa-billing' },
    { label: 'Payment DB', id: 'sr-payment-db' },
    { label: 'Cloud IAM Secrets', id: 'sr-cloud-iam' },
  ];

  useEffect(() => {
    if (!cyRef.current || !subgraph) return;

    const elements = [...subgraph.nodes, ...subgraph.edges];

    const cy = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-size': '11px',
            'font-family': 'Plus Jakarta Sans, sans-serif',
            color: '#24211e',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#d8d0c0',
            width: 30,
            height: 30,
          },
        },
        {
          selector: 'node[type = "Pod"]',
          style: { 'background-color': '#4a7c59' },
        },
        {
          selector: 'node[type = "Workload"]',
          style: { 'background-color': '#33658a' },
        },
        {
          selector: 'node[type = "ServiceAccount"]',
          style: { 'background-color': '#f26419' },
        },
        {
          selector: 'node[type = "AgentSession"]',
          style: { 'background-color': '#8f2d56' },
        },
        {
          selector: 'node[type = "SensitiveResource"]',
          style: { 'background-color': '#b83432', width: 38, height: 38 },
        },
        {
          selector: 'node[type = "Alert"]',
          style: { 'background-color': '#c07828', width: 34, height: 34 },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#c9c0ae',
            'target-arrow-color': '#9e9481',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9px',
            color: '#736b63',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 24,
      },
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedNode({
        id: node.id(),
        label: node.data('label'),
        type: node.data('type'),
      });
    });

    return () => {
      cy.destroy();
    };
  }, [subgraph]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      onSearchNode(searchInput.trim(), depth);
    }
  };

  return (
    <div className="graph-explorer-view">
      <div className="view-header">
        <h1 className="view-title">FalkorDB Connected Security Graph</h1>
        <p className="view-description">
          Explore entities, relationships, temporal edges, and reachability paths across the live FalkorDB security graph.
        </p>
      </div>

      {/* Control bar */}
      <div
        className="card"
        style={{
          marginBottom: 20,
          padding: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Entity ID (e.g. pod-checkout-1)"
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              border: '1px solid var(--border-medium)',
              fontSize: 13,
              fontFamily: 'var(--font-mono)',
              width: 240,
            }}
          />
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            style={{
              padding: '8px 12px',
              borderRadius: 8,
              border: '1px solid var(--border-medium)',
              fontSize: 13,
            }}
          >
            <option value={1}>1 Hop</option>
            <option value={2}>2 Hops</option>
            <option value={3}>3 Hops</option>
          </select>
          <button type="submit" className="btn btn-primary btn-sm" disabled={isLoading}>
            Explore Subgraph
          </button>
        </form>

        {/* Quick Presets */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Presets:</span>
          {presets.map((p) => (
            <button
              key={p.id}
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSearchInput(p.id);
                onSearchNode(p.id, depth);
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Canvas with Node Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 20 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              Interactive Topology Visualization ({subgraph?.nodes.length || 0} Nodes,{' '}
              {subgraph?.edges.length || 0} Edges)
            </span>
            <span className="badge badge-neutral">Cytoscape Engine</span>
          </div>
          <div className="card-body">
            <div ref={cyRef} style={{ width: '100%', height: '560px', backgroundColor: '#faf8f5', borderRadius: 10 }} />
            <div
              style={{
                display: 'flex',
                gap: 16,
                marginTop: 12,
                fontSize: 11,
                color: 'var(--text-muted)',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <span>● Green: Pod</span>
              <span>● Blue: Workload</span>
              <span>● Orange: ServiceAccount</span>
              <span>● Purple: AgentSession</span>
              <span>● Red: SensitiveResource</span>
              <span>● Amber: Alert</span>
            </div>
          </div>
        </div>

        {/* Node Inspector Drawer */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Entity Inspector</span>
          </div>
          <div className="card-body">
            {selectedNode ? (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <span className="badge badge-neutral">{selectedNode.type}</span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{selectedNode.label}</h3>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                  <strong>FalkorDB ID:</strong> <code>{selectedNode.id}</code>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ width: '100%', marginBottom: 12 }}
                  onClick={() => onSearchNode(selectedNode.id, depth)}
                >
                  Focus This Entity →
                </button>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)', fontSize: 13 }}>
                Click any node in the graph to inspect its properties and connected neighborhood.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
