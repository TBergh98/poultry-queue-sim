import csv
import json
import heapq
import random
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
from datetime import datetime, timedelta

from src.core.nest import Nest
from src.stochastic.distributions import ServiceTimeSampler
from src.stochastic.generators import ArrivalGenerator
from src.utils.logger import setup_logger


class Simulator:
    def __init__(self, sim_config: Dict, time_windows: Dict | None = None, seed: int | None = None):
        self.config = sim_config
        self.name = sim_config.get("name", "unknown")
        self.logger = setup_logger()
        if seed is not None:
            random.seed(seed)
        self.n_nests = sim_config["n_nests"]
        self.weights = sim_config.get("nest_selection_weights") or [
            1 / self.n_nests
        ] * self.n_nests
        self.sampler = ServiceTimeSampler(sim_config["distributions"])
        if time_windows is None:
            time_windows = {
                "notte": {"start": 20, "end": 4},
                "giorno": {"start": 5, "end": 15},
                "sera": {"start": 16, "end": 19},
            }
        self.arrival_generator = ArrivalGenerator(time_windows, self.sampler)
        self.nests = [Nest(i) for i in range(self.n_nests)]
        self.logs: List[Dict] = []

    def _choose_nest(self) -> Nest:
        idx = random.choices(range(self.n_nests), weights=self.weights, k=1)[0]
        return self.nests[idx]

    def _get_area_number(self) -> str:
        """Extract area number from simulation name.
        
        Examples:
        - "pre_1" -> "1"
        - "post_2" -> "2"
        - "pre_2" -> "2"
        """
        # Extract the last digit(s) from the simulation name
        for i in range(len(self.name) - 1, -1, -1):
            if self.name[i].isdigit():
                return self.name[i]
        return "1"  # Default to 1 if no digit found

    def _map_nest_id(self, nest_index: int) -> str:
        """Map nest index (0-3) to formatted nest ID.
        
        Examples:
        - nest_index=0, area="1" -> "1.1"
        - nest_index=1, area="1" -> "1.2"
        - nest_index=0, area="2" -> "2.1"
        - nest_index=3, area="2" -> "2.4"
        """
        area = self._get_area_number()
        return f"{area}.{nest_index + 1}"

    def _timestamp_to_datetime(self, timestamp_seconds: float) -> Tuple[str, str]:
        """Convert simulation timestamp (seconds) to date and time strings.
        
        Simulation starts at 01/01/2000 00:00:00.
        
        Returns: (date_str, time_str) where date_str is "DD/MM/YYYY" and time_str is "HH:MM:SS"
        """
        start_date = datetime(2000, 1, 1)
        event_date = start_date + timedelta(seconds=timestamp_seconds)
        date_str = event_date.strftime("%d/%m/%Y")
        time_str = event_date.strftime("%H:%M:%S")
        return date_str, time_str

    def _write_csv(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["Data", "Ora", "Azione", "ID Gallina", "ID Nido"]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in self.logs:
                date_str, time_str = self._timestamp_to_datetime(log["timestamp"])
                action = "IN" if log["event_type"] == "entry" else "OUT"
                formatted_nest_id = self._map_nest_id(log["nest_id"])
                
                writer.writerow({
                    "Data": date_str,
                    "Ora": time_str,
                    "Azione": action,
                    "ID Gallina": log["hen_id"],
                    "ID Nido": formatted_nest_id,
                })

    def _write_metrics(self, output_dir: Path) -> Dict[int, Dict]:
        """Write nest occupancy metrics to JSON file and return them."""
        output_dir.mkdir(parents=True, exist_ok=True)
        metrics = {}
        for nest in self.nests:
            nest_metrics = nest.get_metrics()
            metrics[nest.nest_id] = nest_metrics
        
        metrics_path = output_dir / "occupancy_metrics.json"
        with metrics_path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
    
    def _aggregate_co_occurrences(self) -> Dict[str, int]:
        """Aggregate co-occurrence counts across all nests.
        
        Returns a dict mapping "hen_A,hen_B" -> total count across all nests.
        """
        total_co_occurrences = Counter()
        
        for nest in self.nests:
            nest_co_occ = nest.get_co_occurrences()
            for pair, count in nest_co_occ.items():
                # Convert tuple to string key for JSON serialization
                pair_key = f"{pair[0]},{pair[1]}"
                total_co_occurrences[pair_key] += count
        
        return dict(total_co_occurrences)
    
    def _write_co_occurrences(self, output_dir: Path) -> Dict[str, int]:
        """Write co-occurrence data to JSON file."""
        co_occurrences = self._aggregate_co_occurrences()
        
        co_occ_path = output_dir / "co_occurrences.json"
        with co_occ_path.open("w", encoding="utf-8") as f:
            json.dump(co_occurrences, f, indent=2)
        
        self.logger.info("Co-occurrence data written to %s (%d pairs)", co_occ_path, len(co_occurrences))
        return co_occurrences

    def run(self, output_path: str | Path) -> Dict[int, Dict]:
        duration_days = self.config["duration_days"]
        arrivals = self.arrival_generator.generate_arrivals(duration_days)
        events: List[Tuple[float, str, int, int | None, str]] = []
        final_time = 0.0
        
        for t, hen_id, window in arrivals:
            heapq.heappush(events, (t, "arrival", hen_id, None, window))
            final_time = max(final_time, t)

        while events:
            current_time, event_type, hen_id, nest_id, window = heapq.heappop(events)
            final_time = max(final_time, current_time)
            
            if event_type == "arrival":
                nest = self._choose_nest()
                logs, exit_event = nest.handle_arrival(current_time, hen_id, self.sampler, window)
                self.logs.extend(logs)
                if exit_event:
                    exit_time, exit_hen = exit_event
                    heapq.heappush(events, (exit_time, "exit", exit_hen, nest.nest_id, window))
            elif event_type == "exit" and nest_id is not None:
                window_now = self.arrival_generator.window_for_time(current_time)
                nest = self.nests[nest_id]
                logs, next_exit = nest.handle_exit(current_time, hen_id, self.sampler, window_now)
                self.logs.extend(logs)
                if next_exit:
                    exit_time, exit_hen = next_exit
                    heapq.heappush(events, (exit_time, "exit", exit_hen, nest.nest_id, window_now))

        # Finalize metrics for all nests at final simulation time
        for nest in self.nests:
            nest.finalize_metrics(final_time)
        
        # Write logs, metrics, and co-occurrences
        output_path = Path(output_path)
        self._write_csv(output_path)
        metrics = self._write_metrics(output_path.parent)
        co_occurrences = self._write_co_occurrences(output_path.parent)
        
        self.logger.info("Simulation complete. Wrote %d events.", len(self.logs))
        self.logger.info("Occupancy metrics written to %s", output_path.parent / "occupancy_metrics.json")
        
        return metrics
