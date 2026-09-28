"""Configuration handling for smoosh."""

from pathlib import Path
from typing import Any, Dict, TypedDict

import yaml

from .. import ConfigurationError  # Import the exception from root package


class SizeLimitsDict(TypedDict):
    """TypedDict for size limits configuration."""

    file_max_mb: float


class OutputDict(TypedDict):
    """TypedDict for output configuration."""

    max_tokens: int
    size_limits: SizeLimitsDict


class ThresholdsDict(TypedDict):
    """TypedDict for thresholds configuration."""

    cat_threshold: int
    fold_threshold: int


class GitignoreDict(TypedDict):
    """TypedDict for gitignore configuration."""

    respect: bool


class ConfigDict(TypedDict):
    """TypedDict for the overall configuration."""

    output: OutputDict
    thresholds: ThresholdsDict
    gitignore: GitignoreDict


# Single source of truth for default configuration values.
DEFAULT_CONFIG: ConfigDict = {
    "output": {"max_tokens": 10000, "size_limits": {"file_max_mb": 1.0}},
    "thresholds": {"cat_threshold": 5000, "fold_threshold": 15000},
    "gitignore": {"respect": True},
}


def load_config(config_dir: Path) -> Dict[str, Any]:
    """Load configuration from smoosh.yaml in the specified directory.

    Values from the file are deep-merged onto :data:`DEFAULT_CONFIG`, so any
    key the user omits keeps its default.

    Args:
        config_dir: Directory containing the configuration file

    Returns:
        Configuration dictionary with defaults applied

    Raises:
        ConfigurationError: If configuration loading fails
    """
    try:
        config_path = config_dir / "smoosh.yaml"

        if config_path.is_file():
            with open(config_path, encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    return deep_merge(DEFAULT_CONFIG, user_config)

        return deep_merge(DEFAULT_CONFIG, {})
    except (OSError, yaml.YAMLError) as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, updating base with values from update.

    Args:
        base: Base dictionary to merge into
        update: Dictionary with values to merge

    Returns:
        Merged dictionary
    """
    merged = base.copy()

    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged
