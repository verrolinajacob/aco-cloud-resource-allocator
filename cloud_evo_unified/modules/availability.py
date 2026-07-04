"""Server Availability Monitoring Module."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_conn


def render():
    st.title("📡 Availability Monitoring")
    conn = get_conn()

    # Summary cards
    df_status = pd.read_sql("""
        SELECT status, COUNT(*) AS cnt FROM Servers GROUP BY status
    """, conn)
    status_dict = dict(zip(df_status["status"], df_status["cnt"]))

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Online",      status_dict.get("online", 0),      delta_color="normal")
    c2.metric("🔧 Maintenance", status_dict.get("maintenance", 0), delta_color="off")
    c3.metric("❌ Offline",     status_dict.get("offline", 0),     delta_color="inverse")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["🟢 Status Board", "📈 Uptime Trend", "⚠️ Link Health"])

    with tab1:
        df = pd.read_sql("""
            SELECT s.server_id, s.name, s.region, s.server_type, s.status,
                   ROUND(AVG(m.cpu_usage_pct),1)  AS cpu,
                   ROUND(AVG(m.ram_usage_pct),1)  AS ram,
                   MAX(m.uptime_seconds)           AS uptime_s
            FROM   Servers s
            LEFT JOIN Metrics m ON s.server_id = m.server_id
            GROUP  BY s.server_id
            ORDER  BY s.status, s.region
        """, conn)

        df["uptime_h"] = (df["uptime_s"].fillna(0) / 3600).round(1)
        df["availability"] = df["status"].map(
            {"online": "🟢 Online", "maintenance": "🟠 Maintenance", "offline": "🔴 Offline"})
        st.dataframe(df[["name","region","server_type","availability","cpu","ram","uptime_h"]],
                     use_container_width=True)

        fig = px.treemap(df, path=["region","name"], color="cpu",
                         color_continuous_scale="RdYlGn_r",
                         title="Server Map (color = CPU%)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Avg Uptime per Server (hours in last 24 h)")
        df_up = pd.read_sql("""
            SELECT s.name,
                   ROUND(MAX(m.uptime_seconds)/3600.0, 1) AS uptime_hours
            FROM   Metrics m
            JOIN   Servers s ON m.server_id = s.server_id
            GROUP  BY m.server_id
            ORDER  BY uptime_hours DESC
        """, conn)
        fig2 = px.bar(df_up, x="name", y="uptime_hours",
                      color="uptime_hours", color_continuous_scale="Blues",
                      labels={"name": "Server", "uptime_hours": "Hours"},
                      title="Uptime Hours (24 h window)")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Network Link Health Summary")
        df_links = pd.read_sql("""
            SELECT nl.status, COUNT(*) AS count,
                   ROUND(AVG(nl.packet_loss_pct),3) AS avg_loss,
                   ROUND(AVG(nl.latency_ms),1)      AS avg_latency
            FROM   NetworkLinks nl
            GROUP  BY nl.status
        """, conn)
        st.dataframe(df_links, use_container_width=True)

        fig3 = px.bar(df_links, x="status", y="count", color="status",
                      color_discrete_map={"active":"green","degraded":"orange","down":"red"},
                      title="Link Status Distribution")
        st.plotly_chart(fig3, use_container_width=True)

    conn.close()
