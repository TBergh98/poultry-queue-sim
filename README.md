# Poultry Nest Simulator

Baseline OOP simulator for hens entering/leaving nests (unit-capacity servers) with stochastic arrivals and service times.

## Run
1. Create venv and install dependencies:
   ```bash
   python -m venv .venv && .venv/Scripts/activate
   pip install -r requirements.txt
   ```
2. Launch simulation and write RFID-like CSV:
   ```bash
   python -m src.main --config config/config.yaml --output data/simulated_log.csv
   ```

## Config
See `config/config.yaml` to tune duration, nests, time windows, arrival rates, and mixture service times.

## Output
CSV columns: `timestamp, hen_id, nest_id, event_type`. Timestamps are seconds from simulation start.
