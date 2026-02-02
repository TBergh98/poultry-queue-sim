# Poultry Nest Simulator

Discrete-event simulation for hens entering/leaving nests with stochastic arrivals and service times. Uses an **infinite-server queue model** where multiple hens can occupy the same nest simultaneously.

## Features

- **Infinite-server queues**: Multiple hens can occupy nests concurrently without waiting
- **Stochastic processes**: Gamma/uniform mixture for residence times, Poisson arrivals
- **Time-window dynamics**: Different behavior patterns for night/day/evening
- **Occupancy metrics**: Track nest utilization and single-hen vs. multi-hen occupancy
- **Co-occurrence analysis**: Identify which hens frequently visit nests together

## Run

1. Create venv and install dependencies:
   ```bash
   python -m venv .venv && .venv/Scripts/activate
   pip install -r requirements.txt
   ```

2. Launch simulation:
   ```bash
   python -m src.main --config config/config.yaml --output-dir data --seed 42
   ```

3. Analyze co-occurrence patterns:
   ```bash
   python analyze_co_occurrences.py --simulation pre_1
   python analyze_co_occurrences.py --simulation pre_1 --hen-id 241
   ```

## Configuration

See `config/config.yaml` to configure:
- **Duration**: Simulation length in days
- **Nests**: Number of nests and selection weights
- **Time windows**: Night/day/evening time ranges (24h format)
- **Distributions**: Gamma/uniform mixture parameters per time window
- **Arrival rates**: Poisson arrival rates per time window

## Output

Each simulation generates 3 files in `data/{simulation_name}/`:

1. **`simulated_log.csv`**: Event log with columns `timestamp, hen_id, nest_id, event_type`
   - Timestamps are seconds from simulation start
   - Events: `entry` (hen enters nest), `exit` (hen leaves nest)

2. **`occupancy_metrics.json`**: Nest occupancy statistics
   ```json
   {
     "0": {
       "nest_id": 0,
       "total_occupancy_time": 246348.81,
       "total_single_hen_time": 185333.69
     }
   }
   ```

3. **`co_occurrences.json`**: Hen pair co-occurrence counts
   ```json
   {
     "241,78": 5,
     "103,105": 3,
     ...
   }
   ```
   - Key format: `"hen_id_1,hen_id_2"` (sorted order)
   - Value: number of times the pair was simultaneously in any nest

## Analysis Tools

### Co-occurrence Analysis

```bash
# Full report for a simulation
python analyze_co_occurrences.py --simulation pre_1

# Find companions of a specific hen
python analyze_co_occurrences.py --simulation pre_1 --hen-id 241
```

### Custom Analysis

```python
import json

# Load co-occurrence data
co_occ = json.load(open("data/pre_1/co_occurrences.json"))

# Find most frequent pairs
pairs = sorted(co_occ.items(), key=lambda x: x[1], reverse=True)
for pair, count in pairs[:10]:
    hen_a, hen_b = pair.split(',')
    print(f"Hen {hen_a} & Hen {hen_b}: {count} co-occurrences")
```

## Architecture

- **Infinite-server model**: No waiting queue, all hens enter service immediately
- **Discrete-event simulation**: Event-driven with heap-based priority queue
- **Service time**: Sampled from gamma/uniform mixture per time window
- **Nest selection**: Weighted random choice based on configuration

See [REFACTORING_NOTES.md](REFACTORING_NOTES.md) for detailed implementation notes.
