from typing import Dict, List, Optional, Tuple
from collections import Counter

from src.stochastic.distributions import ServiceTimeSampler


class Nest:
    def __init__(self, nest_id: int):
        self.nest_id = nest_id
        self.active_hens: Dict[int, float] = {}  # Maps hen_id -> entry_time
        
        # Occupancy metrics tracking
        self.occupancy_start: Optional[float] = None  # When nest transitions from empty to occupied
        self.total_occupancy_duration: float = 0.0  # Total time nest had ≥1 hen in service
        self.single_hen_start: Optional[float] = None  # When service started with exactly 1 hen
        self.total_single_hen_duration: float = 0.0  # Total time with exactly 1 hen in service
        
        # Co-occurrence tracking: count how many times each pair of hens are together
        self.co_occurrence_counts: Counter = Counter()  # Maps (hen_a, hen_b) tuples -> count

    def handle_arrival(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Process an arrival; returns log entries and next exit event (time, hen_id).
        
        With infinite servers, every hen is immediately accepted and starts service.
        """
        logs: List[Dict] = []
        n_active_before = len(self.active_hens)
        
        # Track occupancy state transitions
        if n_active_before == 0:
            # Nest transitions from empty to occupied (0 -> 1 hen)
            self.occupancy_start = current_time
            self.single_hen_start = current_time
        elif n_active_before == 1:
            # Transition from single hen to multiple hens (1 -> 2+)
            if self.single_hen_start is not None:
                self.total_single_hen_duration += current_time - self.single_hen_start
                self.single_hen_start = None
        
        # Track co-occurrences: this hen is now with all currently active hens
        for other_hen_id in self.active_hens.keys():
            # Store pairs in sorted order to ensure (A,B) == (B,A)
            pair = tuple(sorted([hen_id, other_hen_id]))
            self.co_occurrence_counts[pair] += 1
        
        # Add hen to active set and schedule exit
        service_time = sampler.sample(window)
        self.active_hens[hen_id] = current_time
        exit_time = current_time + service_time
        
        logs.append(
            {
                "timestamp": current_time,
                "hen_id": hen_id,
                "nest_id": self.nest_id,
                "event_type": "entry",
            }
        )
        
        return logs, (exit_time, hen_id)

    def handle_exit(
        self, current_time: float, hen_id: int, sampler: ServiceTimeSampler, window: str
    ) -> Tuple[List[Dict], Optional[Tuple[float, int]]]:
        """Process a hen's exit from the nest.
        
        With infinite servers, we simply remove the hen from active set.
        No queue processing needed.
        """
        logs: List[Dict] = [
            {
                "timestamp": current_time,
                "hen_id": hen_id,
                "nest_id": self.nest_id,
                "event_type": "exit",
            }
        ]
        
        # Remove hen from active set
        if hen_id in self.active_hens:
            del self.active_hens[hen_id]
        
        n_active_after = len(self.active_hens)
        
        # Track occupancy state transitions
        if n_active_after == 0:
            # Nest transitions from occupied to empty
            if self.single_hen_start is not None:
                self.total_single_hen_duration += current_time - self.single_hen_start
                self.single_hen_start = None
            
            if self.occupancy_start is not None:
                self.total_occupancy_duration += current_time - self.occupancy_start
                self.occupancy_start = None
        elif n_active_after == 1:
            # Transition from multiple hens to single hen (2+ -> 1)
            if self.single_hen_start is None:
                self.single_hen_start = current_time
        
        return logs, None

    def finalize_metrics(self, final_time: float) -> None:
        """Called at end of simulation to account for incomplete occupancy sessions."""
        # If nest still has active hens at simulation end
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
    
    def get_co_occurrences(self) -> Dict[Tuple[int, int], int]:
        """Return co-occurrence counts as a regular dict."""
        return dict(self.co_occurrence_counts)
