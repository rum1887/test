"""
Scenario Loader, Pydantic Validator, Mutation Engine, and Alert Generator.
Loads YAML scenarios, executes graph mutations, replays telemetry, and registers alerts in FalkorDB.
"""

import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.graph.client import GraphClient
from backend.app.graph.temporal import create_temporal_edge, invalidate_edge
from backend.app.sim.clock import SimulatedClock, get_clock
from backend.app.sim.telemetry import TelemetryEvent, emit_event

logger = logging.getLogger("trust_analyst.scenarios")


class WorldMutation(BaseModel):
    """Specification of a world mutation (node addition, edge creation, or edge invalidation)."""

    action: Literal["create_node", "create_edge", "invalidate_edge"]
    label: str | None = None
    id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    from_id: str | None = None
    to_id: str | None = None
    rel_type: str | None = None
    valid_from: int | None = None
    valid_to: int | None = None
    provenance: str = "configured"
    source: str = "scenario"


class TelemetryEventSpec(BaseModel):
    """Specification of a Tetragon runtime telemetry event to replay during scenario setup."""

    ts_offset: int = 0
    pod_id: str
    pid: int = 1000
    ppid: int = 1
    binary: str
    args: list[str] = Field(default_factory=list)
    kind: str = "exec"
    dest: str | None = None


class AlertSpec(BaseModel):
    """Specification of the security alert raised by the scenario."""

    id: str
    title: str
    kind: str
    severity: str = "high"
    status: str = "new"
    target_id: str
    target_label: str = "Pod"
    at_offset: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class GroundTruth(BaseModel):
    """Ground truth verdict, expected evidence citations, and correct containment actions."""

    verdict: Literal["benign", "malicious"]
    rationale: str
    required_evidence: list[str] = Field(default_factory=list)
    correct_actions: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    """Complete declarative scenario definition."""

    id: str
    pair_id: str
    variant: Literal["benign", "malicious"]
    title: str
    description: str
    inject: bool = False
    injection_target: str | None = None  # "doc_body" or "process_args"
    injection_payload: str | None = None
    mutations: list[WorldMutation] = Field(default_factory=list)
    telemetry: list[TelemetryEventSpec] = Field(default_factory=list)
    alert: AlertSpec
    ground_truth: GroundTruth


def load_scenario(path_or_id: str | Path) -> Scenario:
    """
    Loads and validates a Scenario YAML file using Pydantic.
    path_or_id can be an absolute path, relative path, or scenario id (e.g. 'pair1_shell_metadata_benign').
    """
    p = Path(path_or_id)
    if not p.is_file():
        # Check inside scenarios dir
        candidate = Path(settings.SCENARIOS_DIR) / f"{path_or_id}.yaml"
        if candidate.is_file():
            p = candidate
        else:
            candidate_yml = Path(settings.SCENARIOS_DIR) / f"{path_or_id}.yml"
            if candidate_yml.is_file():
                p = candidate_yml
            else:
                raise FileNotFoundError(f"Scenario file not found: {path_or_id}")

    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Scenario.model_validate(data)


def load_all_scenarios(scenarios_dir: str | Path | None = None) -> list[Scenario]:
    """
    Scans the scenarios directory and loads all validated Scenario specifications.
    """
    s_dir = Path(scenarios_dir or settings.SCENARIOS_DIR)
    if not s_dir.exists():
        logger.warning(f"Scenarios directory does not exist: {s_dir}")
        return []

    yaml_files = sorted(list(s_dir.glob("*.yaml")) + list(s_dir.glob("*.yml")))
    scenarios: list[Scenario] = []
    for f in yaml_files:
        try:
            sc = load_scenario(f)
            scenarios.append(sc)
        except Exception as e:
            logger.error(f"Failed to load scenario {f}: {e}")
            raise

    return scenarios


def raise_alert(
    client: GraphClient,
    alert_spec: AlertSpec,
    base_time: int,
) -> str:
    """
    Creates an Alert node in FalkorDB and connects it to its target entity.
    """
    alert_time = base_time + alert_spec.at_offset
    params = {
        "id": alert_spec.id,
        "title": alert_spec.title,
        "kind": alert_spec.kind,
        "severity": alert_spec.severity,
        "status": alert_spec.status,
        "at": alert_time,
        "target_id": alert_spec.target_id,
    }

    # 1. Upsert Alert node
    client.query(
        """
        MERGE (a:Alert {id: $id})
        SET a.title = $title,
            a.kind = $kind,
            a.severity = $severity,
            a.status = $status,
            a.at = $at
        """,
        params,
    )

    # 2. Connect Alert to target entity if it exists
    client.query(
        """
        MATCH (a:Alert {id: $id}), (t {id: $target_id})
        MERGE (a)-[:TARGETS]->(t)
        """,
        params,
    )

    logger.info(f"Raised alert {alert_spec.id} targeting {alert_spec.target_id} at sim time {alert_time}")
    return alert_spec.id


def apply_scenario(
    client: GraphClient,
    scenario: Scenario,
    clock: SimulatedClock | None = None,
) -> str:
    """
    Applies scenario mutations, replays scenario telemetry events, and raises the alert in FalkorDB.
    Returns the created Alert id.
    """
    sim_clock = clock or get_clock()
    base_time = sim_clock.now()

    # 1. Apply world mutations
    for m in scenario.mutations:
        if m.action == "create_node":
            if not m.label or not m.id:
                continue
            props = dict(m.properties)
            props["id"] = m.id

            # Handle prompt injection payload in untrusted document body if specified
            if scenario.inject and scenario.injection_payload:
                if m.label == "Document" and props.get("trust") == "untrusted":
                    orig_body = props.get("body", "")
                    props["body"] = f"{orig_body}\n\n[PROMPT_INJECTION]: {scenario.injection_payload}".strip()

            set_clauses = [f"n.{k} = ${k}" for k in props.keys() if k != "id"]
            set_str = f"SET {', '.join(set_clauses)}" if set_clauses else ""

            cypher = f"MERGE (n:{m.label} {{id: $id}}) {set_str}"
            client.query(cypher, props)

        elif m.action == "create_edge":
            if not m.from_id or not m.to_id or not m.rel_type:
                continue
            vf = m.valid_from if m.valid_from is not None else base_time
            vt = m.valid_to
            create_temporal_edge(
                client=client,
                from_id=m.from_id,
                to_id=m.to_id,
                rel_type=m.rel_type,
                valid_from=vf,
                valid_to=vt,
                provenance=m.provenance,
                source=m.source,
            )

        elif m.action == "invalidate_edge":
            if not m.from_id or not m.to_id or not m.rel_type:
                continue
            inv_time = m.valid_to if m.valid_to is not None else base_time
            invalidate_edge(
                client=client,
                from_id=m.from_id,
                to_id=m.to_id,
                rel_type=m.rel_type,
                at_time=inv_time,
            )

    # 2. Emit telemetry events
    for t_spec in scenario.telemetry:
        ev_ts = base_time + t_spec.ts_offset
        args = list(t_spec.args)

        # Handle telemetry prompt injection if specified
        if (
            scenario.inject
            and scenario.injection_payload
            and scenario.injection_target == "process_args"
            and t_spec.kind == "exec"
        ):
            args.append(f"--note={scenario.injection_payload}")

        event = TelemetryEvent(
            ts=ev_ts,
            pod_id=t_spec.pod_id,
            pid=t_spec.pid,
            ppid=t_spec.ppid,
            binary=t_spec.binary,
            args=args,
            kind=t_spec.kind,
            dest=t_spec.dest,
        )
        emit_event(client, event)

    # 3. Raise Alert
    alert_id = raise_alert(client, scenario.alert, base_time)
    alert_time = base_time + scenario.alert.at_offset
    if sim_clock.now() < alert_time:
        sim_clock.advance(alert_time - sim_clock.now())
    return alert_id
