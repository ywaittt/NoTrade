from __future__ import annotations

"""Helpers for loading NoTrade SSOT constants and stable IDs."""

from functools import lru_cache
from pathlib import Path
import re
from typing import Any

import yaml


_CONSTANTS_RELATIVE_PATH = Path("DATA_LAYER") / "NOTRADE_CONSTANTS.yaml"
_PASS_CODES_RELATIVE_PATH = Path("DATA_LAYER") / "PASS_CODES.md"
_PASS_CODE_PATTERN = re.compile(r"- `([A-Z0-9_]+)`")


@lru_cache(maxsize=1)
def find_repo_root() -> Path:
    """Return the repository root by walking upward from this module."""
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / _CONSTANTS_RELATIVE_PATH).exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {_CONSTANTS_RELATIVE_PATH} from {Path(__file__).resolve()}"
    )


@lru_cache(maxsize=1)
def get_constants() -> dict[str, Any]:
    """Load the canonical constants YAML once and cache it."""
    constants_path = find_repo_root() / _CONSTANTS_RELATIVE_PATH
    with constants_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    if not isinstance(payload, dict):
        raise ValueError("NOTRADE_CONSTANTS.yaml must deserialize into a dictionary.")

    return payload


@lru_cache(maxsize=1)
def get_pass_codes() -> tuple[str, ...]:
    """Parse stable PASS codes from the markdown SSOT."""
    pass_codes_path = find_repo_root() / _PASS_CODES_RELATIVE_PATH
    text = pass_codes_path.read_text(encoding="utf-8")
    codes = tuple(dict.fromkeys(_PASS_CODE_PATTERN.findall(text)))

    if not codes:
        raise ValueError("No PASS codes found in DATA_LAYER/PASS_CODES.md")

    return codes


def ssot_section(section: str) -> dict[str, Any]:
    """Return a top-level SSOT section and fail loudly if missing."""
    constants = get_constants()
    if section not in constants:
        raise KeyError(f"SSOT section '{section}' is missing from NOTRADE_CONSTANTS.yaml")

    value = constants[section]
    if not isinstance(value, dict):
        raise TypeError(f"SSOT section '{section}' must be a mapping.")

    return value


def ssot_value(section: str, key: str) -> Any:
    """Return a single SSOT value from a top-level section."""
    block = ssot_section(section)
    if key not in block:
        raise KeyError(f"SSOT key '{section}.{key}' is missing from NOTRADE_CONSTANTS.yaml")
    return block[key]


@lru_cache(maxsize=None)
def ssot_list(section: str, key: str) -> tuple[str, ...]:
    """Return a canonical enum-like SSOT list as an immutable tuple."""
    value = ssot_value(section, key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"SSOT key '{section}.{key}' must be a list[str].")
    return tuple(value)


@lru_cache(maxsize=None)
def ssot_mapping(section: str, key: str) -> dict[str, Any]:
    """Return a canonical mapping from the SSOT constants file."""
    value = ssot_value(section, key)
    if not isinstance(value, dict):
        raise TypeError(f"SSOT key '{section}.{key}' must be a mapping.")
    return value
