"""CPU / RAM / Storage Resource Metrics Module."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_conn
from utils.helpers import simulate_live_metric
from datetime import datetime


def render():
    st.title("💾 CPU / RAM / Storage Monitoring")
    conn = get_conn()

    servers = pd.read_sql("SELECT server_id, name FROM Servers", conn)
    srv_map = dict(zip(servers["name"], servers["server_id"]))

    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🖥️ Per-Server", "📝 Log Metric"])

    with tab1:
        st.subheader("Latest Resource Utilization (All Servers)")
        df_latest = pd.read_sql("""
            SELECT s.name,
                   m.cpu_usage_pct, m.ram_usage_pct, m.storage_usage_pct,
                   m.network_in_mbps, m.network_out_mbps, m.timestamp
            FROM   Metrics m
            JOIN   Servers s ON m.server_id = s.server_id
            WHERE  m.timestamp = (
                SELECT MAX(m2.timestamp) FROM Metrics m2
                WHERE  m2.server_id = m.server_id
            )
            ORDER  BY m.cpu_usage_pct DESC
        """, conn)
        st.dataframe(df_latest, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_latest, x="name", y=["cpu_usage_pct","ram_usage_pct","storage_usage_pct"],
                         barmode="group",
                         labels={"value": "%", "variable": "Metric", "name": "Server"},
                         title="Current Resource Usage (%)")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.scatter(df_latest, x="network_in_mbps", y="network_out_mbps",
                              text="name", color="cpu_usage_pct",
                              color_continuous_scale="RdYlGn_r",
                              title="Network I/O vs Server Name")
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        sel_srv = st.selectbox("Select Server", list(srv_map.keys()))
        sid = srv_map[sel_srv]

        df_hist = pd.read_sql("""
            SELECT strftime('%H:00', timestamp) AS hour,
                   ROUND(AVG(cpu_usage_pct),1)     AS cpu,
                   ROUND(AVG(ram_usage_pct),1)     AS ram,
                   ROUND(AVG(storage_usage_pct),1) AS storage
            FROM   Metrics
            WHERE  server_id = ?
            GROUP  BY hour ORDER BY hour
        """, conn, params=(sid,))

        fig3 = go.Figure()
        for col, color in [("cpu","#ef553b"),("ram","#636efa"),("storage","#00cc96")]:
            fig3.add_trace(go.Scatter(x=df_hist["hour"], y=df_hist[col],
                                      name=col.upper()+" %", mode="lines+markers",
                                      line=dict(color=color)))
        fig3.update_layout(title=f"Resource Trend — {sel_srv}",
                           yaxis_title="%", xaxis_title="Hour")
        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.subheader("Log Resource Snapshot")
        with st.form("log_metric"):
            c1, c2 = st.columns(2)
            srv_sel = c1.selectbox("Server", list(srv_map.keys()), key="ms")
            cpu_u   = c2.slider("CPU Usage %",     0.0, 100.0, simulate_live_metric(10,90))
            ram_u   = c1.slider("RAM Usage %",     0.0, 100.0, simulate_live_metric(10,90))
            sto_u   = c2.slider("Storage Usage %", 0.0, 100.0, simulate_live_metric(5, 80))
            net_in  = c1.number_input("Network In  (Mbps)", 0.0, 10000.0, 100.0)
            net_out = c2.number_input("Network Out (Mbps)", 0.0, 10000.0, 80.0)

            if st.form_submit_button("📝 Save Snapshot"):
                conn.execute("""
                    INSERT INTO Metrics
                    (server_id, cpu_usage_pct, ram_usage_pct, storage_usage_pct,
                     network_in_mbps, network_out_mbps, timestamp)
                    VALUES (?,?,?,?,?,?,?)
                """, (srv_map[srv_sel], cpu_u, ram_u, sto_u, net_in, net_out,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("Snapshot saved.")
                st.rerun()

    conn.close()
