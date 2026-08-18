"""Raw LA-ICP-MS line-scan CSV file parser.

Each raw file is one laser line/spot: a small text header (source path,
"Intensity Vs Time,CPS", an "Acquired : <timestamp> using Batch <batch>.b"
line, then a comma-delimited column-header row) followed by comma-delimited
data rows (Time [Sec] + one CPS column per analyte), and a trailing blank
line + "Printed:<timestamp>" line. Row count and sweep interval vary per
file and must be read from the data, not assumed.
"""
from __future__ import annotations

import csv
import re
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

_ACQUIRED_RE = re.compile(r"^Acquired\s*:\s*(.+)$")
_FILENAME_RE = re.compile(r"^(?P<label>.+?)\s-\s(?P<index>\d+)$")
_ANALYTE_RE = re.compile(r"^([A-Za-z]{1,2})(\d+)$")

# Candidate "Acquired" timestamp formats, tried in order until one matches --
# different instrument software/export versions have been seen to use both
# 4-digit ("18/03/2020") and 2-digit ("30/07/26") years, and this project has
# so far only seen day-first ordering, but month-first is included as a
# plausible alternative (confirmed unambiguous either way whenever day > 12).
# ``parse_line_file``'s ``acquired_time_format`` lets a caller override this
# list entirely with an explicit ``datetime.strptime`` pattern for a format
# not covered here.
_ACQUIRED_TIME_FORMATS = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)

DEFAULT_ISOTOPE_TABLE_PATH = "resources/app_data/isotope_info.csv"


class RawFileFormatError(ValueError):
    """Raised when a raw line file doesn't match the expected instrument export format."""


@dataclass
class LineFileMeta:
    path: Path
    label: str
    index: int
    is_standard: bool
    acquired_at: datetime
    batch: str | None


@dataclass
class LineFileData:
    meta: LineFileMeta
    time_s: np.ndarray
    absolute_time: np.ndarray          # np.datetime64[us], one per row
    analytes: list[str]
    signal: pd.DataFrame                # index = row number, columns = analytes, values = CPS
    dt_s: float                          # median sweep interval, seconds
    n_rows: int


def parse_filename_label(path: Path) -> tuple[str, int]:
    """Split '<label> - <N>.csv' into (label, N)."""
    m = _FILENAME_RE.match(path.stem)
    if not m:
        raise RawFileFormatError(
            f"Filename '{path.name}' doesn't match the expected '<label> - <N>.csv' pattern."
        )
    return m.group("label"), int(m.group("index"))


def list_line_files(directory: str | Path) -> list[Path]:
    """All files in ``directory`` matching the raw '<label> - <N>.csv' pattern."""
    directory = Path(directory)
    files = []
    for p in sorted(directory.glob("*.csv")):
        try:
            parse_filename_label(p)
        except RawFileFormatError:
            continue
        files.append(p)
    return files


def _is_standard(label: str, standard_names) -> bool:
    if standard_names is None:
        return False
    if callable(standard_names):
        return bool(standard_names(label))
    return label in set(standard_names)


def _parse_acquired_line(line: str, time_format: str | None = None) -> tuple[datetime, str | None]:
    """Parses the ``Acquired : <timestamp> using Batch <batch>`` header line.

    ``time_format`` (a ``datetime.strptime`` pattern, e.g. ``"%d/%m/%y %H:%M:%S"``)
    overrides auto-detection entirely -- for a timestamp format not covered
    by :data:`_ACQUIRED_TIME_FORMATS` (different instrument software/export
    versions have already been seen to differ on 2- vs 4-digit years). When
    omitted (the default), every candidate in :data:`_ACQUIRED_TIME_FORMATS`
    is tried in order and the first match wins.
    """
    m = _ACQUIRED_RE.match(line.strip())
    if not m:
        raise RawFileFormatError(f"Could not parse 'Acquired' line: {line!r}")
    rest = m.group(1)
    if " using Batch " in rest:
        timestamp_str, batch = rest.split(" using Batch ", 1)
        batch = batch.strip() or None
    else:
        timestamp_str, batch = rest, None
    timestamp_str = timestamp_str.strip()

    candidates = (time_format,) if time_format else _ACQUIRED_TIME_FORMATS
    for fmt in candidates:
        try:
            return datetime.strptime(timestamp_str, fmt), batch
        except ValueError:
            continue
    tried = repr(time_format) if time_format else ", ".join(repr(f) for f in _ACQUIRED_TIME_FORMATS)
    raise RawFileFormatError(
        f"Could not parse acquired timestamp {timestamp_str!r} against format(s) tried: {tried}. "
        "Pass an explicit acquired_time_format (a datetime.strptime pattern) if this instrument "
        "export uses a different timestamp layout."
    )


def _is_numeric_row(fields: list[str]) -> bool:
    if not fields or fields[0].strip() == "":
        return False
    try:
        float(fields[0])
    except ValueError:
        return False
    return True


def validate_analyte_columns(
    analytes: list[str], isotope_table_path: str | Path = DEFAULT_ISOTOPE_TABLE_PATH
) -> list[str]:
    """Analyte column names (e.g. 'Al27') not found in the isotope reference table.

    Non-fatal by design: an unrecognized column is reported for the caller to
    warn about, not treated as a parse failure, since instruments can report
    isotopes absent from any particular local reference table.
    """
    path = Path(isotope_table_path)
    if not path.exists():
        return []
    table = pd.read_csv(path)
    # 'atomic_mass' holds the integer nominal mass number (e.g. Al -> 27); the
    # separate 'mass' column holds the precise isotope mass (e.g. 26.9815...).
    known = set(zip(table["symbol"], table["atomic_mass"].astype(int)))
    unknown = []
    for col in analytes:
        m = _ANALYTE_RE.match(col)
        if not m:
            unknown.append(col)
            continue
        element, mass = m.group(1), int(m.group(2))
        if (element, mass) not in known:
            unknown.append(col)
    return unknown


def parse_line_file(
    path: str | Path,
    standard_names: Iterable[str] | Callable[[str], bool] | None = None,
    validate_isotopes: bool = True,
    acquired_time_format: str | None = None,
) -> LineFileData:
    """Parse one raw LA-ICP-MS line-scan CSV export.

    Parameters
    ----------
    path : str or Path
    standard_names : iterable of str, or callable(label) -> bool, optional
        Determines ``LineFileMeta.is_standard`` from the filename label (the
        text before ' - N' in the filename stem).
    validate_isotopes : bool
        Cross-check analyte column names against
        ``resources/app_data/isotope_info.csv`` and warn (not raise) on
        unrecognized columns.
    acquired_time_format : str, optional
        A ``datetime.strptime`` pattern (e.g. ``"%d/%m/%y %H:%M:%S"``)
        overriding auto-detection of the header's ``Acquired : <timestamp>``
        line -- see :func:`_parse_acquired_line`. Only needed when the
        instrument export uses a timestamp layout not already covered by
        :data:`_ACQUIRED_TIME_FORMATS`.
    """
    path = Path(path)
    label, index = parse_filename_label(path)
    is_standard = _is_standard(label, standard_names)

    with path.open("r", newline="") as f:
        lines = f.read().splitlines()

    if len(lines) < 4:
        raise RawFileFormatError(f"{path}: expected at least 4 header lines, got {len(lines)}.")

    acquired_at, batch = _parse_acquired_line(lines[2], time_format=acquired_time_format)

    header = next(csv.reader([lines[3]]))
    if not header or header[0].strip().lower() != "time [sec]":
        raise RawFileFormatError(f"{path}: unexpected column header row: {lines[3]!r}")
    analytes = [c.strip() for c in header[1:]]

    if validate_isotopes:
        unknown = validate_analyte_columns(analytes)
        if unknown:
            warnings.warn(
                f"{path.name}: analyte column(s) not found in isotope reference table: {unknown}",
                stacklevel=2,
            )

    rows = []
    for line in lines[4:]:
        fields = next(csv.reader([line])) if line.strip() else []
        if not _is_numeric_row(fields):
            break
        rows.append([float(x) for x in fields])

    if not rows:
        raise RawFileFormatError(f"{path}: no numeric data rows found after the header.")

    data = np.array(rows, dtype=float)
    time_s = data[:, 0]
    signal = pd.DataFrame(data[:, 1:], columns=analytes)

    dt_s = float(np.median(np.diff(time_s))) if len(time_s) > 1 else float("nan")
    absolute_time = np.array(
        [np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s]
    )

    meta = LineFileMeta(
        path=path, label=label, index=index, is_standard=is_standard,
        acquired_at=acquired_at, batch=batch,
    )
    return LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=analytes,
        signal=signal, dt_s=dt_s, n_rows=len(rows),
    )
