"""
Cloud Evo Unified — Single Streamlit App
ACO Intelligence + Cloud Environment + OS Evolutionary Comparison
All in one unified navigation. No section split.
"""

import streamlit as st

st.set_page_config(
    page_title="Cloud Evo Unified",
    page_icon="🌩️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB Init ────────────────────────────────────────────────────────────────────
from database.db import init_db
from database.seed import seed_data

if "db_initialized" not in st.session_state:
    init_db()
    seed_data()
    st.session_state.db_initialized = True

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.image(
    "https://img.icons8.com/fluency/96/cloud-computing.png", width=60
)
st.sidebar.title("Cloud Evo Unified")
st.sidebar.caption("ACO · GA Mutation · OS Comparison")
st.sidebar.divider()

PAGES = {
    # ── Overview ──────────────────────────────────────────────────────────
    "📊 Dashboard":                  "dashboard",
    # ── Cloud Infrastructure ──────────────────────────────────────────────
    "👤 User Management":            "users",
    "🖥️ Server Management":          "servers",
    "📦 Workload / Tasks":           "tasks",
    "🌐 Network Topology":           "network",
    "🗺️ Routing Table":              "routing",
    "📈 Traffic Monitoring":         "traffic",
    "💾 Resource Metrics":           "metrics",
    "📡 Availability Monitor":       "availability",
    "📏 Distance & Hops":            "distance",
    "🔌 API Output Viewer":          "api",
    # ── ACO + Evolutionary Intelligence ───────────────────────────────────
    "🐜 Resource Allocation (ACO)":  "allocation",
    "⚖️ Load Balancing (ACO)":       "loadbalancer",
    "🏆 Server Ranking":             "ranking",
    "🗺️ Path & Pheromones":          "paths",
    "📊 Performance Evaluation":     "perf",
    "🧬 Dataset Collection":         "dataset",
    "🧪 Parameter Comparison (3 Trials)": "paramcompare",
    "📊 Confusion Matrix":           "modeleval",
    "📋 ACO Report":                 "report",
    # ── OS Evolutionary Comparison ────────────────────────────────────────
    "🖥️ OS Evolutionary Comparison": "oscompare",
}

# Group labels in sidebar
st.sidebar.markdown("**☁️ Cloud Infrastructure**")
cloud_pages  = list(PAGES.keys())[:11]
st.sidebar.markdown("**🐜 ACO Intelligence**")
aco_pages    = list(PAGES.keys())[11:20]
st.sidebar.markdown("**🧬 Evolutionary OS**")
evo_pages    = list(PAGES.keys())[20:]

all_page_keys = list(PAGES.keys())
selection = st.sidebar.radio("Navigate", all_page_keys, label_visibility="collapsed")
page_key  = PAGES[selection]

# ── DB status ──────────────────────────────────────────────────────────────────
from aco_engine.data_loader import is_db_available
db_ok, db_msg = is_db_available()
if db_ok:
    st.sidebar.success("🟢 DB Connected")
else:
    st.sidebar.error("🔴 DB Missing")

st.sidebar.divider()
st.sidebar.caption("Jain University · ECE Batch 3 · 2026")

# ── Page Routing ───────────────────────────────────────────────────────────────
if page_key == "dashboard":
    from dashboard.overview import render; render()

elif page_key == "users":
    from modules.users import render; render()

elif page_key == "servers":
    from modules.servers import render; render()

elif page_key == "tasks":
    from modules.tasks import render; render()

elif page_key == "network":
    from modules.network import render; render()

elif page_key == "routing":
    from modules.routing import render; render()

elif page_key == "traffic":
    from modules.traffic import render; render()

elif page_key == "metrics":
    from modules.metrics import render; render()

elif page_key == "availability":
    from modules.availability import render; render()

elif page_key == "distance":
    from modules.distance import render; render()

elif page_key == "api":
    from modules.api_viewer import render; render()

elif page_key == "allocation":
    from aco_modules.allocation import render; render()

elif page_key == "loadbalancer":
    from aco_modules.load_balancer import render; render()

elif page_key == "ranking":
    from aco_modules.server_ranking import render; render()

elif page_key == "paths":
    from aco_modules.path_discovery import render; render()

elif page_key == "perf":
    from aco_modules.performance_eval import render; render()

elif page_key == "dataset":
    from aco_modules.dataset_collection import render; render()

elif page_key == "paramcompare":
    from aco_modules.parameter_comparison import render; render()

elif page_key == "modeleval":
    from aco_modules.model_evaluation import render; render()

elif page_key == "report":
    from aco_dashboard.report import render; render()

elif page_key == "oscompare":
    from aco_modules.os_comparison import render; render()
