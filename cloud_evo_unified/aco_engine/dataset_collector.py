"""
Dataset Collector — snapshots live cloud_sim.db state into a separate
training/evaluation dataset, and runs repeatable parameter trials for
the hybrid ACO+GA engine.

Two artefacts are produced (both under the `dataset/` folder):
  - collected_dataset.csv   : one row per allocation sample
                              (predicted best server vs ground-truth best)
  - trial_comparisons.csv   : one row per parameter-comparison trial run
"""

import os
import csv
import random
from datetime import datetime
from typing import List, Dict

from aco_engine.aco_core import ACOEngine, ACOParameters
from aco_engine.data_loader import load_server_nodes, load_network_edges, get_server_names

_HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(_HERE, "..", "dataset")
DATASET_PATH = os.path.join(DATASET_DIR, "collected_dataset.csv")
TRIALS_PATH = os.path.join(DATASET_DIR, "trial_comparisons.csv")

DATASET_FIELDS = [
    "timestamp", "source_id", "source_name",
    "predicted_best_id", "predicted_best_name",
    "true_best_id", "true_best_name",
    "match", "mutation_count", "mutation_rate",
    "n_ants", "n_iterations", "alpha", "beta", "rho",
]

TRIAL_FIELDS = [
    "timestamp", "trial_label", "n_samples",
    "mutation_rate", "alpha", "beta", "rho", "n_ants", "n_iterations",
    "accuracy", "avg_mutation_count",
]


def _ensure_dir():
    os.makedirs(DATASET_DIR, exist_ok=True)


def _append_csv(path: str, fields: List[str], row: Dict):
    _ensure_dir()
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _read_csv(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_dataset() -> List[Dict]:
    return _read_csv(DATASET_PATH)


def load_trials() -> List[Dict]:
    return _read_csv(TRIALS_PATH)


def reset_dataset():
    if os.path.exists(DATASET_PATH):
        os.remove(DATASET_PATH)


def reset_trials():
    if os.path.exists(TRIALS_PATH):
        os.remove(TRIALS_PATH)


def _build_engine(params: ACOParameters) -> ACOEngine:
    """Load the CURRENT live database state into a fresh ACO engine."""
    servers = load_server_nodes()
    edges = load_network_edges()
    engine = ACOEngine(params)
    engine.load_graph(servers, edges)
    return engine


def collect_samples(n_samples: int, mutation_rate: float = 0.05,
                     n_ants: int = 20, n_iterations: int = 50,
                     alpha: float = 1.0, beta: float = 2.5, rho: float = 0.3
                     ) -> List[Dict]:
    """
    Snapshot the live database `n_samples` times: each sample picks a random
    source server, runs the hybrid ACO+GA engine to predict the best target
    server, and compares it against the deterministic ground-truth best
    server. Every row is appended to dataset/collected_dataset.csv.

    Returns the list of newly added rows.
    """
    names = get_server_names()
    if len(names) < 2:
        return []

    params = ACOParameters(
        n_ants=n_ants, n_iterations=n_iterations,
        alpha=alpha, beta=beta, rho=rho,
        mutation_rate=mutation_rate, enable_mutation=True,
    )

    new_rows = []
    for _ in range(n_samples):
        engine = _build_engine(params)
        if not engine.servers:
            break
        source_id = random.choice(list(engine.servers.keys()))

        result = engine.run(source_id)
        true_id, _ = engine.ground_truth_best(source_id)

        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source_id": source_id,
            "source_name": names.get(source_id, str(source_id)),
            "predicted_best_id": result.best_server_id,
            "predicted_best_name": result.best_server_name,
            "true_best_id": true_id,
            "true_best_name": names.get(true_id, str(true_id)),
            "match": int(result.best_server_id == true_id),
            "mutation_count": result.mutation_count,
            "mutation_rate": mutation_rate,
            "n_ants": n_ants,
            "n_iterations": n_iterations,
            "alpha": alpha,
            "beta": beta,
            "rho": rho,
        }
        _append_csv(DATASET_PATH, DATASET_FIELDS, row)
        new_rows.append(row)

    return new_rows


def run_trial(trial_label: str, n_samples: int, mutation_rate: float,
              alpha: float, beta: float, rho: float,
              n_ants: int, n_iterations: int, seed: int = 42) -> Dict:
    """
    Run ONE parameter configuration across `n_samples` allocation requests
    and measure top-1 accuracy against the deterministic ground truth.

    Uses a fixed random seed + the same sequence of source servers across
    trials, so trials with different parameters are compared fairly (same
    requests, only the algorithm's parameters differ).
    Saves a summary row to dataset/trial_comparisons.csv and returns it.
    """
    names = get_server_names()
    server_ids = list(names.keys())
    if len(server_ids) < 2:
        return {}

    rng = random.Random(seed)
    sources = [rng.choice(server_ids) for _ in range(n_samples)]

    params = ACOParameters(
        n_ants=n_ants, n_iterations=n_iterations,
        alpha=alpha, beta=beta, rho=rho,
        mutation_rate=mutation_rate, enable_mutation=True,
    )

    random.seed(seed)  # also seed the module-level random used inside aco_core
    matches = 0
    mutation_counts = []
    for source_id in sources:
        engine = _build_engine(params)
        if source_id not in engine.servers:
            continue
        result = engine.run(source_id)
        true_id, _ = engine.ground_truth_best(source_id)
        matches += int(result.best_server_id == true_id)
        mutation_counts.append(result.mutation_count)

    accuracy = matches / len(sources) if sources else 0.0
    avg_mut = sum(mutation_counts) / len(mutation_counts) if mutation_counts else 0.0

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "trial_label": trial_label,
        "n_samples": n_samples,
        "mutation_rate": mutation_rate,
        "alpha": alpha,
        "beta": beta,
        "rho": rho,
        "n_ants": n_ants,
        "n_iterations": n_iterations,
        "accuracy": round(accuracy, 4),
        "avg_mutation_count": round(avg_mut, 2),
    }
    _append_csv(TRIALS_PATH, TRIAL_FIELDS, row)
    return row
