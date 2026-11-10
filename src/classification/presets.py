"""User-defined mineral subsets for classification: named lists of mineral
names, recalled later so the user doesn't have to re-check the same subset
of ``listMinerals`` every session -- stored long-format (one row per
mineral per preset) in ``resources/minerals/classification_presets.csv``,
the simplest schema that's still trivially hand-editable/diffable.
"""
from __future__ import annotations

import csv
from pathlib import Path

from lame_core.config import RESOURCE_PATH

# Anchored to the installed resources directory, not the working directory: a
# frozen app launched from Finder runs with cwd "/". src/app/config.py calls
# lame_core.config.setup() before any app module is imported, so RESOURCE_PATH is
# already correct by the time this binds.
DEFAULT_PRESETS_PATH = str(Path(RESOURCE_PATH) / "minerals" / "classification_presets.csv")


def load_presets(path: str | Path = DEFAULT_PRESETS_PATH) -> dict[str, list[str]]:
    """preset_name -> list of mineral names, in the order they appear in the
    file. Returns an empty dict if the file doesn't exist yet (no presets
    saved yet is not an error)."""
    path = Path(path)
    if not path.exists():
        return {}

    presets: dict[str, list[str]] = {}
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("preset_name") or "").strip()
            mineral = (row.get("mineral_name") or "").strip()
            if not name or not mineral:
                continue
            presets.setdefault(name, []).append(mineral)
    return presets


def save_preset(path: str | Path, name: str, mineral_names: list[str]) -> None:
    """Writes (or overwrites) one named preset, leaving every other preset
    already in the file untouched."""
    path = Path(path)
    presets = load_presets(path)
    presets[name] = list(mineral_names)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["preset_name", "mineral_name"])
        for preset_name, names in presets.items():
            for mineral_name in names:
                writer.writerow([preset_name, mineral_name])
