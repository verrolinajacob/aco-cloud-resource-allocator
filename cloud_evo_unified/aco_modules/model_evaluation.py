"""
Model Evaluation — confusion matrix for the hybrid ACO+GA "model".

Classifies: predicted best server (what the algorithm chose) vs the
deterministic ground-truth best server (top-1 match), built from the
dataset collected on the Dataset Collection page.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from aco_engine.dataset_collector import load_dataset


def _precision_recall_f1(df: pd.DataFrame, labels):
    """Compute per-class precision/recall/F1/support without sklearn."""
    rows = []
    for label in labels:
        tp = ((df["predicted_best_name"] == label) & (df["true_best_name"] == label)).sum()
        fp = ((df["predicted_best_name"] == label) & (df["true_best_name"] != label)).sum()
        fn = ((df["predicted_best_name"] != label) & (df["true_best_name"] == label)).sum()
        support = (df["true_best_name"] == label).sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        rows.append({
            "Server": label, "Precision": round(precision, 3),
            "Recall": round(recall, 3), "F1-score": round(f1, 3), "Support": int(support),
        })
    return pd.DataFrame(rows)


def render():
    st.title("📊 Model Evaluation — Confusion Matrix")
    st.markdown(
        "**Classification task:** for each allocation request, did the hybrid ACO+GA engine's "
        "predicted best server match the deterministic ground-truth best server? This is a "
        "**top-1 match** evaluation — each server is treated as one \"class\"."
    )

    data = load_dataset()
    if not data:
        st.warning("No dataset yet. Go to **Dataset Collection** and collect some samples first.")
        return

    df = pd.DataFrame(data)
    df["match"] = df["match"].astype(int)

    labels = sorted(set(df["true_best_name"]) | set(df["predicted_best_name"]))

    accuracy = df["match"].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Samples", len(df))
    m2.metric("Correct (Top-1 Match)", int(df["match"].sum()))
    m3.metric("Accuracy", f"{accuracy:.1%}")

    st.divider()
    st.subheader("Confusion Matrix")
    st.caption("Rows = ground-truth best server · Columns = predicted best server")

    cm = pd.crosstab(df["true_best_name"], df["predicted_best_name"])
    cm = cm.reindex(index=labels, columns=labels, fill_value=0)

    fig = px.imshow(
        cm, text_auto=True, color_continuous_scale="Blues",
        labels=dict(x="Predicted Best Server", y="True Best Server", color="Count"),
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw confusion matrix table"):
        st.dataframe(cm, use_container_width=True)

    st.divider()
    st.subheader("Per-Server Precision / Recall / F1")
    st.caption(
        "Precision: of the times the model predicted this server, how often was it actually "
        "right? Recall: of the times this server was truly best, how often did the model find it?"
    )
    pr_df = _precision_recall_f1(df, labels)
    st.dataframe(pr_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Mutation Activity")
    st.caption("How often the GA-style mutation step overrode the pheromone-guided choice.")
    mc1, mc2 = st.columns(2)
    mc1.metric("Avg Mutations / Run", f"{df['mutation_count'].astype(float).mean():.2f}")
    mc2.metric("Avg Mutation Rate Used", f"{df['mutation_rate'].astype(float).mean():.2%}")

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Full Dataset CSV", csv_bytes,
                        file_name="collected_dataset.csv", mime="text/csv")
