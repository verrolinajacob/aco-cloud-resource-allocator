"""
Dataset Collection — snapshot the LIVE cloud_sim.db into a separate dataset
file (dataset/collected_dataset.csv). Each row = one allocation request:
the server the hybrid ACO+GA predicted vs the deterministic ground-truth
best server. This dataset feeds the Model Evaluation (confusion matrix) page.
"""

import streamlit as st
import pandas as pd

from aco_engine.dataset_collector import collect_samples, load_dataset, reset_dataset


def render():
    st.title("🧬 Dataset Collection (Hybrid ACO+GA)")
    st.markdown(
        "This is a **separate dataset** from the live simulation database. Each time you "
        "click *Collect Samples*, it snapshots the current server/network state, runs the "
        "hybrid ACO+GA engine for a random allocation request, and records whether the "
        "predicted best server matched the deterministic ground-truth best server.\n\n"
        "This file (`dataset/collected_dataset.csv`) is what the **Model Evaluation** page "
        "uses to build the confusion matrix."
    )
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        n_samples = st.slider("Samples to collect now", 1, 100, 20, 1)
        mutation_rate = st.slider("Mutation rate", 0.0, 0.5, 0.05, 0.01)
    with c2:
        n_ants = st.slider("Ants", 5, 50, 20, 1)
        n_iterations = st.slider("Iterations", 10, 100, 50, 5)

    with st.expander("Advanced ACO parameters (α, β, ρ)"):
        a1, a2, a3 = st.columns(3)
        alpha = a1.slider("α (pheromone trust)", 0.1, 3.0, 1.0, 0.1)
        beta = a2.slider("β (heuristic trust)", 0.1, 4.0, 2.5, 0.1)
        rho = a3.slider("ρ (evaporation rate)", 0.05, 0.9, 0.3, 0.05)

    run_col, reset_col = st.columns([3, 1])
    if run_col.button("📥 Collect Samples", type="primary", use_container_width=True):
        with st.spinner(f"Collecting {n_samples} samples..."):
            new_rows = collect_samples(
                n_samples=n_samples, mutation_rate=mutation_rate,
                n_ants=n_ants, n_iterations=n_iterations,
                alpha=alpha, beta=beta, rho=rho,
            )
        if not new_rows:
            st.error("No servers found — visit a Part 1 page first to initialize the database.")
        else:
            matches = sum(r["match"] for r in new_rows)
            st.success(f"Collected {len(new_rows)} new samples — {matches}/{len(new_rows)} matched ground truth.")
            st.dataframe(pd.DataFrame(new_rows), use_container_width=True, hide_index=True)

    if reset_col.button("🗑️ Reset Dataset", use_container_width=True):
        reset_dataset()
        st.success("Dataset cleared.")

    st.divider()
    st.subheader("📊 Full Collected Dataset")
    data = load_dataset()
    if not data:
        st.info("No samples collected yet. Click **Collect Samples** above.")
        return

    df = pd.DataFrame(data)
    df["match"] = df["match"].astype(int)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Samples", len(df))
    m2.metric("Matches", int(df["match"].sum()))
    m3.metric("Running Accuracy", f"{df['match'].mean():.1%}")

    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Dataset CSV", csv_bytes,
                        file_name="collected_dataset.csv", mime="text/csv")
