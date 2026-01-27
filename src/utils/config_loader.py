from pathlib import Path
from typing import Any, Dict
import yaml


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load YAML configuration into a dictionary."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
