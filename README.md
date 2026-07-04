# Cloud Evo Unified

**ACO-Driven Intelligent Cloud Resource Allocation** — a Streamlit-based cloud
infrastructure simulator combining Ant Colony Optimization (ACO) with Genetic
Algorithm (GA) mutation, backed by a 7-table SQLite schema.



---

## Overview

Cloud Evo Unified simulates a full cloud environment — users, servers,
tasks, network links, routing, and traffic — then layers an ACO+GA
intelligence engine on top to make adaptive, real-time workload allocation
decisions. The engine's predictions are evaluated against a deterministic
ground truth using precision/recall/F1 and a confusion matrix.

## Features

**Cloud Infrastructure Simulator**
- User, Server, and Task management (CRUD)
- Network topology with Dijkstra & Floyd-Warshall routing
- Live traffic monitoring and resource metrics dashboards
- Availability monitor, distance/hop calculator, API output viewer

**ACO Intelligence Layer**
- Ant Colony Optimization engine (pheromone-based path selection)
- Genetic Algorithm mutation layer to prevent premature convergence
- Resource allocation & load balancing driven by a weighted composite score
- Server ranking and pheromone trail visualization

**Evaluation & Reporting**
- OS Evolutionary Comparison across 5 OS types (Linux, Windows Server,
  FreeBSD, Ubuntu, CentOS)
- Parameter comparison across 3 experimental trials
- Confusion matrix / model evaluation (precision, recall, F1, accuracy)
- Dataset collection pipeline (CSV export) and consolidated ACO report

## Tech Stack

| Layer          | Technology                          |
|----------------|--------------------------------------|
| Frontend/UI    | Streamlit (multi-page app)          |
| Visualization  | Plotly Express                      |
| Data handling  | Pandas, NumPy                       |
| Database       | SQLite (7-table relational schema)  |
| Algorithms     | ACO, GA mutation, Dijkstra, Floyd-Warshall |

## Setup & Installation

### Prerequisites
- Python 3.9+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/verrolinajacob/aco-cloud-resource-allocator.git
cd aco-cloud-resource-allocator/cloud_evo_unified

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
