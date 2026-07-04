"""
Data Loader — reads ServerNode and NetworkEdge objects from cloud_sim.db.
Assigns OS types round-robin from the seeded servers so every OS type
appears even in the small demo dataset.
"""

import os
import random
from typing import List, Tuple, Dict

from aco_engine.aco_core import ServerNode, NetworkEdge, OS_TYPES

_DB_REL_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "cloud_sim.db")

# ── Public helpers ─────────────────────────────────────────────────────────────

def is_db_available() -> Tuple[bool, str]:
    path = os.path.abspath(_DB_REL_PATH)
    if os.path.exists(path):
        return True, f"DB found at {path}"
    return False, f"DB not found at {path}"


def load_server_nodes() -> List[ServerNode]:
    import sqlite3
    path = os.path.abspath(_DB_REL_PATH)
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT s.server_id, s.name, s.region, s.status,
               COALESCE(AVG(m.cpu_usage_pct), 45.0)  AS cpu_usage_pct,
               COALESCE(AVG(m.ram_usage_pct), 50.0)  AS ram_usage_pct,
               COALESCE(COUNT(t.task_id), 0)          AS queue_length
        FROM Servers s
        LEFT JOIN Metrics m ON m.server_id = s.server_id
        LEFT JOIN Tasks   t ON t.assigned_server = s.server_id
                            AND t.status = 'running'
        GROUP BY s.server_id
    """).fetchall()
    conn.close()

    # Deterministically assign OS types (so results are reproducible)
    nodes = []
    for i, r in enumerate(rows):
        os_type = OS_TYPES[i % len(OS_TYPES)]
        nodes.append(ServerNode(
            server_id    = r["server_id"],
            name         = r["name"],
            region       = r["region"],
            cpu_usage_pct= float(r["cpu_usage_pct"]),
            ram_usage_pct= float(r["ram_usage_pct"]),
            availability = r["status"],
            queue_length = int(r["queue_length"]),
            os_type      = os_type,
        ))
    return nodes


def load_network_edges() -> List[NetworkEdge]:
    import sqlite3
    path = os.path.abspath(_DB_REL_PATH)
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT nl.source_server, nl.dest_server, nl.latency_ms, nl.bandwidth_mbps,
               COALESCE(rt.hop_count, 1) AS hop_count,
               COALESCE(AVG(tl.throughput_mbps), 0) / NULLIF(nl.bandwidth_mbps, 0) * 100 AS traffic_load
        FROM NetworkLinks nl
        LEFT JOIN RoutingTable rt ON rt.source_server = nl.source_server
                                  AND rt.dest_server  = nl.dest_server
        LEFT JOIN TrafficLogs tl  ON tl.link_id = nl.link_id
        WHERE nl.status != 'down'
        GROUP BY nl.link_id
    """).fetchall()
    conn.close()
    return [
        NetworkEdge(
            source_id     = r["source_server"],
            dest_id       = r["dest_server"],
            latency_ms    = float(r["latency_ms"]),
            bandwidth_mbps= float(r["bandwidth_mbps"]),
            hop_count     = int(r["hop_count"] or 1),
            traffic_load  = min(float(r["traffic_load"] or 0.0), 100.0),
        )
        for r in rows
    ]


def get_server_names() -> Dict[int, str]:
    servers = load_server_nodes()
    return {s.server_id: s.name for s in servers}
