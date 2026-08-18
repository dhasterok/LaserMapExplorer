"""Raw-file parser tests against small synthetic fixtures matching the real
instrument export format (CRLF, 4-line header, trailing 'Printed:' line).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.rawfile import (
    RawFileFormatError,
    _parse_acquired_line,
    list_line_files,
    parse_filename_label,
    parse_line_file,
    validate_analyte_columns,
)

FIXTURE_DIR = project_root / "tests" / "fixtures" / "calibration"
STD_FILE = FIXTURE_DIR / "SYNSTD - 1.csv"
SAMPLE_FILE = FIXTURE_DIR / "SYNSAMPLE - 1.csv"


def test_parse_filename_label():
    assert parse_filename_label(Path("NIST610 - 8.csv")) == ("NIST610", 8)
    assert parse_filename_label(Path("WGC-25B-1 - 116.csv")) == ("WGC-25B-1", 116)


def test_parse_filename_label_rejects_bad_pattern():
    with pytest.raises(RawFileFormatError):
        parse_filename_label(Path("not_a_valid_name.csv"))


def test_list_line_files_filters_to_matching_pattern(tmp_path):
    (tmp_path / "NIST610 - 1.csv").write_text("x")
    (tmp_path / "NIST610 - 2.csv").write_text("x")
    (tmp_path / "readme.txt").write_text("x")
    (tmp_path / "not a match.csv").write_text("x")
    files = list_line_files(tmp_path)
    assert [p.name for p in files] == ["NIST610 - 1.csv", "NIST610 - 2.csv"]


def test_parse_line_file_header_and_timing():
    data = parse_line_file(STD_FILE, standard_names={"SYNSTD"})

    assert data.meta.label == "SYNSTD"
    assert data.meta.index == 1
    assert data.meta.is_standard is True
    assert data.meta.acquired_at == datetime(2026, 3, 1, 10, 0, 0)
    assert data.meta.batch == "SyntheticBatch.b"
    assert data.analytes == ["Al27", "Ca43", "Fe57"]
    # 5 background + 15 ablation rows were written into the fixture.
    assert data.n_rows == 20
    assert data.signal.shape == (20, 3)
    # dt is read from actual time deltas (0.30s), not assumed.
    assert data.dt_s == pytest.approx(0.30, abs=1e-6)
    # parsing must stop before the blank lines / trailing "Printed:" line.
    assert data.time_s[-1] == pytest.approx(0.30 + 19 * 0.30, abs=1e-6)


def test_parse_line_file_is_standard_via_callable():
    data = parse_line_file(SAMPLE_FILE, standard_names=lambda label: label.startswith("SYNSTD"))
    assert data.meta.is_standard is False
    assert data.meta.label == "SYNSAMPLE"


def test_parse_line_file_absolute_time_combines_acquired_and_time_column():
    data = parse_line_file(STD_FILE, standard_names={"SYNSTD"})
    expected_first = np.datetime64(datetime(2026, 3, 1, 10, 0, 0)) + np.timedelta64(300000, "us")
    assert data.absolute_time[0] == expected_first


def test_parse_acquired_line_auto_detects_two_digit_year():
    """Regression test: an instrument export using a 2-digit year
    ("30/07/26") must parse without an explicit format override -- an
    earlier version hardcoded a 4-digit-year-only pattern and raised
    RawFileFormatError on this real export style."""
    acquired_at, batch = _parse_acquired_line(
        "Acquired      : 30/07/26 12:15:58 using Batch 20260730_UPbCarb.b"
    )
    assert acquired_at == datetime(2026, 7, 30, 12, 15, 58)
    assert batch == "20260730_UPbCarb.b"


def test_parse_acquired_line_still_handles_four_digit_year():
    acquired_at, _ = _parse_acquired_line("Acquired      : 18/03/2020 17:12:42 using Batch x.b")
    assert acquired_at == datetime(2020, 3, 18, 17, 12, 42)


def test_parse_acquired_line_explicit_format_override():
    acquired_at, _ = _parse_acquired_line(
        "Acquired      : 2026.07.30 12:15:58 using Batch x.b", time_format="%Y.%m.%d %H:%M:%S",
    )
    assert acquired_at == datetime(2026, 7, 30, 12, 15, 58)


def test_parse_acquired_line_explicit_format_that_does_not_match_raises():
    with pytest.raises(RawFileFormatError):
        _parse_acquired_line("Acquired      : 30/07/26 12:15:58 using Batch x.b", time_format="%Y.%m.%d %H:%M:%S")


def test_parse_acquired_line_unparseable_timestamp_raises_with_attempted_formats():
    with pytest.raises(RawFileFormatError, match="format"):
        _parse_acquired_line("Acquired      : not-a-timestamp using Batch x.b")


def test_parse_line_file_acquired_time_format_override(tmp_path):
    """End-to-end: parse_line_file threads acquired_time_format through to
    the header parse."""
    content = (
        "D:\\Data\\x.d\r\n"
        "Intensity Vs Time,CPS\r\n"
        "Acquired      : 2026.07.30 12:15:58 using Batch x.b\r\n"
        "Time [Sec],Al27\r\n"
        "0.30,100.0\r\n"
        "0.60,100.0\r\n"
        "0.90,100.0\r\n"
    )
    p = tmp_path / "NIST610 - 1.csv"
    p.write_text(content, newline="")
    data = parse_line_file(p, standard_names={"NIST610"}, acquired_time_format="%Y.%m.%d %H:%M:%S")
    assert data.meta.acquired_at == datetime(2026, 7, 30, 12, 15, 58)


def test_validate_analyte_columns_flags_unknown_names():
    unknown = validate_analyte_columns(["Al27", "NotAnIsotope99"])
    assert "NotAnIsotope99" in unknown
    assert "Al27" not in unknown
