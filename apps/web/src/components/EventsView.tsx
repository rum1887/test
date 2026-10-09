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
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            <span>Runtime Telemetry & Observed Events</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time process execution, kernel probes, and socket telemetry correlated with Kubernetes workloads.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleInjectReplay}
            disabled={injecting}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded text-xs font-semibold transition cursor-pointer disabled:opacity-50"
          >
            <Play className="w-3 h-3 fill-sky-400" />
            <span>{injecting ? 'Injecting...' : 'Inject Replay Telemetry'}</span>
          </button>

          <button
            onClick={loadEvents}
            disabled={loading}
            className="p-1.5 bg-[#0d1322] border border-[#1e2942] text-slate-300 hover:text-white rounded transition"
            title="Refresh Events"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[#0d1322] border border-[#1e2942] rounded-lg p-3 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-slate-400">Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium transition cursor-pointer ${
                severityFilter === s
                  ? 'bg-sky-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 bg-[#12192b]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="h-4 w-[1px] bg-[#1e2942] mx-2 hidden sm:block" />

        <div className="flex items-center space-x-2">
          <span className="text-slate-400">Mode:</span>
          {['ALL', 'live_ebpf', 'replay_synthetic'].map((m) => (
            <button
              key={m}
              onClick={() => setModeFilter(m)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition cursor-pointer ${
                modeFilter === m
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 bg-[#12192b]'
              }`}
            >
              {m === 'live_ebpf' ? 'Live eBPF' : m === 'replay_synthetic' ? 'Replay' : 'All Modes'}
            </button>
          ))}
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-[#0d1322] border border-[#1e2942] rounded-xl overflow-hidden shadow-lg">
        <div className="divide-y divide-[#151f33]">
          {events.map((e) => {
            const isCritical = e.severity === 'CRITICAL';
            const isLive = e.mode === 'live_ebpf';

            return (
              <div key={e.id} className="p-4 space-y-2 hover:bg-[#121a2d] transition">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                        isCritical
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : 'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}
                    >
                      {e.severity}
                    </span>

                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        isLive
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : 'bg-sky-950 text-sky-300 border border-sky-800'
                      }`}
                    >
                      {isLive ? 'LIVE eBPF' : 'SYNTHETIC REPLAY'}
                    </span>

                    <span className="font-mono text-xs font-semibold text-white">
                      {e.process_name || e.event_type}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-slate-400">
                    {e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>

                {e.command_line && (
                  <div className="bg-[#090e1a] border border-[#1e2942] rounded p-2 font-mono text-[11px] text-slate-300 overflow-x-auto">
                    {e.command_line}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2 pt-1">
                  <div className="flex items-center space-x-3">
                    <span>Source: {e.source}</span>
                    {e.correlated_source && (
                      <>
                        <span>•</span>
                        <span className="text-sky-300 font-mono">
                          Pod: {e.correlated_source.id}
                        </span>
                      </>
                    )}
                  </div>

                  {e.policy_violation && (
                    <div className="flex items-center space-x-1 text-rose-400 font-semibold text-[11px]">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Violated: {e.policy_violation.name}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {events.length === 0 && (
            <div className="p-12 text-center text-xs text-slate-500">
              No runtime telemetry events match current filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
