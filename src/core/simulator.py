import csv
import heapq
import random
from pathlib import Path
from typing import Dict, List, Tuple

from src.core.nest import Nest
from src.stochastic.distributions import ServiceTimeSampler
from src.stochastic.generators import ArrivalGenerator
from src.utils.logger import setup_logger


class Simulator:
    def __init__(self, config: Dict, seed: int | None = None):
        self.config = config
        self.logger = setup_logger()
        if seed is not None:
            random.seed(seed)
        self.n_nests = config["simulation"]["n_nests"]
        self.weights = config["simulation"].get("nest_selection_weights") or [
            1 / self.n_nests
        ] * self.n_nests
        self.sampler = ServiceTimeSampler(config["distributions"])
        self.arrival_generator = ArrivalGenerator(config["time_windows"], self.sampler)
        self.nests = [Nest(i) for i in range(self.n_nests)]
        self.logs: List[Dict] = []

    def _choose_nest(self) -> Nest:
        idx = random.choices(range(self.n_nests), weights=self.weights, k=1)[0]
        return self.nests[idx]

    def _write_csv(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["timestamp", "hen_id", "nest_id", "event_type"]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.logs)

    def run(self, output_path: str | Path) -> None:
        duration_days = self.config["simulation"]["duration_days"]
        arrivals = self.arrival_generator.generate_arrivals(duration_days)
        events: List[Tuple[float, str, int, int | None, str]] = []
        for t, hen_id, window in arrivals:
            heapq.heappush(events, (t, "arrival", hen_id, None, window))

        while events:
            current_time, event_type, hen_id, nest_id, window = heapq.heappop(events)
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

        self._write_csv(Path(output_path))
        self.logger.info("Simulation complete. Wrote %d events.", len(self.logs))
