"""
Nexus - Standalone Autonomous Corporate Settlement & FinOps Multi-Agent System.
Port 3002.
Powered by Google ADK (Agent Development Kit v2.11) Multi-Agent Architecture.
Governed in real-time by the Runtime Trust Layer Policy Gateway.

Shares underlying production infrastructure (sr-financial-db: Production Financial Ledger)
with the Orbit Customer Support Agent (Port 3001).

Demonstrates:
When Orbit suffers prompt injection contamination, the Runtime Trust Layer's graph engine
detects the shared attack path and locks the shared infrastructure via blast radius containment,
preventing Nexus from touching the contaminated ledger and protecting the rest of the enterprise!
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from apps.standalone_agent_app.trust_guard import TrustGuard, GuardDecision
from services.mcp_server.server import (
    process_settlement_payout,
    verify_treasury_ledger,
    get_transaction_history,
)
from services.database.live_db import (
    live_process_settlement_payout,
    live_verify_treasury_ledger,
    live_get_transactions,
    initialize_live_database,
)

# Google ADK Multi-Agent System for Nexus
from apps.nexus_settlement_agent.adk_multi_agent import nexus_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nexus_agent")

app = FastAPI(
    title="Nexus Autonomous Settlement Engine (Google ADK Multi-Agent)",
    description="Enterprise Multi-Agent FinOps & Settlement System built with Google ADK (Agent Development Kit v2.11)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

# Services Configuration
TRUST_LAYER_URL = os.getenv("TRUST_LAYER_URL", "http://localhost:8000/api/gateway/invoke")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8443/mcp")

# Initialize Runtime Trust Layer Guard Middleware
guard = TrustGuard(gateway_url=TRUST_LAYER_URL, session_id="session-nexus-settlement-01")

# Initialize database
initialize_live_database()

# Application State
NEXUS_STATE = {
    "app_name": "Nexus",
    "session_id": "session-nexus-settlement-01",
    "principal": {
        "id": "principal-marcus",
        "name": "Marcus Vance",
        "role": "Treasury Operations Director",
        "department": "Corporate Treasury & Settlement",
        "badge": "#fin-902",
    },
    "shared_infrastructure": {
        "resource_id": "sr-financial-db",
        "name": "Production Financial Ledger (prod-financial-db)",
        "shared_with": "Orbit Customer Support AI (Port 3001)",
    },
}

class NexusChatRequest(BaseModel):
    message: str

class SettlementTriggerRequest(BaseModel):
    payout_id: Optional[str] = "pay-settle-8891"
    amount: Optional[str] = "$125,000.00"
    target_account: Optional[str] = "acc-treasury-global"

@app.get("/api/state")
def get_nexus_state():
    # Sync guard state from central gateway
    guard_active = True
    try:
        with httpx.Client(timeout=1.0) as client:
            res = client.get("http://localhost:8000/api/gateway/guard-state")
            if res.status_code == 200:
                guard_active = res.json().get("guard_enabled", True)
    except Exception:
        pass

    return {
        "app_name": NEXUS_STATE["app_name"],
        "session_id": NEXUS_STATE["session_id"],
        "principal": NEXUS_STATE["principal"],
        "shared_infrastructure": NEXUS_STATE["shared_infrastructure"],
        "guard_active": guard_active,
        "trust_layer_url": TRUST_LAYER_URL,
    }

@app.get("/api/multi-agent")
def get_multi_agent():
    return nexus_router.get_system_hierarchy()

@app.post("/api/chat")
def handle_chat(req: NexusChatRequest):
    user_prompt = req.message.strip()
    prompt_lower = user_prompt.lower()

    # Determine tool called
    tool_called = None
    tool_args = {}

    if any(w in prompt_lower for w in ["settle", "payout", "disburse", "pay"]):
        tool_called = "process_settlement_payout"
        tool_args = {"payout_id": "pay-settle-8891", "amount": "$125,000.00", "target_account": "acc-treasury-global"}
    elif any(w in prompt_lower for w in ["verify", "ledger", "checksum"]):
        tool_called = "verify_treasury_ledger"
        tool_args = {}
    elif any(w in prompt_lower for w in ["history", "transaction", "record"]):
        tool_called = "get_transaction_history"
        tool_args = {"account_id": "acc-104"}

    # Google ADK multi-agent routing
    target_subagent, agent_obj, delegation_chain = nexus_router.route_request(user_prompt, tool_called)
    multi_agent_meta = {
        "framework": "Google ADK (Agent Development Kit v2.11)",
        "delegated_subagent": target_subagent,
        "delegation_chain": delegation_chain,
        "subagent_description": agent_obj.description,
    }

    if not tool_called:
        return {
            "message": user_prompt,
            "tool_called": None,
            "tool_args": {},
            "multi_agent": multi_agent_meta,
            "blocked": False,
            "status_code": 200,
            "decision_rationale": "Direct conversational response from Nexus Settlement Orchestrator.",
            "agent_reply": f"Hello Marcus! Nexus Treasury Orchestrator is online. Ready to dispatch automated settlement batches or verify shared financial ledgers.",
            "execution_result": None,
            "blast_radius_containment": False,
        }

    # Evaluate via Runtime Trust Layer Gateway
    decision = guard.evaluate(tool_called, tool_args)

    if decision.blocked:
        is_blast_containment = "BLAST RADIUS CONTAINMENT" in decision.rationale
        agent_reply = (
            f"🛡️ [INTERCEPTED BY RUNTIME TRUST LAYER]\n\n"
            f"Execution of '{tool_called}' was halted at the gateway boundary.\n"
            f"Multi-Agent Target: {target_subagent}\n"
            f"HTTP Status: {decision.status_code}\n\n"
            f"Policy Decision: {decision.rationale}\n\n"
            f"{'⚠️ LATERAL CONTAMINATION PREVENTED: Access to shared infrastructure was suspended to protect corporate treasury from upstream Orbit compromise.' if is_blast_containment else 'Action unauthorized under active delegation boundaries.'}"
        )
        return {
            "message": user_prompt,
            "tool_called": tool_called,
            "tool_args": tool_args,
            "multi_agent": multi_agent_meta,
            "blocked": True,
            "status_code": decision.status_code,
            "decision_rationale": decision.rationale,
            "gateway_latency_ms": decision.latency_ms,
            "agent_reply": agent_reply,
            "execution_result": None,
            "blast_radius_containment": is_blast_containment,
            "evaluated_rules": decision.evaluated_rules,
        }
    else:
        # ALLOWED: Execute tool on live MCP / DB
        if tool_called == "process_settlement_payout":
            exec_res = live_process_settlement_payout(**tool_args)
            agent_reply = f"✅ Settlement Batch '{exec_res['payout_id']}' of {exec_res['amount']} successfully disbursed to {exec_res['target_account']}. Ledger balance verified on shared financial database."
        elif tool_called == "verify_treasury_ledger":
            exec_res = live_verify_treasury_ledger()
            agent_reply = f"✅ Shared Financial Ledger ({exec_res['shared_resource']}) verified healthy. Checksum: {exec_res['checksum']}."
        else:
            exec_res = live_get_transactions()
            agent_res_count = len(exec_res.get("transactions", []))
            agent_reply = f"✅ Retrieved {agent_res_count} verified transactions from shared financial ledger."

        return {
            "message": user_prompt,
            "tool_called": tool_called,
            "tool_args": tool_args,
            "multi_agent": multi_agent_meta,
            "blocked": False,
            "status_code": 200,
            "decision_rationale": decision.rationale,
            "gateway_latency_ms": decision.latency_ms,
            "agent_reply": agent_reply,
            "execution_result": exec_res,
            "blast_radius_containment": False,
            "evaluated_rules": decision.evaluated_rules,
        }

@app.post("/api/trigger-settlement")
def trigger_settlement(req: SettlementTriggerRequest):
    return handle_chat(NexusChatRequest(message="Execute settlement payout batch immediately"))

@app.get("/", response_class=HTMLResponse)
def index_page():
    return HTML_CONTENT

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus — FinOps Settlement Multi-Agent</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    pre, code, .font-mono { font-family: 'JetBrains Mono', monospace; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #2e3035; border-radius: 9999px; }
  </style>
</head>
<body class="bg-[#0f1117] text-slate-100 min-h-screen flex overflow-hidden">

  <!-- Left Sidebar -->
  <aside class="w-72 bg-[#141721] border-r border-[#1f2433] flex flex-col justify-between p-3.5 select-none">
    <div class="space-y-4">
      <!-- Brand Header -->
      <div class="flex items-center space-x-2.5 px-2 pt-1 pb-2">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-teal-500/20">
          <span class="text-white font-bold text-sm">❖</span>
        </div>
        <div>
          <div class="font-bold text-sm text-white flex items-center space-x-1.5">
            <span>Nexus</span>
            <span class="text-[10px] font-mono bg-teal-950 text-teal-400 border border-teal-800 px-1.5 rounded font-semibold">FINOPS</span>
          </div>
          <div class="text-[11px] text-slate-400">Settlement Engine</div>
        </div>
      </div>

      <!-- Authenticated User Card -->
      <div class="bg-[#191d2b] border border-[#262c3f] rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between text-[11px]">
          <span class="text-slate-400 font-medium">Treasury Director</span>
          <span class="text-[9px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800 px-1 rounded font-bold">ACTIVE</span>
        </div>
        <div class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center font-bold text-xs text-slate-200">
            MV
          </div>
          <div class="text-xs leading-tight">
            <div class="font-semibold text-white">Marcus Vance</div>
            <div class="text-[10px] text-slate-400 font-mono">#fin-902 • Corporate Treasury</div>
          </div>
        </div>
      </div>

      <!-- Shared Infrastructure Card -->
      <div class="bg-[#191d2b] border border-[#262c3f] rounded-xl p-3 space-y-2 text-xs">
        <div class="flex items-center justify-between text-[10px] uppercase font-bold text-slate-400">
          <span>Shared Infrastructure</span>
          <span class="text-amber-400 font-mono">SHARED</span>
        </div>
        <div class="space-y-1 text-[11px] text-slate-300 font-mono bg-black/40 p-2 rounded border border-[#212739]">
          <div class="text-teal-300 font-bold truncate">prod-financial-db</div>
          <div class="text-[10px] text-slate-400">Shared with: Orbit AI (:3001)</div>
          <div class="text-[9px] text-slate-500">Resource: sr-financial-db</div>
        </div>
        <p class="text-[10px] text-slate-400 leading-relaxed">
          Subject to lateral blast-radius containment if Orbit agent is compromised.
        </p>
      </div>

      <!-- Quick Actions -->
      <div class="space-y-1.5 text-xs">
        <div class="text-[10px] uppercase font-bold text-slate-500 px-2 tracking-wider">Automated Workflows</div>
        <button onclick="sendPreset('Execute settlement payout batch immediately')" class="w-full text-left px-2.5 py-2 rounded-lg bg-teal-950/40 text-teal-300 hover:bg-teal-900/60 border border-teal-800/60 font-semibold transition truncate block">
          1. Dispatch Settlement ($125,000)
        </button>
        <button onclick="sendPreset('Verify shared treasury ledger status')" class="w-full text-left px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-[#1a1e2d] hover:text-white transition truncate block border border-transparent hover:border-[#262c3f]">
          2. Audit Ledger Checksum
        </button>
        <button onclick="sendPreset('Show recent transaction ledger records')" class="w-full text-left px-2.5 py-1.5 rounded-lg text-slate-300 hover:bg-[#1a1e2d] hover:text-white transition truncate block border border-transparent hover:border-[#262c3f]">
          3. View Ledger History
        </button>
      </div>
    </div>

    <!-- Sidebar Bottom -->
    <div class="space-y-2.5 pt-3 border-t border-[#1f2433] text-xs">
      <div class="flex items-center justify-between px-1 text-[11px] text-slate-400 font-mono">
        <span>Gateway SLA:</span>
        <span class="text-emerald-400 font-bold">&lt; 15 ms</span>
      </div>
      <div class="flex items-center space-x-2">
        <a href="http://localhost:3001" target="_blank" class="flex-1 py-1 px-2 rounded bg-[#191d2b] hover:bg-[#23293d] border border-[#262c3f] text-[10px] text-slate-300 text-center transition">
          Orbit Agent ➔
        </a>
        <a href="http://localhost:5173" target="_blank" class="flex-1 py-1 px-2 rounded bg-sky-950/40 hover:bg-sky-900/60 border border-sky-800/50 text-[10px] text-sky-300 text-center transition">
          Console ➔
        </a>
      </div>
    </div>
  </aside>

  <!-- Main Chat Workspace -->
  <main class="flex-1 flex flex-col h-screen bg-[#0f1117] relative">
    <!-- Top Bar -->
    <header class="h-14 border-b border-[#1f2433] px-6 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center space-x-3">
        <span class="font-bold text-sm text-white">Nexus Settlement Orchestrator</span>
        <span class="text-[10px] font-mono bg-purple-950/80 text-purple-300 border border-purple-800 px-2.5 py-0.5 rounded-full font-semibold flex items-center space-x-1">
          <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          <span>Google ADK Multi-Agent (:3002)</span>
        </span>
        <span class="text-[10px] font-mono bg-teal-950 text-teal-300 border border-teal-800 px-2.5 py-0.5 rounded-full font-semibold flex items-center space-x-1">
          <span class="w-1.5 h-1.5 rounded-full bg-teal-400"></span>
          <span>Shared Infra: sr-financial-db</span>
        </span>
      </div>
      <div class="flex items-center space-x-2 text-xs">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="text-slate-400 text-xs">Runtime Gateway Active</span>
      </div>
    </header>

    <!-- Messages List -->
    <div id="chatScrollArea" class="flex-1 overflow-y-auto px-4 py-6">
      <div class="max-w-3xl mx-auto space-y-6">

        <!-- Welcome Banner -->
        <div id="heroGreeting" class="pt-8 pb-6 space-y-4 text-center">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-xl shadow-teal-500/20">
            <span class="text-2xl font-bold">❖</span>
          </div>
          <div>
            <h1 class="text-2xl font-bold text-white tracking-tight">Nexus Settlement Engine</h1>
            <p class="text-xs text-slate-400 mt-1 max-w-lg mx-auto">
              Autonomous corporate treasury payouts and financial ledger verification. Protected by Runtime Trust Layer blast-radius containment.
            </p>
          </div>

          <!-- Quick Action Buttons -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto pt-2 text-left">
            <button onclick="sendPreset('Execute settlement payout batch immediately')" class="p-3 rounded-xl bg-[#171b26] hover:bg-[#1f2433] border border-[#262c3f] hover:border-teal-500/50 transition cursor-pointer">
              <div class="text-xs font-bold text-teal-300 flex justify-between">
                <span>💰 Execute Settlement Batch</span>
                <span>➔</span>
              </div>
              <p class="text-[10px] text-slate-400 mt-1">Disburse $125,000.00 payout on shared financial ledger</p>
            </button>

            <button onclick="sendPreset('Verify shared treasury ledger status')" class="p-3 rounded-xl bg-[#171b26] hover:bg-[#1f2433] border border-[#262c3f] hover:border-cyan-500/50 transition cursor-pointer">
              <div class="text-xs font-bold text-cyan-300 flex justify-between">
                <span>🔍 Verify Treasury Ledger</span>
                <span>➔</span>
              </div>
              <p class="text-[10px] text-slate-400 mt-1">Audit shared database integrity and checksums</p>
            </button>
          </div>
        </div>

        <div id="messagesList" class="space-y-5"></div>

      </div>
    </div>

    <!-- Bottom Input -->
    <div class="px-4 pb-4 pt-2 flex-shrink-0">
      <div class="max-w-3xl mx-auto">
        <form onsubmit="handleFormSubmit(event)" class="relative flex items-center">
          <input
            id="promptInput"
            type="text"
            placeholder="Instruct Nexus: 'Execute settlement payout batch' or 'Verify treasury ledger'..."
            class="w-full bg-[#161924] text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-full pl-5 pr-14 py-3.5 border border-[#262c3f] focus:outline-none focus:border-teal-500 shadow-xl"
          />
          <button
            type="submit"
            id="sendBtn"
            class="absolute right-2 w-9 h-9 rounded-full bg-teal-500 hover:bg-teal-400 text-slate-950 flex items-center justify-center transition shadow-md cursor-pointer"
          >
            ➔
          </button>
        </form>
        <p class="text-[11px] text-center text-slate-500 mt-2">
          Nexus shares infrastructure (sr-financial-db) with Orbit. Governed by Runtime Trust Layer.
        </p>
      </div>
    </div>
  </main>

  <script>
    function sendPreset(text) {
      document.getElementById('promptInput').value = text;
      sendMessage(text);
    }

    function handleFormSubmit(e) {
      e.preventDefault();
      const input = document.getElementById('promptInput');
      const msg = input.value.trim();
      if (!msg) return;
      sendMessage(msg);
      input.value = '';
    }

    async function sendMessage(msg) {
      document.getElementById('heroGreeting').classList.add('hidden');
      const messagesList = document.getElementById('messagesList');
      const scrollArea = document.getElementById('chatScrollArea');
      const sendBtn = document.getElementById('sendBtn');
      sendBtn.disabled = true;

      // User Bubble
      const userDiv = document.createElement('div');
      userDiv.className = 'flex justify-end';
      userDiv.innerHTML = `
        <div class="max-w-[85%] bg-[#1f2435] text-slate-100 rounded-2xl rounded-tr-sm px-4 py-3 text-xs sm:text-sm leading-relaxed shadow-sm font-sans">
          ${escapeHtml(msg)}
        </div>
      `;
      messagesList.appendChild(userDiv);
      scrollArea.scrollTop = scrollArea.scrollHeight;

      // Loading Bubble
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'flex items-start space-x-3 text-xs text-slate-400';
      loadingDiv.innerHTML = `
        <div class="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300 font-bold text-xs animate-pulse">
          ❖
        </div>
        <div class="p-3 rounded-xl bg-[#161924] border border-[#262c3f] text-slate-300 text-xs flex items-center space-x-2">
          <span class="animate-spin inline-block w-3 h-3 border-2 border-teal-400 border-t-transparent rounded-full"></span>
          <span>Nexus is evaluating policy with Runtime Trust Layer...</span>
        </div>
      `;
      messagesList.appendChild(loadingDiv);
      scrollArea.scrollTop = scrollArea.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        messagesList.removeChild(loadingDiv);
        sendBtn.disabled = false;

        const nexusDiv = document.createElement('div');
        nexusDiv.className = 'flex items-start space-x-3 text-xs';

        let badgeBanner = '';
        let cardBg = 'bg-[#141722]';
        let cardBorder = 'border-[#262c3f]';

        if (data.blocked) {
          if (data.blast_radius_containment) {
            cardBg = 'bg-[#29120c]';
            cardBorder = 'border-amber-600/80 animate-pulse';
            badgeBanner = `
              <div class="mb-2 pb-2 border-b border-amber-700/60 flex justify-between items-center text-[11px] font-bold text-amber-300">
                <span>🛡️ LATERAL SPREAD BLOCKED: BLAST RADIUS CONTAINMENT</span>
                <span class="font-mono bg-amber-950 text-amber-200 px-2 py-0.5 rounded border border-amber-800 text-[10px]">
                  HTTP 428 (${data.gateway_latency_ms} ms)
                </span>
              </div>
            `;
          } else {
            cardBg = 'bg-[#210c12]';
            cardBorder = 'border-rose-700/80';
            badgeBanner = `
              <div class="mb-2 pb-2 border-b border-rose-800/60 flex justify-between items-center text-[11px] font-bold text-rose-300">
                <span>🛡️ INTERCEPTED BY RUNTIME TRUST LAYER</span>
                <span class="font-mono bg-rose-950 text-rose-200 px-2 py-0.5 rounded border border-rose-800 text-[10px]">
                  HTTP ${data.status_code} (${data.gateway_latency_ms} ms)
                </span>
              </div>
            `;
          }
        } else {
          badgeBanner = `
            <div class="mb-2 pb-1.5 border-b border-[#262c3f] flex justify-between items-center text-[10px] text-slate-400 font-mono">
              <span>Tool: <strong class="text-teal-300">${data.tool_called || 'Conversational'}</strong></span>
              <span class="text-emerald-400 font-bold">200 ALLOWED (${data.gateway_latency_ms} ms)</span>
            </div>
          `;
        }

        const adkRoute = data.multi_agent ? data.multi_agent.delegation_chain.join(' ➔ ') : 'NexusSettlementOrchestrator';

        nexusDiv.innerHTML = `
          <div class="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300 font-bold text-xs flex-shrink-0">
            ❖
          </div>
          <div class="max-w-[85%] rounded-2xl rounded-tl-sm p-4 ${cardBg} border ${cardBorder} text-sm leading-relaxed text-slate-200 shadow-md">
            ${badgeBanner}
            <div class="mb-2 inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-purple-950/70 text-purple-300 border border-purple-800/80 text-[10px] font-mono">
              <span>🤖 Google ADK Delegated:</span>
              <span class="font-bold text-white">${data.multi_agent.delegated_subagent}</span>
            </div>
            <div class="whitespace-pre-line text-xs sm:text-sm">${escapeHtml(data.agent_reply)}</div>
            <details class="mt-3 pt-2 border-t border-white/10 text-[10px] font-mono text-slate-400">
              <summary class="cursor-pointer text-slate-400 hover:text-slate-200 select-none flex justify-between">
                <span>Telemetry: ${data.tool_called || 'Direct'}</span>
                <span class="text-teal-400">View Delegation & Rules ▾</span>
              </summary>
              <div class="mt-2 p-2 rounded bg-black/40 border border-white/10 space-y-1 text-slate-300">
                <div><strong>Framework:</strong> Google ADK v2.11</div>
                <div><strong>Delegation Chain:</strong> <span class="text-purple-300">${escapeHtml(adkRoute)}</span></div>
                <div><strong>Shared Resource:</strong> sr-financial-db (Production Financial Ledger)</div>
                <div><strong>Decision Rationale:</strong> ${escapeHtml(data.decision_rationale)}</div>
              </div>
            </details>
          </div>
        `;

        messagesList.appendChild(nexusDiv);
        scrollArea.scrollTop = scrollArea.scrollHeight;

      } catch (e) {
        messagesList.removeChild(loadingDiv);
        sendBtn.disabled = false;
        console.error(e);
      }
    }

    function escapeHtml(text) {
      if (!text) return '';
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("NEXUS_PORT", 3002))
    print(f"🚀 Starting Nexus Settlement Agent on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
