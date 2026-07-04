"""
Dashboard Overview — KPIs, charts, live summary across all layers.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_conn
from utils.helpers import simulate_live_metric


def render():
    st.title("📊 Cloud Environment Dashboard")
    st.caption("Real-time overview of all cloud infrastructure components")

    conn = get_conn()

    # ── KPI Row ──────────────────────────────────────────────────────────────
    total_servers  = pd.read_sql("SELECT COUNT(*) AS n FROM Servers", conn).iloc[0,0]
    online_servers = pd.read_sql("SELECT COUNT(*) AS n FROM Servers WHERE status='online'", conn).iloc[0,0]
    total_users    = pd.read_sql("SELECT COUNT(*) AS n FROM Users", conn).iloc[0,0]
    total_tasks    = pd.read_sql("SELECT COUNT(*) AS n FROM Tasks", conn).iloc[0,0]
    running_tasks  = pd.read_sql("SELECT COUNT(*) AS n FROM Tasks WHERE status='running'", conn).iloc[0,0]
    total_links    = pd.read_sql("SELECT COUNT(*) AS n FROM NetworkLinks", conn).iloc[0,0]
    active_links   = pd.read_sql("SELECT COUNT(*) AS n FROM NetworkLinks WHERE status='active'", conn).iloc[0,0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🖥️ Servers Online",   f"{online_servers}/{total_servers}")
    c2.metric("👤 Total Users",       str(total_users))
    c3.metric("📦 Tasks Running",     f"{running_tasks}/{total_tasks}")
    c4.metric("🌐 Active Links",      f"{active_links}/{total_links}")
    c5.metric("⚡ Live CPU (avg)",    f"{simulate_live_metric(40,80):.1f}%")

    st.divider()

    # ── Row 2: Server Status Pie + CPU chart ─────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Server Status Distribution")
        df_status = pd.read_sql(
            "SELECT status, COUNT(*) AS count FROM Servers GROUP BY status", conn)
        fig = px.pie(df_status, names="status", values="count",
                     color_discrete_sequence=px.colors.qualitative.Set2,
                     hole=0.4)
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Avg CPU Usage — Last 24 Hours")
        df_cpu = pd.read_sql("""
            SELECT strftime('%H:00', timestamp) AS hour,
                   ROUND(AVG(cpu_usage_pct), 1) AS avg_cpu
            FROM   Metrics
            GROUP  BY hour
            ORDER  BY hour
        """, conn)
        fig2 = px.line(df_cpu, x="hour", y="avg_cpu",
                       labels={"hour": "Hour", "avg_cpu": "CPU %"},
                       markers=True, color_discrete_sequence=["#4C9BE8"])
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 3: Task status bar + Region breakdown ─────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Task Status Breakdown")
        df_tasks = pd.read_sql(
            "SELECT status, COUNT(*) AS count FROM Tasks GROUP BY status", conn)
        fig3 = px.bar(df_tasks, x="status", y="count",
                      color="status",
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig3.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Servers by Region")
        df_region = pd.read_sql(
            "SELECT region, COUNT(*) AS count FROM Servers GROUP BY region", conn)
        fig4 = px.bar(df_region, x="region", y="count",
                      color="region",
                      color_discrete_sequence=px.colors.qualitative.Bold)
        fig4.update_layout(showlegend=False, margin=dict(t=10, b=10),
                           xaxis_tickangle=-30)
        st.plotly_chart(fig4, use_container_width=True)

    # ── Row 4: Traffic Throughput trend ──────────────────────────────────────
    st.subheader("📈 Network Throughput — Last 24 Hours (all links)")
    df_traffic = pd.read_sql("""
        SELECT strftime('%H:00', timestamp) AS hour,
               ROUND(AVG(throughput_mbps), 2) AS avg_throughput,
               ROUND(AVG(latency_ms), 2)      AS avg_latency
        FROM   TrafficLogs
        GROUP  BY hour
        ORDER  BY hour
    """, conn)

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=df_traffic["hour"], y=df_traffic["avg_throughput"],
                              name="Throughput (Mbps)", mode="lines+markers",
                              line=dict(color="#00cc96")))
    fig5.add_trace(go.Scatter(x=df_traffic["hour"], y=df_traffic["avg_latency"],
                              name="Latency (ms)", mode="lines+markers",
                              line=dict(color="#ef553b"), yaxis="y2"))
    fig5.update_layout(
        yaxis=dict(title="Throughput (Mbps)"),
        yaxis2=dict(title="Latency (ms)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        margin=dict(t=10, b=10)
    )
    st.plotly_chart(fig5, use_container_width=True)

    conn.close()
