"""Mineral-formula outputs as ordinary, usable fields.

``StoichiometryDock`` writes its results back as ``'Stoichiometry'``-typed
columns (``Grt_almandine``, ``Grt_dominant``, ...). ``get_map_data`` served
them and ``SampleObj._compute_filter_mask`` evaluated them correctly, but
``FieldLogicUI.update_field_type_combobox`` never offered the type, so the
Filter tab could not see them -- and since filtering is how a region of
interest is defined (``SampleObj.add_roi`` stores the filter definition,
not a frozen mask), that also meant end-member fractions could not become
the ROIs that TEC and radar plots colour by.

Also covers the dock's own construction crash:
``CustomDockWidget.__init__`` calls ``self.show()``, so with an already
visible parent Qt delivers a ``QShowEvent`` *before* ``setupUI()`` has made
any widgets, and ``showEvent``'s ``_refresh_region_columns()`` died on the
not-yet-existent ``filter_combobox``.
"""
import sys

import numpy as np
import pytest
from PyQt6.QtWidgets import QMainWindow

from src.control.FieldLogic import FieldLogicUI
from src.data.DataHandling import LaserSampleObj

MEMBERS = ['pyrope', 'almandine', 'spessartine', 'grossular', 'andradite',
           'uvarovite']
ALMANDINE_CODE = MEMBERS.index('almandine') + 1


class ComboStub:
    """Just the QComboBox surface ``update_field_type_combobox`` touches."""

    def __init__(self):
        self.items = []

    def clear(self):
        self.items = []

    def addItems(self, items):
        self.items += list(items)

    def currentText(self):
        return self.items[0] if self.items else ''


class FieldLogicStub(FieldLogicUI):
    """``update_field_type_combobox`` reads only ``self.data``."""

    def __init__(self, data):
        self.data = data


@pytest.fixture
def garnet_sample(sample_factory, qapp):
    """``(sample, dominant)`` -- a sample carrying a stoichiometry run's output."""
    sample = LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore',
    )
    fractions = np.random.default_rng(1).random((len(sample.processed), len(MEMBERS))) * 100
    dominant = np.argmax(fractions, axis=1) + 1.0
    sample.add_columns(
        'Stoichiometry',
        [f'Grt_{m}' for m in MEMBERS] + ['Grt_dominant'],
        np.column_stack([fractions, dominant]),
    )
    return sample, dominant


def field_types_for(data, **kwargs):
    box = ComboStub()
    FieldLogicStub(data).update_field_type_combobox(box, addNone=False, **kwargs)
    return box.items


# --- the field type is offered ----------------------------------------------

def test_stoichiometry_is_offered_once_columns_exist(garnet_sample):
    sample, _ = garnet_sample
    assert 'Stoichiometry' in field_types_for(sample)


def test_the_fields_under_the_type_are_the_mineral_columns(garnet_sample):
    """Offering the type is only useful if the field box beneath it fills --
    ``get_field_list`` reads the same grouping."""
    sample, _ = garnet_sample
    grouped = sample.processed.get_attribute_dict('data_type')
    assert set(grouped['Stoichiometry']) == (
        {f'Grt_{m}' for m in MEMBERS} | {'Grt_dominant'}
    )


def test_stoichiometry_is_absent_before_anything_is_computed(sample_factory, qapp):
    """The list is built from the data types actually present, so a sample
    with no mineral formulae must not advertise the type."""
    sample = LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore',
    )
    assert 'Stoichiometry' not in field_types_for(sample)


def test_no_sample_is_not_an_error(garnet_sample):
    """The docks build before any sample is loaded."""
    assert field_types_for(None) == []


def test_the_processed_frame_is_accepted_as_well_as_the_sample(garnet_sample):
    """``CalculatorDock.data`` is the AttributeDataFrame while every other
    dock's is the SampleObj -- assuming one shape is why the calculator's
    field-type box stayed empty."""
    sample, _ = garnet_sample
    assert 'Stoichiometry' in field_types_for(sample.processed)


def test_colour_by_lists_are_unchanged(garnet_sample):
    """TEC/radar/correlation/histogram group by discrete membership, so they
    take Cluster and ROI only -- a continuous end-member fraction is not a
    grouping."""
    sample, _ = garnet_sample
    assert field_types_for(sample, plot_type='TEC') == []


# --- and it actually filters -------------------------------------------------

def test_filtering_on_an_end_member_code_selects_the_right_pixels(garnet_sample):
    sample, dominant = garnet_sample
    sample.add_filter('Stoichiometry', 'Grt_dominant',
                      ALMANDINE_CODE - 0.5, ALMANDINE_CODE + 0.5)
    sample.apply_field_filters()

    assert sample.filter_mask.sum() == (dominant == ALMANDINE_CODE).sum()


def test_an_end_member_filter_commits_to_a_region(garnet_sample):
    """``add_roi`` stores the filter definition, so the region re-evaluates
    from the stoichiometry column rather than a snapshot."""
    sample, dominant = garnet_sample
    sample.add_filter('Stoichiometry', 'Grt_dominant',
                      ALMANDINE_CODE - 0.5, ALMANDINE_CODE + 0.5)
    sample.apply_field_filters()
    roi_id = sample.add_roi(name='almandine', color='#cc3333')

    assert (sample.processed['ROI'] == roi_id).sum() == (dominant == ALMANDINE_CODE).sum()
    # ...and now TEC has something to colour by.
    assert field_types_for(sample, plot_type='TEC') == ['ROI']


@pytest.mark.parametrize("code,member", list(enumerate(MEMBERS, start=1)))
def test_every_end_member_can_become_its_own_region(garnet_sample, code, member):
    sample, dominant = garnet_sample
    sample.add_filter('Stoichiometry', 'Grt_dominant', code - 0.5, code + 0.5)
    sample.apply_field_filters()

    assert sample.filter_mask.sum() == (dominant == code).sum()


# --- the dock opens ----------------------------------------------------------

def test_the_dock_survives_being_shown_during_construction(qapp):
    """``CustomDockWidget.__init__``'s ``self.show()`` fires showEvent before
    setupUI whenever the parent is already on screen -- which is every time
    the dock is opened from the toolbar.

    Qt does not propagate an exception raised inside an event handler, so the
    failure has to be caught at ``sys.excepthook``: without the guard the
    constructor still 'succeeds' while printing
    ``AttributeError: 'StoichiometryDock' object has no attribute
    'filter_combobox'``.
    """
    from src.stoichiometry.dock import StoichiometryDock

    escaped = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda exc_type, exc, tb: escaped.append(exc)

    parent = QMainWindow()
    parent.show()
    try:
        dock = StoichiometryDock(parent)
        dock.show()          # the real one, which must still refresh
    finally:
        sys.excepthook = previous_hook
        parent.close()

    assert escaped == [], f"exception escaped an event handler: {escaped}"
    assert dock._ui_ready is True
    assert dock.filter_combobox.count() >= 1
