import argparse
from pathlib import Path

from src.core.simulator import Simulator
from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poultry nest simulator (multi-sim runner)")
    parser.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data"), help="Output directory base"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logger()
    config = load_config(args.config)

    time_windows = config.get("time_windows", {})
    simulations = config.get("simulations", [])

    if not simulations:
        logger.error("No simulations found in config['simulations']")
        return

    for sim_config in simulations:
        sim_name = sim_config.get("name", "unnamed")
        output_dir = args.output_dir / sim_name
        output_path = output_dir / "simulated_log.csv"

        logger.info(f"Running simulation: {sim_name}")
        sim = Simulator(sim_config, time_windows=time_windows, seed=args.seed)
        metrics = sim.run(output_path)
        logger.info(f"Simulation {sim_name} complete. Output: {output_path}")
        
        # Display occupancy metrics
        logger.info("=" * 80)
        logger.info("OCCUPANCY METRICS")
        logger.info("=" * 80)
        for nest_id in sorted(metrics.keys()):
            m = metrics[nest_id]
            logger.info(
                f"Nest {m['nest_id']}: "
                f"total_occupancy_time={m['total_occupancy_time']:.2f}s, "
                f"total_single_hen_time={m['total_single_hen_time']:.2f}s"
            )
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
