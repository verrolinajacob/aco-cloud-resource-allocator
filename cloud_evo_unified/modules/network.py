"""Network Topology Management Module."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database.db import get_conn


def render():
    st.title("🌐 Network Topology Management")
    conn = get_conn()

    tab1, tab2, tab3 = st.tabs(["🗺️ Topology Graph", "📋 Link Table", "➕ Add Link"])

    with tab1:
        st.subheader("Interactive Network Graph")
        servers = pd.read_sql("SELECT server_id, name, region FROM Servers", conn)
        links   = pd.read_sql("""
            SELECT nl.link_id, s1.name AS src, s2.name AS dst,
                   nl.bandwidth_mbps, nl.latency_ms, nl.status, nl.link_type
            FROM   NetworkLinks nl
            JOIN   Servers s1 ON nl.source_server = s1.server_id
            JOIN   Servers s2 ON nl.dest_server   = s2.server_id
        """, conn)

        # Assign positions by region
        region_pos = {
            "us-east-1":     (1, 3),
            "us-west-2":     (0, 2),
            "eu-west-1":     (2, 4),
            "ap-south-1":    (3, 1),
            "ap-southeast-1":(4, 2),
        }
        import random, math
        pos = {}
        region_count = {}
        for _, row in servers.iterrows():
            rx, ry = region_pos.get(row["region"], (2, 2))
            cnt = region_count.get(row["region"], 0)
            angle = cnt * 0.8
            px_ = rx + 0.4 * math.cos(angle)
            py_ = ry + 0.4 * math.sin(angle)
            pos[row["name"]] = (px_, py_)
            region_count[row["region"]] = cnt + 1

        color_map = {"active": "#00cc96", "degraded": "#ffa500", "down": "#ef553b"}

        edge_traces = []
        for _, lnk in links.iterrows():
            if lnk["src"] in pos and lnk["dst"] in pos:
                x0, y0 = pos[lnk["src"]]
                x1, y1 = pos[lnk["dst"]]
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None],
                    mode="lines",
                    line=dict(width=2, color=color_map.get(lnk["status"], "#aaa")),
                    hoverinfo="text",
                    text=f"{lnk['src']} → {lnk['dst']}<br>"
                         f"BW: {lnk['bandwidth_mbps']} Mbps | Lat: {lnk['latency_ms']} ms<br>"
                         f"Status: {lnk['status']}",
                    showlegend=False
                ))

        node_x = [pos[n][0] for n in pos]
        node_y = [pos[n][1] for n in pos]
        node_names = list(pos.keys())
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            text=node_names,
            textposition="top center",
            marker=dict(size=18, color="#4C9BE8",
                        line=dict(width=2, color="white")),
            hoverinfo="text"
        )

        fig = go.Figure(data=edge_traces + [node_trace])
        fig.update_layout(
            height=500,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Link status colors:** 🟢 Active  🟠 Degraded  🔴 Down")

    with tab2:
        df = pd.read_sql("""
            SELECT nl.link_id, s1.name AS source, s2.name AS dest,
                   nl.bandwidth_mbps, nl.latency_ms, nl.packet_loss_pct,
                   nl.link_type, nl.status
            FROM   NetworkLinks nl
            JOIN   Servers s1 ON nl.source_server = s1.server_id
            JOIN   Servers s2 ON nl.dest_server   = s2.server_id
            ORDER  BY nl.status, nl.latency_ms
        """, conn)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.histogram(df, x="latency_ms", nbins=20, title="Latency Distribution")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            fig3 = px.scatter(df, x="bandwidth_mbps", y="latency_ms",
                              color="status", symbol="link_type",
                              title="Bandwidth vs Latency")
            st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.subheader("Add Network Link")
        servers_df = pd.read_sql("SELECT server_id, name FROM Servers", conn)
        srv_names  = servers_df["name"].tolist()
        srv_map    = dict(zip(servers_df["name"], servers_df["server_id"]))

        with st.form("add_link"):
            c1, c2 = st.columns(2)
            src  = c1.selectbox("Source Server", srv_names, key="lsrc")
            dst  = c2.selectbox("Dest Server",   srv_names, key="ldst")
            bw   = c1.number_input("Bandwidth (Mbps)", 1.0, 100000.0, 1000.0)
            lat  = c2.number_input("Latency (ms)", 0.1, 1000.0, 10.0)
            loss = c1.number_input("Packet Loss (%)", 0.0, 100.0, 0.0)
            ltype = c2.selectbox("Link Type", ["fiber","wireless","satellite"])
            status = c1.selectbox("Status", ["active","degraded","down"])

            if st.form_submit_button("➕ Add Link"):
                if src != dst:
                    conn.execute("""
                        INSERT INTO NetworkLinks
                        (source_server,dest_server,bandwidth_mbps,latency_ms,
                         packet_loss_pct,link_type,status)
                        VALUES (?,?,?,?,?,?,?)
                    """, (srv_map[src], srv_map[dst], bw, lat, loss, ltype, status))
                    conn.commit()
                    st.success("Link added.")
                    st.rerun()
                else:
                    st.error("Source and destination must differ.")

    conn.close()
