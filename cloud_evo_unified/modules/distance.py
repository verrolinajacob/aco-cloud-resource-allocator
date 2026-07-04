"""Distance & Hop Count Matrix Module — Floyd-Warshall implementation."""

import streamlit as st
import pandas as pd
import plotly.express as px
import math
from database.db import get_conn
from utils.helpers import build_distance_matrix, build_hop_matrix


def render():
    st.title("📏 Distance & Hop Count Calculator")
    conn = get_conn()

    servers_df = pd.read_sql("SELECT server_id, name FROM Servers", conn)
    server_ids = servers_df["server_id"].tolist()
    id_to_name = dict(zip(servers_df["server_id"], servers_df["name"]))

    link_rows = conn.execute("""
        SELECT source_server, dest_server, latency_ms
        FROM   NetworkLinks WHERE status != 'down'
    """).fetchall()

    if not link_rows:
        st.warning("No active network links found. Add links in Network Topology.")
        conn.close()
        return

    dist = build_distance_matrix(server_ids, link_rows)
    hops = build_hop_matrix(server_ids, link_rows)

    tab1, tab2, tab3 = st.tabs(["📐 Distance Matrix", "🔢 Hop Matrix", "🔍 Path Query"])

    with tab1:
        st.subheader("Latency Distance Matrix (ms) — Floyd-Warshall")
        rows = []
        for src in server_ids:
            row = {"Server": id_to_name[src]}
            for dst in server_ids:
                val = dist[src][dst]
                row[id_to_name[dst]] = round(val, 1) if val != math.inf else "∞"
            rows.append(row)
        df_dist = pd.DataFrame(rows).set_index("Server")
        st.dataframe(df_dist, use_container_width=True)

        # Heatmap (replace inf with large num for color)
        numeric_rows = []
        for src in server_ids:
            row = {}
            for dst in server_ids:
                val = dist[src][dst]
                row[id_to_name[dst]] = val if val != math.inf else 9999
            numeric_rows.append(row)
        df_heat = pd.DataFrame(numeric_rows, index=[id_to_name[s] for s in server_ids])
        fig = px.imshow(df_heat, text_auto=True, aspect="auto",
                        color_continuous_scale="Blues",
                        title="Latency Heatmap (ms)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Hop Count Matrix")
        rows_h = []
        for src in server_ids:
            row = {"Server": id_to_name[src]}
            for dst in server_ids:
                val = hops[src][dst]
                row[id_to_name[dst]] = int(val) if val != math.inf else "∞"
            rows_h.append(row)
        df_hops = pd.DataFrame(rows_h).set_index("Server")
        st.dataframe(df_hops, use_container_width=True)

        numeric_hops = []
        for src in server_ids:
            row = {}
            for dst in server_ids:
                val = hops[src][dst]
                row[id_to_name[dst]] = int(val) if val != math.inf else 99
            numeric_hops.append(row)
        df_hop_heat = pd.DataFrame(numeric_hops, index=[id_to_name[s] for s in server_ids])
        fig2 = px.imshow(df_hop_heat, text_auto=True, aspect="auto",
                         color_continuous_scale="Greens",
                         title="Hop Count Heatmap")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Query Source → Destination")
        names = [id_to_name[s] for s in server_ids]
        name_to_id = {v: k for k, v in id_to_name.items()}
        c1, c2 = st.columns(2)
        src_name = c1.selectbox("Source",      names, key="qsrc")
        dst_name = c2.selectbox("Destination", names, key="qdst")

        src_id = name_to_id[src_name]
        dst_id = name_to_id[dst_name]

        if src_id == dst_id:
            st.info("Source and destination are the same node.")
        else:
            lat_val  = dist[src_id][dst_id]
            hop_val  = hops[src_id][dst_id]

            r1, r2, r3 = st.columns(3)
            r1.metric("📍 Min Latency", f"{lat_val:.1f} ms" if lat_val != math.inf else "Unreachable")
            r2.metric("🔢 Hop Count",   str(int(hop_val)) if hop_val != math.inf else "N/A")
            r3.metric("🔗 Reachable",   "✅ Yes" if lat_val != math.inf else "❌ No")

            if lat_val != math.inf:
                # Lookup routing table for the path
                route = conn.execute("""
                    SELECT route_path FROM RoutingTable
                    WHERE source_server=? AND dest_server=?
                    ORDER BY total_latency LIMIT 1
                """, (src_id, dst_id)).fetchone()
                if route and route[0]:
                    import json
                    path_ids = json.loads(route[0])
                    path_names = [id_to_name.get(p, str(p)) for p in path_ids]
                    st.info("**Route path:** " + " → ".join(path_names))

    conn.close()
