"""Live `.rst` report generation driven by the ActionRecorder.

Appends a chronological entry to the active sample's Notes (`.rst`) file for
each action recorded by `MainWindow.action_recorder` while a report session is
open, then compiles the notes to PDF when the session ends. A session spans one
Workflow run (see `Workflow.run_workflow`), so the report captures filter
settings, analyte-list changes, figures, and clustering/PCA results exactly as
they stood when each step executed - whether the step came from interactive UI
use or from `exec()`'d Blockly-generated code, since both paths fire the same
`ActionRecorder`-connected signals.

Recording is opt-in per workflow, via the "Record notes" Global Settings
Blockly block (`LameBlockly.record_notes`, defaults to `False`). A session is
always started/ended around a run, but nothing is actually written to Notes
(and no PDF is compiled) unless that block turns recording on at some point
during the run - see `_recording_enabled`.

Reuses the same note-writing primitives as the manual "Formatted Info" menu
(`MainWindow.insert_info_note`): `NotesWidget.print_info`, `to_rst_table`, and
(via `LameIO.add_figure_to_notes`) `insert_image`.
"""
from datetime import datetime


class ReportWriter:
    """Appends a live `.rst` report to the sample's Notes dock as a workflow runs.

    Parameters
    ----------
    main_window : MainWindow
        Owning main window; supplies `action_recorder`, `notes_dock` (opened on
        demand), `app_data`, and `io` (for figure export).
    """

    def __init__(self, main_window):
        self.main_window = main_window
        self._connected = False
        self._step = 0
        self._title = None
        self._header_written = False

    @property
    def notes(self):
        """The active `NotesWidget`, opening the Notes dock on first use."""
        self.main_window.open_notes()
        return self.main_window.notes_dock.notes

    def _recording_enabled(self):
        """Whether the workflow's "Record notes" Global Settings block is
        currently on for this run (see `LameBlockly.record_notes`, which
        defaults to `False` -- recording is opt-in per workflow).
        """
        workflow = getattr(self.main_window, 'workflow', None)
        lame_blockly = getattr(getattr(workflow, 'bridge', None), 'lame_blockly', None)
        return bool(getattr(lame_blockly, 'record_notes', False))

    def start_session(self, title=None):
        """Begin a report session: subscribe to the recorder.

        Nothing is written to Notes yet -- whether anything gets written at
        all depends on the workflow's "Record notes" setting, which is only
        known once its generated code starts executing (after this call
        returns), so it's checked per recorded action instead (see
        `_on_action_recorded`).

        Parameters
        ----------
        title : str, optional
            Section title for this run, by default a timestamped "Workflow run".
        """
        if self._connected:
            return
        self._title = title or f"Workflow run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self._step = 0
        self._header_written = False
        self.main_window.action_recorder.actionRecorded.connect(self._on_action_recorded)
        self._connected = True

    def end_session(self):
        """End a report session: unsubscribe, and compile to PDF only if
        recording was actually turned on and something was written.
        """
        if not self._connected:
            return
        self.main_window.action_recorder.actionRecorded.disconnect(self._on_action_recorded)
        self._connected = False
        if self._header_written:
            self.notes.save_notes_to_pdf()

    def _on_action_recorded(self, event):
        if not self._recording_enabled():
            return

        if not self._header_written:
            self.notes.print_info(f"\n\n{self._title}\n{'=' * len(self._title)}\n\n")
            self._header_written = True

        self._step += 1
        self.notes.print_info(f"\n.. rubric:: Step {self._step}: {event['label']}\n\n")

        handler = self._HANDLERS.get(event['action_type'])
        if handler:
            handler(self, event['fields'])

    def _write_sample_change(self, fields):
        self.notes.print_info(f":sample: {fields.get('sample_id')}\n\n")

    def _write_field_selection(self, fields):
        text = ''
        if fields.get('fields'):
            text += ':fields used: ' + ', '.join(fields['fields']) + '\n'
        if fields.get('norms'):
            text += ':norms: ' + ', '.join(str(n) for n in fields['norms']) + '\n'
        text += '\n'
        self.notes.print_info(text)

    def _write_filter(self, fields):
        filter_df = fields.get('filter_df')
        if filter_df is None or filter_df.empty:
            self.notes.print_info(':filters: none active\n\n')
            return
        self.notes.print_info(self.notes.to_rst_table(filter_df))

    def _write_plot(self, fields):
        metadata = fields.get('metadata', {})
        label = metadata.get('plot_name') or metadata.get('plot_type') or 'plot'
        canvas = metadata.get('figure')
        if canvas is None:
            self.notes.print_info(f":plot: {label}\n\n")
            return

        basename = f"step{self._step:03d}_{label}".replace(' ', '_')
        settings = {
            'directory': str(getattr(self.main_window.app_data, 'selected_directory', '.') or '.'),
            'basename': basename,
            'fig_type': 'png',
            'add_to_notes': True,
        }
        self.main_window.io.save_plot(canvas, save_figure_flag=True, save_data_flag=False, settings=settings)

    def _write_clustering(self, fields):
        text = f":clustering method: {fields.get('method')}\n:clusters: {fields.get('n_clusters')}\n\n"
        self.notes.print_info(text)

    def _write_dim_red(self, fields):
        text = f":dimensional reduction method: {fields.get('method')}\n:components: {fields.get('n_components')}\n\n"
        self.notes.print_info(text)

    def _write_snapshot(self, fields):
        text = f":snapshot of: {fields.get('plot_type')}\n"
        if fields.get('fields_used'):
            text += ':fields used: ' + ', '.join(fields['fields_used']) + '\n'
        text += '\n'
        self.notes.print_info(text)

    _HANDLERS = {
        'sample_change': _write_sample_change,
        'field_selection': _write_field_selection,
        'filter': _write_filter,
        'plot': _write_plot,
        'snapshot': _write_snapshot,
        'clustering': _write_clustering,
        'dim_red': _write_dim_red,
    }
