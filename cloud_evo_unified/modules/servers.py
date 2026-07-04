"""Server Management Module."""

import streamlit as st
import pandas as pd
import plotly.express as px
from database.db import get_conn


def render():
    st.title("🖥️ Server Management")
    conn = get_conn()

    tab1, tab2 = st.tabs(["📋 Server List", "➕ Add Server"])

    with tab1:
        df = pd.read_sql("""
            SELECT server_id, name, region, ip_address, cpu_cores,
                   ram_gb, storage_tb, server_type, status, created_at
            FROM   Servers ORDER BY region, name
        """, conn)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df.groupby("region").size().reset_index(name="count"),
                         x="region", y="count", color="region", title="Servers per Region")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.scatter(df, x="cpu_cores", y="ram_gb",
                              color="server_type", size="storage_tb",
                              hover_name="name",
                              title="CPU vs RAM (bubble = Storage)")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Update Server Status")
        srv_map = dict(zip(df["name"], df["server_id"]))
        sel = st.selectbox("Select Server", list(srv_map.keys()))
        new_status = st.selectbox("New Status", ["online", "offline", "maintenance"])
        if st.button("✏️ Update Status"):
            conn.execute("UPDATE Servers SET status=? WHERE server_id=?",
                         (new_status, srv_map[sel]))
            conn.commit()
            st.success(f"{sel} → {new_status}")
            st.rerun()

    with tab2:
        st.subheader("Register New Server")
        with st.form("add_server"):
            c1, c2 = st.columns(2)
            name    = c1.text_input("Server Name")
            region  = c2.selectbox("Region",
                       ["us-east-1","us-west-2","eu-west-1","ap-south-1","ap-southeast-1"])
            ip      = c1.text_input("IP Address")
            stype   = c2.selectbox("Type", ["compute","storage","edge"])
            cpu     = c1.number_input("CPU Cores", 1, 256, 8)
            ram     = c2.number_input("RAM (GB)", 1.0, 2048.0, 16.0)
            storage = c1.number_input("Storage (TB)", 0.1, 100.0, 1.0)
            status  = c2.selectbox("Status", ["online","offline","maintenance"])

            if st.form_submit_button("➕ Register"):
                if name and ip:
                    try:
                        conn.execute("""
                            INSERT INTO Servers
                            (name,region,ip_address,cpu_cores,ram_gb,storage_tb,server_type,status)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (name, region, ip, cpu, ram, storage, stype, status))
                        conn.commit()
                        st.success(f"Server **{name}** registered.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    conn.close()
