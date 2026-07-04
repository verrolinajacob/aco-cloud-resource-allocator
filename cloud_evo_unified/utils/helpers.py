"""Shared utility helpers."""

import random
import math


def simulate_live_metric(low: float, high: float) -> float:
    """Return a random float in [low, high] to mimic a live sensor reading."""
    return round(random.uniform(low, high), 2)


def build_distance_matrix(server_ids, link_rows):
    """
    Build a distance (latency) matrix using Floyd-Warshall.
    link_rows: list of (source_server, dest_server, latency_ms)
    Returns dict of dicts: dist[src][dst] = latency
    """
    INF = math.inf
    dist = {s: {t: (0.0 if s == t else INF) for t in server_ids} for s in server_ids}

    for src, dst, lat in link_rows:
        dist[src][dst] = min(dist[src][dst], lat)
        dist[dst][src] = min(dist[dst][src], lat)   # undirected

    for k in server_ids:
        for i in server_ids:
            for j in server_ids:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]

    return dist


def build_hop_matrix(server_ids, link_rows):
    """
    Build a hop-count matrix (unweighted BFS / Floyd-Warshall with weight=1).
    """
    INF = math.inf
    hop = {s: {t: (0 if s == t else INF) for t in server_ids} for s in server_ids}

    for src, dst, _ in link_rows:
        hop[src][dst] = min(hop[src][dst], 1)
        hop[dst][src] = min(hop[dst][src], 1)

    for k in server_ids:
        for i in server_ids:
            for j in server_ids:
                if hop[i][k] + hop[k][j] < hop[i][j]:
                    hop[i][j] = hop[i][k] + hop[k][j]

    return hop


def fmt_bytes(n: int) -> str:
    """Human-readable byte count."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
