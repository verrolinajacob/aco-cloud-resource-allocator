"""Routing Table Management Module."""

import streamlit as st
import pandas as pd
import json
from database.db import get_conn


def render():
    st.title("🗺️ Routing Table Management")
    conn = get_conn()

    tab1, tab2 = st.tabs(["📋 Routing Table", "🔄 Recompute Routes"])

    with tab1:
        df = pd.read_sql("""
            SELECT r.route_id,
                   s1.name AS source, s2.name AS dest, s3.name AS next_hop,
                   r.hop_count, r.total_latency, r.route_path, r.algorithm,
                   r.updated_at
            FROM   RoutingTable r
            JOIN   Servers s1 ON r.source_server = s1.server_id
            JOIN   Servers s2 ON r.dest_server   = s2.server_id
            LEFT JOIN Servers s3 ON r.next_hop   = s3.server_id
            ORDER  BY r.total_latency
        """, conn)
        st.dataframe(df, use_container_width=True)

        st.subheader("Route Path Inspector")
        route_sel = st.selectbox("Select Route ID",
                                  df["route_id"].astype(str).tolist())
        row = df[df["route_id"] == int(route_sel)].iloc[0]
        try:
            path_ids = json.loads(row["route_path"])
            st.info(f"**{row['source']}** → ... → **{row['dest']}** | "
                    f"Hops: {row['hop_count']} | Latency: {row['total_latency']} ms | "
                    f"Algorithm: {row['algorithm']}")
        except Exception:
            st.warning("Could not parse route path.")

    with tab2:
        st.subheader("Recompute All Routes (Dijkstra)")
        st.info("This will regenerate routing entries based on current active NetworkLinks.")
        if st.button("🔄 Recompute Routes Now"):
            _recompute_routes(conn)
            st.success("Routes recomputed successfully.")
            st.rerun()

    conn.close()


def _recompute_routes(conn):
    """Simple Dijkstra-based route recomputation using active links."""
    import heapq, json
    from datetime import datetime

    servers = [r[0] for r in conn.execute("SELECT server_id FROM Servers").fetchall()]
    links   = conn.execute("""
        SELECT source_server, dest_server, latency_ms
        FROM   NetworkLinks WHERE status='active'
    """).fetchall()

    # Build adjacency
    graph = {s: [] for s in servers}
    for src, dst, lat in links:
        graph[src].append((lat, dst))
        graph[dst].append((lat, src))

    conn.execute("DELETE FROM RoutingTable")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for src in servers:
        # Dijkstra from src
        dist = {s: float("inf") for s in servers}
        prev = {s: None for s in servers}
        dist[src] = 0
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for w, v in graph[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))

        for dst in servers:
            if src == dst or dist[dst] == float("inf"):
                continue
            # Reconstruct path
            path, cur = [], dst
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            next_hop   = path[1] if len(path) > 1 else dst
            hop_count  = len(path) - 1
            conn.execute("""
                INSERT INTO RoutingTable
                (source_server, dest_server, next_hop, hop_count, total_latency,
                 route_path, algorithm, updated_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (src, dst, next_hop, hop_count,
                  round(dist[dst], 2), json.dumps(path), "dijkstra", now))

    conn.commit()
