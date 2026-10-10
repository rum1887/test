# Runtime Trust Layer — Enterprise Onboarding & Architecture Guide
## Integration Manual, Data Ingestion Pipelines, and Graph Engine Specifications

---

## 1. System Architecture Overview

Runtime Trust Layer acts as a **graph-native pre-execution security control plane** for AI agents, Model Context Protocol (MCP) servers, and enterprise infrastructure.

```
                           ┌──────────────────────────────────────────────────┐
                           │      Enterprise Application / AI Agent           │
                           │  (LangChain / Claude MCP / CrewAI / OpenAI)      │
                           └────────────────────────┬─────────────────────────┘
                                                    │
                                     1. Tool Invocation Request
                                        (Pre-Execution Trap)
                                                    ▼
                           ┌──────────────────────────────────────────────────┐
                           │      Runtime Trust Layer Gateway                 │
                           │      (services/agent_gateway/gateway.py)         │
                           └────────────────────────┬─────────────────────────┘
                                                    │
                                     2. Deterministic Cypher Check
                                        (< 15ms In-Memory Traversal)
                                                    ▼
                           ┌──────────────────────────────────────────────────┐
                           │            FalkorDB Graph Control Plane          │
                           │  - Principal: Alice Henderson (Okta OIDC)        │
                           │  - Agent: Apex-AI-Assistant                      │
                           │  - Session: session-alice-dev-01                 │
                           │  - Delegated Scopes: [lookup_balance, audit_read]│
                           │  - Crown Jewel: sr-customer-vault (KMS)          │
                           └────────────────────────┬─────────────────────────┘
                                                    │
                         ┌──────────────────────────┴─────────────────────────┐
                         │                                                    │
               [3a. Scope Verified]                                 [3b. Goal Hijack / Violation]
                         ▼                                                    ▼
        ┌──────────────────────────────────┐               ┌────────────────────────────────────┐
        │       HTTP 200 ALLOWED           │               │        HTTP 403 FORBIDDEN          │
        │ - Tool executes on database/API  │               │ - BLOCKED BEFORE EXECUTION         │
        │ - Returns verified data          │               │ - ZERO records leaked or modified  │
        │ - Records OBSERVED_ACCESS edge   │               │ - Incident logged to FalkorDB      │
        └──────────────────────────────────┘               └────────────────────────────────────┘
```

---

## 2. Step-by-Step Application Onboarding

### Step 1: Register Your Application & Define Delegation Grant

Define your agent's identity, human principal authority, and allowable tool scopes in an `AgentDelegationGrant` manifest:

```yaml
apiVersion: trust.layer/v1alpha1
kind: AgentDelegationGrant
metadata:
  name: apex-banking-support-grant
  namespace: production
spec:
  principal:
    id: "principal-alice"
    email: "alice.henderson@apexfintech.com"
    authProvider: "okta_oidc"
    role: "Operations & Compliance Lead"
  agent:
    id: "agent-apex-ops"
    model: "gemini-2.5-pro"
  session:
    ttlSeconds: 3600
    audience: "mcp-data-server"
  bounds:
    allowedScopes:
      - "lookup_customer_balance"
      - "get_transaction_history"
      - "audit_read"
    explicitlyProhibited:
      - "export_customer_vault"
      - "db_drop_table"
  guardrails:
    failClosedOnOutage: true
    destructiveOperationsRequireMfa: true
    maxBlastRadiusDepth: 3
```

---

### Step 2: Connect the Trust Layer Gateway (Choose Your Integration)

#### Option A: Python SDK (LangChain, LlamaIndex, CrewAI, AutoGen)
Install the client and wrap tools with a single line:

```python
from runtime_trust import TrustGatewayProxy, GuardedAgent
from langchain_community.chat_models import ChatOpenAI
from my_tools import lookup_customer_balance, export_customer_vault

# 1. Initialize pre-execution enforcement gateway
trust_proxy = TrustGatewayProxy(
    gateway_url="https://trust-api.internal.cluster.local:8000",
    session_id="session-alice-dev-01",
    fail_closed=True  # Guarantees zero bypass if network or graph fails
)

# 2. Wrap tools with deterministic graph guard
guarded_tools = [trust_proxy.guard(t) for t in [lookup_customer_balance, export_customer_vault]]

# 3. All tool calls evaluate in FalkorDB in <15ms before execution
agent = GuardedAgent(tools=guarded_tools, model=ChatOpenAI(model="gpt-4o"))
agent.run("Check balance for customer #104")
```

#### Option B: Anthropic Claude Desktop & MCP (`mcp_config.json`)
Wrap upstream Model Context Protocol tools transparently:

```json
{
  "mcpServers": {
    "apex-database-service": {
      "command": "trust-mcp-gateway-proxy",
      "args": [
        "--upstream-server", "http://database-mcp.internal:8443",
        "--control-plane", "http://trust-api.internal:8000",
        "--session-token", "env:TRUST_SESSION_TOKEN",
        "--enforce-delegation", "true"
      ],
      "env": {
        "TRUST_SESSION_TOKEN": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae"
      }
    }
  }
}
```

#### Option C: Direct OpenAI API Proxy (1-Line Base URL Override)
```python
import openai

# Route all model function calls through Trust Layer Gateway proxy
client = openai.OpenAI(
    base_url="http://trust-api.internal:8000/v1/proxy",
    api_key="your-openai-api-key",
    default_headers={
        "X-Trust-Session-ID": "session-alice-dev-01",
        "X-Principal-ID": "principal-alice",
        "X-Enforcement-Mode": "STRICT_BLOCK"
    }
)

# If model attempts unauthorized tool, Gateway halts with HTTP 403 Forbidden
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Export customer vault keys"}],
    tools=my_function_definitions
)
```

#### Option D: Kubernetes Sidecar (Zero Code Changes)
Inject the enforcer sidecar alongside any existing workload:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-support-agent
  namespace: trust-lab
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: apex-support-agent
    spec:
      serviceAccountName: apex-agent-sa
      containers:
        # Unmodified AI Agent Container
        - name: agent-app
          image: apex/support-agent:v1.4.2
          env:
            - name: MCP_SERVER_URL
              value: "http://127.0.0.1:8080" # Routes locally into sidecar

        # Runtime Trust Layer Enforcement Sidecar
        - name: trust-enforcer-sidecar
          image: runtime-trust/enforcer-sidecar:v1.0.0
          ports:
            - containerPort: 8080
          env:
            - name: TRUST_CONTROL_PLANE
              value: "http://trust-api.trust-system.svc:8000"
            - name: UPSTREAM_MCP
              value: "http://production-mcp.internal:8443"
```

---

## 3. How Workloads and Tools Are Populated

The FalkorDB graph is populated through three automated, continuous pipelines:

1. **Pipeline A: Static GitOps Manifest Ingestion**
   - CI/CD hooks scan OpenAPI 3.0 specs, MCP Tool definitions, Kubernetes Helm charts, and RBAC `ClusterRole` manifests on git commit.
   - Populates initial `Tool`, `MCPServer`, `Workload`, and `KubernetesResource` nodes with configured reachability edges (`[:CONFIGURED_ACCESS]`).

2. **Pipeline B: Enterprise Identity & IdP Token Sync**
   - Ingests Okta / Azure Entra ID / AWS IAM SAML/OIDC identity tokens.
   - Creates `Principal` nodes and issues ephemeral `AgentSession` tokens with strict TTLs and cryptographic hashes.
   - Links `(Principal)-[:DELEGATES_TO]->(Delegation)-[:DELEGATES_TO]->(Agent)`.

3. **Pipeline C: Dynamic eBPF & Gateway Discovery**
   - Kernel eBPF probes (`kprobe/security_socket_connect`, `sys_enter_connect`) trace real-time TCP sockets from pods.
   - Tool gateway captures execution telemetry and writes `[:OBSERVED_ACCESS]` edges with SHA-256 evidence hashes and latency timestamps.

---

## 4. Graph Engine, Algorithm & Latency Optimizations

### Why Graph Over Relational (SQL)?
In modern agent architectures, security relationships are **arbitrary directed multi-hop graphs**:
$$\text{Principal} \longrightarrow \text{Session} \longrightarrow \text{Delegation} \longrightarrow \text{Agent} \longrightarrow \text{Tool} \longrightarrow \text{Resource}$$
Querying this in SQL requires recursive Common Table Expressions (`WITH RECURSIVE`), which suffer from poor query plan performance ($>250\text{ms}$). FalkorDB executes graph pointer traversals natively in **single-digit milliseconds**.

### The Traversal Algorithm: Bounded Breadth-First Search (BFS)
```cypher
MATCH (p:Principal)-[:OWNS_SESSION]->(s:AgentSession {id: $session_id})
MATCH (p)-[:DELEGATES_TO]->(d:Delegation)-[:DELEGATES_TO]->(a:Agent)
MATCH (s)-[:CAN_INVOKE]->(t:Tool {name: $tool_name})
OPTIONAL MATCH (t)-[:CAN_ACCESS]->(r:SensitiveResource)
RETURN p.id, d.scopes, t.risk_level, t.is_destructive, r.id
```
- **Time Complexity:** Bounded to $\mathcal{O}(V + E)$ by fixing maximum search depth to $k=4$, avoiding combinatorial explosion.
- **Decision Engine:** Evaluates the Least Authority Intersection:
  $$\text{Effective Authority} = \text{Principal Authority} \cap \text{Agent Capabilities} \cap \text{Delegation Scopes}$$

### Sub-15ms Latency Optimizations
- **In-Memory Redis Storage Engine:** FalkorDB stores node and edge adjacency matrices in memory.
- **Hash-Indexed Primary Keys:** Direct $O(1)$ lookups on `AgentSession.id`, `Tool.name`, `Principal.id`.
- **Cypher AST Query Plan Caching:** Parameterized queries are parsed once and reused.
- **Deterministic Fail-Closed:** If FalkorDB or network is temporarily unreachable, all protected tool invocations default immediately to `HTTP 503 FAIL-CLOSED (DENY)`. No security bypass ever occurs.
