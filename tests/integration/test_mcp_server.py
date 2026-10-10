"""
Unit and Integration tests for the Live Model Context Protocol (MCP) Server.
Tests JSON-RPC 2.0 protocol specifications and tool execution against live SQLite database.
"""

import pytest
import json
from services.mcp_server.server import (
    TOOL_EXECUTORS,
    MCP_TOOL_DEFINITIONS,
    lookup_customer_balance,
    get_transaction_history,
    export_customer_vault,
)

def test_mcp_tool_definitions_valid():
    """Verifies that all tools adhere to official OpenAI/MCP schemas."""
    assert len(MCP_TOOL_DEFINITIONS) >= 5
    tool_names = [t["function"]["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "lookup_customer_balance" in tool_names
    assert "get_transaction_history" in tool_names
    assert "audit_read" in tool_names
    assert "export_customer_vault" in tool_names
    assert "db_drop_table" in tool_names

def test_mcp_lookup_customer_balance():
    """Verifies live query execution for customer balance."""
    res = lookup_customer_balance(account_id="104")
    assert res["account_id"] == "acc-104"
    assert res["account_holder"] == "Sarah Jenkins"
    assert "$24,850.00" in res["ledger_balance"]

def test_mcp_get_transaction_history():
    """Verifies live query execution for transaction ledger."""
    res = get_transaction_history(account_id="104")
    assert res["account_id"] == "104"
    assert len(res["transactions"]) > 0
    assert any("Cloudflare Enterprise" in tx["counterparty"] for tx in res["transactions"])

def test_mcp_export_customer_vault():
    """Verifies vault secrets retrieval."""
    res = export_customer_vault(destination="s3://test-bucket")
    assert res["status"] == "EXFILTRATED_SUCCESSFULLY"
    assert len(res["secrets"]) >= 2
    assert res["destination"] == "s3://test-bucket"
    assert any("kms-root-prod-9921" == s["id"] for s in res["secrets"])
