import React, { useState, useEffect } from 'react';
import {
  Users,
  Shield,
  Bot,
  Server,
  Wrench,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ArrowRight,
  ExternalLink,
  Layers,
  Sparkles,
  Database,
  Radio,
} from 'lucide-react';
import { api, CytoscapeNode, CytoscapeEdge } from '../api/client';

interface TrustStoreViewProps {
  onNavigateToFirewall: (toolName?: string, identityId?: string) => void;
}

export const TrustStoreView: React.FC<TrustStoreViewProps> = ({ onNavigateToFirewall }) => {
  const [inventory, setInventory] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'identities' | 'roles' | 'agents' | 'tools' | 'services'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals for dynamic live mutations
  const [showToolModal, setShowToolModal] = useState(false);
  const [showUserModal, setShowUserModal] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New Tool Form State
  const [newTool, setNewTool] = useState({
    name: '',
    risk_level: 'MEDIUM',
    operation_type: 'READ_ONLY',
    is_destructive: false,
    required_role: 'Operations & Compliance Lead',
    target_resource_id: 'sr-financial-db',
    description: '',
  });

  // New User Form State
  const [newUser, setNewUser] = useState({
    username: '',
    full_name: '',
    email: '',
    role: 'Security Analyst',
    permissions: ['audit_read', 'report_generate'],
    assign_agent_id: 'agent-autodev',
  });

  useEffect(() => {
    loadInventory();
  }, []);

  const showNotice = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadInventory = async () => {
    try {
      setLoading(true);
      const data = await api.getTrustStoreInventory();
      setInventory(data);
    } catch (err: any) {
      console.error('Failed to load trust store inventory:', err);
      showNotice('error', 'Could not fetch dynamic inventory from graph');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterTool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTool.name.trim()) return;
    try {
      const res = await api.registerTrustStoreTool({
        name: newTool.name.trim(),
        risk_level: newTool.risk_level,
        is_destructive: newTool.is_destructive,
        operation_type: newTool.operation_type,
        required_role: newTool.required_role,
        target_resource_id: newTool.target_resource_id,
        description: newTool.description || `Registered tool ${newTool.name}`,
      });
      showNotice('success', res.message || `Tool '${newTool.name}' registered into graph!`);
      setShowToolModal(false);
      setNewTool({
        name: '',
        risk_level: 'MEDIUM',
        operation_type: 'READ_ONLY',
        is_destructive: false,
        required_role: 'Operations & Compliance Lead',
        target_resource_id: 'sr-financial-db',
        description: '',
      });
      await loadInventory();
    } catch (err: any) {
      showNotice('error', 'Failed to register tool into graph');
    }
  };

  const handleRegisterUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUser.username.trim() || !newUser.full_name.trim()) return;
    try {
      const res = await api.registerTrustStoreIdentity({
        username: newUser.username.trim(),
        full_name: newUser.full_name.trim(),
        email: newUser.email || `${newUser.username}@acme.corp`,
        role: newUser.role,
        permissions: newUser.permissions,
        assign_agent_id: newUser.assign_agent_id,
      });
      showNotice('success', res.message || `User '${newUser.full_name}' detected & added to graph!`);
      setShowUserModal(false);
      setNewUser({
        username: '',
        full_name: '',
        email: '',
        role: 'Security Analyst',
        permissions: ['audit_read', 'report_generate'],
        assign_agent_id: 'agent-autodev',
      });
      await loadInventory();
    } catch (err: any) {
      showNotice('error', 'Failed to register identity into graph');
    }
  };

  const handleScanFleet = async () => {
    try {
      setScanning(true);
      const res = await api.scanAndReloadFleet();
      showNotice('success', res.message || 'Fleet scanned: new tools and servers synced into graph!');
      await loadInventory();
    } catch (err: any) {
      showNotice('error', 'Fleet scan failed');
    } finally {
      setScanning(false);
    }
  };

  const summary = inventory?.summary || {
    total_identities: 0,
    total_roles: 0,
    total_agents: 0,
    total_services: 0,
    total_tools: 0,
  };

  // Filter items based on active tab and search query
  const identities = (inventory?.identities || []).filter((i: any) =>
    i.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    i.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
    i.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const roles = (inventory?.roles || []).filter((r: any) =>
    r.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const agents = (inventory?.agents || []).filter((a: any) =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tools = (inventory?.tools || []).filter((t: any) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.risk_level.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const services = (inventory?.services || []).filter((s: any) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.sensitivity_level.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-20 right-6 z-50 px-4 py-3 rounded-xl shadow-lg border flex items-center space-x-2 text-xs font-medium animate-in fade-in slide-in-from-top-2 ${
          notification.type === 'success'
            ? 'bg-emerald-900 border-emerald-700 text-emerald-100'
            : 'bg-rose-900 border-rose-700 text-rose-100'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-300" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-300" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Hero Header */}
      <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center space-x-2.5 mb-2">
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-[#ede7da] text-stone-800 border border-[#ded7c8]">
                <Radio className="w-3 h-3 text-emerald-600 animate-pulse" />
                <span>DYNAMIC GRAPH STORE</span>
              </span>
              <span className="text-stone-400">&bull;</span>
              <span className="text-xs text-stone-500 font-mono">FalkorDB v1.0.0</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900">
              Trust Store & Living Knowledge Graph
            </h1>
            <p className="mt-1.5 text-sm text-stone-600 max-w-2xl">
              Dynamic real-time storage of Identities, RBAC Roles, AI Agents, Services, and MCP Tools.
              Whenever a tool is registered, user detected, or server reloaded, the graph updates automatically.
            </p>
          </div>

          {/* Dynamic Mutation Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setShowToolModal(true)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-stone-900 hover:bg-stone-800 text-stone-50 text-xs font-semibold shadow-sm transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register Tool</span>
            </button>

            <button
              onClick={() => setShowUserModal(true)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-[#ede7da] hover:bg-[#ded4c0] text-stone-900 text-xs font-semibold border border-[#ded7c8] shadow-2xs transition cursor-pointer"
            >
              <Users className="w-3.5 h-3.5 text-stone-700" />
              <span>Detect New User</span>
            </button>

            <button
              onClick={handleScanFleet}
              disabled={scanning}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-[#ede7da] hover:bg-[#ded4c0] text-stone-900 text-xs font-semibold border border-[#ded7c8] shadow-2xs transition cursor-pointer disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-stone-700 ${scanning ? 'animate-spin' : ''}`} />
              <span>{scanning ? 'Scanning Fleet...' : 'Reload & Discover Servers'}</span>
            </button>
          </div>
        </div>

        {/* Dynamic Topology Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 mt-8 pt-6 border-t border-[#ded7c8]">
          <div
            onClick={() => setActiveTab('identities')}
            className={`p-3.5 rounded-xl border transition cursor-pointer ${
              activeTab === 'identities'
                ? 'bg-[#ffffff] border-stone-800 shadow-xs'
                : 'bg-[#faf7f0] border-[#ded7c8] hover:bg-[#ffffff]'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
              <span>Identities & Users</span>
              <Users className="w-3.5 h-3.5 text-blue-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {summary.total_identities}
            </div>
            <div className="text-[10px] text-stone-500 mt-0.5">Active principals</div>
          </div>

          <div
            onClick={() => setActiveTab('roles')}
            className={`p-3.5 rounded-xl border transition cursor-pointer ${
              activeTab === 'roles'
                ? 'bg-[#ffffff] border-stone-800 shadow-xs'
                : 'bg-[#faf7f0] border-[#ded7c8] hover:bg-[#ffffff]'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
              <span>RBAC Roles</span>
              <Shield className="w-3.5 h-3.5 text-violet-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {summary.total_roles}
            </div>
            <div className="text-[10px] text-stone-500 mt-0.5">Least-privilege scopes</div>
          </div>

          <div
            onClick={() => setActiveTab('agents')}
            className={`p-3.5 rounded-xl border transition cursor-pointer ${
              activeTab === 'agents'
                ? 'bg-[#ffffff] border-stone-800 shadow-xs'
                : 'bg-[#faf7f0] border-[#ded7c8] hover:bg-[#ffffff]'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
              <span>AI Agents</span>
              <Bot className="w-3.5 h-3.5 text-amber-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {summary.total_agents}
            </div>
            <div className="text-[10px] text-stone-500 mt-0.5">Autonomous fleet</div>
          </div>

          <div
            onClick={() => setActiveTab('services')}
            className={`p-3.5 rounded-xl border transition cursor-pointer ${
              activeTab === 'services'
                ? 'bg-[#ffffff] border-stone-800 shadow-xs'
                : 'bg-[#faf7f0] border-[#ded7c8] hover:bg-[#ffffff]'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
              <span>Protected Infra</span>
              <Server className="w-3.5 h-3.5 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {summary.total_services}
            </div>
            <div className="text-[10px] text-stone-500 mt-0.5">Databases & Vaults</div>
          </div>

          <div
            onClick={() => setActiveTab('tools')}
            className={`p-3.5 rounded-xl border transition cursor-pointer ${
              activeTab === 'tools'
                ? 'bg-[#ffffff] border-stone-800 shadow-xs'
                : 'bg-[#faf7f0] border-[#ded7c8] hover:bg-[#ffffff]'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
              <span>MCP Tools</span>
              <Wrench className="w-3.5 h-3.5 text-rose-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-stone-900">
              {summary.total_tools}
            </div>
            <div className="text-[10px] text-stone-500 mt-0.5">Catalog operations</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Tab Filters */}
        <div className="flex items-center space-x-1.5 p-1 bg-[#faf7f0] border border-[#ded7c8] rounded-xl overflow-x-auto text-xs">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'all'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            All Entities
          </button>
          <button
            onClick={() => setActiveTab('identities')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'identities'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            Identities ({identities.length})
          </button>
          <button
            onClick={() => setActiveTab('roles')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'roles'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            Roles & RBAC ({roles.length})
          </button>
          <button
            onClick={() => setActiveTab('agents')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'agents'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            Agents ({agents.length})
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'tools'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            MCP Tools ({tools.length})
          </button>
          <button
            onClick={() => setActiveTab('services')}
            className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              activeTab === 'services'
                ? 'bg-stone-900 text-stone-50 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7da]'
            }`}
          >
            Services ({services.length})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative min-w-[260px]">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search graph entities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#faf7f0] border border-[#ded7c8] rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-stone-800 placeholder-stone-400 focus:outline-hidden focus:border-stone-800 focus:bg-white shadow-2xs"
          />
        </div>
      </div>

      {/* Main Inventory Sections */}
      <div className="space-y-8">
        {/* Section 1: Identities & RBAC */}
        {(activeTab === 'all' || activeTab === 'identities' || activeTab === 'roles') && (
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Users className="w-5 h-5 text-blue-600" />
                <h2 className="text-base font-semibold text-stone-900">
                  Identities, Principals & Active Delegations
                </h2>
              </div>
              <span className="text-xs text-stone-500 font-mono">
                {identities.length} Verified Principals
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {identities.map((ident: any) => (
                <div
                  key={ident.id}
                  className="bg-white border border-[#ded7c8] rounded-xl p-4 space-y-3 hover:border-stone-400 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-sm text-stone-900">{ident.name}</div>
                      <div className="text-[11px] font-mono text-stone-500">{ident.id}</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      {ident.status}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-[#f0ede6] space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-stone-500">RBAC Role:</span>
                      <span className="font-medium text-stone-800">{ident.role}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-stone-500">Delegated Agent:</span>
                      <span className="font-mono text-[11px] text-amber-700">
                        {ident.delegated_agents?.[0] || 'agent-autodev'}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[#f0ede6]">
                    <div className="text-[11px] text-stone-500 mb-1.5">Granted Scopes & Permissions:</div>
                    <div className="flex flex-wrap gap-1">
                      {ident.permissions.map((p: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#f5f0e8] text-stone-700 border border-[#ded7c8]"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => onNavigateToFirewall(undefined, ident.id)}
                    className="w-full mt-2 inline-flex items-center justify-center space-x-1.5 py-1.5 rounded-lg bg-[#f5f0e8] hover:bg-[#ede7da] text-stone-800 text-[11px] font-medium border border-[#ded7c8] transition cursor-pointer"
                  >
                    <span>Test In AI Firewall</span>
                    <ArrowRight className="w-3 h-3 text-stone-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 2: AI Agents Fleet */}
        {(activeTab === 'all' || activeTab === 'agents') && (
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-amber-600" />
                <h2 className="text-base font-semibold text-stone-900">
                  Autonomous AI Agents & Active Frameworks
                </h2>
              </div>
              <span className="text-xs text-stone-500 font-mono">
                {agents.length} Online Agents
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agents.map((agent: any) => (
                <div
                  key={agent.id}
                  className="bg-white border border-[#ded7c8] rounded-xl p-4 space-y-3 hover:border-stone-400 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-sm text-stone-900 flex items-center space-x-2">
                        <span>{agent.name}</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      </div>
                      <div className="text-[11px] font-mono text-stone-500">{agent.id}</div>
                    </div>
                    <span className="text-[11px] font-mono bg-[#f5f0e8] text-stone-700 px-2 py-0.5 rounded border border-[#ded7c8]">
                      {agent.endpoint}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-[#f0ede6]">
                    <div>
                      <span className="text-stone-500 block text-[11px]">Framework</span>
                      <span className="font-medium text-stone-800">{agent.framework}</span>
                    </div>
                    <div>
                      <span className="text-stone-500 block text-[11px]">Model Engine</span>
                      <span className="font-mono text-stone-800">{agent.model}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[#f0ede6]">
                    <span className="text-[11px] text-stone-500 block mb-1">Permitted Tool Scopes in Graph:</span>
                    <div className="flex flex-wrap gap-1">
                      {agent.allowed_scopes.map((s: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-50 text-amber-900 border border-amber-200"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 3: Registered MCP Tools */}
        {(activeTab === 'all' || activeTab === 'tools') && (
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Wrench className="w-5 h-5 text-rose-600" />
                <h2 className="text-base font-semibold text-stone-900">
                  Registered MCP Tools & Operation Boundaries
                </h2>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowToolModal(true)}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-stone-900 text-stone-100 text-xs font-medium hover:bg-stone-800 transition cursor-pointer"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Tool</span>
                </button>
                <span className="text-xs text-stone-500 font-mono">
                  {tools.length} Tools in Graph
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#ded7c8] text-stone-500">
                    <th className="pb-2.5 font-medium">Tool Name</th>
                    <th className="pb-2.5 font-medium">Risk Level</th>
                    <th className="pb-2.5 font-medium">Type</th>
                    <th className="pb-2.5 font-medium">MCP Gateway</th>
                    <th className="pb-2.5 font-medium">Target Resource</th>
                    <th className="pb-2.5 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f0ede6]">
                  {tools.map((t: any) => (
                    <tr key={t.id} className="hover:bg-white/60 transition">
                      <td className="py-2.5 font-mono font-medium text-stone-900">
                        {t.name}
                      </td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          t.risk_level === 'CRITICAL'
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : t.risk_level === 'HIGH'
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : t.risk_level === 'MEDIUM'
                            ? 'bg-yellow-100 text-yellow-800 border border-yellow-300'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        }`}>
                          {t.risk_level}
                        </span>
                      </td>
                      <td className="py-2.5 text-stone-600">
                        <span className="font-mono text-[11px]">{t.operation_type}</span>
                        {t.is_destructive && (
                          <span className="ml-1.5 text-[10px] text-rose-600 font-semibold">[DESTRUCTIVE]</span>
                        )}
                      </td>
                      <td className="py-2.5 font-mono text-[11px] text-stone-600">
                        {t.mcp_server?.name || 'MCP Gateway (:8443)'}
                      </td>
                      <td className="py-2.5">
                        <span className="font-medium text-stone-800">
                          {t.target_resource?.name || 'Connected DB'}
                        </span>
                        {t.target_resource?.sensitivity && (
                          <span className="ml-1 text-[10px] text-stone-500 font-mono">
                            ({t.target_resource.sensitivity})
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => onNavigateToFirewall(t.name)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-[#f5f0e8] hover:bg-[#ede7da] text-stone-800 border border-[#ded7c8] text-[11px] font-medium transition cursor-pointer"
                        >
                          <span>Intercept</span>
                          <ArrowRight className="w-3 h-3 text-stone-500" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Section 4: Protected Infrastructure & Services */}
        {(activeTab === 'all' || activeTab === 'services') && (
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-emerald-600" />
                <h2 className="text-base font-semibold text-stone-900">
                  Protected Services, Live Databases & Vaults
                </h2>
              </div>
              <span className="text-xs text-stone-500 font-mono">
                {services.length} Crown Jewel Assets
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {services.map((srv: any) => (
                <div
                  key={srv.id}
                  className="bg-white border border-[#ded7c8] rounded-xl p-4 space-y-2 hover:border-stone-400 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-xs text-stone-900">{srv.name}</div>
                      <div className="text-[10px] font-mono text-stone-500">{srv.id}</div>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                      srv.sensitivity_level === 'CRITICAL'
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : 'bg-amber-100 text-amber-800 border border-amber-300'
                    }`}>
                      {srv.sensitivity_level}
                    </span>
                  </div>

                  <div className="text-[11px] text-stone-500 pt-1">
                    <span>Target Type: </span>
                    <span className="font-medium text-stone-700">{srv.type}</span>
                  </div>

                  <div className="text-[11px] text-stone-500 pt-1 border-t border-[#f0ede6]">
                    <span>Linked Tools: </span>
                    <span className="font-mono text-stone-800">
                      {srv.accessing_tools?.length || 0} operations mapped
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* MODAL 1: Register New Tool */}
      {showToolModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4">
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-[#ded7c8]">
              <div className="flex items-center space-x-2">
                <Wrench className="w-5 h-5 text-stone-800" />
                <h3 className="text-base font-semibold text-stone-900">
                  Register New Tool into Graph
                </h3>
              </div>
              <button
                onClick={() => setShowToolModal(false)}
                className="text-stone-400 hover:text-stone-700 text-sm font-mono cursor-pointer"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleRegisterTool} className="space-y-4 text-xs">
              <div>
                <label className="block text-stone-700 font-medium mb-1">
                  Tool Function Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. rotate_kms_key or export_database_snapshot"
                  value={newTool.name}
                  onChange={(e) => setNewTool({ ...newTool, name: e.target.value })}
                  className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 placeholder-stone-400 font-mono focus:outline-hidden focus:border-stone-800"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-stone-700 font-medium mb-1">Risk Level</label>
                  <select
                    value={newTool.risk_level}
                    onChange={(e) => setNewTool({ ...newTool, risk_level: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-stone-700 font-medium mb-1">Operation Type</label>
                  <select
                    value={newTool.operation_type}
                    onChange={(e) => setNewTool({ ...newTool, operation_type: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800"
                  >
                    <option value="READ_ONLY">READ_ONLY</option>
                    <option value="MUTATION">MUTATION</option>
                    <option value="DESTRUCTIVE">DESTRUCTIVE</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-stone-700 font-medium mb-1">Target Sensitive Resource</label>
                  <select
                    value={newTool.target_resource_id}
                    onChange={(e) => setNewTool({ ...newTool, target_resource_id: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800 font-mono text-[11px]"
                  >
                    <option value="sr-financial-db">sr-financial-db (HIGH)</option>
                    <option value="sr-customer-vault">sr-customer-vault (CRITICAL)</option>
                    <option value="sr-payment-db">sr-payment-db (CRITICAL)</option>
                    <option value="sr-cloud-iam">sr-cloud-iam (CRITICAL)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-stone-700 font-medium mb-1">Required RBAC Role</label>
                  <input
                    type="text"
                    value={newTool.required_role}
                    onChange={(e) => setNewTool({ ...newTool, required_role: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="destruct_check"
                  checked={newTool.is_destructive}
                  onChange={(e) => setNewTool({ ...newTool, is_destructive: e.target.checked })}
                  className="rounded text-stone-900 focus:ring-0"
                />
                <label htmlFor="destruct_check" className="text-stone-700">
                  Mark as Destructive / High-Impact Operation
                </label>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-[#ded7c8]">
                <button
                  type="button"
                  onClick={() => setShowToolModal(false)}
                  className="px-4 py-2 rounded-xl bg-[#ede7da] text-stone-700 hover:bg-[#ded4c0] font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-stone-900 text-stone-50 hover:bg-stone-800 font-semibold cursor-pointer shadow-sm"
                >
                  Register Tool into Graph
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Detect / Onboard New User */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4">
          <div className="bg-[#faf7f0] border border-[#ded7c8] rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-[#ded7c8]">
              <div className="flex items-center space-x-2">
                <Users className="w-5 h-5 text-stone-800" />
                <h3 className="text-base font-semibold text-stone-900">
                  Detect & Onboard New User
                </h3>
              </div>
              <button
                onClick={() => setShowUserModal(false)}
                className="text-stone-400 hover:text-stone-700 text-sm font-mono cursor-pointer"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleRegisterUser} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-stone-700 font-medium mb-1">
                    Username / ID <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. charlie.davis"
                    value={newUser.username}
                    onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 placeholder-stone-400 font-mono focus:outline-hidden focus:border-stone-800"
                  />
                </div>

                <div>
                  <label className="block text-stone-700 font-medium mb-1">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Charlie Davis"
                    value={newUser.full_name}
                    onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 placeholder-stone-400 focus:outline-hidden focus:border-stone-800"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-stone-700 font-medium mb-1">Email</label>
                  <input
                    type="email"
                    placeholder="charlie@acme.corp"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800"
                  />
                </div>

                <div>
                  <label className="block text-stone-700 font-medium mb-1">RBAC Role</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                    className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800"
                  >
                    <option value="Security Analyst">Security Analyst</option>
                    <option value="Operations & Compliance Lead">Operations & Compliance Lead</option>
                    <option value="Treasury Operations Director">Treasury Operations Director</option>
                    <option value="DevOps Administrator">DevOps Administrator</option>
                    <option value="External Auditor">External Auditor</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-stone-700 font-medium mb-1">Assigned Agent</label>
                <select
                  value={newUser.assign_agent_id}
                  onChange={(e) => setNewUser({ ...newUser, assign_agent_id: e.target.value })}
                  className="w-full bg-white border border-[#ded7c8] rounded-xl px-3 py-2 text-stone-900 focus:outline-hidden focus:border-stone-800 font-mono"
                >
                  <option value="agent-autodev">agent-autodev (Orbit Support Agent :3001)</option>
                  <option value="agent-nexus-settlement">agent-nexus-settlement (Nexus FinOps :3002)</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-[#ded7c8]">
                <button
                  type="button"
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 rounded-xl bg-[#ede7da] text-stone-700 hover:bg-[#ded4c0] font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-stone-900 text-stone-50 hover:bg-stone-800 font-semibold cursor-pointer shadow-sm"
                >
                  Onboard User into Graph
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
