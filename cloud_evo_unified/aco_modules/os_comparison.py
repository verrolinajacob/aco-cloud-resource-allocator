"""
OS Evolutionary Comparison — compare Linux / Windows Server / FreeBSD / Ubuntu / CentOS
using the unified ACO+GA engine.

Runs 3 configurable trials with different parameter sets and visualises:
  - Per-OS accuracy (ACO predicted == ground truth)
  - Over-used vs Under-used classification
  - Selection frequency (which OS does the algorithm prefer?)
  - Per-trial accuracy breakdown
  - Side-by-side comparison across all 3 trials
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from aco_engine.aco_core import (
    ACOParameters, OS_TYPES, run_os_evolutionary_comparison
)
from aco_engine.data_loader import (
    load_server_nodes, load_network_edges, is_db_available
)


# ── Colour map for OS types ────────────────────────────────────────────────────

OS_COLORS = {
    "Linux":          "#2196F3",
    "Windows Server": "#FF9800",
    "FreeBSD":        "#9C27B0",
    "Ubuntu":         "#E91E63",
    "CentOS":         "#4CAF50",
}

USAGE_COLORS = {
    "Over-used":  "#F44336",
    "Normal":     "#4CAF50",
    "Under-used": "#2196F3",
}


def _trial_cfg(col, label: str, defaults: dict):
    with col:
        st.markdown(f"**{label}**")
        mr   = st.slider("Mutation rate",      0.0, 0.5, defaults["mr"],   0.01, key=f"{label}_mr")
        al   = st.slider("α (pheromone trust)", 0.1, 3.0, defaults["al"],   0.1,  key=f"{label}_al")
        be   = st.slider("β (heuristic trust)", 0.1, 4.0, defaults["be"],   0.1,  key=f"{label}_be")
        rho  = st.slider("ρ (evaporation)",     0.05, 0.9, defaults["rho"],  0.05, key=f"{label}_rho")
        ants = st.slider("Ants",                5,   50,  defaults["ants"],  1,    key=f"{label}_ants")
        itr  = st.slider("Iterations",          10,  100, defaults["itr"],   5,    key=f"{label}_itr")
    return dict(mutation_rate=mr, alpha=al, beta=be, rho=rho, n_ants=ants, n_iterations=itr)


def _run_single_trial(label: str, n_samples: int, cfg: dict):
    servers = load_server_nodes()
    edges   = load_network_edges()
    params  = ACOParameters(**cfg)
    result  = run_os_evolutionary_comparison(
        servers=servers,
        edges=edges,
        n_trials=3,
        n_samples_per_trial=n_samples,
        params=params,
    )
    return result, label


def render():
    st.title("🖥️ OS Evolutionary Comparison")
    st.markdown(
        "Use the **Hybrid ACO + Genetic Mutation** engine to compare how different "
        "Operating Systems perform under cloud workload allocation.  \n"
        "The evolutionary algorithm assigns OS types to servers and evaluates:  \n"
        "- **Over-used OS** — high avg CPU/RAM, selected often even when resource-constrained  \n"
        "- **Under-used OS** — low avg CPU/RAM, rarely chosen by the algorithm  \n"
        "- **Accuracy** — how often ACO picks the same OS-bearing server as ground truth  \n\n"
        "Run **3 parameter trials** to compare behaviour across different ACO configurations."
    )
    st.divider()

    ok, msg = is_db_available()
    if not ok:
        st.error(f"⚠️ Database not found: {msg}")
        return
    st.success(f"✅ {msg}")

    n_samples = st.slider("Samples per trial", 10, 80, 20, 5,
                           help="How many allocation requests per trial per OS comparison run.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    cfg1 = _trial_cfg(c1, "Trial 1 — Conservative",
                       dict(mr=0.00, al=1.0, be=2.5, rho=0.3,  ants=20, itr=50))
    cfg2 = _trial_cfg(c2, "Trial 2 — Balanced",
                       dict(mr=0.05, al=1.0, be=2.5, rho=0.3,  ants=20, itr=50))
    cfg3 = _trial_cfg(c3, "Trial 3 — Aggressive Mutation",
                       dict(mr=0.25, al=1.5, be=3.0, rho=0.5,  ants=30, itr=60))

    st.divider()
    run_btn = st.button("▶️ Run OS Evolutionary Comparison (All 3 Trials)", type="primary",
                         use_container_width=True)

    if not run_btn:
        st.info("Configure the 3 trial parameter sets above and click **Run**.")
        return

    results = []
    for i, (label, cfg) in enumerate([
        ("Trial 1 — Conservative", cfg1),
        ("Trial 2 — Balanced",     cfg2),
        ("Trial 3 — Aggressive",   cfg3),
    ], 1):
        with st.spinner(f"Running {label}..."):
            res, lbl = _run_single_trial(label, n_samples, cfg)
            results.append((lbl, res))

    st.success("✅ All 3 trials complete!")
    st.divider()

    # ── Combined DataFrame ──────────────────────────────────────────────────
    all_rows = []
    for lbl, res in results:
        for row in res["rows"]:
            all_rows.append({**row, "trial": lbl})
    df_all = pd.DataFrame(all_rows)

    # ── Section 1: Usage Classification per OS ─────────────────────────────
    st.subheader("📊 OS Usage Classification (Trial 2 — Balanced baseline)")
    baseline_rows = results[1][1]["rows"]  # Trial 2 as baseline
    df_base = pd.DataFrame(baseline_rows)

    col_a, col_b = st.columns(2)
    with col_a:
        # Usage pie
        usage_counts = df_base["usage_class"].value_counts().reset_index()
        usage_counts.columns = ["Usage Class", "Count"]
        fig_pie = px.pie(
            usage_counts, names="Usage Class", values="Count",
            color="Usage Class",
            color_discrete_map=USAGE_COLORS,
            title="OS Usage Distribution",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        # CPU & RAM bubble
        fig_bubble = px.scatter(
            df_base,
            x="avg_cpu", y="avg_ram",
            size=[max(r["selected"], 1) for r in baseline_rows],
            color="usage_class",
            color_discrete_map=USAGE_COLORS,
            text="os_type",
            labels={"avg_cpu": "Avg CPU %", "avg_ram": "Avg RAM %"},
            title="CPU vs RAM by OS (bubble = selection frequency)",
        )
        fig_bubble.update_traces(textposition="top center")
        fig_bubble.update_layout(showlegend=True)
        st.plotly_chart(fig_bubble, use_container_width=True)

    # Usage table
    disp_cols = ["os_type", "avg_cpu", "avg_ram", "usage_class", "selected", "sel_pct", "accuracy"]
    st.dataframe(
        df_base[disp_cols].rename(columns={
            "os_type": "OS Type", "avg_cpu": "Avg CPU %", "avg_ram": "Avg RAM %",
            "usage_class": "Usage Class", "selected": "Times Selected",
            "sel_pct": "Selection %", "accuracy": "Accuracy",
        }),
        use_container_width=True, hide_index=True
    )

    st.divider()

    # ── Section 2: Accuracy Comparison Across 3 Trials ─────────────────────
    st.subheader("🎯 OS Accuracy — All 3 Trials")
    df_acc = df_all[df_all["accuracy"].notna()].copy()
    df_acc["accuracy_pct"] = (df_acc["accuracy"] * 100).round(1)

    fig_bar = px.bar(
        df_acc,
        x="os_type", y="accuracy_pct",
        color="trial",
        barmode="group",
        text=df_acc["accuracy_pct"].apply(lambda v: f"{v:.0f}%"),
        labels={"os_type": "OS Type", "accuracy_pct": "Accuracy (%)", "trial": "Trial"},
        title="Prediction Accuracy per OS — Comparing 3 Parameter Trials",
        color_discrete_sequence=["#2196F3", "#4CAF50", "#FF9800"],
    )
    fig_bar.update_layout(yaxis_range=[0, 110], legend_title="Trial")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ── Section 3: Selection Frequency per OS per Trial ────────────────────
    st.subheader("📡 OS Selection Frequency Across Trials")
    fig_sel = px.bar(
        df_all,
        x="os_type", y="sel_pct",
        color="trial",
        barmode="group",
        text=df_all["sel_pct"].apply(lambda v: f"{v:.0%}"),
        labels={"os_type": "OS Type", "sel_pct": "Selection Share", "trial": "Trial"},
        title="Which OS Does the Algorithm Prefer?",
        color_discrete_sequence=["#9C27B0", "#E91E63", "#00BCD4"],
    )
    fig_sel.update_layout(yaxis_tickformat=".0%", legend_title="Trial")
    st.plotly_chart(fig_sel, use_container_width=True)

    st.divider()

    # ── Section 4: Per-trial internal accuracy across inner runs ───────────
    st.subheader("📈 Accuracy per Inner Run (across 3 inner iterations within each trial)")
    n_inner = results[0][1]["n_trials"]  # always 3
    for trial_lbl, res in results:
        inner_rows = []
        for row in res["rows"]:
            for j, acc in enumerate(row["trial_accs"]):
                if acc is not None:
                    inner_rows.append({
                        "Inner Run": f"Run {j+1}",
                        "OS Type":   row["os_type"],
                        "Accuracy":  round(acc * 100, 1),
                    })
        if not inner_rows:
            continue
        df_inner = pd.DataFrame(inner_rows)
        with st.expander(f"🔬 {trial_lbl} — inner run breakdown"):
            fig_inner = px.line(
                df_inner, x="Inner Run", y="Accuracy",
                color="OS Type",
                markers=True,
                color_discrete_map=OS_COLORS,
                title=f"{trial_lbl}: Accuracy per Inner Run",
                labels={"Accuracy": "Accuracy (%)"},
            )
            fig_inner.update_layout(yaxis_range=[0, 110])
            st.plotly_chart(fig_inner, use_container_width=True)

    st.divider()

    # ── Section 5: Heatmap — Accuracy × OS × Trial ─────────────────────────
    st.subheader("🗺️ Accuracy Heatmap — OS × Trial")
    heat_data = df_acc.pivot_table(
        index="os_type", columns="trial", values="accuracy_pct", aggfunc="mean"
    ).fillna(0)
    fig_heat = px.imshow(
        heat_data, text_auto=".1f",
        color_continuous_scale="RdYlGn",
        labels=dict(x="Trial", y="OS Type", color="Accuracy %"),
        title="Accuracy Heatmap (Green = high, Red = low)",
    )
    fig_heat.update_layout(height=350)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # ── Section 6: Summary table ───────────────────────────────────────────
    st.subheader("📋 Full Results Table")
    disp = df_all[[
        "trial", "os_type", "avg_cpu", "avg_ram", "usage_class",
        "selected", "sel_pct", "accuracy"
    ]].copy()
    disp["sel_pct"] = (disp["sel_pct"] * 100).round(1)
    disp["accuracy"] = disp["accuracy"].apply(lambda v: f"{v:.1%}" if v is not None else "—")
    disp.columns = [
        "Trial", "OS Type", "Avg CPU %", "Avg RAM %", "Usage Class",
        "Times Selected", "Selection %", "Accuracy"
    ]
    st.dataframe(disp, use_container_width=True, hide_index=True)

    csv = df_all.to_csv(index=False).encode()
    st.download_button("⬇️ Download OS Comparison CSV", csv,
                        file_name="os_comparison_results.csv", mime="text/csv")
