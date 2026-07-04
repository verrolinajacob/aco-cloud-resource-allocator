"""User Management Module."""

import streamlit as st
import pandas as pd
from database.db import get_conn


def render():
    st.title("👤 User Management")

    conn = get_conn()
    tab1, tab2 = st.tabs(["📋 View Users", "➕ Add / Edit"])

    with tab1:
        df = pd.read_sql("SELECT * FROM Users ORDER BY created_at DESC", conn)
        st.dataframe(df, use_container_width=True)

        st.subheader("Role Distribution")
        import plotly.express as px
        fig = px.pie(df, names="role", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Add New User")
        with st.form("add_user"):
            uname  = st.text_input("Username")
            email  = st.text_input("Email")
            role   = st.selectbox("Role", ["viewer", "developer", "admin"])
            status = st.selectbox("Status", ["active", "inactive"])
            if st.form_submit_button("➕ Add User"):
                if uname and email:
                    try:
                        conn.execute(
                            "INSERT INTO Users (username, email, role, status) VALUES (?,?,?,?)",
                            (uname, email, role, status))
                        conn.commit()
                        st.success(f"User **{uname}** added.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.warning("Username and email are required.")

        st.subheader("Delete User")
        users = pd.read_sql("SELECT user_id, username FROM Users", conn)
        umap = dict(zip(users["username"], users["user_id"]))
        sel = st.selectbox("Select user to delete", list(umap.keys()))
        if st.button("🗑️ Delete User", type="primary"):
            conn.execute("DELETE FROM Users WHERE user_id=?", (umap[sel],))
            conn.commit()
            st.success(f"Deleted **{sel}**.")
            st.rerun()

    conn.close()
