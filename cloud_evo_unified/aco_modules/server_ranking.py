"""
Server Ranking Engine — Part 2, Module 3.

Scores and ranks all servers using ACO pheromone data combined with
real-time metrics. Supports custom weight tuning.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, is_db_available
)


def render():
    st.title("🏆 Server Ranking Engine")
    st.markdown(
        "Rank all servers by **ACO composite score** combining pheromone trails, "
        "CPU, RAM, availability, and queue depth."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ {msg}")
        return

    servers = load_server_nodes()
    edges   = load_network_edges()

    # ── Weight Tuner ──────────────────────────────────────────────────────
    st.subheader("🎚️ Scoring Weight Configuration")
    col1, col2, col3, col4, col5 = st.columns(5)
    w_lat  = col1.slider("Latency",   0.0, 1.0, 0.30, 0.05, key="rk_lat")
    w_cpu  = col2.slider("CPU Load",  0.0, 1.0, 0.25, 0.05, key="rk_cpu")
    w_ram  = col3.slider("RAM Load",  0.0, 1.0, 0.20, 0.05, key="rk_ram")
    w_tr   = col4.slider("Traffic",   0.0, 1.0, 0.15, 0.05, key="rk_tr")
    w_hop  = col5.slider("Hop Count", 0.0, 1.0, 0.10, 0.05, key="rk_hop")

    total = w_lat + w_cpu + w_ram + w_tr + w_hop
    if abs(total - 1.0) > 0.01:
        st.warning(f"⚠️ Weights sum to {total:.2f}. They don't need to sum to 1 but results are best when normalised.")

    source_name = st.selectbox(
        "Reference Source Server (ranking perspective)",
        [s.name for s in servers]
    )
    source_id = next(s.server_id for s in servers if s.name == source_name)

    if st.button("🏆 Compute Rankings", type="primary", use_container_width=True):
        params = ACOParameters(
            n_ants=25, n_iterations=60,
            w_latency=w_lat, w_cpu=w_cpu, w_ram=w_ram,
            w_traffic=w_tr, w_hops=w_hop
        )
        engine = ACOEngine(params)
        engine.load_graph(servers, edges)

        with st.spinner("Computing ACO scores for all servers..."):
            result = engine.run(source_id=source_id)

        srv_map = {s.server_id: s for s in servers}

        # Build ranking table
        rows = []
        for rank, (sid, score) in enumerate(
            sorted(result.server_scores.items(), key=lambda x: -x[1]), start=1
        ):
            s = srv_map.get(sid)
            if not s:
                continue
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            rows.append({
                "Rank": medal,
                "Server": s.name,
                "Region": s.region,
                "ACO Score": round(score, 4),
                "CPU %": round(s.cpu_usage_pct, 1),
                "RAM %": round(s.ram_usage_pct, 1),
                "Queue": s.queue_length,
                "Availability": s.availability,
            })

        df_rank = pd.DataFrame(rows)
        st.subheader("📋 Server Rankings")
        st.dataframe(df_rank, use_container_width=True, hide_index=True)

        # Horizontal score bar
        fig = px.bar(
            df_rank.sort_values("ACO Score"),
            x="ACO Score", y="Server",
            orientation="h",
            color="ACO Score",
            color_continuous_scale="RdYlGn",
            title="Server ACO Scores (Best → Worst)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Radar comparison – top 4
        top4 = df_rank.head(4)
        st.subheader("📡 Top 4 Radar Comparison")
        categories = ["ACO Score", "CPU %", "RAM %", "Queue"]

        fig2 = go.Figure()
        for _, row in top4.iterrows():
            vals = [
                row["ACO Score"] * 100,          # scale to 0-100
                100 - row["CPU %"],               # invert (lower CPU = better)
                100 - row["RAM %"],
                max(0, 10 - row["Queue"]) * 10,  # queue 0=100, 10+=0
            ]
            fig2.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=row["Server"],
            ))
        fig2.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="Top 4 Server Comparison Radar"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Region heatmap
        st.subheader("🗺️ Score by Region")
        df_region = df_rank.groupby("Region")["ACO Score"].mean().reset_index()
        fig3 = px.bar(df_region, x="Region", y="ACO Score",
                      color="ACO Score", color_continuous_scale="Blues",
                      title="Average ACO Score per Region")
        st.plotly_chart(fig3, use_container_width=True)
