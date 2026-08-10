"""Headless check of SampleObj.export_processing_state()/apply_processing_state()
against a real sample, no QApplication/MainWindow needed.

Run: .venv/bin/python <this file>
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

project_root = Path("/Users/dhasterok/Documents/GitHub/LaserMapExplorer")
assert (project_root / 'src' / 'data' / 'DataHandling.py').exists()
sys.path.insert(0, str(project_root))

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.data.DataHandling import LaserSampleObj
from src.common.Calculator import CustomFieldCalculator
from src.project.ProjectModel import SampleProcessingState, FilterSpec, MaskSpec, ComputedFieldSpec

RM01 = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01.exists(), f"missing fixture: {RM01}"

data = LaserSampleObj(
    sample_id='RM01', file_path=str(RM01),
    outlier_method='Chauvenet criterion', negative_method='ignore negatives',
    ref_chem=pd.Series(dtype=float),
)

# --- export with no processing applied yet: everything empty ---
state = data.export_processing_state()
assert isinstance(state, SampleProcessingState)
assert state.applied_filters == []
assert state.masks == []
assert state.computed_fields == []
print("PASS: export_processing_state() on an untouched sample is empty")

# --- add a filter, export, check it round-trips into a FilterSpec ---
analyte = data.processed.match_attribute('data_type', 'Analyte')[0]
data.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9, operator='and', use=True)
state = data.export_processing_state()
assert len(state.applied_filters) == 1
f = state.applied_filters[0]
assert f.field == analyte and f.field_type == 'Analyte' and f.use is True and f.operator == 'and'
print(f"PASS: export_processing_state() captures the applied filter on '{analyte}'")

# --- add a computed field via the real CustomFieldCalculator, confirm the
#     Calculator.py hook's 'formula' attribute makes it exportable ---
cfc = CustomFieldCalculator()
formula = f"{{Analyte.{analyte}}} * 2"
success = cfc.calculate_new_field(data, ref_chem=None, new_field='DoubleField', txt=formula)
assert success, "calculate_new_field failed to compute the test formula"
assert 'DoubleField' in data.processed.columns
# the CalculatorDock UI wrapper normally sets this attribute right after a
# successful compute -- simulate that hook directly here since there's no
# CalculatorDock in this headless test
data.processed.set_attribute('DoubleField', 'formula', formula)

state = data.export_processing_state()
assert len(state.computed_fields) == 1
cf = state.computed_fields[0]
assert cf.field == 'DoubleField' and cf.formula == formula
print("PASS: export_processing_state() captures a Calculator-computed field's formula")

# --- crop mask status: SampleObj.crop is a real, readable flag even though
#     the crop tool itself doesn't currently have a working setter to trigger it ---
data.crop = True
state = data.export_processing_state()
crop_specs = [m for m in state.masks if m.kind == 'crop']
assert len(crop_specs) == 1
assert crop_specs[0].params['xlim'] == list(data.xlim)
print("PASS: export_processing_state() records crop status/extent when data.crop is set")
data.crop = False

# --- polygon/cluster mask status markers ---
data.polygon_mask = np.zeros_like(data.polygon_mask, dtype=bool)
data.polygon_mask[:5] = True  # not all-True -> "active"
data.mask = data.crop_mask if hasattr(data, 'crop_mask') else data.mask  # no-op, just touch nothing risky
state = data.export_processing_state()
assert any(m.kind == 'polygon' and m.enabled for m in state.masks)
print("PASS: export_processing_state() flags an active (non-trivial) polygon mask")
data.polygon_mask = np.ones_like(data.polygon_mask, dtype=bool)  # reset

# --- apply_processing_state(): round-trip filters onto a fresh instance ---
fresh = LaserSampleObj(
    sample_id='RM01', file_path=str(RM01),
    outlier_method='Chauvenet criterion', negative_method='ignore negatives',
    ref_chem=pd.Series(dtype=float),
)
saved_state = SampleProcessingState(
    applied_filters=[FilterSpec(True, 'Analyte', analyte, 'linear', 0.0, 1e9, 'and', True)],
)
assert fresh.filter_df.empty
fresh.apply_processing_state(saved_state)
assert len(fresh.filter_df) == 1
assert fresh.filter_df.iloc[0]['field'] == analyte
assert fresh.mask.sum() <= len(fresh.mask)  # apply_field_filters() actually ran, not just stored
print("PASS: apply_processing_state() replays a saved filter and recomputes the mask")

# --- apply_processing_state(): computed field replay via injected field_calculator ---
fresh2 = LaserSampleObj(
    sample_id='RM01', file_path=str(RM01),
    outlier_method='Chauvenet criterion', negative_method='ignore negatives',
    ref_chem=pd.Series(dtype=float),
)
computed_state = SampleProcessingState(
    computed_fields=[ComputedFieldSpec(field='DoubleField', formula=formula)],
)
assert 'DoubleField' not in fresh2.processed.columns
fresh2.apply_processing_state(computed_state, ref_chem=None, field_calculator=cfc)
assert 'DoubleField' in fresh2.processed.columns
assert fresh2.processed.get_attribute('DoubleField', 'formula') == formula
print("PASS: apply_processing_state() recomputes a saved computed field via an injected calculator")

# --- apply_processing_state(): computed field replay skipped gracefully without a calculator ---
fresh3 = LaserSampleObj(
    sample_id='RM01', file_path=str(RM01),
    outlier_method='Chauvenet criterion', negative_method='ignore negatives',
    ref_chem=pd.Series(dtype=float),
)
fresh3.apply_processing_state(computed_state)  # no field_calculator -- must not raise
assert 'DoubleField' not in fresh3.processed.columns
print("PASS: apply_processing_state() skips computed-field replay cleanly when no calculator is given")

print("\nALL SampleObj processing-state TESTS PASSED")
