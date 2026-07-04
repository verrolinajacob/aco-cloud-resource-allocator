"""
Parameter Comparison — run the hybrid ACO+GA engine under 3 different
parameter configurations and compare their top-1 accuracy side by side.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from aco_engine.dataset_collector import run_trial, load_trials, reset_trials


def _trial_inputs(col, label: str, defaults: dict):
    with col:
        st.markdown(f"**{label}**")
        mutation_rate = st.slider("Mutation rate", 0.0, 0.5, defaults["mutation_rate"],
                                   0.01, key=f"{label}_mut")
        alpha = st.slider("α (pheromone trust)", 0.1, 3.0, defaults["alpha"], 0.1, key=f"{label}_a")
        beta = st.slider("β (heuristic trust)", 0.1, 4.0, defaults["beta"], 0.1, key=f"{label}_b")
        rho = st.slider("ρ (evaporation rate)", 0.05, 0.9, defaults["rho"], 0.05, key=f"{label}_r")
        n_ants = st.slider("Ants", 5, 50, defaults["n_ants"], 1, key=f"{label}_ants")
        n_iter = st.slider("Iterations", 10, 100, defaults["n_iterations"], 5, key=f"{label}_iter")
    return dict(mutation_rate=mutation_rate, alpha=alpha, beta=beta, rho=rho,
                n_ants=n_ants, n_iterations=n_iter)


def render():
    st.title("🧪 Parameter Comparison — Hybrid ACO+GA")
    st.markdown(
        "Run the **same set of allocation requests** through 3 different parameter "
        "configurations of the hybrid ACO+GA engine, and compare their **top-1 accuracy** "
        "against the deterministic ground truth. All 3 trials use the same random seed and "
        "the same sequence of requests, so the comparison is fair — only the parameters change."
    )
    st.divider()

    n_samples = st.slider("Requests per trial", 5, 100, 20, 5,
                           help="How many allocation requests each of the 3 trials is tested on.")

    c1, c2, c3 = st.columns(3)
    cfg1 = _trial_inputs(c1, "Trial 1 — Low mutation",
                          dict(mutation_rate=0.0, alpha=1.0, beta=2.5, rho=0.3, n_ants=20, n_iterations=50))
    cfg2 = _trial_inputs(c2, "Trial 2 — Default",
                          dict(mutation_rate=0.05, alpha=1.0, beta=2.5, rho=0.3, n_ants=20, n_iterations=50))
    cfg3 = _trial_inputs(c3, "Trial 3 — High mutation",
                          dict(mutation_rate=0.25, alpha=1.0, beta=2.5, rho=0.3, n_ants=20, n_iterations=50))

    st.divider()
    run_col, reset_col = st.columns([3, 1])
    run_clicked = run_col.button("▶️ Run All 3 Trials", type="primary", use_container_width=True)
    reset_clicked = reset_col.button("🗑️ Clear History", use_container_width=True)

    if reset_clicked:
        reset_trials()
        st.success("Trial history cleared.")

    if run_clicked:
        with st.spinner("Running Trial 1..."):
            r1 = run_trial("Trial 1 — Low mutation", n_samples, **cfg1, seed=42)
        with st.spinner("Running Trial 2..."):
            r2 = run_trial("Trial 2 — Default", n_samples, **cfg2, seed=42)
        with st.spinner("Running Trial 3..."):
            r3 = run_trial("Trial 3 — High mutation", n_samples, **cfg3, seed=42)

        rows = [r for r in (r1, r2, r3) if r]
        if not rows:
            st.error("No servers found — visit a Part 1 page first to initialize the database.")
        else:
            st.success("All 3 trials complete.")
            df = pd.DataFrame(rows)

            fig = px.bar(
                df, x="trial_label", y="accuracy", color="trial_label",
                text=df["accuracy"].apply(lambda v: f"{v:.0%}"),
                labels={"trial_label": "Trial", "accuracy": "Top-1 Accuracy"},
                title="Accuracy by Parameter Configuration",
            )
            fig.update_layout(yaxis_range=[0, 1], showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[["trial_label", "mutation_rate", "alpha", "beta", "rho",
                    "n_ants", "n_iterations", "accuracy", "avg_mutation_count"]],
                use_container_width=True, hide_index=True,
            )

    st.divider()
    st.subheader("📜 Past Trial Runs")
    history = load_trials()
    if not history:
        st.info("No trials run yet. Click **Run All 3 Trials** above.")
    else:
        hist_df = pd.DataFrame(history)
        hist_df["accuracy"] = hist_df["accuracy"].astype(float)
        st.dataframe(hist_df, use_container_width=True, hide_index=True)

        fig2 = px.line(
            hist_df, x="timestamp", y="accuracy", color="trial_label", markers=True,
            title="Accuracy Across All Past Runs",
        )
        fig2.update_layout(yaxis_range=[0, 1])
        st.plotly_chart(fig2, use_container_width=True)

        csv_bytes = hist_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Trial History CSV", csv_bytes,
                            file_name="trial_comparisons.csv", mime="text/csv")
