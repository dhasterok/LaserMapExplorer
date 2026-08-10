"""Structured capture of user actions for the Workflow and reporting tools.

This complements the free-text debug Logger (``src.common.Logger``) with a
structured, replayable record of *what changed* in the app - sample changes,
analyte/field selection, filter settings, figures, and clustering/PCA runs.

One :class:`ActionRecorder` instance (owned by ``MainWindow``) is fed by
signals from the relevant classes (``AppData.sampleChanged``,
``AppData.fieldSelectionChanged``, ``FilterTab.filtersApplied``,
``PlotRegistry.plotRegistered``, ``ClusterPage.clusteringComputed``,
``DimensionalReductionPage.dimRedComputed``) and in turn drives two
independent consumers via its ``actionRecorded`` signal:

- the Workflow dock (``src.app.Workflow``), which can push matching events
  live into the open Blockly workspace as blocks when capture is enabled, or
  on demand via an "Add to Workflow" action;
- the report writer (``src.app.ReportWriter``), which appends each event to
  the sample's ``.rst`` notes file while a workflow run is in progress.

Not every action type has a corresponding Blockly block yet - see
``build_block_state``. Those events still flow to the report but are skipped
for live block insertion.
"""
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal


def build_block_state(action_type, fields):
    """Build a Blockly block-state dict for the given action type, if supported.

    Only action types with a simple, statically-fielded Blockly block are
    handled here. Compound blocks that populate themselves asynchronously
    from the running app (e.g. ``plot_clustering``, ``dimensional_reduction``)
    and actions with no corresponding block yet (filters, ad-hoc analyte
    selection) return None - callers should treat those as report-only.

    Parameters
    ----------
    action_type : str
        Category key, matching the ``action_type`` passed to `ActionRecorder.record`.
    fields : dict
        Event fields captured by `ActionRecorder.record`.

    Returns
    -------
    dict or None
        A Blockly block-state object (``{"type": ..., "fields": {...}}``)
        suitable for ``Blockly.serialization.blocks.append`` via the
        `addBlockToWorkspace` JS function, or None if this action type isn't
        (yet) representable as a block.
    """
    if action_type == 'sample_change':
        return {'type': 'select_samples', 'fields': {'SAMPLE_IDS': fields.get('sample_id', '')}}
    return None


class ActionRecorder(QObject):
    """Captures structured action events and notifies subscribers.

    Parameters
    ----------
    parent : QObject, optional
        Owning object, typically ``MainWindow``.
    """

    actionRecorded = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.capture_enabled = False

    def record(self, action_type, label, fields=None, force=False):
        """Record a structured action event and notify subscribers.

        Parameters
        ----------
        action_type : str
            Short category key, e.g. 'sample_change', 'field_selection',
            'filter', 'clustering', 'dim_red', 'plot'.
        label : str
            Human-readable description used in the report and status messages.
        fields : dict, optional
            Data describing the action (parameters, selections, table contents).
        force : bool, optional
            If True, this event should be pushed into the Blockly workspace as
            a block even if auto-capture is off (the "Add to Workflow" path),
            provided a block mapping exists for `action_type` (see
            `build_block_state`). By default False.

        Returns
        -------
        dict
            The recorded event, also emitted via `actionRecorded`.
        """
        fields = fields or {}
        event = {
            'timestamp': datetime.now(),
            'action_type': action_type,
            'label': label,
            'fields': fields,
            'block_state': build_block_state(action_type, fields),
            'force': force,
        }
        self.actionRecorded.emit(event)
        return event

    def set_capture_enabled(self, enabled):
        """Toggle whether recorded events should be pushed live into the Blockly workspace.

        Parameters
        ----------
        enabled : bool
            New capture state.
        """
        self.capture_enabled = bool(enabled)
