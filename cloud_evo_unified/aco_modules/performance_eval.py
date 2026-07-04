"""
Performance Evaluation Module — Part 2, Module 4.

Evaluates ACO algorithm performance across multiple runs,
including convergence speed, solution quality, and stability analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import math
import random
import time

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, is_db_available
)


def render():
    st.title("📊 Performance Evaluation Module")
    st.markdown(
        "Benchmark the ACO engine: measure convergence speed, solution quality, "
        "and compare parameter configurations."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ {msg}")
        return

    servers = load_server_nodes()
    edges   = load_network_edges()
    srv_names = {s.server_id: s.name for s in servers}
    source_id  = servers[0].server_id if servers else 1

    tab1, tab2, tab3 = st.tabs([
        "🔁 Multi-Run Analysis",
        "⚙️ Parameter Sensitivity",
        "📈 Metrics Overview"
    ])

    # ── Tab 1: Multi-Run Analysis ─────────────────────────────────────────
    with tab1:
        st.subheader("Multi-Run Convergence Analysis")
        st.markdown("Run ACO multiple times and compare results for stability.")

        c1, c2 = st.columns(2)
        n_runs      = c1.slider("Number of Runs", 3, 15, 5, key="pe_runs")
        n_iter_eval = c2.slider("Iterations per Run", 20, 150, 50, key="pe_iter")

        if st.button("▶️ Run Analysis", type="primary", key="pe_run_btn"):
            params = ACOParameters(n_ants=20, n_iterations=n_iter_eval)
            engine = ACOEngine(params)
            engine.load_graph(servers, edges)

            run_results = []
            all_curves = []

            bar = st.progress(0)
            for run_i in range(n_runs):
                t0 = time.time()
                result = engine.run(source_id=source_id)
                elapsed = time.time() - t0

                run_results.append({
                    "Run": run_i + 1,
                    "Best Server": result.best_server_name,
                    "Score": round(result.best_score, 4),
                    "Best Cost (ms)": round(result.best_path_cost, 2) if result.best_path_cost < math.inf else 9999,
                    "Converged At": result.convergence_iteration,
                    "Runtime (s)": round(elapsed, 3),
                })
                all_curves.append(result.iteration_costs)
                bar.progress((run_i + 1) / n_runs)

            bar.empty()
            df_runs = pd.DataFrame(run_results)
            st.dataframe(df_runs, use_container_width=True, hide_index=True)

            # Stats
            scores = df_runs["Score"].tolist()
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Best Score",   f"{max(scores):.4f}")
            s2.metric("Avg Score",    f"{sum(scores)/len(scores):.4f}")
            s3.metric("Worst Score",  f"{min(scores):.4f}")
            s4.metric("Std Dev",      f"{pd.Series(scores).std():.4f}")

            # Convergence curves
            st.subheader("📉 Convergence Curves (All Runs)")
            fig = go.Figure()
            for i, curve in enumerate(all_curves):
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(curve)+1)),
                    y=curve,
                    name=f"Run {i+1}",
                    mode="lines",
                    opacity=0.7,
                ))
            # Average curve
            if all_curves:
                min_len = min(len(c) for c in all_curves)
                avg_curve = [
                    sum(c[i] for c in all_curves if i < len(c)) / n_runs
                    for i in range(min_len)
                ]
                fig.add_trace(go.Scatter(
                    x=list(range(1, min_len+1)),
                    y=avg_curve,
                    name="Average",
                    mode="lines",
                    line=dict(color="black", width=3, dash="dash"),
                ))
            fig.update_layout(title="Best Cost per Iteration (All Runs)",
                              xaxis_title="Iteration", yaxis_title="Cost (ms)")
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: Parameter Sensitivity ─────────────────────────────────────
    with tab2:
        st.subheader("⚙️ Parameter Sensitivity Analysis")
        st.markdown("Test how α, ρ, and ant count affect score quality.")

        param_to_test = st.selectbox(
            "Parameter to sweep",
            ["Alpha (α)", "Rho (ρ) Evaporation", "Ant Count"]
        )

        if st.button("🔬 Run Sensitivity Test", type="primary", key="sens_btn"):
            results_sens = []

            if param_to_test == "Alpha (α)":
                sweep_vals = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
                label = "Alpha"
                def make_params(v): return ACOParameters(alpha=v, n_ants=15, n_iterations=40)
            elif param_to_test == "Rho (ρ) Evaporation":
                sweep_vals = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7]
                label = "Rho"
                def make_params(v): return ACOParameters(rho=v, n_ants=15, n_iterations=40)
            else:
                sweep_vals = [5, 10, 15, 20, 30, 50]
                label = "Ants"
                def make_params(v): return ACOParameters(n_ants=int(v), n_iterations=40)

            bar2 = st.progress(0)
            for i, val in enumerate(sweep_vals):
                p = make_params(val)
                eng = ACOEngine(p)
                eng.load_graph(servers, edges)
                r = eng.run(source_id=source_id)
                results_sens.append({
                    label: val,
                    "Best Score": round(r.best_score, 4),
                    "Converged At": r.convergence_iteration,
                    "Best Cost": round(r.best_path_cost, 2) if r.best_path_cost < math.inf else 9999,
                })
                bar2.progress((i+1)/len(sweep_vals))

            bar2.empty()
            df_sens = pd.DataFrame(results_sens)
            st.dataframe(df_sens, use_container_width=True, hide_index=True)

            fig_s1 = px.line(df_sens, x=label, y="Best Score", markers=True,
                             title=f"Score vs {label}")
            st.plotly_chart(fig_s1, use_container_width=True)

            fig_s2 = px.line(df_sens, x=label, y="Converged At", markers=True,
                             title=f"Convergence Speed vs {label}",
                             color_discrete_sequence=["#f39c12"])
            st.plotly_chart(fig_s2, use_container_width=True)

    # ── Tab 3: Metrics Overview ────────────────────────────────────────────
    with tab3:
        st.subheader("📈 Live Metrics from Part 1")

        from aco_engine.data_loader import get_all_metrics_snapshot, get_traffic_summary

        metrics = get_all_metrics_snapshot()
        if metrics:
            df_m = pd.DataFrame(metrics)
            st.dataframe(df_m, use_container_width=True, hide_index=True)

            fig_m = px.scatter(
                df_m, x="cpu_usage_pct", y="ram_usage_pct",
                color="status", size="network_in_mbps",
                hover_name="name", text="name",
                title="CPU vs RAM Usage (bubble = Network In)",
                labels={"cpu_usage_pct": "CPU %", "ram_usage_pct": "RAM %"}
            )
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("No metrics data found. Run Part 1 to populate metrics.")

        traffic = get_traffic_summary()
        if traffic:
            st.subheader("🌐 Traffic Summary (24h)")
            df_t = pd.DataFrame(traffic)
            fig_t = px.bar(
                df_t.head(10), x="src_name", y="avg_throughput",
                color="avg_latency", color_continuous_scale="RdYlGn_r",
                title="Top 10 Links by Throughput",
                labels={"src_name": "Source", "avg_throughput": "Throughput (Mbps)"}
            )
            st.plotly_chart(fig_t, use_container_width=True)
