"""Workload / Task Management Module."""

import streamlit as st
import pandas as pd
import plotly.express as px
from database.db import get_conn


def render():
    st.title("📦 Workload & Task Management")
    conn = get_conn()

    tab1, tab2 = st.tabs(["📋 Task Queue", "➕ Submit Task"])

    with tab1:
        df = pd.read_sql("""
            SELECT t.task_id, t.name, u.username, s.name AS server,
                   t.cpu_required, t.ram_required, t.priority, t.status,
                   t.submitted_at, t.completed_at
            FROM   Tasks t
            LEFT JOIN Users   u ON t.user_id = u.user_id
            LEFT JOIN Servers s ON t.assigned_server = s.server_id
            ORDER  BY t.priority DESC, t.submitted_at DESC
        """, conn)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df.groupby("status").size().reset_index(name="count"),
                         x="status", y="count", color="status",
                         title="Task Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.scatter(df, x="cpu_required", y="ram_required",
                              color="status", size="priority",
                              hover_name="name",
                              title="CPU vs RAM requirements")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Update Task Status")
        task_map = dict(zip(df["name"], df["task_id"]))
        sel = st.selectbox("Select Task", list(task_map.keys()))
        new_stat = st.selectbox("New Status", ["queued","running","completed","failed"])
        if st.button("✏️ Update"):
            from datetime import datetime
            comp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_stat == "completed" else None
            conn.execute("UPDATE Tasks SET status=?, completed_at=? WHERE task_id=?",
                         (new_stat, comp, task_map[sel]))
            conn.commit()
            st.success("Updated.")
            st.rerun()

    with tab2:
        st.subheader("Submit New Task")
        users   = pd.read_sql("SELECT user_id, username FROM Users", conn)
        servers = pd.read_sql("SELECT server_id, name FROM Servers WHERE status='online'", conn)

        with st.form("submit_task"):
            c1, c2 = st.columns(2)
            tname = c1.text_input("Task Name")
            uid   = c2.selectbox("User", users["username"].tolist())
            sid   = c1.selectbox("Assign to Server", servers["name"].tolist())
            cpu_r = c2.number_input("CPU Required", 0.1, 64.0, 1.0)
            ram_r = c1.number_input("RAM Required (GB)", 0.5, 256.0, 2.0)
            prio  = c2.slider("Priority (1=low, 5=critical)", 1, 5, 2)

            if st.form_submit_button("🚀 Submit Task"):
                u_id = int(users[users["username"] == uid]["user_id"].iloc[0])
                s_id = int(servers[servers["name"] == sid]["server_id"].iloc[0])
                conn.execute("""
                    INSERT INTO Tasks
                    (name, user_id, assigned_server, cpu_required, ram_required, priority, status)
                    VALUES (?,?,?,?,?,?,'queued')
                """, (tname, u_id, s_id, cpu_r, ram_r, prio))
                conn.commit()
                st.success(f"Task **{tname}** submitted.")
                st.rerun()

    conn.close()
