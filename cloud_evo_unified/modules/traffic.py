"""Traffic Monitoring Module."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_conn
from utils.helpers import fmt_bytes
import random
from datetime import datetime


def render():
    st.title("📈 Traffic Monitoring")
    conn = get_conn()

    tab1, tab2 = st.tabs(["📊 Live Traffic View", "📝 Log Traffic"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        total_bytes = pd.read_sql(
            "SELECT SUM(bytes_sent)+SUM(bytes_received) AS tb FROM TrafficLogs", conn
        ).iloc[0, 0] or 0
        avg_tput = pd.read_sql(
            "SELECT AVG(throughput_mbps) AS t FROM TrafficLogs", conn
        ).iloc[0, 0] or 0
        avg_lat  = pd.read_sql(
            "SELECT AVG(latency_ms) AS l FROM TrafficLogs", conn
        ).iloc[0, 0] or 0

        col1.metric("📦 Total Data Transferred", fmt_bytes(total_bytes))
        col2.metric("⚡ Avg Throughput",          f"{avg_tput:.1f} Mbps")
        col3.metric("🕐 Avg Latency",             f"{avg_lat:.1f} ms")

        st.subheader("Throughput Over Time (per hour)")
        df_time = pd.read_sql("""
            SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hour,
                   ROUND(AVG(throughput_mbps),2) AS throughput,
                   ROUND(AVG(latency_ms),2)      AS latency,
                   SUM(active_sessions)           AS sessions
            FROM   TrafficLogs
            GROUP  BY hour ORDER BY hour
        """, conn)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_time["hour"], y=df_time["sessions"],
                             name="Active Sessions", marker_color="#6EA6D8", opacity=0.5))
        fig.add_trace(go.Scatter(x=df_time["hour"], y=df_time["throughput"],
                                 name="Throughput (Mbps)", mode="lines+markers",
                                 line=dict(color="#00cc96"), yaxis="y2"))
        fig.update_layout(
            yaxis=dict(title="Sessions"),
            yaxis2=dict(title="Mbps", overlaying="y", side="right"),
            legend=dict(orientation="h"),
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Top 10 Busiest Links")
        df_top = pd.read_sql("""
            SELECT s1.name||' → '||s2.name AS link,
                   ROUND(AVG(tl.throughput_mbps),1) AS avg_throughput,
                   ROUND(AVG(tl.latency_ms),1)      AS avg_latency,
                   SUM(tl.bytes_sent)                AS bytes_sent
            FROM   TrafficLogs tl
            JOIN   NetworkLinks nl ON tl.link_id = nl.link_id
            JOIN   Servers s1 ON nl.source_server = s1.server_id
            JOIN   Servers s2 ON nl.dest_server   = s2.server_id
            GROUP  BY tl.link_id
            ORDER  BY avg_throughput DESC
            LIMIT  10
        """, conn)
        st.dataframe(df_top, use_container_width=True)

    with tab2:
        st.subheader("Simulate Traffic Log Entry")
        links_df = pd.read_sql("""
            SELECT nl.link_id, s1.name||' → '||s2.name AS label
            FROM   NetworkLinks nl
            JOIN   Servers s1 ON nl.source_server = s1.server_id
            JOIN   Servers s2 ON nl.dest_server   = s2.server_id
        """, conn)
        lmap = dict(zip(links_df["label"], links_df["link_id"]))

        with st.form("log_traffic"):
            sel_link  = st.selectbox("Network Link", list(lmap.keys()))
            sent      = st.number_input("Bytes Sent",     0, 10**9, 1_000_000)
            received  = st.number_input("Bytes Received", 0, 10**9, 1_000_000)
            sessions  = st.number_input("Active Sessions", 0, 10000, 10)
            tput      = st.number_input("Throughput (Mbps)", 0.0, 100000.0, 100.0)
            lat       = st.number_input("Latency (ms)", 0.0, 10000.0, 10.0)

            if st.form_submit_button("📝 Log Entry"):
                conn.execute("""
                    INSERT INTO TrafficLogs
                    (link_id, bytes_sent, bytes_received, active_sessions,
                     throughput_mbps, latency_ms, timestamp)
                    VALUES (?,?,?,?,?,?,?)
                """, (lmap[sel_link], sent, received, sessions, tput, lat,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("Traffic entry logged.")
                st.rerun()

    conn.close()
