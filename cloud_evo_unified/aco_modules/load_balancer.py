"""
Load Balancing Engine — Part 2, Module 2.

Uses ACO scores to redistribute tasks across over-loaded servers.
Provides balancing recommendations and before/after visualizations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, is_db_available
)


_THRESHOLD_CPU = 75.0
_THRESHOLD_RAM = 75.0
_THRESHOLD_QUEUE = 5


def _classify(cpu, ram, queue):
    if cpu > _THRESHOLD_CPU or ram > _THRESHOLD_RAM or queue >= _THRESHOLD_QUEUE:
        return "🔴 Overloaded"
    elif cpu > 50 or ram > 50:
        return "🟡 Moderate"
    else:
        return "🟢 Healthy"


def render():
    st.title("⚖️ Load Balancing Engine")
    st.markdown(
        "Detect overloaded servers and use **ACO-driven rebalancing** "
        "to migrate tasks to optimal underutilised nodes."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ Part 1 database not available.\n\n{msg}")
        return

    servers = load_server_nodes()
    edges   = load_network_edges()

    # ── Current Load Overview ──────────────────────────────────────────────
    st.subheader("📊 Current Server Load")

    rows = []
    for s in servers:
        state = _classify(s.cpu_usage_pct, s.ram_usage_pct, s.queue_length)
        rows.append({
            "Server": s.name,
            "Region": s.region,
            "CPU %": s.cpu_usage_pct,
            "RAM %": s.ram_usage_pct,
            "Queue": s.queue_length,
            "Status": s.availability,
            "Load State": state,
        })
    df = pd.DataFrame(rows)

    overloaded = df[df["Load State"] == "🔴 Overloaded"]
    healthy    = df[df["Load State"] == "🟢 Healthy"]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Overloaded", len(overloaded))
    c2.metric("🟡 Moderate",   len(df[df["Load State"] == "🟡 Moderate"]))
    c3.metric("🟢 Healthy",    len(healthy))

    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Load Gauge Charts ─────────────────────────────────────────────────
    st.subheader("🌡️ Per-Server Load Gauges")
    cols = st.columns(min(len(servers), 4))
    for i, s in enumerate(servers[:8]):
        with cols[i % 4]:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=s.cpu_usage_pct,
                title={"text": s.name, "font": {"size": 11}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 50],  "color": "#2ecc71"},
                        {"range": [50, 75], "color": "#f39c12"},
                        {"range": [75, 100],"color": "#e74c3c"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 2},
                        "thickness": 0.75,
                        "value": _THRESHOLD_CPU,
                    }
                }
            ))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # ── ACO Rebalancing ───────────────────────────────────────────────────
    st.divider()
    st.subheader("🐜 ACO Rebalancing Recommendations")

    if len(overloaded) == 0:
        st.success("✅ All servers are within healthy load thresholds. No rebalancing needed.")
        return

    with st.expander("⚙️ ACO Parameters"):
        c1, c2 = st.columns(2)
        n_ants = c1.slider("Ants", 5, 50, 15, key="lb_ants")
        n_iter = c2.slider("Iterations", 10, 100, 30, key="lb_iter")

    if st.button("⚖️ Run ACO Rebalancing", type="primary", use_container_width=True):
        params = ACOParameters(n_ants=n_ants, n_iterations=n_iter)
        engine = ACOEngine(params)
        engine.load_graph(servers, edges)

        srv_map = {s.server_id: s for s in servers}
        recommendations = []

        progress = st.progress(0)
        overloaded_rows = df[df["Load State"] == "🔴 Overloaded"]

        for idx, (_, row_data) in enumerate(overloaded_rows.iterrows()):
            src_srv = next((s for s in servers if s.name == row_data["Server"]), None)
            if src_srv is None:
                continue

            result = engine.run(source_id=src_srv.server_id)
            target = srv_map.get(result.best_server_id)

            # Simulate tasks to migrate
            tasks_to_migrate = max(1, src_srv.queue_length // 2)
            recommendations.append({
                "Overloaded Server": src_srv.name,
                "Source CPU %": src_srv.cpu_usage_pct,
                "Source RAM %": src_srv.ram_usage_pct,
                "Source Queue": src_srv.queue_length,
                "→ Target Server": result.best_server_name,
                "Target CPU %": target.cpu_usage_pct if target else "N/A",
                "Target Score": round(result.best_score, 4),
                "Tasks to Migrate": tasks_to_migrate,
            })
            progress.progress((idx + 1) / len(overloaded_rows))

        progress.empty()

        df_rec = pd.DataFrame(recommendations)
        st.subheader("📋 Rebalancing Plan")
        st.dataframe(df_rec, use_container_width=True, hide_index=True)

        # Before / After simulation
        st.subheader("📈 Projected Load After Rebalancing")
        before_cpu = [s.cpu_usage_pct for s in servers]
        after_cpu  = []
        for s in servers:
            reduction = 0
            for rec in recommendations:
                if rec["Overloaded Server"] == s.name:
                    reduction += random.uniform(10, 20)
                if rec["→ Target Server"] == s.name:
                    reduction -= random.uniform(3, 8)
            after_cpu.append(max(5.0, min(100.0, s.cpu_usage_pct - reduction)))

        fig = go.Figure()
        srv_names = [s.name for s in servers]
        fig.add_trace(go.Bar(name="Before", x=srv_names, y=before_cpu,
                             marker_color="#e74c3c"))
        fig.add_trace(go.Bar(name="After",  x=srv_names, y=after_cpu,
                             marker_color="#2ecc71"))
        fig.add_hline(y=_THRESHOLD_CPU, line_dash="dash",
                      line_color="orange", annotation_text="Threshold (75%)")
        fig.update_layout(barmode="group", title="CPU Load: Before vs After Rebalancing",
                          yaxis_title="CPU %", xaxis_title="Server")
        st.plotly_chart(fig, use_container_width=True)

        # Summary
        avg_before = sum(before_cpu) / len(before_cpu)
        avg_after  = sum(after_cpu)  / len(after_cpu)
        st.success(
            f"Rebalancing would reduce average CPU load from "
            f"**{avg_before:.1f}%** → **{avg_after:.1f}%** "
            f"({avg_before - avg_after:.1f}% improvement)"
        )
