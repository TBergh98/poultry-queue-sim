import argparse
import json
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
    repetitions = int(config.get("repetitions", 1))

    if not simulations:
        logger.error("No simulations found in config['simulations']")
        return

    for sim_config in simulations:
        sim_name = sim_config.get("name", "unnamed")
        output_dir = args.output_dir / sim_name
        mc_runs = []

        logger.info(f"Running simulation: {sim_name} (repetitions={repetitions})")
        for run_index in range(1, repetitions + 1):
            run_seed = None if args.seed is None else args.seed + run_index - 1
            output_path = output_dir / "mc_metrics.json"

            logger.info(f"Run {run_index}/{repetitions}: {sim_name}")
            sim = Simulator(sim_config, time_windows=time_windows, seed=run_seed)
            metrics, co_occurrences = sim.run(
                output_path,
                write_csv=False,
                write_metrics=False,
                write_co_occurrences=False,
            )

            mc_runs.append(
                {
                    "run_index": run_index,
                    "seed": run_seed,
                    "occupancy_metrics": metrics,
                    "co_occurrences": co_occurrences,
                }
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        mc_output_path = output_dir / "mc_metrics.json"
        mc_payload = {
            "simulation": sim_name,
            "repetitions": repetitions,
            "runs": mc_runs,
        }
        mc_output_path.write_text(json.dumps(mc_payload, indent=2), encoding="utf-8")

        logger.info(f"Simulation {sim_name} complete. Output: {mc_output_path}")


if __name__ == "__main__":
    main()
