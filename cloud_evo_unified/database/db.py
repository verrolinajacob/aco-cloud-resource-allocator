"""
Database Layer — SQLite with all 7 tables defined in the spec.
Tables: Users, Servers, Tasks, NetworkLinks, RoutingTable, TrafficLogs, Metrics
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cloud_sim.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT    NOT NULL UNIQUE,
        email       TEXT    NOT NULL UNIQUE,
        role        TEXT    NOT NULL DEFAULT 'viewer',   -- admin | developer | viewer
        status      TEXT    NOT NULL DEFAULT 'active',   -- active | inactive
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS Servers (
        server_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL UNIQUE,
        region          TEXT    NOT NULL,
        ip_address      TEXT    NOT NULL UNIQUE,
        cpu_cores       INTEGER NOT NULL DEFAULT 8,
        ram_gb          REAL    NOT NULL DEFAULT 16.0,
        storage_tb      REAL    NOT NULL DEFAULT 1.0,
        server_type     TEXT    NOT NULL DEFAULT 'compute',   -- compute | storage | edge
        status          TEXT    NOT NULL DEFAULT 'online',    -- online | offline | maintenance
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS Tasks (
        task_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        user_id         INTEGER REFERENCES Users(user_id),
        assigned_server INTEGER REFERENCES Servers(server_id),
        cpu_required    REAL    NOT NULL DEFAULT 1.0,
        ram_required    REAL    NOT NULL DEFAULT 2.0,
        priority        INTEGER NOT NULL DEFAULT 1,           -- 1 low … 5 critical
        status          TEXT    NOT NULL DEFAULT 'queued',   -- queued | running | completed | failed
        submitted_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        completed_at    DATETIME
    );

    CREATE TABLE IF NOT EXISTS NetworkLinks (
        link_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        source_server   INTEGER NOT NULL REFERENCES Servers(server_id),
        dest_server     INTEGER NOT NULL REFERENCES Servers(server_id),
        bandwidth_mbps  REAL    NOT NULL DEFAULT 1000.0,
        latency_ms      REAL    NOT NULL DEFAULT 5.0,
        packet_loss_pct REAL    NOT NULL DEFAULT 0.0,
        link_type       TEXT    NOT NULL DEFAULT 'fiber',    -- fiber | wireless | satellite
        status          TEXT    NOT NULL DEFAULT 'active',   -- active | degraded | down
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS RoutingTable (
        route_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        source_server   INTEGER NOT NULL REFERENCES Servers(server_id),
        dest_server     INTEGER NOT NULL REFERENCES Servers(server_id),
        next_hop        INTEGER REFERENCES Servers(server_id),
        hop_count       INTEGER NOT NULL DEFAULT 1,
        total_latency   REAL    NOT NULL DEFAULT 0.0,
        route_path      TEXT,                                -- JSON array of server_ids
        algorithm       TEXT    NOT NULL DEFAULT 'dijkstra',
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS TrafficLogs (
        log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id         INTEGER NOT NULL REFERENCES NetworkLinks(link_id),
        timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
        bytes_sent      INTEGER NOT NULL DEFAULT 0,
        bytes_received  INTEGER NOT NULL DEFAULT 0,
        active_sessions INTEGER NOT NULL DEFAULT 0,
        throughput_mbps REAL    NOT NULL DEFAULT 0.0,
        latency_ms      REAL    NOT NULL DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS Metrics (
        metric_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id       INTEGER NOT NULL REFERENCES Servers(server_id),
        timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
        cpu_usage_pct   REAL    NOT NULL DEFAULT 0.0,
        ram_usage_pct   REAL    NOT NULL DEFAULT 0.0,
        storage_usage_pct REAL  NOT NULL DEFAULT 0.0,
        network_in_mbps REAL    NOT NULL DEFAULT 0.0,
        network_out_mbps REAL   NOT NULL DEFAULT 0.0,
        uptime_seconds  INTEGER NOT NULL DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
