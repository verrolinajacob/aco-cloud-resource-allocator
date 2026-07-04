"""
Reporting Dashboard — Part 2, Module 6.

Comprehensive performance analytics, allocation summaries,
and exportable reports integrating all Part 2 outputs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import math

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges,
    get_all_metrics_snapshot, get_traffic_summary, is_db_available
)


def render():
    st.title("📋 ACO Reporting Dashboard")
    st.markdown(
        "Unified view of allocation performance, server health, "
        "traffic analysis, and ACO decision analytics."
    )

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ {msg}")
        return

    servers  = load_server_nodes()
    edges    = load_network_edges()
    metrics  = get_all_metrics_snapshot()
    traffic  = get_traffic_summary()

    srv_map  = {s.server_id: s for s in servers}
    srv_names = {s.server_id: s.name for s in servers}

    # ── KPI Header ────────────────────────────────────────────────────────
    total     = len(servers)
    online    = sum(1 for s in servers if s.availability == "online")
    avg_cpu   = sum(s.cpu_usage_pct for s in servers) / total if total else 0
    avg_ram   = sum(s.ram_usage_pct for s in servers) / total if total else 0
    overloaded = sum(1 for s in servers if s.cpu_usage_pct > 75 or s.ram_usage_pct > 75)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🖥️ Total Servers", total)
    k2.metric("✅ Online",        online,     delta=f"{total-online} offline", delta_color="inverse")
    k3.metric("⚡ Avg CPU",       f"{avg_cpu:.1f}%")
    k4.metric("💾 Avg RAM",       f"{avg_ram:.1f}%")
    k5.metric("🔴 Overloaded",    overloaded, delta_color="inverse")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Infrastructure Health",
        "🐜 ACO Decision Summary",
        "📈 Traffic Analytics",
        "📤 Export Report"
    ])

    # ── Tab 1: Infrastructure Health ─────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            df_status = pd.DataFrame([
                {"Status": s.availability, "Count": 1}
                for s in servers
            ]).groupby("Status").sum().reset_index()
            fig = px.pie(df_status, names="Status", values="Count",
                         title="Server Availability Distribution",
                         color="Status",
                         color_discrete_map={
                             "online": "#2ecc71",
                             "maintenance": "#f39c12",
                             "offline": "#e74c3c"
                         })
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if metrics:
                df_m = pd.DataFrame(metrics)
                fig2 = px.scatter(
                    df_m, x="cpu_usage_pct", y="ram_usage_pct",
                    color="status", text="name", size_max=20,
                    title="CPU vs RAM: All Servers",
                    labels={"cpu_usage_pct": "CPU %", "ram_usage_pct": "RAM %"}
                )
                fig2.add_shape(type="rect",
                               x0=75, y0=0, x1=100, y1=100,
                               fillcolor="red", opacity=0.05,
                               line_color="red", line_dash="dot")
                st.plotly_chart(fig2, use_container_width=True)

        # Resource heatmap
        if metrics:
            df_m = pd.DataFrame(metrics)
            fig3 = go.Figure()
            metrics_cols = ["cpu_usage_pct", "ram_usage_pct", "storage_usage_pct"]
            for col in metrics_cols:
                fig3.add_trace(go.Bar(
                    name=col.replace("_usage_pct", "").upper(),
                    x=df_m["name"],
                    y=df_m[col]
                ))
            fig3.add_hline(y=75, line_dash="dash", line_color="red",
                           annotation_text="Overload threshold")
            fig3.update_layout(barmode="group",
                               title="Resource Usage per Server",
                               yaxis_title="%", xaxis_title="Server")
            st.plotly_chart(fig3, use_container_width=True)

    # ── Tab 2: ACO Decision Summary ───────────────────────────────────────
    with tab2:
        st.subheader("Run ACO across all online servers")

        if st.button("🐜 Generate ACO Summary", type="primary", key="rpt_aco"):
            params = ACOParameters(n_ants=20, n_iterations=50)
            engine = ACOEngine(params)
            engine.load_graph(servers, edges)

            summary_rows = []
            online_servers = [s for s in servers if s.availability == "online"]
            bar = st.progress(0)

            for idx, src in enumerate(online_servers):
                result = engine.run(source_id=src.server_id)
                summary_rows.append({
                    "Source Server": src.name,
                    "Best Allocation": result.best_server_name,
                    "ACO Score": round(result.best_score, 4),
                    "Path Cost (ms)": round(result.best_path_cost, 2) if result.best_path_cost < math.inf else "∞",
                    "Converged @": result.convergence_iteration,
                    "Path Hops": len(result.best_path) - 1 if result.best_path else 0,
                })
                bar.progress((idx+1)/len(online_servers))
            bar.empty()

            df_aco = pd.DataFrame(summary_rows)
            st.dataframe(df_aco, use_container_width=True, hide_index=True)

            fig_aco = px.bar(df_aco, x="Source Server", y="ACO Score",
                             color="ACO Score", color_continuous_scale="RdYlGn",
                             title="ACO Best Score per Source Server")
            st.plotly_chart(fig_aco, use_container_width=True)

            # Allocation frequency
            alloc_freq = df_aco["Best Allocation"].value_counts().reset_index()
            alloc_freq.columns = ["Server", "Times Selected"]
            fig_af = px.bar(alloc_freq, x="Server", y="Times Selected",
                            color="Times Selected", color_continuous_scale="Blues",
                            title="How Often Each Server Was Selected as Best")
            st.plotly_chart(fig_af, use_container_width=True)

            st.session_state["aco_summary"] = df_aco

        elif "aco_summary" in st.session_state:
            st.info("Showing last computed ACO summary:")
            st.dataframe(st.session_state["aco_summary"], use_container_width=True, hide_index=True)

    # ── Tab 3: Traffic Analytics ──────────────────────────────────────────
    with tab3:
        if traffic:
            df_t = pd.DataFrame(traffic)

            col1, col2 = st.columns(2)
            with col1:
                fig_t1 = px.bar(
                    df_t.sort_values("avg_throughput", ascending=False).head(10),
                    x="src_name", y="avg_throughput",
                    title="Top 10 Links — Avg Throughput (Mbps)",
                    color="avg_throughput", color_continuous_scale="Greens"
                )
                st.plotly_chart(fig_t1, use_container_width=True)

            with col2:
                fig_t2 = px.scatter(
                    df_t, x="avg_latency", y="avg_throughput",
                    text="src_name", color="avg_sessions",
                    title="Latency vs Throughput",
                    labels={"avg_latency": "Latency (ms)",
                            "avg_throughput": "Throughput (Mbps)"}
                )
                st.plotly_chart(fig_t2, use_container_width=True)
        else:
            st.info("No traffic data found. Run Part 1 to generate traffic logs.")

    # ── Tab 4: Export ─────────────────────────────────────────────────────
    with tab4:
        st.subheader("📤 Export Report Data")

        # Build combined report
        report_sections = {}

        srv_df = pd.DataFrame([{
            "Server": s.name, "Region": s.region,
            "CPU %": s.cpu_usage_pct, "RAM %": s.ram_usage_pct,
            "Status": s.availability, "Queue": s.queue_length
        } for s in servers])
        report_sections["Servers"] = srv_df

        if metrics:
            report_sections["Metrics"] = pd.DataFrame(metrics)

        if traffic:
            report_sections["Traffic"] = pd.DataFrame(traffic)

        if "aco_summary" in st.session_state:
            report_sections["ACO_Summary"] = st.session_state["aco_summary"]

        if "allocations" in st.session_state and st.session_state.allocations:
            report_sections["Allocations"] = pd.DataFrame(st.session_state.allocations)

        for section, df_sec in report_sections.items():
            with st.expander(f"📄 {section}"):
                st.dataframe(df_sec, use_container_width=True, hide_index=True)
                csv = df_sec.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download {section}.csv",
                    data=csv,
                    file_name=f"aco_{section.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key=f"dl_{section}"
                )

        st.info(
            "💡 Run 'ACO Decision Summary' in Tab 2 and allocations in the "
            "Resource Allocation module to populate all report sections."
        )
