"""
ACO Core Engine — Ant Colony Optimization + Genetic Mutation
for Cloud Resource Allocation & OS Workload Comparison.
"""

import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class ServerNode:
    server_id: int
    name: str
    region: str
    cpu_usage_pct: float
    ram_usage_pct: float
    availability: str
    queue_length: int = 0
    os_type: str = "Linux"   # NEW: OS type for OS comparison


@dataclass
class NetworkEdge:
    source_id: int
    dest_id: int
    latency_ms: float
    bandwidth_mbps: float
    hop_count: int = 1
    traffic_load: float = 0.0


@dataclass
class Ant:
    ant_id: int
    start_node: int
    current_node: int
    visited: List[int] = field(default_factory=list)
    path: List[int] = field(default_factory=list)
    path_cost: float = 0.0

    def reset(self, start_node: int):
        self.current_node = start_node
        self.start_node = start_node
        self.visited = [start_node]
        self.path = [start_node]
        self.path_cost = 0.0


@dataclass
class ACOResult:
    best_server_id: int
    best_server_name: str
    best_path: List[int]
    best_path_cost: float
    best_score: float
    iteration_costs: List[float]
    pheromone_history: List[Dict]
    convergence_iteration: int
    all_ant_paths: List[List[int]]
    server_scores: Dict[int, float]
    mutation_count: int = 0


# ─── OS Types supported ───────────────────────────────────────────────────────

OS_TYPES = ["Linux", "Windows Server", "FreeBSD", "Ubuntu", "CentOS"]

# OS performance profile modifiers (used in heuristic)
OS_PERF_PROFILE = {
    "Linux":          {"cpu_mod": 0.92, "ram_mod": 0.90, "latency_mod": 0.95},
    "Windows Server": {"cpu_mod": 1.15, "ram_mod": 1.20, "latency_mod": 1.10},
    "FreeBSD":        {"cpu_mod": 0.88, "ram_mod": 0.85, "latency_mod": 0.90},
    "Ubuntu":         {"cpu_mod": 0.93, "ram_mod": 0.91, "latency_mod": 0.96},
    "CentOS":         {"cpu_mod": 0.94, "ram_mod": 0.93, "latency_mod": 0.97},
}


# ─── ACO Parameters ───────────────────────────────────────────────────────────

class ACOParameters:
    def __init__(
        self,
        n_ants: int = 20,
        n_iterations: int = 50,
        alpha: float = 1.0,
        beta: float = 2.5,
        rho: float = 0.3,
        q: float = 100.0,
        tau_init: float = 1.0,
        tau_min: float = 0.01,
        tau_max: float = 10.0,
        w_latency: float = 0.30,
        w_cpu: float = 0.25,
        w_ram: float = 0.20,
        w_traffic: float = 0.15,
        w_hops: float = 0.10,
        mutation_rate: float = 0.05,
        enable_mutation: bool = True,
    ):
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.tau_init = tau_init
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.w_latency = w_latency
        self.w_cpu = w_cpu
        self.w_ram = w_ram
        self.w_traffic = w_traffic
        self.w_hops = w_hops
        self.mutation_rate = mutation_rate
        self.enable_mutation = enable_mutation


# ─── ACO Engine ───────────────────────────────────────────────────────────────

class ACOEngine:
    def __init__(self, params: ACOParameters):
        self.params = params
        self.servers: Dict[int, ServerNode] = {}
        self.edges: Dict[Tuple[int, int], NetworkEdge] = {}
        self.adjacency: Dict[int, List[int]] = {}
        self.pheromones: Dict[Tuple[int, int], float] = {}
        self.mutation_count = 0

    def load_graph(self, servers: List[ServerNode], edges: List[NetworkEdge]):
        self.servers = {s.server_id: s for s in servers}
        self.edges = {}
        self.adjacency = {s.server_id: [] for s in servers}
        for e in edges:
            self.edges[(e.source_id, e.dest_id)] = e
            self.edges[(e.dest_id, e.source_id)] = NetworkEdge(
                source_id=e.dest_id, dest_id=e.source_id,
                latency_ms=e.latency_ms, bandwidth_mbps=e.bandwidth_mbps,
                hop_count=e.hop_count, traffic_load=e.traffic_load,
            )
            self.adjacency.setdefault(e.source_id, []).append(e.dest_id)
            self.adjacency.setdefault(e.dest_id, []).append(e.source_id)
        p = self.params
        for key in self.edges:
            self.pheromones[key] = p.tau_init

    def _heuristic(self, edge: NetworkEdge, dest_server: ServerNode) -> float:
        p = self.params
        all_lat = [e.latency_ms for e in self.edges.values()] or [1.0]
        all_tr  = [e.traffic_load for e in self.edges.values()] or [1.0]
        max_lat = max(all_lat) or 1.0
        max_tr  = max(all_tr)  or 1.0

        # OS modifier
        os_prof = OS_PERF_PROFILE.get(dest_server.os_type, OS_PERF_PROFILE["Linux"])
        eff_lat = edge.latency_ms * os_prof["latency_mod"]
        eff_cpu = dest_server.cpu_usage_pct * os_prof["cpu_mod"]
        eff_ram = dest_server.ram_usage_pct * os_prof["ram_mod"]

        lat_norm  = eff_lat / (max_lat + 1e-9)
        cpu_norm  = eff_cpu / 100.0
        ram_norm  = eff_ram / 100.0
        tr_norm   = edge.traffic_load / (max_tr + 1e-9)
        hop_norm  = min(edge.hop_count / 5.0, 1.0)
        avail_pen = 0.0 if dest_server.availability == "online" else 0.5

        cost = (
            p.w_latency  * lat_norm +
            p.w_cpu      * cpu_norm +
            p.w_ram      * ram_norm +
            p.w_traffic  * tr_norm  +
            p.w_hops     * hop_norm +
            avail_pen
        )
        return 1.0 / (cost + 1e-9)

    def _choose_next(self, ant: Ant, candidates: List[int]) -> int:
        p = self.params
        unvisited = [c for c in candidates if c not in ant.visited]
        if not unvisited:
            unvisited = candidates

        # GA Mutation — randomly override pheromone-guided choice
        if p.enable_mutation and random.random() < p.mutation_rate:
            self.mutation_count += 1
            return random.choice(unvisited)

        probs = []
        for c in unvisited:
            key = (ant.current_node, c)
            tau = self.pheromones.get(key, p.tau_init)
            edge = self.edges.get(key)
            if edge and c in self.servers:
                eta = self._heuristic(edge, self.servers[c])
            else:
                eta = 1.0
            probs.append((c, (tau ** p.alpha) * (eta ** p.beta)))

        total = sum(v for _, v in probs)
        if total == 0:
            return random.choice(unvisited)
        r = random.random() * total
        cum = 0.0
        for c, v in probs:
            cum += v
            if r <= cum:
                return c
        return probs[-1][0]

    def _ant_traverse(self, ant: Ant, target: int):
        neighbors = self.adjacency.get(ant.current_node, [])
        if target in neighbors:
            edge = self.edges.get((ant.current_node, target))
            if edge and target in self.servers:
                ant.path_cost += edge.latency_ms
                ant.path.append(target)
                ant.visited.append(target)
                ant.current_node = target
        elif neighbors:
            next_n = self._choose_next(ant, neighbors)
            edge = self.edges.get((ant.current_node, next_n))
            if edge:
                ant.path_cost += edge.latency_ms
            ant.path.append(next_n)
            ant.visited.append(next_n)
            ant.current_node = next_n

    def _evaporate(self):
        p = self.params
        for key in self.pheromones:
            self.pheromones[key] = max(
                p.tau_min,
                self.pheromones[key] * (1 - p.rho)
            )

    def _deposit(self, ant_results: List[Tuple[List[int], float]]):
        p = self.params
        for path, cost in ant_results:
            if cost <= 0 or len(path) < 2:
                continue
            delta = p.q / cost
            for i in range(len(path) - 1):
                key_fwd = (path[i], path[i + 1])
                key_rev = (path[i + 1], path[i])
                self.pheromones[key_fwd] = min(
                    p.tau_max,
                    self.pheromones.get(key_fwd, p.tau_init) + delta
                )
                self.pheromones[key_rev] = min(
                    p.tau_max,
                    self.pheromones.get(key_rev, p.tau_init) + delta
                )

    def _score_server(self, server: ServerNode, source_id: int) -> float:
        p = self.params
        os_prof = OS_PERF_PROFILE.get(server.os_type, OS_PERF_PROFILE["Linux"])

        incoming_keys = [(src, server.server_id)
                         for src in self.adjacency.get(server.server_id, [])]
        ph_vals = [self.pheromones.get(k, p.tau_init) for k in incoming_keys]
        avg_ph = sum(ph_vals) / len(ph_vals) if ph_vals else p.tau_init
        direct_key = (source_id, server.server_id)
        direct_ph = self.pheromones.get(direct_key, avg_ph)
        pheromone_score = (direct_ph + avg_ph) / 2.0

        cpu_score  = (100 - server.cpu_usage_pct * os_prof["cpu_mod"]) / 100
        ram_score  = (100 - server.ram_usage_pct * os_prof["ram_mod"]) / 100
        avail_score = {"online": 1.0, "maintenance": 0.4, "offline": 0.0}.get(
            server.availability, 0.0
        )
        queue_penalty = min(server.queue_length / 20.0, 1.0)

        composite = (
            0.30 * pheromone_score / (self.params.tau_max + 1e-9) +
            0.25 * cpu_score +
            0.20 * ram_score +
            0.20 * avail_score -
            0.05 * queue_penalty
        )
        return max(0.0, composite)

    def run(self, source_id: int) -> ACOResult:
        p = self.params
        self.mutation_count = 0
        candidates = [sid for sid, srv in self.servers.items()
                      if srv.availability != "offline" and sid != source_id]
        if not candidates:
            candidates = list(self.servers.keys())

        best_cost = math.inf
        best_path: List[int] = []
        best_server_id: int = candidates[0] if candidates else source_id
        iteration_costs: List[float] = []
        pheromone_history: List[Dict] = []
        all_ant_paths: List[List[int]] = []
        convergence_iter = p.n_iterations

        ants = [Ant(ant_id=i, start_node=source_id, current_node=source_id)
                for i in range(p.n_ants)]

        for iteration in range(p.n_iterations):
            iteration_ant_paths: List[Tuple[List[int], float]] = []
            for ant in ants:
                ant.reset(source_id)
                target = random.choice(candidates)
                self._ant_traverse(ant, target)
                cost = ant.path_cost if ant.path_cost > 0 else (
                    self.edges.get((source_id, target), NetworkEdge(
                        source_id=source_id, dest_id=target,
                        latency_ms=50, bandwidth_mbps=1000
                    )).latency_ms
                )
                iteration_ant_paths.append((ant.path[:], cost))
                all_ant_paths.append(ant.path[:])
                if cost < best_cost and ant.path:
                    best_cost = cost
                    best_path = ant.path[:]
                    best_server_id = ant.path[-1]
                    if convergence_iter == p.n_iterations:
                        convergence_iter = iteration + 1

            self._evaporate()
            self._deposit(iteration_ant_paths)
            iteration_costs.append(best_cost)
            if iteration % 10 == 0:
                snap = {k: round(v, 4) for k, v in list(self.pheromones.items())[:20]}
                pheromone_history.append({"iteration": iteration, "pheromones": snap})

        server_scores = {
            sid: round(self._score_server(srv, source_id), 4)
            for sid, srv in self.servers.items()
            if srv.availability != "offline"
        }
        if server_scores:
            best_server_id = max(server_scores, key=server_scores.get)
            best_server_name = self.servers[best_server_id].name
            best_score = server_scores[best_server_id]
        else:
            best_server_name = "N/A"
            best_score = 0.0

        return ACOResult(
            best_server_id=best_server_id,
            best_server_name=best_server_name,
            best_path=best_path,
            best_path_cost=best_cost,
            best_score=best_score,
            iteration_costs=iteration_costs,
            pheromone_history=pheromone_history,
            convergence_iteration=convergence_iter,
            all_ant_paths=all_ant_paths,
            server_scores=server_scores,
            mutation_count=self.mutation_count,
        )

    def ground_truth_best(self, source_id: int) -> Tuple[int, Dict[int, float]]:
        p = self.params
        all_lat = [e.latency_ms for e in self.edges.values()] or [1.0]
        all_tr  = [e.traffic_load for e in self.edges.values()] or [1.0]
        max_lat = max(all_lat) or 1.0
        max_tr  = max(all_tr)  or 1.0

        costs: Dict[int, float] = {}
        for sid, srv in self.servers.items():
            if sid == source_id or srv.availability == "offline":
                continue
            os_prof = OS_PERF_PROFILE.get(srv.os_type, OS_PERF_PROFILE["Linux"])
            direct = self.edges.get((source_id, sid))
            incoming = [e for (s, d), e in self.edges.items() if d == sid]
            if direct is not None:
                lat, tr, hops = direct.latency_ms, direct.traffic_load, direct.hop_count
            elif incoming:
                lat = sum(e.latency_ms for e in incoming) / len(incoming)
                tr  = sum(e.traffic_load for e in incoming) / len(incoming)
                hops= sum(e.hop_count for e in incoming) / len(incoming)
            else:
                lat, tr, hops = max_lat, max_tr, 5

            lat_norm  = (lat * os_prof["latency_mod"]) / (max_lat + 1e-9)
            tr_norm   = tr / (max_tr + 1e-9)
            cpu_norm  = (srv.cpu_usage_pct * os_prof["cpu_mod"]) / 100.0
            ram_norm  = (srv.ram_usage_pct * os_prof["ram_mod"]) / 100.0
            hop_norm  = min(hops / 5.0, 1.0)
            avail_pen = 0.0 if srv.availability == "online" else 0.5

            cost = (
                p.w_latency  * lat_norm +
                p.w_cpu      * cpu_norm +
                p.w_ram      * ram_norm +
                p.w_traffic  * tr_norm  +
                p.w_hops     * hop_norm +
                avail_pen
            )
            costs[sid] = cost

        if not costs:
            return source_id, {}
        best_id = min(costs, key=costs.get)
        return best_id, costs


# ─── OS Evolutionary Comparison Engine ────────────────────────────────────────

def run_os_evolutionary_comparison(
    servers: List[ServerNode],
    edges: List[NetworkEdge],
    n_trials: int = 3,
    n_samples_per_trial: int = 20,
    params: ACOParameters = None,
) -> Dict:
    """
    Evolutionary algorithm that runs ACO allocation across OS types and measures:
    - Over-used OS types (high CPU/RAM but still selected)
    - Under-used OS types (low CPU/RAM, rarely selected)
    - Per-OS accuracy vs ground truth
    - Selection frequency per OS
    Returns a structured result dict for visualization.
    """
    if params is None:
        params = ACOParameters()

    os_stats = {os: {
        "selected": 0, "total": 0, "matches": 0,
        "cpu_sum": 0.0, "ram_sum": 0.0, "count": 0,
        "trial_accuracies": []
    } for os in OS_TYPES}

    rng = random.Random(42)

    for trial in range(n_trials):
        trial_matches = {os: 0 for os in OS_TYPES}
        trial_counts  = {os: 0 for os in OS_TYPES}

        engine = ACOEngine(params)
        engine.load_graph(servers, edges)
        all_ids = [s.server_id for s in servers if s.availability != "offline"]

        if len(all_ids) < 2:
            break

        for _ in range(n_samples_per_trial):
            source_id = rng.choice(all_ids)
            result = engine.run(source_id)
            true_id, _ = engine.ground_truth_best(source_id)

            pred_srv = engine.servers.get(result.best_server_id)
            true_srv = engine.servers.get(true_id)

            if pred_srv:
                os_stats[pred_srv.os_type]["selected"] += 1

            if true_srv:
                os_t = true_srv.os_type
                os_stats[os_t]["total"] += 1
                trial_counts[os_t] += 1
                if result.best_server_id == true_id:
                    os_stats[os_t]["matches"] += 1
                    trial_matches[os_t] += 1

        # Trial accuracy per OS
        for os in OS_TYPES:
            if trial_counts[os] > 0:
                acc = trial_matches[os] / trial_counts[os]
            else:
                acc = None
            os_stats[os]["trial_accuracies"].append(acc)

    # Aggregate CPU/RAM per OS from server list
    for srv in servers:
        if srv.os_type in os_stats:
            os_stats[srv.os_type]["cpu_sum"] += srv.cpu_usage_pct
            os_stats[srv.os_type]["ram_sum"] += srv.ram_usage_pct
            os_stats[srv.os_type]["count"]   += 1

    # Build summary rows
    rows = []
    total_selected = sum(v["selected"] for v in os_stats.values()) or 1
    for os, s in os_stats.items():
        cnt = s["count"] or 1
        avg_cpu = s["cpu_sum"] / cnt
        avg_ram = s["ram_sum"] / cnt
        accuracy = s["matches"] / s["total"] if s["total"] > 0 else None
        sel_pct  = s["selected"] / total_selected

        # Classify usage
        if avg_cpu > 70 or avg_ram > 70:
            usage_class = "Over-used"
        elif avg_cpu < 30 and avg_ram < 30:
            usage_class = "Under-used"
        else:
            usage_class = "Normal"

        rows.append({
            "os_type":      os,
            "avg_cpu":      round(avg_cpu, 1),
            "avg_ram":      round(avg_ram, 1),
            "selected":     s["selected"],
            "sel_pct":      round(sel_pct, 3),
            "total":        s["total"],
            "matches":      s["matches"],
            "accuracy":     round(accuracy, 3) if accuracy is not None else None,
            "usage_class":  usage_class,
            "trial_accs":   s["trial_accuracies"],
        })

    return {"rows": rows, "n_trials": n_trials, "n_samples_per_trial": n_samples_per_trial}
