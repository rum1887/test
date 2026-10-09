import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Search,
  X,
  Shield,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { CytoscapeNode, CytoscapeEdge } from '../api/client';

interface GraphViewProps {
  nodes: CytoscapeNode[];
  edges: CytoscapeEdge[];
  onSelectNodeForBlastRadius?: (nodeId: string) => void;
  onSelectNodeForContainment?: (nodeId: string) => void;
}

export const GraphView: React.FC<GraphViewProps> = ({
  nodes,
  edges,
  onSelectNodeForBlastRadius,
  onSelectNodeForContainment,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [selectedNode, setSelectedNode] = useState<CytoscapeNode['data'] | null>(null);
  const [layoutName, setLayoutName] = useState<'cose' | 'concentric' | 'breadthfirst' | 'grid'>('cose');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  useEffect(() => {
    if (!containerRef.current) return;

    // Filter elements based on active category filter
    const filteredNodes = nodes.filter((n) => {
      if (activeFilter === 'ALL') return true;
      if (activeFilter === 'WORKLOAD') return n.data.category === 'workload';
      if (activeFilter === 'AGENT') return n.data.category === 'agent' || n.data.label === 'Principal';
      if (activeFilter === 'SENSITIVE') return n.data.category === 'sensitive';
      if (activeFilter === 'EVENT') return n.data.category === 'event';
      if (activeFilter === 'POLICY') return n.data.category === 'policy';
      return true;
    });

    const nodeIds = new Set(filteredNodes.map((n) => n.data.id));
    const filteredEdges = edges.filter(
      (e) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target)
    );

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...filteredNodes, ...filteredEdges],
      style: [
        // Base Node Style
        {
          selector: 'node',
          style: {
            label: 'data(name)',
            color: '#e2e8f0',
            'font-size': '11px',
            'font-family': 'Plus Jakarta Sans, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'background-color': '#334155',
            'border-width': 2,
            'border-color': '#1e293b',
            width: 32,
            height: 32,
          },
        },
        // Workloads & Pods
        {
          selector: 'node[label = "Workload"]',
          style: {
            'background-color': '#0284c7',
            'border-color': '#38bdf8',
            shape: 'round-rectangle',
            width: 38,
            height: 38,
          },
        },
        {
          selector: 'node[label = "Pod"]',
          style: {
            'background-color': '#0369a1',
            'border-color': '#7dd3fc',
            shape: 'ellipse',
            width: 30,
            height: 30,
          },
        },
        // Principals & Identities
        {
          selector: 'node[label = "Principal"]',
          style: {
            'background-color': '#9333ea',
            'border-color': '#c084fc',
            shape: 'diamond',
            width: 38,
            height: 38,
          },
        },
        {
          selector: 'node[label = "Agent"]',
          style: {
            'background-color': '#db2777',
            'border-color': '#f472b6',
            shape: 'round-diamond',
            width: 36,
            height: 36,
          },
        },
        {
          selector: 'node[label = "AgentSession"]',
          style: {
            'background-color': '#e11d48',
            'border-color': '#fb7185',
            shape: 'round-rectangle',
            width: 28,
            height: 28,
          },
        },
        {
          selector: 'node[label = "Tool"]',
          style: {
            'background-color': '#2563eb',
            'border-color': '#60a5fa',
            shape: 'round-triangle',
            width: 30,
            height: 30,
          },
        },
        // Sensitive Resources (Target Jewels)
        {
          selector: 'node[label = "SensitiveResource"]',
          style: {
            'background-color': '#dc2626',
            'border-color': '#f87171',
            'border-width': 3,
            shape: 'star',
            width: 44,
            height: 44,
            'font-weight': 'bold',
            color: '#fca5a5',
          },
        },
        // Runtime Events
        {
          selector: 'node[label = "RuntimeEvent"]',
          style: {
            'background-color': '#d97706',
            'border-color': '#fbbf24',
            shape: 'triangle',
            width: 28,
            height: 28,
          },
        },
        // Policies & Enforcement
        {
          selector: 'node[label = "Policy"]',
          style: {
            'background-color': '#059669',
            'border-color': '#34d399',
            shape: 'tag',
            width: 32,
            height: 32,
          },
        },
        {
          selector: 'node[label = "EnforcementPoint"]',
          style: {
            'background-color': '#475569',
            'border-color': '#94a3b8',
            shape: 'hexagon',
            width: 34,
            height: 34,
          },
        },
        // Base Edge Style
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            label: 'data(label)',
            'font-size': '8px',
            'font-family': 'JetBrains Mono, monospace',
            color: '#64748b',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        // Edge: Inferred Reachability (Dashed Cyan)
        {
          selector: 'edge[evidence_type = "inferred"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#0284c7',
            'target-arrow-color': '#0284c7',
          },
        },
        // Edge: Observed Telemetry (Emerald)
        {
          selector: 'edge[evidence_type = "observed"]',
          style: {
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            width: 2.2,
          },
        },
        // Edge: Simulated Containment (Dotted Amber)
        {
          selector: 'edge[evidence_type = "simulated"]',
          style: {
            'line-style': 'dotted',
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
          },
        },
        // Node selection highlight
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#facc15',
          },
        },
      ],
      layout: {
        name: layoutName,
        animate: false,
        padding: 50,
      },
    });

    // Handle node selection click
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedNode(node.data());
    });

    // Deselect click on canvas background
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [nodes, edges, layoutName, activeFilter]);

  // Handle Search Query Highlight
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    if (!searchQuery.trim()) {
      cy.nodes().style('opacity', 1);
      cy.edges().style('opacity', 1);
      return;
    }
    const q = searchQuery.toLowerCase();
    cy.nodes().forEach((node) => {
      const name = String(node.data('name') || '').toLowerCase();
      const id = String(node.data('id') || '').toLowerCase();
      const label = String(node.data('label') || '').toLowerCase();
      if (name.includes(q) || id.includes(q) || label.includes(q)) {
        node.style('opacity', 1);
      } else {
        node.style('opacity', 0.2);
      }
    });
  }, [searchQuery]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 40);

  return (
    <div className="relative w-full h-[calc(100vh-106px)] bg-[#070b14] overflow-hidden flex">
      {/* Main Cytoscape Canvas */}
      <div className="flex-1 relative h-full">
        <div ref={containerRef} className="w-full h-full" />

        {/* Floating Top Controls (Search & Category Filters) */}
        <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="flex items-center bg-[#0d1322]/90 backdrop-blur border border-[#1e2942] rounded-md px-2.5 py-1.5 text-xs text-slate-200 shadow-lg">
            <Search className="w-3.5 h-3.5 text-slate-400 mr-2" />
            <input
              type="text"
              placeholder="Search graph nodes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent focus:outline-none w-44 placeholder-slate-500"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="text-slate-400 hover:text-white">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center space-x-1 bg-[#0d1322]/90 backdrop-blur border border-[#1e2942] rounded-md p-1 text-xs shadow-lg">
            <Filter className="w-3 h-3 text-slate-400 ml-1.5 mr-1" />
            {[
              { id: 'ALL', label: 'All' },
              { id: 'WORKLOAD', label: 'Workloads' },
              { id: 'AGENT', label: 'Agents' },
              { id: 'SENSITIVE', label: 'Sensitive' },
              { id: 'EVENT', label: 'Events' },
              { id: 'POLICY', label: 'Policies' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  activeFilter === f.id
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Floating Bottom-Left Controls (Zoom, Fit, Layout) */}
        <div className="absolute bottom-4 left-4 z-10 flex items-center space-x-2 bg-[#0d1322]/90 backdrop-blur border border-[#1e2942] rounded-md p-1 shadow-lg">
          <button
            onClick={handleZoomIn}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-[#192540] transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-[#192540] transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleFit}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-[#192540] transition"
            title="Fit to Canvas"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <div className="h-4 w-[1px] bg-[#1e2942] mx-1" />
          <select
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value as any)}
            className="bg-transparent text-slate-300 text-xs focus:outline-none cursor-pointer pr-1"
            title="Change Layout Algorithm"
          >
            <option value="cose" className="bg-[#0d1322]">COSE Physics</option>
            <option value="concentric" className="bg-[#0d1322]">Concentric Rings</option>
            <option value="breadthfirst" className="bg-[#0d1322]">Hierarchy Tree</option>
            <option value="grid" className="bg-[#0d1322]">Grid</option>
          </select>
        </div>

        {/* Graph Legend Overlay */}
        <div className="absolute bottom-4 right-4 z-10 hidden sm:flex items-center space-x-3 bg-[#0d1322]/90 backdrop-blur border border-[#1e2942] rounded-md px-3 py-1.5 text-[11px] text-slate-400 shadow-lg">
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-sky-500" />
            <span>Workload</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-pink-500" />
            <span>Agent</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-rose-500" />
            <span>Sensitive</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-amber-500" />
            <span>Event</span>
          </div>
          <div className="flex items-center space-x-1 border-l border-slate-700 pl-2">
            <span className="w-3 h-0.5 border-t border-slate-400" />
            <span>Configured</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-3 h-0.5 border-t border-dashed border-sky-400" />
            <span>Inferred</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-3 h-0.5 border-t border-emerald-400" />
            <span>Observed</span>
          </div>
        </div>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <aside className="w-96 bg-[#0d1322] border-l border-[#1e2942] h-full overflow-y-auto p-5 shadow-2xl z-20 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between pb-3 border-b border-[#1e2942]">
              <div>
                <span className="text-[10px] font-mono uppercase bg-[#1a253e] text-sky-300 border border-sky-800/60 px-1.5 py-0.5 rounded">
                  {selectedNode.label}
                </span>
                <h3 className="text-base font-semibold text-white mt-1.5 truncate">
                  {selectedNode.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#1a253e]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Properties List */}
            <div className="mt-4 space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block font-mono text-[11px]">ID</span>
                <span className="font-mono text-slate-200 select-all bg-[#121a2d] px-1.5 py-0.5 rounded block mt-0.5">
                  {selectedNode.id}
                </span>
              </div>

              {selectedNode.status && (
                <div className="flex justify-between items-center py-1 border-b border-[#151f33]">
                  <span className="text-slate-400">Status</span>
                  <span className="font-mono text-emerald-400 font-medium">{selectedNode.status}</span>
                </div>
              )}

              {selectedNode.sensitivity && selectedNode.sensitivity !== 'NONE' && (
                <div className="flex justify-between items-center py-1 border-b border-[#151f33]">
                  <span className="text-slate-400">Sensitivity</span>
                  <span className="font-mono font-bold text-rose-400 bg-rose-950/60 border border-rose-800/60 px-1.5 py-0.5 rounded">
                    {selectedNode.sensitivity}
                  </span>
                </div>
              )}

              {selectedNode.severity && selectedNode.severity !== 'NONE' && (
                <div className="flex justify-between items-center py-1 border-b border-[#151f33]">
                  <span className="text-slate-400">Severity</span>
                  <span className="font-mono font-bold text-amber-400 bg-amber-950/60 border border-amber-800/60 px-1.5 py-0.5 rounded">
                    {selectedNode.severity}
                  </span>
                </div>
              )}

              {selectedNode.command_line && (
                <div className="mt-2">
                  <span className="text-slate-400 block font-mono text-[11px]">Command Line</span>
                  <pre className="font-mono text-[11px] bg-[#121a2d] p-2 rounded text-slate-300 mt-1 overflow-x-auto border border-[#1e2942]">
                    {selectedNode.command_line}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="mt-6 pt-4 border-t border-[#1e2942] space-y-2">
            {onSelectNodeForBlastRadius && (selectedNode.label === 'Workload' || selectedNode.label === 'Pod') && (
              <button
                onClick={() => onSelectNodeForBlastRadius(selectedNode.id)}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold transition cursor-pointer"
              >
                <span>Analyze Blast Radius</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {onSelectNodeForContainment && (
              <button
                onClick={() => onSelectNodeForContainment(selectedNode.id)}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-[#192540] hover:bg-[#223154] text-slate-200 border border-[#2b3c66] rounded text-xs font-semibold transition cursor-pointer"
              >
                <Shield className="w-3.5 h-3.5 text-amber-400" />
                <span>Simulate Containment</span>
              </button>
            )}
          </div>
        </aside>
      )}
    </div>
  );
};
