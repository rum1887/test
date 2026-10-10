"""
Trust Analyst Background Worker.
Orchestrates three background loops driven by the simulated clock:
1. Investigation Runner: picks up pending alerts and drives autonomous investigations.
2. Watch Evaluator: evaluates active telemetry & graph pattern watches.
3. Task Scheduler: executes due ScheduledTask nodes.
"""

import logging
import time

from backend.app.agent.runner import durable_runner
from backend.app.agent.scheduler import task_scheduler
from backend.app.agent.watcher import watch_evaluator
from backend.app.graph.client import get_graph_client
from backend.app.sim.clock import get_clock

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("trust_analyst.worker")


def worker_tick(client=None, clock=None) -> dict[str, int]:
    """Executes a single processing tick across investigations, watches, and schedules."""
    c = client or get_graph_client()
    sim_clock = clock or get_clock()

    # 1. Check for unhandled Alerts
    unhandled_alerts = c.query_dicts(
        """
        MATCH (a:Alert {status: 'new'})
        WHERE NOT (a)<-[:INVESTIGATES]-(:Investigation)
        RETURN a.id AS id
        ORDER BY a.at ASC
        LIMIT 5
        """
    )
    started_invs = 0
    for row in unhandled_alerts:
        alert_id = row["id"]
        try:
            logger.info(f"Worker starting investigation for Alert {alert_id}")
            durable_runner.start_investigation(alert_id=alert_id, client=c, clock=sim_clock)
            c.query("MATCH (a:Alert {id: $id}) SET a.status = 'investigating'", {"id": alert_id})
            started_invs += 1
        except Exception as e:
            logger.error(f"Error starting investigation for alert {alert_id}: {e}")

    # 2. Evaluate Watches
    wake_events = watch_evaluator.evaluate_all(client=c, clock=sim_clock)
    for w in wake_events:
        logger.info(f"Watch {w.watch_id} triggered wake event for Investigation {w.investigation_id}")

    # 3. Dispatch Scheduled Tasks
    executed_tasks = task_scheduler.evaluate_due_tasks(client=c, clock=sim_clock)
    if executed_tasks:
        logger.info(f"Executed {len(executed_tasks)} scheduled tasks")

    return {
        "started_investigations": started_invs,
        "watch_wakes": len(wake_events),
        "executed_tasks": len(executed_tasks),
    }


def run_worker_loop(interval_sec: float = 2.0):
    """Continuous worker daemon loop."""
    logger.info("Trust Analyst Background Worker started.")
    client = get_graph_client()
    clock = get_clock()

    while True:
        try:
            if client.is_alive():
                worker_tick(client=client, clock=clock)
        except Exception as e:
            logger.error(f"Worker tick encountered error: {e}")
        time.sleep(interval_sec)


if __name__ == "__main__":
    run_worker_loop()
