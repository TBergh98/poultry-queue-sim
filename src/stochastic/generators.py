import random
from typing import Dict, List, Mapping, Tuple

from src.stochastic.distributions import ServiceTimeSampler

SECONDS_PER_DAY = 24 * 3600


def _in_window(hour: float, start: int, end: int) -> bool:
    if start <= end:
        return start <= hour <= end
    return hour >= start or hour <= end


class ArrivalGenerator:
    def __init__(self, time_windows: Mapping[str, Dict], sampler: ServiceTimeSampler, hens_number: int = 100):
        self.time_windows = dict(time_windows)
        self.sampler = sampler
        self.hens_number = hens_number

    def window_for_time(self, current_time: float) -> str:
        hour = (current_time % SECONDS_PER_DAY) / 3600.0
        for name, span in self.time_windows.items():
            if _in_window(hour, span["start"], span["end"]):
                return name
        raise ValueError(f"No time window found for hour {hour}")

    def _next_boundary_seconds(self, current_time: float) -> float:
        current_day = int(current_time // SECONDS_PER_DAY)
        candidates: List[float] = []
        for span in self.time_windows.values():
            start_hour = span["start"]
            candidate = current_day * SECONDS_PER_DAY + start_hour * 3600
            if candidate <= current_time:
                candidate += SECONDS_PER_DAY
            candidates.append(candidate)
        return min(candidates)

    def generate_arrivals(self, duration_days: int) -> List[Tuple[float, int, str]]:
        total_seconds = duration_days * SECONDS_PER_DAY
        t = 0.0
        arrivals: List[Tuple[float, int, str]] = []

        while t < total_seconds:
            window = self.window_for_time(t)
            rate_sec = self.sampler.arrival_rate_per_second(window)
            boundary = self._next_boundary_seconds(t)

            if rate_sec <= 0:
                t = min(boundary, total_seconds)
                continue

            dt = random.expovariate(rate_sec)
            if t + dt >= boundary:
                t = boundary
                continue

            t += dt
            if t > total_seconds:
                break
            hen_id = random.randint(1, self.hens_number)
            arrivals.append((t, hen_id, window))

        return arrivals
