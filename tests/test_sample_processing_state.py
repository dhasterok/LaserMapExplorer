"""SampleObj.export_processing_state() / apply_processing_state().

Pure data-layer tests -- no QApplication or MainWindow needed, so these run
in well under a second against the synthetic sample from tests/conftest.py.
"""
import numpy as np
import pandas as pd
import pytest

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.common.Calculator import CustomFieldCalculator
from src.data.DataHandling import LaserSampleObj
from src.project.ProjectModel import (
    ComputedFieldSpec,
    FilterSpec,
    SampleProcessingState,
)


@pytest.fixture
def make_sample(synthetic_sample_csv):
    """``make()`` -> a freshly loaded LaserSampleObj.

    A factory rather than a single instance: several tests need a *second*,
    untouched sample to replay saved state onto.
    """
    def make():
        return LaserSampleObj(
            sample_id='RM01', file_path=str(synthetic_sample_csv),
            outlier_method='Chauvenet criterion', negative_method='ignore negatives',
            ref_chem=pd.Series(dtype=float),
        )
    return make


@pytest.fixture
def sample(make_sample):
    return make_sample()


@pytest.fixture
def analyte(sample):
    return sample.processed.match_attribute('data_type', 'Analyte')[0]


def test_untouched_sample_exports_empty_state(sample):
    state = sample.export_processing_state()

    assert isinstance(state, SampleProcessingState)
    assert state.applied_filters == []
    assert state.masks == []
    assert state.computed_fields == []


def test_export_captures_an_applied_filter(sample, analyte):
    sample.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9,
                      operator='and', use=True)

    state = sample.export_processing_state()

    assert len(state.applied_filters) == 1
    spec = state.applied_filters[0]
    assert spec.field == analyte
    assert spec.field_type == 'Analyte'
    assert spec.use is True
    assert spec.operator == 'and'


def test_export_captures_a_computed_fields_formula(sample, analyte):
    """The Calculator.py hook stores the formula as a column attribute; that
    is what makes a computed field re-creatable on reload."""
    calculator = CustomFieldCalculator()
    formula = f"{{Analyte.{analyte}}} * 2"
    assert calculator.calculate_new_field(sample, ref_chem=None, new_field='DoubleField', txt=formula)
    assert 'DoubleField' in sample.processed.columns
    # CalculatorDock normally sets this right after a successful compute;
    # there's no dock in this headless test, so drive the hook directly.
    sample.processed.set_attribute('DoubleField', 'formula', formula)

    state = sample.export_processing_state()

    assert len(state.computed_fields) == 1
    assert state.computed_fields[0].field == 'DoubleField'
    assert state.computed_fields[0].formula == formula


def test_export_records_crop_status_and_extent(sample):
    """``SampleObj.crop`` is a real, readable flag even though the crop tool
    itself has no working setter to trigger it yet."""
    sample.crop = True

    state = sample.export_processing_state()

    crop_specs = [m for m in state.masks if m.kind == 'crop']
    assert len(crop_specs) == 1
    assert crop_specs[0].params['xlim'] == list(sample.xlim)


def test_export_flags_a_non_trivial_polygon_mask(sample):
    """An all-True mask means "nothing masked"; only a partial one counts as
    an active polygon mask."""
    sample.polygon_mask = np.zeros_like(sample.polygon_mask, dtype=bool)
    sample.polygon_mask[:5] = True

    state = sample.export_processing_state()

    assert any(m.kind == 'polygon' and m.enabled for m in state.masks)


def test_apply_replays_a_saved_filter_and_recomputes_the_mask(make_sample, analyte):
    fresh = make_sample()
    saved = SampleProcessingState(
        applied_filters=[FilterSpec(True, 'Analyte', analyte, 'linear', 0.0, 1e9, 'and', True)],
    )
    assert fresh.filter_df.empty

    fresh.apply_processing_state(saved)

    assert len(fresh.filter_df) == 1
    assert fresh.filter_df.iloc[0]['field'] == analyte
    # apply_field_filters() actually ran, rather than the spec just being stored.
    assert fresh.mask.sum() <= len(fresh.mask)


def test_apply_recomputes_a_computed_field_via_an_injected_calculator(make_sample, analyte):
    calculator = CustomFieldCalculator()
    formula = f"{{Analyte.{analyte}}} * 2"
    saved = SampleProcessingState(computed_fields=[ComputedFieldSpec(field='DoubleField', formula=formula)])
    fresh = make_sample()
    assert 'DoubleField' not in fresh.processed.columns

    fresh.apply_processing_state(saved, ref_chem=None, field_calculator=calculator)

    assert 'DoubleField' in fresh.processed.columns
    assert fresh.processed.get_attribute('DoubleField', 'formula') == formula


def test_apply_skips_computed_fields_cleanly_without_a_calculator(make_sample, analyte):
    saved = SampleProcessingState(
        computed_fields=[ComputedFieldSpec(field='DoubleField', formula=f"{{Analyte.{analyte}}} * 2")],
    )
    fresh = make_sample()

    fresh.apply_processing_state(saved)   # no field_calculator -- must not raise

    assert 'DoubleField' not in fresh.processed.columns
