from collections import deque
from typing import Deque, Dict, List, Optional, Tuple
import random

from src.stochastic.distributions import ServiceTimeSampler


class Nest:
    def __init__(self, nest_id: int):
        self.nest_id = nest_id
        self.busy_until: float = 0.0
        self.queue: Deque[int] = deque()
        
        # Occupancy metrics tracking
        self.occupancy_start: Optional[float] = None  # When nest transitions from empty to occupied
        self.total_occupancy_duration: float = 0.0  # Total time nest had ≥1 hen in service
        self.single_hen_start: Optional[float] = None  # When service started with exactly 1 hen
        self.total_single_hen_duration: float = 0.0  # Total time with exactly 1 hen in service

    def handle_arrival(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Process an arrival; returns log entries and next exit event (time, hen_id)."""
        logs: List[Dict] = []
        was_empty = current_time >= self.busy_until and not self.queue
        
        if was_empty:
            # Nest transitions from empty to occupied with 1 hen
            self.occupancy_start = current_time
            self.single_hen_start = current_time
            
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

        # Nest was already occupied; add to queue
        # If queue was empty (1 hen in service), transition from 1 hen to 2+ hens
        if not self.queue and self.single_hen_start is not None:
            self.total_single_hen_duration += current_time - self.single_hen_start
            self.single_hen_start = None
        
        self.queue.append(hen_id)
        return logs, None

    def handle_exit(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Complete current service; start next if queued (SIRO policy)."""
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
            # SIRO: Service In Random Order
            idx = random.randrange(len(self.queue))
            next_hen = self.queue[idx]
            del self.queue[idx]
            
            # If there are still hens in queue after this one, we go from 1 hen to 2+ hens
            # If queue becomes empty, we stay at 1 hen
            if self.queue and self.single_hen_start is not None:
                # Ending single-hen period (about to serve hen while others wait)
                self.total_single_hen_duration += current_time - self.single_hen_start
                self.single_hen_start = None
            elif not self.queue and self.single_hen_start is None:
                # Starting single-hen period (next hen will be alone)
                self.single_hen_start = current_time
            
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
            # Queue is now empty; nest transitions from occupied to empty
            if self.single_hen_start is not None:
                self.total_single_hen_duration += current_time - self.single_hen_start
                self.single_hen_start = None
            
            if self.occupancy_start is not None:
                self.total_occupancy_duration += current_time - self.occupancy_start
                self.occupancy_start = None
            
            self.busy_until = current_time

        return logs, next_exit

    def finalize_metrics(self, final_time: float) -> None:
        """Called at end of simulation to account for incomplete occupancy sessions."""
        # If nest still has hen in service at simulation end
        if self.occupancy_start is not None:
            self.total_occupancy_duration += final_time - self.occupancy_start
            self.occupancy_start = None
        
        if self.single_hen_start is not None:
            self.total_single_hen_duration += final_time - self.single_hen_start
            self.single_hen_start = None
    
    def get_metrics(self) -> Dict:
        """Return occupancy metrics for this nest."""
        return {
            "nest_id": self.nest_id,
            "total_occupancy_time": self.total_occupancy_duration,
            "total_single_hen_time": self.total_single_hen_duration,
        }
