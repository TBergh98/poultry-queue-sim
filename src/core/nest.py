from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from src.stochastic.distributions import ServiceTimeSampler


class Nest:
    def __init__(self, nest_id: int):
        self.nest_id = nest_id
        self.busy_until: float = 0.0
        self.queue: Deque[int] = deque()

    def handle_arrival(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Process an arrival; returns log entries and next exit event (time, hen_id)."""
        logs: List[Dict] = []
        if current_time >= self.busy_until and not self.queue:
            service_time = sampler.sample(window)
            self.busy_until = current_time + service_time
            logs.append(
                {
                    "timestamp": current_time,
                    "hen_id": hen_id,
                    "nest_id": self.nest_id,
                    "event_type": "entry",
                }
            )
            return logs, (self.busy_until, hen_id)

        self.queue.append(hen_id)
        return logs, None

    def handle_exit(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Complete current service; start next if queued."""
        logs: List[Dict] = [
            {
                "timestamp": current_time,
                "hen_id": hen_id,
                "nest_id": self.nest_id,
                "event_type": "exit",
            }
        ]
        next_exit: Optional[Tuple[float, int]] = None

        if self.queue:
            next_hen = self.queue.popleft()
            service_time = sampler.sample(window)
            self.busy_until = current_time + service_time
            logs.append(
                {
                    "timestamp": current_time,
                    "hen_id": next_hen,
                    "nest_id": self.nest_id,
                    "event_type": "entry",
                }
            )
            next_exit = (self.busy_until, next_hen)
        else:
            self.busy_until = current_time

        return logs, next_exit
