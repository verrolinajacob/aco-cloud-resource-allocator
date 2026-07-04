"""
API Output Viewer
Simulates the REST API output this layer exposes to the Optimization layer (Part 2).
All outputs described in the spec:
  traffic metrics, server availability, distance matrix, hop-count matrix,
  resource utilization metrics, task information, routing information.
"""

import streamlit as st
import pandas as pd
import json
import math
from database.db import get_conn
from utils.helpers import build_distance_matrix, build_hop_matrix


def render():
    st.title("🔌 API Output Viewer")
    st.caption("Simulated REST API responses that Part 2 (Optimization Layer) will consume.")

    conn = get_conn()

    endpoints = {
        "GET /api/traffic-metrics":       _traffic_metrics,
        "GET /api/server-availability":   _server_availability,
        "GET /api/distance-matrix":       _distance_matrix,
        "GET /api/hop-count-matrix":      _hop_matrix,
        "GET /api/resource-utilization":  _resource_utilization,
        "GET /api/tasks":                 _tasks,
        "GET /api/routing-table":         _routing_table,
    }

    sel = st.selectbox("Select API Endpoint", list(endpoints.keys()))
    st.divider()

    with st.spinner("Fetching..."):
        payload = endpoints[sel](conn)

    st.success(f"200 OK  |  {sel}")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.json(payload)
    with col2:
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(payload, indent=2),
            file_name=sel.replace("GET /api/", "").replace("-","_") + ".json",
            mime="application/json"
        )

    conn.close()


# ── Endpoint implementations ────────────────────────────────────────────────

def _traffic_metrics(conn):
    rows = conn.execute("""
        SELECT s1.name||'→'||s2.name AS link,
               ROUND(AVG(tl.throughput_mbps),2) AS avg_throughput_mbps,
               ROUND(AVG(tl.latency_ms),2)      AS avg_latency_ms,
               SUM(tl.bytes_sent)               AS total_bytes_sent,
               SUM(tl.bytes_received)           AS total_bytes_received,
               SUM(tl.active_sessions)          AS total_sessions
        FROM   TrafficLogs tl
        JOIN   NetworkLinks nl ON tl.link_id = nl.link_id
        JOIN   Servers s1 ON nl.source_server = s1.server_id
        JOIN   Servers s2 ON nl.dest_server   = s2.server_id
        GROUP  BY tl.link_id
        ORDER  BY avg_throughput_mbps DESC
    """).fetchall()
    return {"traffic_metrics": [dict(r) for r in rows]}


def _server_availability(conn):
    rows = conn.execute("""
        SELECT s.server_id, s.name, s.region, s.server_type, s.status,
               s.ip_address,
               ROUND(AVG(m.cpu_usage_pct),1)  AS avg_cpu_pct,
               ROUND(AVG(m.ram_usage_pct),1)  AS avg_ram_pct,
               MAX(m.uptime_seconds)           AS uptime_seconds
        FROM   Servers s
        LEFT JOIN Metrics m ON s.server_id = m.server_id
        GROUP  BY s.server_id
    """).fetchall()
    return {"server_availability": [dict(r) for r in rows]}


def _distance_matrix(conn):
    servers = conn.execute("SELECT server_id, name FROM Servers").fetchall()
    server_ids = [r[0] for r in servers]
    id_to_name = {r[0]: r[1] for r in servers}
    link_rows  = conn.execute(
        "SELECT source_server, dest_server, latency_ms FROM NetworkLinks WHERE status!='down'"
    ).fetchall()
    dist = build_distance_matrix(server_ids, link_rows)
    matrix = {}
    for src in server_ids:
        matrix[id_to_name[src]] = {
            id_to_name[dst]: (round(dist[src][dst], 2) if dist[src][dst] != math.inf else None)
            for dst in server_ids
        }
    return {"distance_matrix_ms": matrix}


def _hop_matrix(conn):
    servers = conn.execute("SELECT server_id, name FROM Servers").fetchall()
    server_ids = [r[0] for r in servers]
    id_to_name = {r[0]: r[1] for r in servers}
    link_rows  = conn.execute(
        "SELECT source_server, dest_server, latency_ms FROM NetworkLinks WHERE status!='down'"
    ).fetchall()
    hops = build_hop_matrix(server_ids, link_rows)
    matrix = {}
    for src in server_ids:
        matrix[id_to_name[src]] = {
            id_to_name[dst]: (int(hops[src][dst]) if hops[src][dst] != math.inf else None)
            for dst in server_ids
        }
    return {"hop_count_matrix": matrix}


def _resource_utilization(conn):
    rows = conn.execute("""
        SELECT s.name, s.region, s.cpu_cores, s.ram_gb, s.storage_tb,
               ROUND(m.cpu_usage_pct,1)     AS cpu_usage_pct,
               ROUND(m.ram_usage_pct,1)     AS ram_usage_pct,
               ROUND(m.storage_usage_pct,1) AS storage_usage_pct,
               ROUND(m.network_in_mbps,2)   AS network_in_mbps,
               ROUND(m.network_out_mbps,2)  AS network_out_mbps,
               m.timestamp
        FROM   Metrics m
        JOIN   Servers s ON m.server_id = s.server_id
        WHERE  m.timestamp = (
            SELECT MAX(m2.timestamp) FROM Metrics m2 WHERE m2.server_id = m.server_id
        )
    """).fetchall()
    return {"resource_utilization": [dict(r) for r in rows]}


def _tasks(conn):
    rows = conn.execute("""
        SELECT t.task_id, t.name, u.username AS user, s.name AS server,
               t.cpu_required, t.ram_required, t.priority, t.status,
               t.submitted_at, t.completed_at
        FROM   Tasks t
        LEFT JOIN Users   u ON t.user_id         = u.user_id
        LEFT JOIN Servers s ON t.assigned_server = s.server_id
        ORDER  BY t.priority DESC
    """).fetchall()
    return {"tasks": [dict(r) for r in rows]}


def _routing_table(conn):
    rows = conn.execute("""
        SELECT s1.name AS source, s2.name AS dest,
               s3.name AS next_hop, r.hop_count,
               r.total_latency, r.route_path, r.algorithm
        FROM   RoutingTable r
        JOIN   Servers s1 ON r.source_server = s1.server_id
        JOIN   Servers s2 ON r.dest_server   = s2.server_id
        LEFT JOIN Servers s3 ON r.next_hop   = s3.server_id
        ORDER  BY r.total_latency
    """).fetchall()
    return {"routing_table": [dict(r) for r in rows]}
