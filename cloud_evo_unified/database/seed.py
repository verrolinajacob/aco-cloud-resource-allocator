"""
Seed the database with realistic initial data for demo/evaluation.
"""

import random
import json
from datetime import datetime, timedelta
from database.db import get_conn


REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1", "ap-southeast-1"]
SERVER_TYPES = ["compute", "storage", "edge"]
LINK_TYPES = ["fiber", "wireless", "satellite"]

USERS = [
    ("alice",    "alice@cloudlab.io",    "admin"),
    ("bob",      "bob@cloudlab.io",      "developer"),
    ("charlie",  "charlie@cloudlab.io",  "developer"),
    ("diana",    "diana@cloudlab.io",    "viewer"),
    ("evan",     "evan@cloudlab.io",     "viewer"),
]

SERVERS = [
    ("node-us-east-01", "us-east-1",     "10.0.1.1",  16, 64,  4.0, "compute"),
    ("node-us-east-02", "us-east-1",     "10.0.1.2",  8,  32,  2.0, "storage"),
    ("node-us-west-01", "us-west-2",     "10.0.2.1",  32, 128, 8.0, "compute"),
    ("node-eu-west-01", "eu-west-1",     "10.0.3.1",  16, 64,  4.0, "compute"),
    ("node-eu-west-02", "eu-west-1",     "10.0.3.2",  4,  16,  1.0, "edge"),
    ("node-ap-south-01","ap-south-1",    "10.0.4.1",  8,  32,  2.0, "compute"),
    ("node-ap-se-01",   "ap-southeast-1","10.0.5.1",  16, 64,  4.0, "edge"),
    ("node-ap-se-02",   "ap-southeast-1","10.0.5.2",  8,  32,  2.0, "storage"),
]


def seed_data():
    conn = get_conn()
    c = conn.cursor()

    # Check if already seeded
    if c.execute("SELECT COUNT(*) FROM Users").fetchone()[0] > 0:
        conn.close()
        return

    # --- Users ---
    for uname, email, role in USERS:
        c.execute("INSERT OR IGNORE INTO Users (username, email, role) VALUES (?,?,?)",
                  (uname, email, role))

    # --- Servers ---
    for name, region, ip, cpu, ram, storage, stype in SERVERS:
        status = random.choice(["online", "online", "online", "maintenance"])
        c.execute("""INSERT OR IGNORE INTO Servers
                     (name, region, ip_address, cpu_cores, ram_gb, storage_tb, server_type, status)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (name, region, ip, cpu, ram, storage, stype, status))

    conn.commit()

    # --- NetworkLinks (mesh between servers) ---
    server_ids = [r[0] for r in c.execute("SELECT server_id FROM Servers").fetchall()]
    pairs = []
    for i in range(len(server_ids)):
        for j in range(i + 1, len(server_ids)):
            if random.random() < 0.6:   # ~60% of possible links exist
                pairs.append((server_ids[i], server_ids[j]))

    for src, dst in pairs:
        bw   = round(random.uniform(100, 10000), 1)
        lat  = round(random.uniform(1, 150), 2)
        loss = round(random.uniform(0, 2), 3)
        ltype = random.choice(LINK_TYPES)
        status = random.choice(["active", "active", "active", "degraded", "down"])
        c.execute("""INSERT INTO NetworkLinks
                     (source_server, dest_server, bandwidth_mbps, latency_ms,
                      packet_loss_pct, link_type, status)
                     VALUES (?,?,?,?,?,?,?)""",
                  (src, dst, bw, lat, loss, ltype, status))

    conn.commit()

    # --- Routing Table (simple direct + multi-hop) ---
    for src in server_ids:
        for dst in server_ids:
            if src == dst:
                continue
            hops = random.randint(1, 3)
            path = [src]
            pool = [s for s in server_ids if s not in (src, dst)]
            for _ in range(hops - 1):
                if pool:
                    mid = random.choice(pool)
                    path.append(mid)
                    pool.remove(mid)
            path.append(dst)
            next_hop = path[1] if len(path) > 1 else dst
            total_lat = round(random.uniform(1, 200), 2)
            c.execute("""INSERT INTO RoutingTable
                         (source_server, dest_server, next_hop, hop_count,
                          total_latency, route_path, algorithm)
                         VALUES (?,?,?,?,?,?,?)""",
                      (src, dst, next_hop, hops, total_lat,
                       json.dumps(path), "dijkstra"))

    conn.commit()

    # --- Tasks ---
    user_ids = [r[0] for r in c.execute("SELECT user_id FROM Users").fetchall()]
    statuses = ["queued", "running", "completed", "completed", "failed"]
    for i in range(20):
        uid   = random.choice(user_ids)
        sid   = random.choice(server_ids)
        cpu_r = round(random.uniform(0.5, 8), 1)
        ram_r = round(random.uniform(1, 32), 1)
        prio  = random.randint(1, 5)
        stat  = random.choice(statuses)
        submitted = datetime.now() - timedelta(hours=random.randint(1, 72))
        completed = (submitted + timedelta(hours=random.randint(1, 5))
                     if stat == "completed" else None)
        c.execute("""INSERT INTO Tasks
                     (name, user_id, assigned_server, cpu_required, ram_required,
                      priority, status, submitted_at, completed_at)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (f"task-{i+1:03d}", uid, sid, cpu_r, ram_r, prio, stat,
                   submitted.strftime("%Y-%m-%d %H:%M:%S"),
                   completed.strftime("%Y-%m-%d %H:%M:%S") if completed else None))

    conn.commit()

    # --- TrafficLogs (last 24 h, one entry per hour per link) ---
    link_ids = [r[0] for r in c.execute("SELECT link_id FROM NetworkLinks").fetchall()]
    now = datetime.now()
    for link_id in link_ids:
        for h in range(24):
            ts = now - timedelta(hours=h)
            c.execute("""INSERT INTO TrafficLogs
                         (link_id, timestamp, bytes_sent, bytes_received,
                          active_sessions, throughput_mbps, latency_ms)
                         VALUES (?,?,?,?,?,?,?)""",
                      (link_id,
                       ts.strftime("%Y-%m-%d %H:%M:%S"),
                       random.randint(1_000_000, 500_000_000),
                       random.randint(1_000_000, 500_000_000),
                       random.randint(1, 200),
                       round(random.uniform(1, 900), 2),
                       round(random.uniform(1, 100), 2)))

    conn.commit()

    # --- Metrics (last 24 h per server) ---
    for sid in server_ids:
        uptime = 0
        for h in range(24):
            ts = now - timedelta(hours=h)
            uptime += 3600
            c.execute("""INSERT INTO Metrics
                         (server_id, timestamp, cpu_usage_pct, ram_usage_pct,
                          storage_usage_pct, network_in_mbps, network_out_mbps,
                          uptime_seconds)
                         VALUES (?,?,?,?,?,?,?,?)""",
                      (sid,
                       ts.strftime("%Y-%m-%d %H:%M:%S"),
                       round(random.uniform(5, 95), 1),
                       round(random.uniform(10, 90), 1),
                       round(random.uniform(5, 80), 1),
                       round(random.uniform(0, 500), 2),
                       round(random.uniform(0, 500), 2),
                       uptime))

    conn.commit()
    conn.close()
