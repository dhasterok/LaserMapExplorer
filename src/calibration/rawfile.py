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
    """Raised when a raw line file does not match the expected instrument export format."""


@dataclass
class LineFileMeta:
    """Identifying metadata for one raw line-scan file.

    Attributes
    ----------
    path : pathlib.Path
        Path to the source CSV.
    label : str
        Filename label -- the text before ``" - N"`` in the filename stem.
    index : int
        The ``N`` in ``"<label> - <N>.csv"``; the line/spot number.
    is_standard : bool
        Whether ``label`` was matched as a reference-standard file.
    acquired_at : datetime.datetime
        Acquisition start time, parsed from the ``Acquired :`` header line.
    batch : str or None
        Batch name from the header, or ``None`` if the line omits it.
    """

    path: Path
    label: str
    index: int
    is_standard: bool
    acquired_at: datetime
    batch: str | None


@dataclass
class LineFileData:
    """Parsed contents of one raw line-scan file.

    Attributes
    ----------
    meta : LineFileMeta
        Identifying metadata for the file.
    time_s : numpy.ndarray
        Per-row elapsed time in seconds (the ``Time [Sec]`` column).
    absolute_time : numpy.ndarray
        Per-row wall-clock time as ``datetime64[us]``
        (``meta.acquired_at + time_s``).
    analytes : list[str]
        Analyte/channel column names, e.g. ``["Al27", "Ca43", ...]``.
    signal : pandas.DataFrame
        CPS values; row-number index, one column per analyte.
    dt_s : float
        Median sweep interval in seconds, or NaN for a single-row file.
    n_rows : int
        Number of numeric data rows parsed.
    """

    meta: LineFileMeta
    time_s: np.ndarray
    absolute_time: np.ndarray          # np.datetime64[us], one per row
    analytes: list[str]
    signal: pd.DataFrame                # index = row number, columns = analytes, values = CPS
    dt_s: float                          # median sweep interval, seconds
    n_rows: int


def parse_filename_label(path: Path) -> tuple[str, int]:
    """Split a ``"<label> - <N>.csv"`` filename into its label and index.

    Parameters
    ----------
    path : pathlib.Path
        File path whose stem is parsed (the extension is ignored).

    Returns
    -------
    tuple[str, int]
        ``(label, N)``.

    Raises
    ------
    RawFileFormatError
        If the stem does not match the ``"<label> - <N>"`` pattern.
    """
    m = _FILENAME_RE.match(path.stem)
    if not m:
        raise RawFileFormatError(
            f"Filename '{path.name}' doesn't match the expected '<label> - <N>.csv' pattern."
        )
    return m.group("label"), int(m.group("index"))


def list_line_files(directory: str | Path) -> list[Path]:
    """List raw line-scan CSVs in a directory.

    Parameters
    ----------
    directory : str or pathlib.Path
        Directory to scan (non-recursively).

    Returns
    -------
    list[pathlib.Path]
        Every ``*.csv`` whose stem matches the ``"<label> - <N>"`` pattern,
        sorted by name. Non-matching CSVs are skipped silently.
    """
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
    """Whether ``label`` names a reference-standard file.

    Parameters
    ----------
    label : str
        Filename label to test.
    standard_names : Iterable[str] or Callable[[str], bool] or None
        A membership collection, a predicate, or ``None``.

    Returns
    -------
    bool
        ``False`` when ``standard_names`` is ``None``; otherwise the
        predicate result or membership test.
    """
    if standard_names is None:
        return False
    if callable(standard_names):
        return bool(standard_names(label))
    return label in set(standard_names)


def _parse_acquired_line(line: str, time_format: str | None = None) -> tuple[datetime, str | None]:
    """Parse the ``Acquired : <timestamp> using Batch <batch>`` header line.

    Parameters
    ----------
    line : str
        The raw header line.
    time_format : str or None, optional
        A :func:`datetime.datetime.strptime` pattern overriding
        auto-detection entirely. When omitted, each candidate in
        :data:`_ACQUIRED_TIME_FORMATS` is tried in order and the first
        match wins.

    Returns
    -------
    tuple[datetime.datetime, str or None]
        ``(acquired_at, batch)``; ``batch`` is ``None`` when the line has
        no ``" using Batch "`` clause.

    Raises
    ------
    RawFileFormatError
        If the line is not an ``Acquired :`` line, or the timestamp does
        not parse against any tried format.
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
    """Whether a split CSV row is a numeric data row.

    Parameters
    ----------
    fields : list[str]
        Comma-split fields of one line.

    Returns
    -------
    bool
        ``True`` only if the first field is non-empty and parses as a
        float -- used to detect the end of the data block.
    """
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
    """Find analyte column names not present in the isotope reference table.

    Parameters
    ----------
    analytes : list[str]
        Analyte column names to check, e.g. ``["Al27", "Ca43"]``.
    isotope_table_path : str or pathlib.Path, optional
        Path to the isotope reference CSV (``symbol`` and ``atomic_mass``
        columns). Defaults to :data:`DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    list[str]
        Column names that do not match the ``<element><mass>`` pattern, or
        whose ``(element, mass)`` pair is absent from the table. Empty if
        the table file does not exist.

    Notes
    -----
    Non-fatal by design: an unrecognized column is reported for the caller
    to warn about, not treated as a parse failure, since instruments can
    report isotopes absent from any particular local reference table.
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
    path : str or pathlib.Path
        Path to the raw line-scan CSV. Its stem must match
        ``"<label> - <N>"``.
    standard_names : Iterable[str] or Callable[[str], bool] or None, optional
        Determines ``LineFileMeta.is_standard`` from the filename label (the
        text before ``" - N"`` in the filename stem). By default ``None``
        (nothing is a standard).
    validate_isotopes : bool, optional
        Cross-check analyte column names against
        ``resources/app_data/isotope_info.csv`` and warn (not raise) on
        unrecognized columns. By default ``True``.
    acquired_time_format : str or None, optional
        A :func:`datetime.datetime.strptime` pattern (e.g.
        ``"%d/%m/%y %H:%M:%S"``) overriding auto-detection of the header's
        ``Acquired : <timestamp>`` line -- see :func:`_parse_acquired_line`.
        Only needed when the instrument export uses a timestamp layout not
        already covered by :data:`_ACQUIRED_TIME_FORMATS`.

    Returns
    -------
    LineFileData
        The parsed timing arrays, analyte list, and CPS signal frame.

    Raises
    ------
    RawFileFormatError
        If the filename, header lines, column header row, or data block do
        not match the expected instrument export format.

    Warns
    -----
    UserWarning
        When ``validate_isotopes`` is true and one or more analyte columns
        are absent from the isotope reference table.
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
