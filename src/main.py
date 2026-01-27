import argparse
from pathlib import Path

from src.core.simulator import Simulator
from src.utils.config_loader import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poultry nest simulator")
    parser.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/simulated_log.csv"), help="CSV output path"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    sim = Simulator(config, seed=args.seed)
    sim.run(args.output)


if __name__ == "__main__":
    main()
