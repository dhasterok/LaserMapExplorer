"""Reference composition library loader: ``resources/minerals/
webmineral_compositions.csv`` -> a list of :class:`MineralReference`.

No YAML-loader precedent applies here (``src/stoichiometry/config.py`` is
YAML-only, one file per mineral); this is a single flat table, so a plain
``csv.DictReader`` pass is enough -- no nested-schema validation framework
needed the way ``MineralConfig`` requires one.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REFERENCE_LIBRARY_PATH = "resources/minerals/webmineral_compositions.csv"

# Elemental weight-percent columns usable for cosine-distance matching
# against LA-ICP-MS data (which measures elements, not oxides/molecular
# species). F and Cl are real, occasionally-diagnostic elements (fluorite,
# apatite, sodalite) but live in the CSV's volatile/halogen block rather
# than being duplicated in the bare-element block further right -- both
# blocks are element-basis wt%, so both are valid match inputs. H2O/CO2/OH
# are deliberately excluded: LA-ICP-MS doesn't measure molecular species
# directly (elemental H and O, when reported, are separate columns already
# included below).
ELEMENT_COLUMNS = [
    "F", "Cl",
    "Si", "Ti", "Al", "Cr", "Fe", "Mn", "Mg", "Ca", "Na", "K", "P", "Ni", "Co", "Zn",
    "Sc", "B", "Li", "Y", "Zr", "Hf", "Nb", "V", "Ba", "Sr",
    "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Th", "U", "Pb", "S", "Cu", "As", "Sb", "Cd", "O", "H",
]


class ReferenceLibraryError(ValueError):
    """Raised for a missing/malformed reference-library CSV."""


@dataclass(frozen=True)
class MineralReference:
    mineral_name: str
    group_yaml: str                 # links back to resources/minerals/<group_yaml>.yaml, when one exists; also drives the classification-ambiguity "same solid-solution group" logic (cosine.py)
    mineral_class: str               # broad browsing category (e.g. "Feldspar", "Clay", "Sulfide") -- UI grouping only, not used by any matching math
    end_member_key: str
    formula: str
    composition: dict[str, float] = field(default_factory=dict)  # element symbol -> wt%, only measured/reported values
    source_url: str = ""


def _parse_row(row: dict[str, str]) -> MineralReference:
    composition = {}
    for el in ELEMENT_COLUMNS:
        raw = (row.get(el) or "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 0:
            composition[el] = value
    return MineralReference(
        mineral_name=row["mineral_name"],
        group_yaml=row.get("group_yaml", ""),
        mineral_class=row.get("mineral_class", ""),
        end_member_key=row.get("end_member_key", ""),
        formula=row.get("formula", ""),
        composition=composition,
        source_url=row.get("source_url", ""),
    )


def load_reference_library(path: str | Path = DEFAULT_REFERENCE_LIBRARY_PATH) -> list[MineralReference]:
    """Loads every usable row of the reference composition CSV.

    Rows with ``basis == "NOT_FOUND"`` (no webmineral.com page existed,
    e.g. Ahrensite -- see the CSV's own ``notes`` column) are skipped: they
    carry no composition data to match against. A row with zero measured
    elements after that (shouldn't happen for a real entry, but a defensive
    check) is also skipped, since it can never score against anything.
    """
    path = Path(path)
    if not path.exists():
        raise ReferenceLibraryError(f"Reference library CSV not found: {path}")

    references = []
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ReferenceLibraryError(f"{path} has no header row.")
        missing = {"mineral_name", "basis"} - set(reader.fieldnames)
        if missing:
            raise ReferenceLibraryError(f"{path} is missing required column(s): {sorted(missing)}.")
        for row in reader:
            if row.get("basis") == "NOT_FOUND":
                continue
            ref = _parse_row(row)
            if not ref.composition:
                continue
            references.append(ref)

    if not references:
        raise ReferenceLibraryError(f"No usable reference compositions found in {path}.")
    return references
