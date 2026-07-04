"""
ACO Path Discovery & Pheromone Visualizer — Part 2, Module 5.

Shows ant paths, pheromone strength on edges, and routing decisions.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import random

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, is_db_available, get_server_names
)


def render():
    st.title("🗺️ ACO Path Discovery & Pheromone Map")
    st.markdown(
        "Visualise how ants discover paths, deposit pheromones, and converge "
        "toward optimal routing decisions."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ {msg}")
        return

    servers = load_server_nodes()
    edges   = load_network_edges()
    srv_map = {s.server_id: s for s in servers}
    srv_names = {s.server_id: s.name for s in servers}

    col1, col2 = st.columns(2)
    source_name = col1.selectbox("Source Server", [s.name for s in servers], key="pd_src")
    target_name = col2.selectbox("Target Server",
                                 [s.name for s in servers if s.name != source_name],
                                 key="pd_tgt")

    source_id = next(s.server_id for s in servers if s.name == source_name)
    target_id = next(s.server_id for s in servers if s.name == target_name)

    with st.expander("⚙️ ACO Settings"):
        c1, c2 = st.columns(2)
        n_ants = c1.slider("Ants", 5, 50, 20, key="pd_ants")
        n_iter = c2.slider("Iterations", 10, 100, 40, key="pd_iter")

    if st.button("🐜 Discover Paths", type="primary", use_container_width=True):
        params = ACOParameters(n_ants=n_ants, n_iterations=n_iter)
        engine = ACOEngine(params)
        engine.load_graph(servers, edges)

        with st.spinner("Ants exploring..."):
            result = engine.run(source_id=source_id)

        # ── Pheromone Heatmap ─────────────────────────────────────────────
        st.subheader("🧪 Pheromone Strength Matrix")
        n_srv = len(servers)
        matrix = [[0.0] * n_srv for _ in range(n_srv)]
        sid_list = [s.server_id for s in servers]
        name_list = [s.name for s in servers]

        for i, si in enumerate(sid_list):
            for j, sj in enumerate(sid_list):
                key = (si, sj)
                matrix[i][j] = engine.pheromones.get(key, 0.0)

        fig_heat = go.Figure(data=go.Heatmap(
            z=matrix,
            x=name_list,
            y=name_list,
            colorscale="YlOrRd",
            colorbar=dict(title="Pheromone τ"),
        ))
        fig_heat.update_layout(
            title="Pheromone Trail Matrix (after ACO convergence)",
            xaxis_title="Destination", yaxis_title="Source",
            height=500
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # ── Ant Path Frequency ────────────────────────────────────────────
        st.subheader("📊 Path Node Visit Frequency")
        visit_count = {s.server_id: 0 for s in servers}
        for path in result.all_ant_paths[:100]:
            for sid in path:
                visit_count[sid] = visit_count.get(sid, 0) + 1

        df_visit = pd.DataFrame([
            {"Server": srv_names.get(sid, str(sid)), "Visits": cnt}
            for sid, cnt in sorted(visit_count.items(), key=lambda x: -x[1])
        ])
        fig_visits = px.bar(
            df_visit, x="Server", y="Visits",
            color="Visits", color_continuous_scale="Viridis",
            title="How Often Each Server Was Visited by Ants"
        )
        st.plotly_chart(fig_visits, use_container_width=True)

        # ── Pheromone Evolution ───────────────────────────────────────────
        if result.pheromone_history:
            st.subheader("📉 Pheromone Evolution (Sample Edges)")
            ph_df_rows = []
            for snap in result.pheromone_history:
                for edge_key, val in list(snap["pheromones"].items())[:5]:
                    ph_df_rows.append({
                        "Iteration": snap["iteration"],
                        "Edge": str(edge_key),
                        "Pheromone": val
                    })
            if ph_df_rows:
                df_ph = pd.DataFrame(ph_df_rows)
                fig_ph = px.line(df_ph, x="Iteration", y="Pheromone",
                                 color="Edge",
                                 title="Pheromone Level per Edge Over Iterations")
                st.plotly_chart(fig_ph, use_container_width=True)

        # ── Best Path ─────────────────────────────────────────────────────
        st.subheader("✅ Best Discovered Path")
        if result.best_path:
            path_names = [srv_names.get(sid, str(sid)) for sid in result.best_path]
            st.markdown("**Route:** " + " **→** ".join(path_names))

            df_path = pd.DataFrame({
                "Step": list(range(1, len(path_names)+1)),
                "Server": path_names,
            })
            st.dataframe(df_path, use_container_width=True, hide_index=True)
        else:
            st.info("No multi-hop path discovered. Servers may be directly connected.")

        # ── Convergence ───────────────────────────────────────────────────
        st.subheader("📉 Convergence Curve")
        df_conv = pd.DataFrame({
            "Iteration": list(range(1, len(result.iteration_costs)+1)),
            "Best Cost": result.iteration_costs
        })
        fig_conv = px.area(df_conv, x="Iteration", y="Best Cost",
                           title="Cost Reduction Over Iterations",
                           color_discrete_sequence=["#3498db"])
        fig_conv.add_vline(x=result.convergence_iteration, line_dash="dash",
                           line_color="green", annotation_text="Converged")
        st.plotly_chart(fig_conv, use_container_width=True)
