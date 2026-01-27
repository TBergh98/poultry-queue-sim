import random
from typing import Dict, Mapping


class ServiceTimeSampler:
    def __init__(self, distribution_config: Mapping[str, Dict]):
        self.distribution_config = distribution_config

    def sample(self, window: str) -> float:
        cfg = self.distribution_config.get(window)
        if cfg is None:
            raise ValueError(f"No distribution config for window '{window}'")

        mixture_prob = cfg.get("mixture_prob", 1.0)
        if random.random() < mixture_prob:
            gamma_cfg = cfg["gamma"]
            shape = gamma_cfg["shape"]
            rate = gamma_cfg["rate"]
            scale = 1.0 / rate
            return random.gammavariate(shape, scale)

        uniform_cfg = cfg["uniform"]
        return random.uniform(uniform_cfg["min"], uniform_cfg["max"])

    def arrival_rate_per_hour(self, window: str) -> float:
        cfg = self.distribution_config.get(window)
        if cfg is None:
            raise ValueError(f"No distribution config for window '{window}'")
        return cfg.get("arrival_rate_per_hour", 0.0)
