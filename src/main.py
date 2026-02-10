import argparse
import json
import random
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
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated list of simulation names to run (overrides config run_only)",
    )
    return parser.parse_args()


def _mean_variance(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "variance": 0.0}
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return {"mean": mean, "variance": variance}


def _aggregate_occupancy_metrics(mc_runs: list[dict]) -> dict:
    aggregated: dict[int, dict] = {}
    for run in mc_runs:
        metrics = run.get("occupancy_metrics", {})
        for nest_id_str, nest_metrics in metrics.items():
            nest_id = int(nest_id_str)
            if nest_id not in aggregated:
                aggregated[nest_id] = {"nest_id": nest_id, "_values": {}}
            for key, value in nest_metrics.items():
                if key == "nest_id":
                    continue
                aggregated[nest_id]["_values"].setdefault(key, []).append(float(value))

    result: dict[int, dict] = {}
    for nest_id, data in aggregated.items():
        result[nest_id] = {"nest_id": nest_id}
        for key, values in data["_values"].items():
            result[nest_id][key] = _mean_variance(values)
    return result


def _coerce_non_negative_int(value: object, default: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, result)


def _normalize_sim_names(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [name.strip() for name in value.split(",") if name.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(name).strip() for name in value if str(name).strip()]
    return []


def main() -> None:
    args = parse_args()
    logger = setup_logger()
    config = load_config(args.config)

    time_windows = config.get("time_windows", {})
    simulations = config.get("simulations", [])
    repetitions = int(config.get("repetitions", 1))
    sample_logs_default = _coerce_non_negative_int(config.get("sample_logs", 3), 3)
    config_only = _normalize_sim_names(config.get("run_only"))
    cli_only = _normalize_sim_names(args.only)
    selected_names = cli_only or config_only

    if not simulations:
        logger.error("No simulations found in config['simulations']")
        return

    if selected_names:
        available_names = [sim.get("name") for sim in simulations]
        simulations = [
            sim for sim in simulations if sim.get("name") in set(selected_names)
        ]
        missing = [name for name in selected_names if name not in available_names]
        if missing:
            logger.warning(f"Requested simulations not found: {', '.join(missing)}")
        if not simulations:
            logger.error("No matching simulations after applying filters")
            return

    for sim_config in simulations:
        sim_name = sim_config.get("name", "unnamed")
        output_dir = args.output_dir / sim_name
        mc_runs = []
        sample_logs = _coerce_non_negative_int(
            sim_config.get("sample_logs", sample_logs_default), sample_logs_default
        )
        sample_logs = min(sample_logs, repetitions)
        rng = (
            random.Random(f"{args.seed}:{sim_name}")
            if args.seed is not None
            else random.Random()
        )
        sample_run_indices = (
            set(rng.sample(range(1, repetitions + 1), k=sample_logs))
            if sample_logs > 0
            else set()
        )
        sample_paths = {
            run_idx: output_dir / f"sample_run_{i:03d}.csv"
            for i, run_idx in enumerate(sorted(sample_run_indices), start=1)
        }

        logger.info(f"Running simulation: {sim_name} (repetitions={repetitions})")
        for run_index in range(1, repetitions + 1):
            run_seed = None if args.seed is None else args.seed + run_index - 1
            output_path = sample_paths.get(run_index, output_dir / "mc_metrics.json")
            write_csv = run_index in sample_paths

            logger.info(f"Run {run_index}/{repetitions}: {sim_name}")
            sim = Simulator(sim_config, time_windows=time_windows, seed=run_seed)
            metrics, co_occurrences, run_metrics = sim.run(
                output_path,
                write_csv=write_csv,
                write_metrics=False,
                write_co_occurrences=False,
            )

            mc_runs.append(
                {
                    "run_index": run_index,
                    "seed": run_seed,
                    "occupancy_metrics": metrics,
                    "co_occurrences": co_occurrences,
                    **run_metrics,
                }
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        mc_output_path = output_dir / "mc_metrics.json"
        aggregates = {"occupancy_metrics": _aggregate_occupancy_metrics(mc_runs)}
        mc_payload = {
            "simulation": sim_name,
            "repetitions": repetitions,
            "runs": mc_runs,
            "aggregates": aggregates,
        }
        mc_output_path.write_text(json.dumps(mc_payload, indent=2), encoding="utf-8")

        logger.info(f"Simulation {sim_name} complete. Output: {mc_output_path}")


if __name__ == "__main__":
    main()
