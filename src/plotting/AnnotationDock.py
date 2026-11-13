"""Annotations dock -- edit the labels and measurements drawn on a plot.

This lived in the Info dock's *Plot Info* tab, beside the plot's metadata.
That tab's siblings are read-only inspectors; the annotations table was the
only editable surface among them, and the only destructive one (Remove
deletes an annotation from every map of the sample). The Info dock also
rebuilds heavyweight tables on tab change, which is the opposite of a panel
you open briefly to move a label. So annotations get their own floating
dock, like the stoichiometric calculator.

The table is a view onto the current canvas's annotations. Where those are
kept depends on the plot:

* a **map** -- field, cluster, score, ROI or ternary map -- shares the
  sample's annotation layer, so an annotation shows on every map of that
  sample (see ``MplCanvas``'s MAP ANNOTATION LAYER section);
* a plot with **its own axes** -- scatter, histogram, ternary diagram --
  keeps its annotations to itself, since a point placed at a pair of
  concentrations has no position anywhere else.

Edits are written to the stored *record*, never to the matplotlib artist:
the sample's ``mapAnnotationsChanged`` signal then redraws every open
canvas. That is what lets a position be typed into the table and move the
annotation on the map.
"""
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QMainWindow, QTableWidget,
    QTableWidgetItem, QToolBar, QVBoxLayout, QWidget,
)

from lame_core.CustomWidgets import CustomAction, CustomDockWidget
from lame_core.UITheme import default_font
from src.control.FieldLogic import FieldLogicUI
from src.control.Logger import auto_log_methods, log
from src.plotting.CustomMplCanvas import MplCanvas


@auto_log_methods(logger_key='Plot')
class AnnotationDock(CustomDockWidget, FieldLogicUI):
    """Floating panel listing and editing the current plot's annotations."""

    #: Table columns. X2/Y2 apply to a distance line's second endpoint and
    #: are left blank, and not editable, for a text annotation.
    COLUMNS = ['Type', 'Text', 'X1', 'Y1', 'X2', 'Y2', 'Size', 'Width',
               'Color', 'Visible']
    COL_TYPE, COL_TEXT, COL_X1, COL_Y1, COL_X2, COL_Y2, \
        COL_SIZE, COL_WIDTH, COL_COLOR, COL_VISIBLE = range(10)

    _MAP_SCOPE = "Shown on every map of this sample."
    _PLOT_SCOPE = "Shown on this plot only."
    _NO_SCOPE = "No plot to annotate."

    def __init__(self, ui=None):
        self.ui = ui
        self.logger_key = "Plot"
        # CustomDockWidget.__init__ calls self.show(). When the parent
        # window is already visible -- i.e. every time the dock is opened
        # from the toolbar rather than built at startup -- Qt delivers the
        # QShowEvent synchronously, before setupUI() has created a single
        # widget. showEvent must therefore not touch the UI until this flag
        # says it exists. (The same crash was found in StoichiometryDock.)
        self._ui_ready = False
        #: The canvas whose annotationsUpdated this table is listening to.
        self._annotation_source = None

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(ui)

        self.setWindowTitle("Annotations")
        self.setObjectName("AnnotationDock")

        self.setupUI()
        self.connect_widgets()
        self._ui_ready = True
        self.update_annotation_table()
        self.setGeometry(QRect(0, 0, 820, 320))

    # -------------------------------------
    # FieldLogicUI plumbing
    # -------------------------------------
    @property
    def app_data(self):
        """Delegate to ui.app_data so FieldLogicUI methods work correctly."""
        return self.ui.app_data

    @property
    def data(self):
        """Access current sample data without caching a reference."""
        if hasattr(self.ui, "app_data"):
            return self.ui.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored -- data is always derived from ui.app_data.current_data."""
        pass

    # -------------------------------------
    # UI construction
    # -------------------------------------
    def setupUI(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)

        self.toolbar = QToolBar("Annotation Toolbar", self)
        self.toolbar.setIconSize(QSize(24, 24))

        self.action_select_all = CustomAction(
            text="Select All",
            light_icon_unchecked="icon-select-all-64.svg",
            dark_icon_unchecked="icon-select-all-dark-64.svg",
            parent=self,
        )
        self.action_select_all.setToolTip("Select every annotation")

        self.action_show_hide = CustomAction(
            text="Show/Hide",
            light_icon_unchecked="icon-show-hide-64.svg",
            light_icon_checked="icon-show-64.svg",
            parent=self,
        )
        self.action_show_hide.setToolTip(
            "Show or hide the selected annotations.\\n"
            "Hiding leaves them out of an exported figure without deleting them."
        )

        self.action_remove = CustomAction(
            text="Remove",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=self,
        )
        self.action_remove.setToolTip("Delete the selected annotations")

        self.toolbar.addAction(self.action_select_all)
        self.toolbar.addAction(self.action_show_hide)
        self.toolbar.addAction(self.action_remove)
        layout.addWidget(self.toolbar)

        # Says which annotations are on screen before Remove is used on
        # them -- deleting from the shared map layer reaches every map.
        self.scope_label = QLabel(self._NO_SCOPE, parent=container)
        self.scope_label.setFont(default_font())
        self.scope_label.setWordWrap(True)
        layout.addWidget(self.scope_label)

        self.annotations_table = QTableWidget(0, len(self.COLUMNS), container)
        self.annotations_table.setObjectName("annotations_table")
        self.annotations_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.annotations_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked)
        self.annotations_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.annotations_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_TEXT, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.annotations_table)

        self.setWidget(container)

    def connect_widgets(self):
        self.action_select_all.triggered.connect(self.select_all_annotations)
        self.action_show_hide.triggered.connect(self.toggle_selected_visibility)
        self.action_remove.triggered.connect(self.remove_selected_annotations)

    def showEvent(self, event):
        """Refresh on open -- the plot may have changed while hidden."""
        super().showEvent(event)
        if self._ui_ready:
            self.update_annotation_table()

    # -------------------------------------
    # Which annotations are being shown
    # -------------------------------------
    def current_canvas(self):
        """The ``MplCanvas`` the table is showing, or None.

        Read from ``ui.plot_info``, the one MainWindow rewrites on every
        plot.
        """
        plot_info = getattr(self.ui, 'plot_info', None)
        if not plot_info:
            return None
        figure = plot_info.get('figure')
        return figure if isinstance(figure, MplCanvas) else None

    def _follow_canvas(self, canvas):
        """Refresh the table when `canvas` gains an annotation.

        Without this the table only catches up on the next plot update, so
        a measurement just drawn would not appear in the list until the
        user changed something else. Only one canvas is followed at a time;
        the previous one's connection is dropped so the table is not
        rebuilt by a figure it is no longer showing.
        """
        previous = self._annotation_source
        if previous is canvas:
            return
        if previous is not None:
            try:
                previous.annotationsUpdated.disconnect(self._on_annotations_updated)
            except (RuntimeError, TypeError):
                pass
        self._annotation_source = canvas
        if canvas is not None:
            canvas.annotationsUpdated.connect(self._on_annotations_updated)

    def _on_annotations_updated(self, _records):
        """Slot for the canvas's ``annotationsUpdated``."""
        self.update_annotation_table()

    def _scope_text(self, canvas):
        if canvas is None:
            return self._NO_SCOPE
        return {'map': self._MAP_SCOPE,
                'plot': self._PLOT_SCOPE}.get(canvas.annotation_scope(), self._NO_SCOPE)

    # -------------------------------------
    # The table
    # -------------------------------------
    def update_annotation_table(self):
        """Rebuild the table from the current plot's annotations.

        Empties it when there is no plot, rather than leaving the previous
        one's annotations on screen where an edit would land on the wrong
        figure.
        """
        if not self._ui_ready:
            return
        canvas = self.current_canvas()
        self._follow_canvas(canvas)
        self.scope_label.setText(self._scope_text(canvas))

        # Writing the cells fires itemChanged for each one, and this method
        # reconnects the handler every time it runs -- without dropping the
        # previous connection, one edit would be applied as many times as
        # the table had been rebuilt.
        self.annotations_table.blockSignals(True)
        try:
            self.annotations_table.itemChanged.disconnect(self.update_annotation_from_table)
        except TypeError:
            pass

        annotations = canvas.annotations if canvas is not None else []
        self.annotations_table.setRowCount(len(annotations))
        for row, ann in enumerate(annotations):
            self._fill_row(row, ann)

        self.annotations_table.blockSignals(False)
        self.annotations_table.itemChanged.connect(self.update_annotation_from_table)

    def _fill_row(self, row, ann):
        """Write one annotation's cells."""
        from src.app.InfoViewer import create_checkbox, create_color_button

        is_line = ann['Type'] == 'line'

        type_item = QTableWidgetItem(ann['Type'])
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        # The row's identity, so an edit still lands on the right
        # annotation after the list is reordered or one is removed.
        type_item.setData(Qt.ItemDataRole.UserRole, ann.get('annotation_id'))
        self.annotations_table.setItem(row, self.COL_TYPE, type_item)

        label = ann['Text']
        if isinstance(label, dict):      # a placement dict, not a string
            label = label.get('Text', '')
        self.annotations_table.setItem(row, self.COL_TEXT, QTableWidgetItem(str(label)))

        for column, value in (
            (self.COL_X1, ann.get('X1')),
            (self.COL_Y1, ann.get('Y1')),
            (self.COL_X2, ann.get('X2') if is_line else None),
            (self.COL_Y2, ann.get('Y2') if is_line else None),
            (self.COL_SIZE, ann.get('Size')),
            (self.COL_WIDTH, ann.get('Width') if is_line else None),
        ):
            item = QTableWidgetItem('' if value is None else f"{float(value):g}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                  | Qt.AlignmentFlag.AlignVCenter)
            if value is None:
                # A text annotation has no second endpoint and no line
                # width; an empty cell that cannot be typed into says so
                # more plainly than one that silently does nothing.
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.annotations_table.setItem(row, column, item)

        self.annotations_table.setCellWidget(row, self.COL_COLOR, create_color_button(
            color=ann["Color"], callback=self.change_annotation_color, key=row))
        self.annotations_table.setCellWidget(row, self.COL_VISIBLE, create_checkbox(
            is_checked=ann["Visible"], callback=self.toggle_annotation, key=row))

    def _annotation_at(self, row):
        """``(canvas, annotation)`` for a table row, or ``(canvas, None)``."""
        canvas = self.current_canvas()
        if canvas is None or row >= len(canvas.annotations):
            return canvas, None
        return canvas, canvas.annotations[row]

    def _artists(self, annotation):
        """Every matplotlib artist drawing one annotation."""
        found = []
        for key in ('object', 'text_object'):
            artist = annotation.get(key)
            if artist is None:
                continue
            found.extend(artist if isinstance(artist, list) else [artist])
        return found

    def _apply_annotation_change(self, canvas, annotation, record_updates,
                                 apply_to_artists):
        """Write a change to the stored record, or to this figure alone.

        An annotation with an ``annotation_id`` is backed by a record, and
        updating it redraws every canvas showing it. One without has only
        its artists, which are changed in place.
        """
        annotation_id = annotation.get('annotation_id')
        if annotation_id and canvas.is_annotatable():
            canvas.update_stored_annotation(annotation_id, record_updates)
            return
        apply_to_artists()
        canvas.draw()

    # -------------------------------------
    # Edits
    # -------------------------------------
    def toggle_annotation(self, state, index):
        """Show or hide one annotation.

        Hiding keeps it: the point is to leave it out of one figure and
        bring it back for the next.
        """
        canvas, annotation = self._annotation_at(index)
        if annotation is None:
            return
        visible = bool(state)
        annotation['Visible'] = visible

        def on_artists():
            for artist in self._artists(annotation):
                artist.set_visible(visible)

        self._apply_annotation_change(canvas, annotation, {'visible': visible},
                                      on_artists)

    def change_annotation_color(self, color, index):
        """Update an annotation's colour."""
        canvas, annotation = self._annotation_at(index)
        if annotation is None:
            return
        annotation['Color'] = color

        def on_artists():
            for artist in self._artists(annotation):
                artist.set_color(color)

        style = dict(annotation.get('style', {}))
        style['color'] = color
        self._apply_annotation_change(canvas, annotation, {'style': style},
                                      on_artists)

    def update_annotation_from_table(self, item):
        """Apply an edited cell: text, position, font size or line width.

        A position change is why the record is edited rather than the
        artist -- moving a line means moving its label too, and the label's
        offset is recomputed per figure, so redrawing from the record is
        the only thing that gets it right.
        """
        row, column = item.row(), item.column()
        canvas, annotation = self._annotation_at(row)
        if annotation is None:
            return

        if column in (self.COL_X1, self.COL_Y1, self.COL_X2, self.COL_Y2):
            self._move_annotation(canvas, annotation, column, item.text())
            return

        style = dict(annotation.get('style', {}))
        updates = {}

        if column == self.COL_TEXT:
            new_text = item.text()
            annotation['Text'] = new_text
            updates['text'] = new_text

            def artist_change():
                for artist in self._artists(annotation):
                    if hasattr(artist, 'set_text'):
                        artist.set_text(new_text)
        elif column in (self.COL_SIZE, self.COL_WIDTH):
            value = self._as_float(item.text())
            if value is None:
                self.update_annotation_table()   # put the old value back
                return
            if column == self.COL_SIZE:
                annotation['Size'] = value
                style['font_size'] = value
                setter = 'set_fontsize'
            else:
                annotation['Width'] = value
                style['line_width'] = value
                setter = 'set_linewidth'
            updates['style'] = style

            def artist_change():
                for artist in self._artists(annotation):
                    if hasattr(artist, setter):
                        getattr(artist, setter)(value)
        else:
            return

        self._apply_annotation_change(canvas, annotation, updates, artist_change)

    def _move_annotation(self, canvas, annotation, column, text):
        """Write one edited coordinate back as a new ``position``."""
        value = self._as_float(text)
        if value is None:
            self.update_annotation_table()
            return

        endpoints = [[annotation['X1'], annotation['Y1']]]
        if annotation['Type'] == 'line':
            endpoints.append([annotation['X2'], annotation['Y2']])

        point, axis = {
            self.COL_X1: (0, 0), self.COL_Y1: (0, 1),
            self.COL_X2: (1, 0), self.COL_Y2: (1, 1),
        }[column]
        if point >= len(endpoints):
            return
        endpoints[point][axis] = value

        annotation_id = annotation.get('annotation_id')
        if not (annotation_id and canvas.is_annotatable()):
            # Nothing stored to move; a canvas-only annotation stays where
            # it was drawn, so put the typed value back.
            self.update_annotation_table()
            return
        canvas.update_stored_annotation(
            annotation_id, {'position': [[float(x), float(y)] for x, y in endpoints]})

    def _as_float(self, text):
        """``float(text)``, or None if it is not a number.

        An ordinary method rather than a staticmethod: ``auto_log_methods``
        rewraps the class's callables and does not preserve the descriptor.
        """
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    # -------------------------------------
    # Toolbar actions
    # -------------------------------------
    def select_all_annotations(self):
        """Select every row of the table."""
        self.annotations_table.selectAll()

    def _selected_rows(self):
        """Table rows currently selected, in order."""
        model = self.annotations_table.selectionModel()
        if model is None:
            return []
        return sorted({index.row() for index in model.selectedIndexes()})

    def toggle_selected_visibility(self):
        """Show or hide the selected annotations.

        Hides them if any are currently shown, otherwise shows them all --
        one button for both directions, and a mixed selection resolves to
        the state the user can see is not yet uniform.
        """
        canvas = self.current_canvas()
        rows = self._selected_rows()
        if canvas is None or not rows:
            return
        visible_now = [canvas.annotations[r].get('Visible', True)
                       for r in rows if r < len(canvas.annotations)]
        new_state = not any(visible_now)
        for row in rows:
            self.toggle_annotation(2 if new_state else 0, row)
        self.update_annotation_table()

    def remove_selected_annotations(self):
        """Delete the selected annotations.

        On a map this takes them off every map of the sample -- hiding, not
        removing, is what leaves one out of a single figure.
        """
        canvas = self.current_canvas()
        rows = self._selected_rows()
        if canvas is None or not rows:
            return

        # Resolve the annotations before touching anything: removing one
        # renumbers the rows underneath it.
        doomed = [canvas.annotations[r] for r in rows if r < len(canvas.annotations)]
        for annotation in doomed:
            annotation_id = annotation.get('annotation_id')
            if annotation_id and canvas.is_annotatable():
                canvas.remove_stored_annotation(annotation_id)
            else:
                for artist in self._artists(annotation):
                    try:
                        artist.remove()
                    except (ValueError, AttributeError):
                        pass
                if annotation in canvas.annotations:
                    canvas.annotations.remove(annotation)
        canvas.draw()
        self.update_annotation_table()
