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
        // Base Node Style (Light Warm Theme)
        {
          selector: 'node',
          style: {
            label: 'data(name)',
            color: '#292524',
            'font-size': '11px',
            'font-family': 'Plus Jakarta Sans, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'background-color': '#e7e5e0',
            'border-width': 2,
            'border-color': '#d6d2c7',
            width: 32,
            height: 32,
          },
        },
        // Workloads & Pods
        {
          selector: 'node[label = "Workload"]',
          style: {
            'background-color': '#0284c7',
            'border-color': '#0369a1',
            shape: 'round-rectangle',
            width: 38,
            height: 38,
            color: '#0c4a6e',
            'font-weight': 'bold',
          },
        },
        {
          selector: 'node[label = "Pod"]',
          style: {
            'background-color': '#38bdf8',
            'border-color': '#0284c7',
            shape: 'ellipse',
            width: 30,
            height: 30,
          },
        },
        // Principals & Identities
        {
          selector: 'node[label = "Principal"]',
          style: {
            'background-color': '#a855f7',
            'border-color': '#7e22ce',
            shape: 'diamond',
            width: 38,
            height: 38,
            color: '#581c87',
            'font-weight': 'bold',
          },
        },
        {
          selector: 'node[label = "Agent"]',
          style: {
            'background-color': '#d946ef',
            'border-color': '#a21caf',
            shape: 'round-diamond',
            width: 36,
            height: 36,
          },
        },
        {
          selector: 'node[label = "AgentSession"]',
          style: {
            'background-color': '#f43f5e',
            'border-color': '#be123c',
            shape: 'round-rectangle',
            width: 28,
            height: 28,
          },
        },
        {
          selector: 'node[label = "Tool"]',
          style: {
            'background-color': '#3b82f6',
            'border-color': '#1d4ed8',
            shape: 'round-triangle',
            width: 30,
            height: 30,
          },
        },
        // Sensitive Resources (Target Jewels)
        {
          selector: 'node[label = "SensitiveResource"]',
          style: {
            'background-color': '#ef4444',
            'border-color': '#b91c1c',
            'border-width': 3,
            shape: 'star',
            width: 44,
            height: 44,
            'font-weight': 'bold',
            color: '#991b1b',
          },
        },
        // Runtime Events
        {
          selector: 'node[label = "RuntimeEvent"]',
          style: {
            'background-color': '#f59e0b',
            'border-color': '#b45309',
            shape: 'triangle',
            width: 28,
            height: 28,
          },
        },
        // Policies & Enforcement
        {
          selector: 'node[label = "Policy"]',
          style: {
            'background-color': '#10b981',
            'border-color': '#047857',
            shape: 'tag',
            width: 32,
            height: 32,
          },
        },
        {
          selector: 'node[label = "EnforcementPoint"]',
          style: {
            'background-color': '#64748b',
            'border-color': '#334155',
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
            'line-color': '#a8a29e',
            'target-arrow-color': '#a8a29e',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            label: 'data(label)',
            'font-size': '8px',
            'font-family': 'JetBrains Mono, monospace',
            color: '#78716c',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        // Edge: Inferred Reachability
        {
          selector: 'edge[evidence_type = "inferred"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#0284c7',
            'target-arrow-color': '#0284c7',
          },
        },
        // Edge: Observed Telemetry
        {
          selector: 'edge[evidence_type = "observed"]',
          style: {
            'line-color': '#059669',
            'target-arrow-color': '#059669',
            width: 2.2,
          },
        },
        // Edge: Simulated Containment
        {
          selector: 'edge[evidence_type = "simulated"]',
          style: {
            'line-style': 'dotted',
            'line-color': '#d97706',
            'target-arrow-color': '#d97706',
          },
        },
        // Node selection highlight
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#b45309',
            'border-opacity': 1,
          } as any,
        },
      ],
      layout: {
        name: layoutName,
        animate: true,
        animationDuration: 500,
        padding: 40,
      } as any,
    });

    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      setSelectedNode(nodeData);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [nodes, edges, activeFilter, layoutName]);

  // Handle Search Filtering
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

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
        node.style('opacity', 0.15);
      }
    });
  }, [searchQuery]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 40);

  return (
    <div className="relative w-full h-[calc(100vh-106px)] bg-[#fbfaf8] overflow-hidden flex font-sans">
      {/* Main Cytoscape Canvas */}
      <div className="flex-1 relative h-full">
        <div ref={containerRef} className="w-full h-full" />

        {/* Floating Top Controls (Search & Category Filters) */}
        <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="flex items-center bg-white/95 backdrop-blur border border-[#e8e5de] rounded-lg px-3 py-1.5 text-xs text-stone-800 shadow-sm">
            <Search className="w-3.5 h-3.5 text-stone-400 mr-2" />
            <input
              type="text"
              placeholder="Search graph nodes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent focus:outline-none w-44 placeholder-stone-400"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="text-stone-400 hover:text-stone-700">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center space-x-1 bg-white/95 backdrop-blur border border-[#e8e5de] rounded-lg p-1 text-xs shadow-sm">
            <Filter className="w-3 h-3 text-stone-400 ml-1.5 mr-1" />
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
                    ? 'bg-stone-900 text-white shadow-sm'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Floating Bottom-Left Controls (Zoom, Fit, Layout) */}
        <div className="absolute bottom-4 left-4 z-10 flex items-center space-x-2 bg-white/95 backdrop-blur border border-[#e8e5de] rounded-lg p-1 shadow-sm">
          <button
            onClick={handleZoomIn}
            className="p-1.5 text-stone-600 hover:text-stone-900 rounded hover:bg-stone-100 transition cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-1.5 text-stone-600 hover:text-stone-900 rounded hover:bg-stone-100 transition cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleFit}
            className="p-1.5 text-stone-600 hover:text-stone-900 rounded hover:bg-stone-100 transition cursor-pointer"
            title="Fit to Canvas"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <div className="h-4 w-[1px] bg-stone-200 mx-1" />
          <select
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value as any)}
            className="bg-transparent text-stone-700 text-xs focus:outline-none cursor-pointer pr-1"
            title="Change Layout Algorithm"
          >
            <option value="cose">COSE Physics</option>
            <option value="concentric">Concentric Rings</option>
            <option value="breadthfirst">Hierarchy Tree</option>
            <option value="grid">Grid</option>
          </select>
        </div>

        {/* Graph Legend Overlay */}
        <div className="absolute bottom-4 right-4 z-10 hidden sm:flex items-center space-x-3 bg-white/95 backdrop-blur border border-[#e8e5de] rounded-lg px-3 py-1.5 text-[11px] text-stone-600 shadow-sm">
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-sky-500" />
            <span>Workload</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded bg-purple-500" />
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
          <div className="flex items-center space-x-1 border-l border-stone-200 pl-2">
            <span className="w-3 h-0.5 border-t border-stone-400" />
            <span>Configured</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-3 h-0.5 border-t border-dashed border-sky-500" />
            <span>Inferred</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-3 h-0.5 border-t border-emerald-600" />
            <span>Observed</span>
          </div>
        </div>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <aside className="w-96 bg-white border-l border-[#e8e5de] h-full overflow-y-auto p-5 shadow-xl z-20 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between pb-3 border-b border-stone-100">
              <div>
                <span className="text-[10px] font-mono uppercase bg-stone-100 text-stone-700 border border-stone-200 px-1.5 py-0.5 rounded font-semibold">
                  {selectedNode.label}
                </span>
                <h3 className="text-base font-semibold text-stone-900 mt-1.5 truncate">
                  {selectedNode.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-stone-400 hover:text-stone-700 p-1 rounded hover:bg-stone-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Properties List */}
            <div className="mt-4 space-y-3 text-xs">
              <div>
                <span className="text-stone-500 block font-mono text-[11px]">ID</span>
                <span className="font-mono text-stone-800 select-all bg-[#faf8f5] px-2 py-1 rounded block mt-0.5 border border-[#ede9df]">
                  {selectedNode.id}
                </span>
              </div>

              {selectedNode.status && (
                <div className="flex justify-between items-center py-1.5 border-b border-stone-100">
                  <span className="text-stone-500">Status</span>
                  <span className="font-mono text-emerald-700 font-semibold">{selectedNode.status}</span>
                </div>
              )}

              {selectedNode.sensitivity && selectedNode.sensitivity !== 'NONE' && (
                <div className="flex justify-between items-center py-1.5 border-b border-stone-100">
                  <span className="text-stone-500">Sensitivity</span>
                  <span className="font-mono font-bold text-rose-700 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded">
                    {selectedNode.sensitivity}
                  </span>
                </div>
              )}

              {selectedNode.severity && selectedNode.severity !== 'NONE' && (
                <div className="flex justify-between items-center py-1.5 border-b border-stone-100">
                  <span className="text-stone-500">Severity</span>
                  <span className="font-mono font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                    {selectedNode.severity}
                  </span>
                </div>
              )}

              {selectedNode.command_line && (
                <div className="mt-2">
                  <span className="text-stone-500 block font-mono text-[11px]">Command Line</span>
                  <pre className="font-mono text-[11px] bg-[#faf8f5] p-2 rounded text-stone-800 mt-1 overflow-x-auto border border-[#ede9df]">
                    {selectedNode.command_line}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="mt-6 pt-4 border-t border-stone-100 space-y-2">
            {onSelectNodeForBlastRadius && (selectedNode.label === 'Workload' || selectedNode.label === 'Pod') && (
              <button
                onClick={() => onSelectNodeForBlastRadius(selectedNode.id)}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-stone-900 hover:bg-stone-800 text-white rounded-lg text-xs font-medium transition cursor-pointer"
              >
                <span>Analyze Blast Radius</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {onSelectNodeForContainment && (
              <button
                onClick={() => onSelectNodeForContainment(selectedNode.id)}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-white hover:bg-stone-50 text-stone-700 border border-stone-300 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                <Shield className="w-3.5 h-3.5 text-stone-500" />
                <span>Simulate Containment</span>
              </button>
            )}
          </div>
        </aside>
      )}
    </div>
  );
};
