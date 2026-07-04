"""
Resource Allocation Manager — Part 2, Module 1.

Accepts a task description, runs ACO, and returns an allocation decision
with resource fit validation and fallback logic.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
import random
from datetime import datetime

from aco_engine.aco_core import ACOEngine, ACOParameters, ACOResult
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, get_server_names, is_db_available
)


def _build_engine(params: ACOParameters) -> ACOEngine:
    engine = ACOEngine(params)
    servers = load_server_nodes()
    edges   = load_network_edges()
    engine.load_graph(servers, edges)
    return engine


def render():
    st.title("🐜 Resource Allocation Manager")
    st.markdown(
        "Submit a workload task and let the **ACO engine** select the optimal "
        "server using ant colony path discovery and pheromone reinforcement."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ Part 1 database not available.\n\n{msg}")
        st.info("Run Part 1 first, then copy `cloud_sim.db` into `part1_db/`.")
        return

    st.success(f"✅ {msg}")

    # ── Task Input ─────────────────────────────────────────────────────────
    st.subheader("📋 Task Definition")
    col1, col2, col3 = st.columns(3)
    task_name  = col1.text_input("Task Name", value=f"task-{random.randint(100,999)}")
    cpu_req    = col2.slider("CPU Required (cores)", 0.5, 32.0, 2.0, 0.5)
    ram_req    = col3.slider("RAM Required (GB)",    1.0, 128.0, 4.0, 1.0)
    priority   = col1.selectbox("Priority", [1, 2, 3, 4, 5],
                                format_func=lambda x: f"{x} – {'Low' if x==1 else 'Med-Low' if x==2 else 'Medium' if x==3 else 'High' if x==4 else 'Critical'}",
                                index=2)

    servers = load_server_nodes()
    srv_options = {s.name: s.server_id for s in servers}
    source_name = col2.selectbox("Source / Origin Server", list(srv_options.keys()))
    source_id   = srv_options[source_name]

    # ── ACO Parameters ─────────────────────────────────────────────────────
    with st.expander("⚙️ ACO Hyperparameters (optional)"):
        c1, c2, c3 = st.columns(3)
        n_ants       = c1.slider("Number of Ants",        5,  100, 20)
        n_iterations = c2.slider("Iterations",            10, 200, 50)
        alpha        = c3.slider("α (pheromone weight)",  0.1, 5.0, 1.0, 0.1)
        rho          = c1.slider("ρ (evaporation rate)",  0.01, 0.9, 0.3, 0.01)
        beta         = c2.slider("β (heuristic weight)",  0.1, 5.0, 2.5, 0.1)
        c3.markdown("")

    params = ACOParameters(
        n_ants=n_ants, n_iterations=n_iterations,
        alpha=alpha, beta=beta, rho=rho
    )

    # ── Run ACO ────────────────────────────────────────────────────────────
    if st.button("🚀 Run ACO Allocation", type="primary", use_container_width=True):
        with st.spinner("🐜 Ants exploring the server graph..."):
            engine = _build_engine(params)
            result: ACOResult = engine.run(source_id=source_id)

        st.divider()
        st.subheader("✅ Allocation Result")

        best_srv = next((s for s in servers if s.server_id == result.best_server_id), None)

        # Summary cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🎯 Best Server",     result.best_server_name)
        m2.metric("⭐ ACO Score",       f"{result.best_score:.4f}")
        m3.metric("📍 Path Cost",       f"{result.best_path_cost:.1f} ms" if result.best_path_cost < math.inf else "N/A")
        m4.metric("🔁 Converged At",   f"Iteration {result.convergence_iteration}")

        if best_srv:
            st.info(
                f"**{best_srv.name}** | Region: `{best_srv.region}` | "
                f"CPU: `{best_srv.cpu_usage_pct:.1f}%` | RAM: `{best_srv.ram_usage_pct:.1f}%` | "
                f"Status: `{best_srv.availability}` | Queue: `{best_srv.queue_length} tasks`"
            )

        # Resource fit check
        st.subheader("🔍 Resource Fit Analysis")
        srv_map = {s.server_id: s for s in servers}
        fit_rows = []
        for sid, score in sorted(result.server_scores.items(), key=lambda x: -x[1]):
            srv = srv_map.get(sid)
            if not srv:
                continue
            fit_rows.append({
                "Server": srv.name,
                "Region": srv.region,
                "ACO Score": round(score, 4),
                "CPU %": srv.cpu_usage_pct,
                "RAM %": srv.ram_usage_pct,
                "Queue": srv.queue_length,
                "Status": srv.availability,
                "Recommended": "✅" if sid == result.best_server_id else "",
            })
        df_fit = pd.DataFrame(fit_rows)
        st.dataframe(df_fit, use_container_width=True, hide_index=True)

        # Score bar chart
        fig = px.bar(
            df_fit, x="Server", y="ACO Score",
            color="ACO Score", color_continuous_scale="Viridis",
            title="Server ACO Scores (Higher = Better)",
            labels={"ACO Score": "Score"}
        )
        fig.add_hline(y=result.best_score, line_dash="dash",
                      line_color="red", annotation_text="Best")
        st.plotly_chart(fig, use_container_width=True)

        # Convergence curve
        st.subheader("📉 ACO Convergence Curve")
        df_conv = pd.DataFrame({
            "Iteration": list(range(1, len(result.iteration_costs)+1)),
            "Best Cost (ms)": result.iteration_costs
        })
        fig2 = px.line(df_conv, x="Iteration", y="Best Cost (ms)",
                       title="Best Path Cost per Iteration",
                       markers=True)
        fig2.add_vline(x=result.convergence_iteration, line_dash="dot",
                       line_color="green", annotation_text="Converged")
        st.plotly_chart(fig2, use_container_width=True)

        # Best path display
        if result.best_path:
            names = get_server_names()
            path_names = [names.get(sid, str(sid)) for sid in result.best_path]
            st.subheader("🗺️ Best Ant Path")
            st.code(" → ".join(path_names), language="")

        # Log allocation to session
        if "allocations" not in st.session_state:
            st.session_state.allocations = []
        st.session_state.allocations.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "task": task_name,
            "cpu_req": cpu_req,
            "ram_req": ram_req,
            "priority": priority,
            "allocated_to": result.best_server_name,
            "score": round(result.best_score, 4),
        })

    # ── Allocation History ─────────────────────────────────────────────────
    if st.session_state.get("allocations"):
        st.divider()
        st.subheader("📜 Allocation History (This Session)")
        df_hist = pd.DataFrame(st.session_state.allocations)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
