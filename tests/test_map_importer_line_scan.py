"""Line-scan import: one file per laser traverse, every analyte as a column.

The Agilent "Intensity Vs Time" export these tests imitate is three preamble
lines, a ``Time [Sec],<analytes...>`` header, the data rows, then a blank line
and a ``          Printed:<datetime>`` footer.

Each test here pins one defect that shipped in that path:

* the footer was read as a data row, which put a timestamp string in
  ``Time [Sec]`` and made the whole column non-numeric. That survived into the
  ``.lame.csv`` and later aborted the sample load, where ``cluster_data`` calls
  ``np.isfinite`` over what had become an object array -- so the import looked
  like it had worked and the sample simply never appeared.
* ``Time [Sec]`` was kept as a column and so was typed ``'Analyte'`` on load,
  joining the field lists, clustering and PCA.
* lines were stacked in ``os.listdir`` order. Stacking order *is* the image's
  column order, so an unsorted list reshapes into a column-shuffled map with no
  error raised anywhere.
* ``Xc`` was keyed off the scan number in the filename. Standards interleaved
  between the sample lines leave gaps in that numbering (203..297 for 91 lines),
  which became uneven pixel spacing.
"""
import numpy as np
import pandas as pd
import pytest

from src.importers.MapImporter import MapImporter, _time_column


PREAMBLE = (
    "D:\\2022\\Batch\\201-SAMPLE.d\n"
    "Intensity Vs Time,CPS\n"
    "Acquired      : 18/06/2022 00:17:39 using Batch Sulphide Images 17-6.b\n"
)
FOOTER = "\n\n          Printed:18/06/2022 00:25:28\n"


def write_line_file(path, n_rows=4, analytes=("Mg24", "Fe57"), sweep=0.306,
                    footer=True):
    """Writes one per-line export; returns the analyte values it contains."""
    values = np.arange(n_rows * len(analytes), dtype=float).reshape(n_rows, len(analytes))
    rows = []
    for i in range(n_rows):
        time = round((i + 1) * sweep, 4)
        rows.append(",".join([f"{time}"] + [f"{v:.2f}" for v in values[i]]))
    text = PREAMBLE + "Time [Sec]," + ",".join(analytes) + "\n" + "\n".join(rows) + "\n"
    if footer:
        text += FOOTER
    path.write_text(text)
    return values


@pytest.fixture
def importer():
    """A MapImporter with no dialog: the readers touch no widgets."""
    return MapImporter.__new__(MapImporter)


# --- the footer, which is what broke the load ------------------------------

def test_footer_row_is_not_read_as_data(importer, tmp_path):
    f = tmp_path / "203-SAMPLE.csv"
    expected = write_line_file(f, n_rows=4)

    df = importer.read_line_file(f)

    assert len(df) == 4, "the 'Printed:' footer must not become a pixel"
    np.testing.assert_allclose(df[["Mg24", "Fe57"]].to_numpy(float), expected)


def test_every_column_stays_numeric(importer, tmp_path):
    """The actual failure mode: one text cell makes the column object dtype,
    and np.isfinite() over it later aborts the sample load."""
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f)

    df = importer.read_raw_folder(0, f, False, 20.0, 6.135)

    assert all(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)
    np.isfinite(df.to_numpy(float))        # must not raise


def test_a_file_with_no_footer_is_unchanged(importer, tmp_path):
    """The strip must not cost a real row when there is no footer."""
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f, n_rows=5, footer=False)

    assert len(importer.read_line_file(f)) == 5


# --- the time axis ---------------------------------------------------------

def test_time_column_is_dropped(importer, tmp_path):
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f)

    df = importer.read_line_file(f)

    assert _time_column(df) is None, "the sweep clock is not a measurement"
    assert list(df.columns) == ["Mg24", "Fe57"]


def test_first_column_is_an_analyte(importer, tmp_path):
    """The preview shows the first column; with Time present it previewed the
    clock, which ramps along every line and so looked like real structure."""
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f)

    assert importer.read_line_file(f).columns[0] == "Mg24"


@pytest.mark.parametrize("header", ["Time [Sec]", "time [sec]", "Time [Sec] "])
def test_time_header_is_matched_loosely(importer, tmp_path, header):
    """Case and padding vary between instrument software versions, and a miss
    here would silently leave both the footer row and the time axis in."""
    f = tmp_path / "203-SAMPLE.csv"
    f.write_text(PREAMBLE + f"{header},Mg24\n0.306,1.0\n0.612,2.0\n" + FOOTER)

    df = importer.read_line_file(f)

    assert list(df.columns) == ["Mg24"]
    assert len(df) == 2


# --- coordinates -----------------------------------------------------------

def test_coordinates_come_from_the_line_index_not_the_scan_number(importer, tmp_path):
    """Scan 203 is the first line of the map, so it belongs at Xc == 0."""
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f, n_rows=3)

    df = importer.read_raw_folder(0, f, False, 20.0, 6.0)

    assert (df["Xc"] == 0).all()
    np.testing.assert_allclose(df["Yc"].to_numpy(), [0.0, 6.0, 12.0])


def test_line_index_scales_by_dx(importer, tmp_path):
    f = tmp_path / "207-SAMPLE.csv"
    write_line_file(f, n_rows=2)

    df = importer.read_raw_folder(4, f, False, 20.0, 6.0)

    assert (df["Xc"] == 80.0).all()


def test_swap_xy_puts_the_line_on_the_other_axis(importer, tmp_path):
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f, n_rows=3)

    df = importer.read_raw_folder(2, f, True, 6.0, 20.0)

    assert (df["Yc"] == 40.0).all()
    np.testing.assert_allclose(df["Xc"].to_numpy(), [0.0, 6.0, 12.0])


def test_row_count_drives_tof_spacing(importer, tmp_path):
    """TOF derives dx from the raster length, so the footer row would have
    skewed the spacing as well as adding a pixel."""
    f = tmp_path / "203-SAMPLE.csv"
    write_line_file(f, n_rows=4)

    df = importer.read_raw_folder(0, f, True, 1.0, 1.0, length=400.0)

    np.testing.assert_allclose(df["Xc"].to_numpy(), [0.0, 100.0, 200.0, 300.0])


# --- stacking order and file selection -------------------------------------

def _file_table(filenames, line_nos, imported=True):
    return pd.DataFrame({
        "Import": [imported] * len(filenames),
        "Filename": list(filenames),
        "Analyte 1": [str(n) for n in line_nos],
        "Analyte 2": [""] * len(filenames),
    })


def test_selected_line_files_are_sorted_by_line_number(importer):
    """os.listdir order is arbitrary; unsorted, the map comes out with its
    columns shuffled and nothing raises."""
    importer.standard_list = []
    df = _file_table(["210-S.csv", "205-S.csv", "227-S.csv"], [210, 205, 227])

    selected, is_numeric = importer.select_import_files(df)

    assert is_numeric
    assert list(selected["Filename"]) == ["205-S.csv", "210-S.csv", "227-S.csv"]


def test_standards_are_dropped_from_the_selection(importer):
    importer.standard_list = ["STDGL3"]
    df = _file_table(["201-STDGL3.csv", "203-S.csv", "204-S.csv"], [201, 203, 204])

    selected, _ = importer.select_import_files(df)

    assert list(selected["Filename"]) == ["203-S.csv", "204-S.csv"]


def test_unticked_files_are_dropped_from_the_selection(importer):
    importer.standard_list = []
    df = _file_table(["203-S.csv", "204-S.csv"], [203, 204])
    df.loc[0, "Import"] = False

    selected, _ = importer.select_import_files(df)

    assert list(selected["Filename"]) == ["204-S.csv"]


def test_layout_is_judged_on_selected_files_only(importer):
    """An unticked stray whose name parses as an analyte used to flip a whole
    line-scan directory into matrix mode, feeding each line to the matrix
    reader."""
    importer.standard_list = []
    df = _file_table(["203-S.csv", "204-S.csv", "Ar40.csv"], [203, 204, "Ar40"])
    df.loc[2, "Import"] = False

    selected, is_numeric = importer.select_import_files(df)

    assert is_numeric, "the one non-line file was not selected for import"
    assert list(selected["Filename"]) == ["203-S.csv", "204-S.csv"]


def test_matrix_sets_are_not_sorted_or_mistaken_for_line_scans(importer):
    importer.standard_list = []
    df = _file_table(["Fe57.csv", "Mg24.csv"], ["Fe57", "Mg24"])

    selected, is_numeric = importer.select_import_files(df)

    assert not is_numeric
    assert list(selected["Filename"]) == ["Fe57.csv", "Mg24.csv"]


# --- the layout comes from the file, not its name --------------------------

def test_sniff_recognizes_a_line_file(tmp_path):
    from src.importers.MapImporter import sniff_file_layout
    f = tmp_path / "203-S.csv"
    write_line_file(f)

    assert sniff_file_layout(f) == 'line'


def test_sniff_recognizes_a_matrix_file(tmp_path):
    """A matrix export is a bare numeric grid -- no header at all."""
    from src.importers.MapImporter import sniff_file_layout
    f = tmp_path / "S Fe57 matrix.csv"
    f.write_text("1.0,2.0,3.0\n4.0,5.0,6.0\n7.0,8.0,9.0\n")

    assert sniff_file_layout(f) == 'matrix'


def test_sniff_is_undecided_rather_than_wrong(tmp_path):
    """Anything else returns None so the caller keeps the filename heuristics,
    instead of having a guess imposed on it."""
    from src.importers.MapImporter import sniff_file_layout
    f = tmp_path / "notes.csv"
    f.write_text("some notes about this sample\nand more prose\n")

    assert sniff_file_layout(f) is None


def test_sniff_survives_a_non_utf8_file(tmp_path):
    """Real exports carry latin-1 bytes (the µ of 'Map dimensions (µm)'), and a
    decode error here would take out the whole file dialog."""
    from src.importers.MapImporter import sniff_file_layout
    f = tmp_path / "S Fe57 matrix.csv"
    f.write_bytes(b"Map dimensions (\xb5m),5120 x 5935\n1.0,2.0\n3.0,4.0\n")

    assert sniff_file_layout(f) in (None, 'matrix')     # must not raise


def test_sniff_missing_file_returns_none(tmp_path):
    from src.importers.MapImporter import sniff_file_layout
    assert sniff_file_layout(tmp_path / "nope.csv") is None


def test_sniff_declines_to_read_a_spreadsheet(tmp_path):
    """xlsx is a valid import format but not text, so there is nothing to sniff."""
    from src.importers.MapImporter import sniff_file_layout
    f = tmp_path / "S Fe57.xlsx"
    f.write_bytes(b"PK\x03\x04binary junk")

    assert sniff_file_layout(f) is None


def test_directory_layout_from_contents(tmp_path):
    from src.importers.MapImporter import sniff_directory_layout
    for n in range(1, 9):
        write_line_file(tmp_path / f"{n:02d}-S.csv")
    files = [p.name for p in tmp_path.iterdir()]

    assert sniff_directory_layout(tmp_path, files) == 'line'


def test_a_mixed_directory_is_left_undecided(tmp_path):
    """Disagreement means None -- one layout must not be imposed on a directory
    that holds two."""
    from src.importers.MapImporter import sniff_directory_layout
    for n in range(1, 5):
        write_line_file(tmp_path / f"{n:02d}-S.csv")
    for n in range(5, 9):
        (tmp_path / f"{n:02d}-S.csv").write_text("1.0,2.0\n3.0,4.0\n")
    files = [p.name for p in tmp_path.iterdir()]

    assert sniff_directory_layout(tmp_path, files) is None


def test_known_line_layout_skips_analyte_matching(parser, tmp_path):
    """The whole point of sniffing: told the layout, the parser never runs the
    element matcher, so a filename that spells an isotope cannot win."""
    files = [f"{n:02d}-75B-Large CPY.csv" for n in range(8, 14)]

    results = parser.parse_filenames("75B-Large Cpy 2", files, layout='line')

    assert all(r[2] == 'line' for r in results)
    assert [int(r[4]) for r in results] == list(range(8, 14))


# --- which token is the line number ----------------------------------------

def test_line_number_inferred_from_the_whole_listing(parser):
    """The line number is the token that is numeric in every file and distinct in
    every file; a sample name's digits are numeric too, but they repeat."""
    files = [f"{n:03d}-71A-PY-11.csv" for n in range(203, 212)]

    candidates = parser.line_number_candidates(files)

    assert candidates, "no position fitted every file"
    numbers = [int(candidates[0]['numbers'][f]) for f in files]
    assert numbers == list(range(203, 212)), "the '11' and '71' must not win"


def test_a_trailing_line_number_is_found(parser):
    """docs/source/import.rst documents both orders."""
    files = [f"RM05 - {n}.csv" for n in range(1, 10)]

    candidates = parser.line_number_candidates(files)

    assert candidates
    assert [int(candidates[0]['numbers'][f]) for f in files] == list(range(1, 10))


def test_a_constant_token_is_not_a_candidate(parser):
    files = ["01-S.csv", "02-S.csv", "03-S.csv", "04-S.csv"]

    for cand in parser.line_number_candidates(files):
        values = [int(v) for v in cand['numbers'].values()]
        assert len(set(values)) == len(values)


def test_candidates_are_ranked_by_how_unbroken_the_run_is(parser):
    """A contiguous 1..N run is a line sequence; a scattered set is something
    else that happens to be unique."""
    files = [f"{n:02d}-S-{n * 7}.csv" for n in range(1, 10)]

    candidates = parser.line_number_candidates(files)

    assert [int(candidates[0]['numbers'][f]) for f in files] == list(range(1, 10))
    assert candidates[0]['density'] >= candidates[-1]['density']


def test_position_override_is_honoured(parser):
    files = [f"{n:02d}-S-{n * 7}.csv" for n in range(1, 10)]
    candidates = parser.line_number_candidates(files)
    other = next(c for c in candidates
                 if [int(c['numbers'][f]) for f in files] != list(range(1, 10)))

    results = parser.parse_line_filenames(files, position=other['key'])

    assert [r[4] for r in results] == [other['numbers'][f] for f in files]


def test_no_workable_position_still_yields_a_line_number(parser):
    """Two files sharing a number means no position fits all of them; each file
    then falls back to its own first number rather than being dropped."""
    files = ["01-S.csv", "01-S-copy.csv", "03-S.csv"]

    results = parser.parse_line_filenames(files)

    assert all(r[2] == 'line' for r in results)
    assert [r[4] for r in results] == ['01', '01', '03']


def test_a_file_with_no_number_is_reported_not_guessed(parser):
    files = ["01-S.csv", "02-S.csv", "notes.csv"]

    results = parser.parse_line_filenames(files)

    by_name = dict(zip(files, results))
    assert by_name["notes.csv"][0] is False, "must be skipped, and visibly"
    assert by_name["notes.csv"][2] is None


# --- filenames the element matcher mistakes for isotopes -------------------

@pytest.fixture
def parser(qapp):
    """A MapImporter able to run parse_filenames (it reads isotope_info.csv)."""
    import src.app.config  # noqa: F401 -- points BASEDIR at the repo
    from PyQt6.QtWidgets import QComboBox

    imp = MapImporter.__new__(MapImporter)
    imp.comboBoxDataType = QComboBox()
    imp.comboBoxDataType.addItem("LA-ICP-MS")
    return imp


def _lines(sample, numbers):
    return [f"{n:02d}-{sample}.csv" for n in numbers]


@pytest.mark.parametrize("sample,bad_lines,isotope", [
    ("75B-Large CPY", [10, 11], "B"),      # boron, from the '75B' in the name
    ("91B-Big Py Inclusion", [10, 11], "B"),
    ("92C-LHS", [12, 13], "C"),            # carbon, from the '92C'
])
def test_sample_name_does_not_turn_lines_into_isotopes(parser, sample, bad_lines, isotope):
    """The element/mass matcher claims any leftover letter+digit pair that spells a
    real isotope, and the sample name supplies the letter. Unrecovered, these files
    are marked invalid, arrive unticked, and their scan lines vanish from the map."""
    numbers = list(range(5, 40))
    assert set(bad_lines) <= set(numbers)
    files = _lines(sample, numbers)

    results = parser.parse_filenames(sample, files)

    assert all(r[2] == 'line' for r in results), \
        f"every file is a scan line, but some parsed as {isotope} isotopes"
    assert [int(r[4]) for r in results] == numbers, "line numbers must survive intact"


def test_recovery_needs_a_clear_line_majority(parser):
    """A matrix directory must be left exactly as parsed -- the recovery is only
    licensed by the surrounding files being line scans."""
    files = ["S Fe57_ppm matrix.csv", "S Mg24_ppm matrix.csv", "S B10_ppm matrix.csv"]

    results = parser.parse_filenames("S", files)

    assert not any(r[2] == 'line' for r in results)


def test_recovered_line_numbers_do_not_collide(parser):
    """The number is the first one not already claimed, so a recovered file can't
    be given a line that another file already occupies."""
    files = _lines("75B-Large CPY", range(5, 40))

    results = parser.parse_filenames("75B-Large CPY", files)

    numbers = [r[4] for r in results]
    assert len(set(numbers)) == len(numbers)


def test_recovery_leaves_a_genuine_analyte_directory_alone(parser):
    """Two line files alongside two analytes is not a majority, so nothing is
    reinterpreted and the analytes keep their names."""
    files = ["S Fe57 matrix.csv", "S Mg24 matrix.csv", "01-S.csv", "02-S.csv"]

    results = parser.parse_filenames("S", files)

    by_name = dict(zip(files, results))
    assert by_name["S Fe57 matrix.csv"][4] == 'Fe57'
    assert by_name["S Mg24 matrix.csv"][4] == 'Mg24'


# --- the file-selection dialog ---------------------------------------------

@pytest.fixture
def stub_parent(qapp):
    """Minimal stand-in for MapImporter: FileSelectData only reads these."""
    from PyQt6.QtWidgets import QComboBox, QWidget

    class StubParent(QWidget):
        def __init__(self):
            super().__init__()
            self.root_path = "/tmp/root"
            self.standard_list = ["STDGL3"]
            self.comboBoxDataType = QComboBox(self)
            self.comboBoxDataType.addItem("LA-ICP-MS")

    return StubParent()


def _line_results(line_nos):
    # parse_filenames' 7-tuple: valid, ext, filetype, fieldtype, a1, a2, unit
    return [(True, 'csv', 'line', None, str(n), None, '') for n in line_nos]


def make_dialog(stub_parent, files, results, **kwargs):
    from src.importers.MapImporter import FileSelectData
    return FileSelectData("S", files, results, parent=stub_parent, **kwargs)


def test_line_scan_dialog_relabels_and_hides_the_analyte_columns(stub_parent):
    """Over line numbers, 'Analyte 1' / Field Type / Analyte 2 / Units are at
    best meaningless and at worst invite the user to 'correct' them."""
    d = make_dialog(stub_parent, ["203-S.csv", "204-S.csv"], _line_results([203, 204]))
    table = d.tableWidgetFileMetadata

    assert d.is_line_scan
    assert table.horizontalHeaderItem(d.LINE_COL).text() == 'Line'
    assert [c for c in range(table.columnCount()) if table.isColumnHidden(c)] == [
        d.FIELD_TYPE_COL, d.ANALYTE2_COL, d.UNITS_COL]


def test_get_data_restores_the_analyte_1_column_name(stub_parent):
    """to_dataframe() names columns after the visible headers, so the display
    relabelling must not leak into the metadata schema."""
    d = make_dialog(stub_parent, ["203-S.csv", "204-S.csv"], _line_results([203, 204]))

    data = d.get_data()

    assert 'Line' not in data.columns
    assert list(data['Analyte 1']) == ['203', '204']


def test_standards_are_unticked_but_still_listed(stub_parent):
    """The import skips them regardless; showing them unticked makes that
    visible and leaves the user able to override it."""
    files = ["201-STDGL3.csv", "203-S.csv"]
    d = make_dialog(stub_parent, files, _line_results([201, 203]))
    table = d.tableWidgetFileMetadata

    assert table.rowCount() == 2, "standards stay listed"
    checked = {table.item(r, d.FILENAME_COL).text():
               table.cellWidget(r, d.IMPORT_COL).isChecked()
               for r in range(table.rowCount())}
    assert checked == {"201-STDGL3.csv": False, "203-S.csv": True}


def test_dialog_states_what_it_will_import(stub_parent):
    files = ["201-STDGL3.csv", "203-S.csv", "204-S.csv"]
    d = make_dialog(stub_parent, files, _line_results([201, 203, 204]))

    text = d.labelSummary.text()
    assert "2 of 3" in text
    assert "1 standard" in text
    assert "⚠" not in text, "nothing was skipped, so no warning"


def test_dialog_names_the_files_it_cannot_interpret(stub_parent):
    """These used to arrive merely unticked among a hundred rows, which is how
    three directories lost scan lines without anyone noticing."""
    files = ["203-S.csv", "204-S.csv", "notes.csv"]
    results = _line_results([203, 204]) + [(False, 'csv', None, 'Analyte', None, None, None)]
    d = make_dialog(stub_parent, files, results)

    text = d.labelSummary.text()
    assert "could not be interpreted" in text
    assert "notes.csv" in text, "name it, don't just count it"
    assert "b00020" in d.labelSummary.styleSheet(), "and make it look like a problem"


def test_dialog_offers_the_line_number_position(stub_parent):
    files = [f"{n:02d}-S-{n * 7}.csv" for n in range(1, 10)]
    positions = [
        {'key': 'left:0', 'label': 'first from the start', 'density': 1.0,
         'numbers': {f: f.split('-')[0] for f in files}},
        {'key': 'right:0', 'label': 'first from the end', 'density': 0.2,
         'numbers': {f: f.split('-')[2].split('.')[0] for f in files}},
    ]
    d = make_dialog(stub_parent, files, _line_results(range(1, 10)),
                    line_positions=positions)

    assert d.comboBoxLinePosition.isEnabled()
    assert d.comboBoxLinePosition.count() == 2


def test_changing_the_position_renumbers_every_row(stub_parent):
    """One control fixes the whole directory instead of retyping a hundred cells."""
    files = [f"{n:02d}-S-{n * 7}.csv" for n in range(1, 10)]
    alt = {f: f.split('-')[2].split('.')[0] for f in files}
    positions = [
        {'key': 'left:0', 'label': 'start', 'density': 1.0,
         'numbers': {f: f.split('-')[0] for f in files}},
        {'key': 'right:0', 'label': 'end', 'density': 0.2, 'numbers': alt},
    ]
    d = make_dialog(stub_parent, files, _line_results(range(1, 10)),
                    line_positions=positions)

    d.comboBoxLinePosition.setCurrentIndex(1)

    assert d.line_position == 'right:0', "the choice is reported back for the batch"
    data = d.get_data()
    assert list(data['Analyte 1']) == [alt[f] for f in files]


def test_single_position_is_shown_but_not_offered_as_a_choice(stub_parent):
    files = ["01-S.csv", "02-S.csv"]
    positions = [{'key': 'left:0', 'label': 'start', 'density': 1.0,
                  'numbers': {f: f.split('-')[0] for f in files}}]
    d = make_dialog(stub_parent, files, _line_results([1, 2]),
                    line_positions=positions)

    assert not d.comboBoxLinePosition.isEnabled()


def test_sniffed_layout_overrides_the_filename_guess(stub_parent):
    """Told the directory is line-scan, the dialog presents it that way even if a
    filename parsed as an analyte."""
    files = ["10-75B-Large CPY.csv", "11-75B-Large CPY.csv"]
    results = [(False, 'csv', None, 'Analyte', 'B10', None, None),
               (False, 'csv', None, 'Analyte', 'B11', None, None)]
    d = make_dialog(stub_parent, files, results, layout='line')

    assert d.is_line_scan
    assert d.tableWidgetFileMetadata.horizontalHeaderItem(d.LINE_COL).text() == 'Line'


def test_matrix_dialog_is_left_alone(stub_parent):
    results = [(True, 'csv', 'matrix', 'Analyte', 'Fe57', '', ''),
               (True, 'csv', 'matrix', 'Analyte', 'Mg24', '', '')]
    d = make_dialog(stub_parent, ["S Fe57 matrix.csv", "S Mg24 matrix.csv"], results)
    table = d.tableWidgetFileMetadata

    assert not d.is_line_scan
    assert table.horizontalHeaderItem(d.LINE_COL).text() == 'Analyte 1'
    assert not any(table.isColumnHidden(c) for c in range(table.columnCount()))
    assert list(d.get_data()['Analyte 1']) == ['Fe57', 'Mg24']


def test_stacking_a_shuffled_directory_gives_increasing_xc(importer, tmp_path):
    """End to end over the two fixes that interact: sorted selection plus
    index-based coordinates must yield evenly spaced, ascending columns."""
    importer.standard_list = ["STDGL3"]
    line_nos = [205, 203, 208, 204]        # gap at 206/207 for the standards
    for n in line_nos + [206, 207]:
        name = f"{n}-STDGL3.csv" if n in (206, 207) else f"{n}-S.csv"
        write_line_file(tmp_path / name, n_rows=3)

    names = [f"{n}-S.csv" for n in line_nos] + ["206-STDGL3.csv", "207-STDGL3.csv"]
    df = _file_table(names, line_nos + [206, 207])
    selected, is_numeric = importer.select_import_files(df)
    assert is_numeric

    frames = [
        importer.read_raw_folder(k, tmp_path / row["Filename"], False, 20.0, 6.0)
        for k, (_, row) in enumerate(selected.iterrows())
    ]
    stacked = pd.concat(frames, ignore_index=True)

    xc = stacked["Xc"].drop_duplicates().to_numpy()
    assert list(xc) == [0.0, 20.0, 40.0, 60.0], "even spacing, standards' gap closed"
    assert np.all(np.diff(xc) > 0), "ascending, so the map is not column-shuffled"
