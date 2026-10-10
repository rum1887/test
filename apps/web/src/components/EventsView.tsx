import React, { useState, useEffect } from 'react';
import { Terminal, ShieldAlert, Play, RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

export const EventsView: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [modeFilter, setModeFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(false);
  const [injecting, setInjecting] = useState(false);

  useEffect(() => {
    loadEvents();
  }, [severityFilter, modeFilter]);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const sev = severityFilter === 'ALL' ? undefined : severityFilter;
      const mod = modeFilter === 'ALL' ? undefined : modeFilter;
      const data = await api.getEvents(sev, mod, 50);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleInjectReplay = async () => {
    setInjecting(true);
    try {
      await api.triggerReplay(3);
      await loadEvents();
    } catch (e) {
      console.error(e);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-stone-900 flex items-center space-x-2">
            <Terminal className="w-5 h-5 text-stone-700" />
            <span>Runtime Telemetry & Observed Events</span>
          </h2>
          <p className="text-xs text-stone-500 mt-1">
            Real-time process execution, kernel probes, and socket telemetry correlated with Kubernetes workloads.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadEvents}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-semibold transition cursor-pointer shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Live Stream</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-white border border-[#e8e5de] shadow-sm rounded-lg p-3 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-stone-500 font-medium">Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium transition cursor-pointer ${
                severityFilter === s
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-600 hover:text-stone-900 bg-[#faf8f5] border border-[#ede9df]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="h-4 w-[1px] bg-[#e8e5de] mx-2 hidden sm:block" />

        <div className="flex items-center space-x-2">
          <span className="text-stone-500 font-medium">Telemetry Source:</span>
          {[
            { id: 'ALL', label: 'All Telemetry' },
            { id: 'fixture_baseline', label: 'Fixture Baseline' },
            { id: 'live_ebpf', label: 'Kernel eBPF' },
            { id: 'live_enforcement', label: 'Agent Gateway' },
            { id: 'replay_synthetic', label: 'Synthetic Replay' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setModeFilter(item.id)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition cursor-pointer ${
                modeFilter === item.id
                  ? 'bg-stone-900 text-white font-medium'
                  : 'text-stone-600 hover:text-stone-900 bg-[#faf8f5] border border-[#ede9df]'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-white border border-[#e8e5de] rounded-xl overflow-hidden shadow-sm">
        <div className="divide-y divide-[#f0ede6]">
          {events.map((e) => {
            const isCritical = e.severity === 'CRITICAL';
            const isLive = e.is_live_telemetry;
            const modeLabel =
              e.mode === 'live_ebpf'
                ? isLive ? 'KERNEL eBPF (LIVE)' : 'KERNEL eBPF (HISTORICAL)'
                : e.mode === 'live_enforcement'
                ? 'AGENT GATEWAY'
                : e.mode === 'replay_synthetic'
                ? 'SYNTHETIC REPLAY'
                : 'FIXTURE BASELINE';

            const badgeColor =
              e.mode === 'live_ebpf' && isLive
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : e.mode === 'replay_synthetic'
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : e.mode === 'live_enforcement'
                ? 'bg-purple-50 text-purple-800 border-purple-200'
                : 'bg-stone-100 text-stone-700 border-stone-200';

            return (
              <div key={e.id} className="p-4 space-y-2 hover:bg-[#faf8f5] transition">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                        isCritical
                          ? 'bg-rose-50 text-rose-800 border border-rose-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {e.severity}
                    </span>

                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border ${badgeColor}`}
                    >
                      {modeLabel}
                    </span>

                    <span className="font-mono text-xs font-semibold text-stone-900">
                      {e.process_name || e.event_type}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-stone-400">
                    {e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>

                {e.command_line && (
                  <div className="bg-[#faf8f5] border border-[#ede9df] rounded p-2 font-mono text-[11px] text-stone-800 overflow-x-auto">
                    {e.command_line}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between text-xs text-stone-500 gap-2 pt-1">
                  <div className="flex items-center space-x-3">
                    <span>Source: {e.source}</span>
                    {e.correlated_source && (
                      <>
                        <span>•</span>
                        <span className="text-stone-800 font-mono">
                          Pod: {e.correlated_source.id}
                        </span>
                      </>
                    )}
                  </div>

                  {e.policy_violation && (
                    <div className="flex items-center space-x-1 text-rose-700 font-semibold text-[11px]">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Violated: {e.policy_violation.name}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {events.length === 0 && (
            <div className="p-12 text-center text-xs text-stone-400">
              No runtime telemetry events match current filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
