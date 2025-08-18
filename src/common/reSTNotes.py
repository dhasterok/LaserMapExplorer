from pathlib import Path
import re, subprocess
from PyQt6.QtCore import ( Qt, QTimer, QSize, QUrl )
from PyQt6.QtWidgets import (
        QMainWindow, QMessageBox, QFileDialog, QWidget, QVBoxLayout, QFormLayout, QSizePolicy,
        QLabel, QDialog, QDialogButtonBox, QToolBar, QSplitter, QTabWidget,
    )
from PyQt6.QtGui import ( QTextCursor, QIcon, QCursor, QDoubleValidator )
from PyQt6.QtWebEngineWidgets import QWebEngineView
from datetime import datetime
import numpy as np
import pandas as pd   
from rst2pdf.createpdf import RstToPdf
from docutils.core import publish_string, publish_file
import src.common.format as fmt
from src.common.CodingWidgets import CodeEditor
from src.common.CustomWidgets import CustomLineEdit, CustomAction, CustomActionMenu, CustomDockWidget
from src.common.SearchTool import SearchWidget
from src.common.Logger import LoggerConfig, auto_log_methods, log

BASE_PATH = Path(__file__).parents[2] 
ICON_PATH = BASE_PATH / "resources/icons"

def convert_rst_to_html(rst_path: Path) -> Path:
    """Converts an rst file to html given a file path.
    
    Parameters
    ----------
    rst_path : Posix.path
        Path to rst file

    Returns
    -------
    html_path : str
        Path to compiled html file as a str.
    """
    html_path = rst_path.with_suffix('.html')
    publish_file(
        source_path=str(rst_path),
        destination_path=str(html_path),
        writer_name='html'
    )
    return html_path

# -------------------------------
# Notes functions
# -------------------------------
class NotesFormatter:
    def __init__(self):
        pass

    def format(self, data) -> str:
        if isinstance(data, dict):
            return self.format_dict(data)
        elif isinstance(data, list):
            return self.format_list(data)
        elif isinstance(data, str):
            return self.format_string(data)
        elif data is None:
            return '*None*'
        elif isinstance(data, bool):
            return f'``{data}``'
        else:
            return str(data)

    def format_dict(self, d: dict, indent: int = 0) -> str:
        lines = []
        prefix = ' ' * indent
        for key, value in d.items():
            key_str = f"{prefix}:{key}:"
            value_str = self.format(value)
            if isinstance(value, (dict, list)):
                lines.append(f"{key_str}\n{value_str}")
            else:
                lines.append(f"{key_str} {value_str}")
        return '\n'.join(lines)

    def format_list(self, items: list, indent: int = 0) -> str:
        lines = []
        prefix = ' ' * indent
        for item in items:
            item_str = self.format(item)
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}‣\n{item_str}")
            else:
                lines.append(f"{prefix}‣ {item_str}")
        return '\n'.join(lines)

    def format_string(self, text: str) -> str:
        # You can optionally escape special reST characters here
        return text

# -------------------------------
# Notes functions
# -------------------------------
class NotesMainWindow(QMainWindow):
    """A reSTructuredText editor built with PyQt6

    This is the main window environment for the reST Notes editor.

    :seealso: NotesWidget
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("reST Editor")

        self.notes = NotesWidget(ui=self)
        self.setCentralWidget(self.notes)


class NotesDock(CustomDockWidget):
    """A dock that can be used to take notes in ReStructured Text (ReST) including formatted output.

    Notes are automatically saved at regular intervals and upon close of the dock.  The
    toolbar includes functions that format selected text into ReST format.  There are also
    options for preformatted output of data and analyses.  Tables, and figures can be
    added, though not viewed in the notes until compiled.  With rst2pdf installed, the
    notes will be compiled into a PDF file.  Equations can be added in LaTeX format for nice
    formatting.

    Parameters
    ----------
    parent : MainWindow, optional
        Parent UI, by default None
    filename : str, optional
        Filename for saving notes, by default None
    title : str, optional
        Title for Notes dockwidget, by default 'Notes'

    Raises
    ------
    TypeError
        Parent must be an instance of QMainWindow.
    """
    def __init__(self, parent: QMainWindow=None, filename: str|Path|None=None, title: str='reST Editor'):
        super().__init__(parent=parent)
        self.setWindowTitle(title)

        self.notes = NotesWidget(ui=self, filename=filename)

        self.setWidget(self.notes)

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)
        self.setFloating(True)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

class NotesTab(QWidget):
    def __init__(self, tab_widget: QTabWidget, filename: str|Path|None=None, title: str="reST Editor"):
        if not tab_widget or not isinstance(tab_widget, QTabWidget):
            raise TypeError("Parent must be an instance of QTabWidget.") 
        super().__init__()
        self.setObjectName("tab_reSTNotes")

        self.tab_widget = tab_widget

        self.notes = NotesWidget(ui=tab_widget, filename=filename)

        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)

        tab_layout.addWidget(self.notes)

        self.setLayout(tab_layout)

        notes_icon = QIcon(str(ICON_PATH / "icon-notes-64.svg"))
        self.tab_widget.addTab(self, notes_icon, title)

@auto_log_methods("Notes")
class NotesWidget(QWidget):
    def __init__(self, ui=None, filename: str|Path|None=None):
        super().__init__()
        self.logger_key = 'Notes'

        self.ui = ui

        self._notes_file = None
        self.options = {'MaxColumns': None, 'MaxVariance': 95}

        self.setupUI()
        self.connect_widgets()

        # autosave notes
        self.autosaveTimer = QTimer()
        self.autosaveTimer.setInterval(300000)

        if self.notes_file is not None:
            try:
                self.autosaveTimer.timeout.connect(self.notes_file)
            except:
                QMessageBox.warning(self, "Warning", f"Autosave could not save notes to file ({self.notes_file}).")

        # initialize notes file and pdf preview
        self.notes_file = filename
        self.toggle_preview_notes()

        if filename:
            self.notes_file = filename

    def setupUI(self):

        # Create the layout within parent.tabWorkflow
        widget_layout = QVBoxLayout()   

        # Create toolbar
        self.toolbar = QToolBar("Notes Toolbar", self)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.action_wrap = CustomAction(
            text="Wrap", 
            light_icon_unchecked="icon-word-wrap-64.svg",
            dark_icon_unchecked="icon-word-wrap-dark-64.svg",
            parent=self.toolbar)
        self.action_wrap.setCheckable(True)
        self.action_wrap.setChecked(True)

        # header button and menu
        header_menu_items = [
            ('H1', lambda: self.format_header('H1')),
            ('H2', lambda: self.format_header('H2')),
            ('H3', lambda: self.format_header('H3')),
            ('H4', lambda: self.format_header('H4')),
            ('H5', lambda: self.format_header('H5')),
            ('H6', lambda: self.format_header('H6')),
        ]
        self.action_header = CustomActionMenu(
            "Header",
            header_menu_items,
            light_icon_unchecked="icon-heading-64.svg",
            dark_icon_unchecked="icon-heading-dark-64.svg",
        )
        self.action_header.setToolTip("Format a heading")

        # bold button
        self.action_bold = CustomAction(
            text="Bold",
            light_icon_unchecked="icon-bold-64.svg",
            dark_icon_unchecked="icon-bold-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_bold.setToolTip("Bold selected text")

        # italic button
        self.action_italic = CustomAction(
            text="Italic",
            light_icon_unchecked="icon-italics-64.svg",
            dark_icon_unchecked="icon-italics-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_italic.setToolTip("Italicize selected text")

        # literal button
        self.action_literal = CustomAction(
            text="Literal",
            light_icon_unchecked="icon-literal-64.svg",
            dark_icon_unchecked="icon-literal-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_literal.setToolTip("Display selected text as a literal")

        # superscript button
        self.action_superscript = CustomAction(
            text="Superscript",
            light_icon_unchecked="icon-superscript-64.svg",
            dark_icon_unchecked="icon-superscript-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_superscript.setToolTip("Superscript selected text")

        # subscript button
        self.action_subscript = CustomAction(
            text="Subscript",
            light_icon_unchecked="icon-subscript-64.svg",
            dark_icon_unchecked="icon-subscript-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_subscript.setToolTip("Subscript selected text")

        self.toolbar.addSeparator()

        # bulleted list button
        bullet_menu_items = [
            ('*', lambda: self.format_list('bullet', '*')),
            ('+', lambda: self.format_list('bullet', '+')),
            ('-', lambda: self.format_list('bullet', '-')),
            ('•', lambda: self.format_list('bullet', '•')),
            ('‣', lambda: self.format_list('bullet', '‣')),
            ('⁃', lambda: self.format_list('bullet', '⁃')),
        ]
        self.action_bullet = CustomActionMenu(
            text="Bullet",
            menu_items=bullet_menu_items,
            light_icon_unchecked="icon-bullet-list-64.svg",
            dark_icon_unchecked="icon-bullet-list-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_bullet.setToolTip("Format bulleted list")

        # numbered list button
        self.action_enumerate = CustomAction(
            text="Enumerate",
            light_icon_unchecked="icon-numbered-list-64.svg",
            dark_icon_unchecked="icon-numbered-list-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_enumerate.setToolTip("Format enumerated list")

        # citation button
        self.action_cite = CustomAction(
            text="Reference",
            light_icon_unchecked="icon-cite-64.svg",
            dark_icon_unchecked="icon-cite-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_cite.setToolTip("Insert citation or footnote")

        # hyperlink button
        self.action_hyperlink = CustomAction(
            text="Hyperlink",
            light_icon_unchecked="icon-hyperlink-64.svg",
            dark_icon_unchecked="icon-hyperlink-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_hyperlink.setToolTip("Insert hyperlink")

        # math button and menu
        math_menu_items = [
            ('Inline math', lambda: self.format_text('inline math')),
            ('Display math', lambda: self.format_text('display math')),
            # ('Calculated field', [
            #     (eq_name, callback) for eq_name, callback in self.ui.calc_dict.items()
            # ])
        ]
        self.action_math = CustomActionMenu(
            "Equation",
            math_menu_items,
            light_icon_unchecked="icon-equation-64.svg",
            dark_icon_unchecked="icon-equation-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_math.setToolTip("Insert equation")

        # image button
        self.action_image = CustomAction(
            text="Figure",
            light_icon_unchecked="icon-image-dark-64.svg",
            dark_icon_unchecked="icon-image-64.svg",
            parent=self.toolbar,
        )
        self.action_image.setToolTip("Insert figure")

        # info button and menu
        self._info_menu_items = []
        # info_menu_items = [
        #     ('Sample info', lambda: self.insert_info('sample info')),
        #     ('List analytes used', lambda: self.insert_info('analytes')),
        #     ('Current plot details', lambda: self.insert_info('plot info')),
        #     ('Filter table', lambda: self.insert_info('filters')),
        #     ('PCA results', lambda: self.insert_info('pca results')),
        #     ('Cluster results', lambda: self.insert_info('cluster results'))
        # ]
        self.action_info = CustomActionMenu(
            "Formatted Info",
            self._info_menu_items,
            light_icon_unchecked="icon-formatted-output-64.svg",
            dark_icon_unchecked="icon-formatted-output-dark-64.svg",
            parent=self.toolbar
        )
        self.action_info.setToolTip("Insert formatted info")

        # options button, opens options dialog
        self.action_options = CustomAction(
            text="Options",
            light_icon_unchecked="icon-gear-64.svg",
            dark_icon_unchecked="icon-gear-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_options.setToolTip("Options")

        # export as rst2pdf button
        self.action_export = CustomActionMenu(
            "Save PDF",
            self._info_menu_items,
            light_icon_unchecked="icon-pdf-64.svg",
            parent=self.toolbar
        )
        self.action_export.setToolTip("Save notes as PDF (must have docutils and rst2pdf installed)")

        self.action_search = CustomAction(
            text="Open Search",
            light_icon_unchecked="icon-search-64.svg",
            dark_icon_unchecked="icon-search-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_search.setCheckable(True)
        self.action_search.setChecked(False)

        # pdf previewer
        self.action_preview_pdf = CustomAction(
            text="View PDF",
            light_icon_unchecked="icon-show-hide-64.svg",
            light_icon_checked="icon-show-64.svg",
            parent=self.toolbar,
        )
        self.action_preview_pdf.setToolTip("Preview PDF")
        self.action_preview_pdf.setCheckable(True)
        self.action_preview_pdf.setChecked(False)
        self.action_preview_pdf.setEnabled(True)

        self.action_recompile = CustomAction(
            text="Refresh",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_recompile.setToolTip("Recompile document")

        # Create Text Edit region for ReST Notes
        self.editor = CodeEditor()
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editor.setMaximumSize(QSize(524287, 524287))
        self.editor.viewport().setProperty("cursor", QCursor(Qt.CursorShape.IBeamCursor))

        settings_icon = QIcon(str(ICON_PATH / "icon-gear-edit-64.svg"))
        self.action_editor = CustomAction(
            text="Editor Settings",
            light_icon_unchecked="icon-gear-edit-64.svg",
            dark_icon_unchecked="icon-gear-edit-dark-64.svg",
            parent=self.toolbar,
        )
        self.action_editor.setIcon(settings_icon)
        self.action_editor.setToolTip("Editor Settings")


        # add buttons to toolbar
        self.toolbar.addAction(self.action_header)
        self.toolbar.addAction(self.action_bold)
        self.toolbar.addAction(self.action_italic)
        self.toolbar.addAction(self.action_literal)
        self.toolbar.addAction(self.action_superscript)
        self.toolbar.addAction(self.action_subscript)
        self.toolbar.addAction(self.action_bullet)
        self.toolbar.addAction(self.action_enumerate)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_cite)
        self.toolbar.addAction(self.action_hyperlink)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_math)
        self.toolbar.addAction(self.action_image)
        self.toolbar.addAction(self.action_options)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_search)
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.action_export)
        self.toolbar.addAction(self.action_recompile)
        self.toolbar.addAction(self.action_preview_pdf)
        self.toolbar.addAction(self.action_editor)

        # Create search
        self.searchbar = QToolBar("Search and Replace", parent=self)

        self.search_widget = SearchWidget(self.editor, self, enable_replace=True, realtime=False)
        self.searchbar.addWidget(self.search_widget)
        self.searchbar.hide()

        # Create a QWebEngineView
        self.notes_browser = QWebEngineView()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Add the web view to the layout
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.notes_browser)
        self.splitter.setSizes([190,190])

        self.status_label = QLabel()
        self.status_label.setFixedHeight(22)

        widget_layout.addWidget(self.toolbar)
        widget_layout.addWidget(self.searchbar)
        widget_layout.addWidget(self.splitter)
        widget_layout.addWidget(self.status_label)

        # Set layout to the container
        self.setLayout(widget_layout)

    def connect_widgets(self):
        self.action_wrap.triggered.connect(lambda checked: self.editor.setWordWrap(checked))
        self.action_bold.triggered.connect(lambda: self.format_text('bold'))
        self.action_italic.triggered.connect(lambda: self.format_text('italic'))
        self.action_literal.triggered.connect(lambda: self.format_text('literal'))
        self.action_superscript.triggered.connect(lambda: self.format_text('superscript'))
        self.action_subscript.triggered.connect(lambda: self.format_text('subscript'))
        self.action_enumerate.triggered.connect(lambda: self.format_list('enumerate'))
        self.action_cite.triggered.connect(lambda: self.format_text('citation'))
        self.action_hyperlink.triggered.connect(lambda: self.format_text('hyperlink'))
        self.action_image.triggered.connect(self.insert_image)
        self.action_options.triggered.connect(self.open_note_options)
        self.action_export.triggered.connect(lambda _: self.save_notes_to_pdf()) # compile rst
        self.action_search.triggered.connect(lambda checked: self.searchbar.setVisible(checked))
        self.action_preview_pdf.triggered.connect(lambda _: self.toggle_preview_notes()) # compile rst
        self.action_recompile.triggered.connect(lambda _: self.update_notes_view())
        self.action_export.triggered.connect(lambda: self.action_preview_pdf.setEnabled(True)) # compile rst
        self.action_editor.triggered.connect(self.editor.open_settings_dialog)


    @property
    def notes_file(self):
        """Path : File name associated with the current sample. When set, the current file will be
        saved before changing files. If the new file name is not None, an autosave timer will be set.
        """   
        return self._notes_file

    @notes_file.setter
    def notes_file(self, filename):
        new_path = Path(filename) if filename else None

        # no need to do anything if the filename is the same
        if self._notes_file == new_path:
            return

        # save current file and stop autosave
        if self._notes_file is not None:
            self.save_notes_file()
            self.autosaveTimer.stop()

        # update filename
        self._notes_file = new_path

        if new_path is None:
            self.status_label.setText("FILE: load sample to display file")
            return
        else:
            self.status_label.setText(f"FILE: {str(new_path)}")

            # generate the HTML preview
            self.update_notes_view()

        # start autosave
        try:
            self.autosaveTimer.timeout.connect(self.save_notes_file)
        except Exception:
            self.status_label.setText(f"WARNING: Autoscave could not save notes to file (str{new_path})")
            QMessageBox.warning(
                self,
                "Warning",
                f"Autosave could not save notes to file ({new_path})."
            )

        # Load file if it exists
        if new_path.exists():
            try:
                file_name = new_path.name
                text = new_path.read_text()
                if text == '':
                    self.status_label.setText(f"File ({file_name}) is empty.")
                else:
                    self.editor.setText(new_path.read_text())
                    self.status_label.setText(f"File ({file_name}) loaded successfully.")
            except Exception:
                file_name = new_path.name
                self.status_label.setText(f"Cannot read {file_name}")

        self.autosaveTimer.start()


    @property
    def info_menu_items(self):
        """
        list[tuple[str, Callable]]: The list of tuples defining the info menu items.

        Each tuple should contain two elements:
            - label (str): The text label to display in the menu.
            - callback (Callable): The function to be called when the menu item is triggered.

        If `self._info_menu_items` is empty, then the action is removed from the toolbar.

        This property reflects the menu items shown under the "Formatted Info" button.
        """
        return self._info_menu_items

    @info_menu_items.setter
    def info_menu_items(self, new_menu_items):
        if new_menu_items == self._info_menu_items:
            return

        self._info_menu_items = new_menu_items

        if self.action_info:
            self.action_info.update_menu(new_menu_items)

            if self._info_menu_items and self.action_info not in self.toolbar.actions():
                self.toolbar.insertAction(self.action_options, self.action_info)
            elif not self._info_menu_items and self.action_info in self.toolbar.actions():
                self.toolbar.removeAction(self.action_info)

    def toggleWrap(self, state):
        """Toggles word wrapping in text editing widget.
        
        Parameters
        ----------
        state : bool
            `True` turns wrapping on
        """
        self.editor.setWordWrap(state == Qt.CheckState.Checked)

    def add_info_menu_item(self, label: str, callback):
        """
        Add a single menu item to the info menu.

        If `self.action_info` is not on the toolbar, then it is added.

        Parameters
        ----------
        label : str
            The menu label to add
        callback : Callable
            The menu callback
        """

        item = (label, callback)
        self._info_menu_items.append(item)
        if self.action_info:
            self.action_info.add_menu_item(label, callback)

            if self.action_info not in self.toolbar.actions():
                self.toolbar.insertAction(self.action_options, self.action_info)


    def remove_info_menu_item(self, label):
        """Remove a single item from the info menu.

        If `self._info_menu_items` is empty after removing the last menu item, then the action
        is removed from the toolbar.

        Parameters
        ----------
        label : str
            Text label of menu item to remove.
        """
        item_to_remove = next((item for item in self._info_menu_items if item[0] == label), None)
        if item_to_remove:
            self._info_menu_items.remove(item_to_remove)
            if self.action_info:
                self.action_info.remove_menu_item(item_to_remove)

                if not self._info_menu_items and self.action_info in self.toolbar.actions():
                    self.toolbar.removeAction(self.action_info)


    def update_equation_menu(self):
        pass
        # new_items = [
        #         (eq_name, lambda: self.write_equation(equation)) for eq_name, equation in self.ui.calc_dict.items()
        #     ]
        # self.action_math.update_submenu("Calculated field", new_items)

    def write_equation(self, equation):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)

        equation_text = equation
        new_text = f"\n.. math::\n  {equation_text}\n"

        cursor.insertText(new_text)

    def add_menu(self, menu_items, menu_obj):
        """Adds items to a context menu

        Parameters
        ----------
        menu_items : list
            Names of the menu text to add
        menu_obj : menu_obj
            context menu object
        """
        for item in menu_items:
            action = menu_obj.addAction(item)
            action.setIconVisibleInMenu(False)

    def save_notes_file(self):
        """Saves notes to an *.rst file

        Autosaves the notes to a file ``[sample_id].rst``
        """
        if self.notes_file is None:
            return

        self.status_label.setText('Saving notes...')

        # write file
        with open(self.notes_file,'w') as file:
            file.write(str(self.editor.toPlainText()))

        self.status_label.setText(f"File: {str(self.notes_file)} saved.")

    def _insert_image(self, filenames, halign, width, alt_text, caption):
        for fn in filenames:
            self.editor.insertPlainText(f"\n\n.. figure:: {fn}\n")
            self.editor.insertPlainText(f"    :align: {halign}\n")
            self.editor.insertPlainText(f"    :alt: {alt_text}\n")
            self.editor.insertPlainText(f"    :width: {width}mm\n")
            self.editor.insertPlainText(f"\n    {caption}\n")

    def insert_image(self, filename=None, halign="center", width=150, alt_text=None, caption=None):
        """Adds a generic placeholder image to notes

        Uses the reStructured Text figure format

        Parameters
        ----------
        filenames : list of str
            A list of filenames to add images 
        """
        if filename is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("Image Files (*.jpg *.png *.tif)")
            filename = []

            if dialog.exec():
                filename = dialog.selectedFiles()
            else:
                return

        if isinstance(filename,str):
            filename = list(filename)
        elif not isinstance(filename,list):
            QMessageBox.warning(self, "Error", f"Filenames must be a str or list.")


        if not isinstance(width,(int, float)):
            QMessageBox.warning(self, "Error", "Page width should be a number.")
            return
        elif width > 203:
            QMessageBox.warning(self, "Warning", "Page width exceeds typical printable page width.")

        if halign not in ["left", "center", "right"]:
            QMessageBox.warning(self, "Error", f"Unknown figure justification {halign}")
            return

        if alt_text is None:
            alt_text = "Alternate text goes here\n"

        if caption is None:
            caption = "Caption goes here\n"

        self._insert_image(filename, halign, width, alt_text, caption)


    def format_header(self, level):
        """Formats a selected line as a header

        Places a symbol consistent with the heading level below the selected text line.

        Parameters
        ----------
        level : str
            The header level is determined from a context menu associated with ``MainWindow.toolButtonNotesHeading``
        """
        # define symbols for heading level
        match level:
            case 'H1':
                symbol = '*'
            case 'H2':
                symbol = '='
            case 'H3':
                symbol = '-'
            case 'H4':
                symbol = '~'
            case 'H5':
                symbol = '^'
            case 'H6':
                symbol = '+'

        # Get the current text cursor
        cursor = self.editor.textCursor()

        # Get the current line number and position
        line_number = cursor.blockNumber()

        # Move the cursor to the end of the selected line
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)

        #cursor.movePosition(QTextCursor.NextBlock)

        # Insert the line of "="
        cursor.insertText('\n' + f'{symbol}' * (cursor.block().length() - 1))

    def format_list(self, list_type, list_style=None):
        """Formats a list in the text, either bulleted or enumerated

        Formats selected text as bulleted or enumerated in restructured text format.

        Parameters
        ----------
        list_type: str
            Type of formatting, ``bullet`` or ``enumerate``
        list_style : str
            Style or symbol for formatting list
        """

        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()

        match list_type:
            case 'bullet':
                symbol = list_style
            case 'enumerate':
                symbol = '#'

        #code to make bulleted list here
        # Split the selected text into lines
        lines = selected_text.split('\u2029')  # QPlainTextEdit uses Unicode Paragraph Separator for newlines

        # Create the formatted list
        formatted_list = "\n".join(f"{symbol} {line.strip()}" for line in lines if line.strip())

        # Replace the selected text with the formatted list
        cursor.beginEditBlock()  # Group the operations as a single undo step
        cursor.insertText(formatted_list)
        cursor.endEditBlock()
        

    def format_text(self, style):
        """Formats the text

        Formats selected text as bold, italic or literal in restructured text format.

        Parameters
        ----------
        style : str
            Type of formatting, options include:  ``bold``, ``italic``, ``literal``,
            ``subscript``, ``superscript``, ``inline math``, ``display math``,
            ``citation``, and ``hyperlink``
        """
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()

        match style:
            case 'italic':
                modified_text = f"*{selected_text}*"
            case 'bold':
                modified_text = f"**{selected_text}**"
            case 'literal':
                modified_text = f"``{selected_text}``"
            case 'subscript':
                modified_text = f":sub:`{selected_text}`"
            case 'superscript':
                modified_text = f":sup:`{selected_text}`"
            case 'inline math':
                modified_text = f":math:`{selected_text}`"
            case 'display math':
                modified_text = f"\n.. math::\n  {selected_text}\n"
            case 'citation':
                self.format_citation(cursor, selected_text)
                return
            case 'hyperlink':
                self.format_hyperlink(cursor, selected_text)
                return

        cursor.insertText(modified_text)

    def format_citation(self, cursor, key):
        """Formats and appends citation under References section.

        Creates a citation at the current location, using the selected text as the citation key
        and then creates an empty referenence in the reference list a the bottom of the document.
        Creates an empty reference at the current location and an empty citation at the end of
        the reference list if no text is selected.  If no Reference section exists, it will be
        created.

        Parameters
        ----------
        cursor : QCursor
            defined by ``self.editor.textCursor()``
        key : str
            selected text to be used for the citation key
        """        
        cursor = self.editor.textCursor()
        key = cursor.selectedText()

        # Define the citation text
        if key == '':
            key_text = "[KEY]_"
            citation_text = ".. [KEY] citation"
        else:
            key_text = f"[{key}]_"
            citation_text = f".. [{key}] citation"

        cursor.insertText(key_text)

        # Search for "References" section
        # Get the entire document text
        full_text = self.editor.toPlainText()
        
        # Locate the "References" section
        references_index = full_text.find("References\n==========")
        if references_index != -1:
            # "References" section exists, move cursor to the end of it
            cursor.setPosition(references_index)
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)  # Move to the block after "References"

            # Move to the last non-empty block in the "References" section
            while cursor.block().text().strip() != "" and not cursor.atEnd():
                cursor.movePosition(QTextCursor.MoveOperation.NextBlock)

            # Insert the citation at the end of the "References" section
            cursor.insertBlock()
            cursor.insertText(f"{citation_text}\n")
        else:
            # "References" section doesn't exist, create it at the end
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertBlock()
            cursor.insertText("\nReferences\n==========\n")
            cursor.insertBlock()
            cursor.insertText(f"{citation_text}\n")

    def format_hyperlink(self, cursor, key='', url='https://www.example.com'):
        """Formats and inserts a hyperlink definition.

        Ensures the hyperlink is placed above the References section if it exists,
        or at the end of the document if it doesn't.

        Parameters
        ----------
        cursor : QCursor
            defined by ``self.editor.textCursor()``
        key : str
            selected text to be used for the citation key
        url : str
            inserts the url into the hyperlink
        """

        # Define the hyperlink text
        if key == '':
            reference_text = "`hyperlink`_"
            hyperlink_text = f".. _`hyperlink`: {url}\n"
        else:
            reference_text = f"`{key}`_"
            hyperlink_text = f".. _`{key}`: {url}\n"

        cursor.insertText(reference_text)

        # Search for "References" section
        plain_text = self.editor.toPlainText()
        references_section = "References\n=========="
        hyperlink_text = f".. _{key}: {url}"

        # Check if "References" exists
        if references_section in plain_text:
            # Locate "References" and insert above it
            references_start = plain_text.index(references_section)
            before_references = plain_text[:references_start].rstrip()
            after_references = plain_text[references_start:]

            updated_text = (
                f"{before_references}\n\n{hyperlink_text}\n\n{after_references.lstrip()}"
            )
        else:
            # Add "References" at the end if it doesn't exist
            updated_text = f"{plain_text.rstrip()}\n\n{references_section}\n\n{hyperlink_text}\n"

        self.editor.setPlainText(updated_text)

    def print_info(self, info_data):
        formatter = NotesFormatter()
        output_rst = formatter.format(info_data)

        cursor = self.editor.textCursor()
        cursor.insertText(output_rst)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def add_table_note(self, matrix, row_labels=None, col_labels=None):
        """Convert matrix to restructured text

        Adds a table to the note tab, including row lables and column headers.

        Parameters
        ----------
        matrix : 2D array
            Data for printing
        row_labels : str, optional
            Row labels
        col_labels : str, optional
            Column header
        """
        if matrix is None:
            return ''

        #matrix = self.convert_to_string(matrix)
        matrix = fmt.oround_matrix(matrix, order=3)

        # Add row labels to the matrix if provided
        if row_labels is not None:
            matrix = np.column_stack((row_labels, matrix))
            if col_labels is not None:
                col_labels = np.insert(col_labels,0,' ')

        # Add column headings to the matrix if provided
        if col_labels is not None:
            matrix = np.vstack((col_labels, matrix))

        # Calculate column widths
        col_widths = np.max([np.vectorize(len)(matrix.astype(str))], axis=0)

        # Generate the reST table
        table = ""
        for i, row in enumerate(matrix):
            table += "|"
            for col, width in zip(row, col_widths[i,:]):
                table += f" {col:{int(width)}} |"
            table += "\n"

        self.editor.insertPlainText(table)


    # CSV tables
    # .. csv-table:: Table Title
    #     :file: CSV file path and name
    #     :widths: 30, 70       # percentage widths
    #     :header-rows: 1

    #def convert_to_string(self, array):
    #    return np.array2string(array, formatter={'all': lambda x: f'{x:02f}'})

    def save_notes_to_pdf(self):
        """Converts notes *.rst file to *.pdf"""
        # save note file first to ensure all changes have been recorded
        if self.notes_file is None:
            self.status_label.setText("WARNING: Cannot save pdf, no notes file found.")
            return

        self.save_notes_file()

        try:
            rst_path = Path(self.notes_file)
            pdf_file_path = rst_path.with_suffix('.pdf')

            # Read the .rst file content
            rst_content = rst_path.read_text(encoding='utf-8')  # specify encoding for robustness

            # Generate PDF content
            pdf = RstToPdf()
            pdf_content = pdf.createPdf(text=rst_content, output=str(pdf_file_path))  # ensure output path is a string

            self.status_label.setText(f"Saved: {str(pdf_file_path)}")

        except Exception as e:
            self.status_label.setText(f"ERROR: Could not save notes to pdf ({pdf_file_path})")
            QMessageBox.warning(self, "Error", f"Could not save to pdf.\n{str(e)}")

    def to_rst_table(self, df):
        """Converts a Pandas DataFrame to a reST table string.

        Parameters
        ----------
        df : pandas.DataFrame
            Data table to convert to restructured text

        Returns
        -------
        str
            Table in restructred text format
        """
        def rst_row(row):
            return ' '.join(f'{str(item):^10}' for item in row)

        # Extracting column names and data as lists
        columns = df.columns.tolist()
        data = df.values.tolist()
        
        # Creating reST table components
        header = rst_row(columns)
        separator = ' '.join(['-'*10]*len(columns))
        rows = [rst_row(row) for row in data]
        
        # Combining components into the reST table format
        rst_table = '\n'.join([header, separator] + rows)
        return rst_table

    def closeEvent(self, event):
        """Override closeEvent to execute custom logic when the dock widget closes."""
        print("Dock widget is closing!")

        self.save_notes_file()
        self.autosaveTimer.stop()

        # close dock
        super().closeEvent(event)

    # Main Function to Open the Dialog
    def open_note_options(self):
        """
        Opens the note options dialog.
        """
        dialog = NoteOptionsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            columns, variance = dialog.get_options()
            if columns:
                print(f"Number of Columns: {columns}")
            if variance:
                print(f"Cumulative Variance: {variance}%")

    def toggle_preview_notes(self):
        """Shows/hides the PDF preview browser"""
        if self.action_preview_pdf.isChecked():
            # show previewer
            self.notes_browser.show()
            self.notes_browser.setMinimumWidth(int(self.editor.width() / 2))

            self.update_notes_view()
        else:
            # hide previewer
            self.notes_browser.hide()

    def update_notes_view(self):
        """Compiles the .rst file to HTML and displays it in QWebEngineView."""
        if not self.notes_file:
            self.status_label.setText("ERROR: no notes file found, cannot render preview.")
            return

        try:
            self.save_notes_file()
        except Exception as e:
            self.status_label.setText(f"ERROR: Failed to save {str(self.notes_file)}")
            return
        
        html_file = convert_rst_to_html(self.notes_file)
        if not html_file.exists():
            self.status_label.setText(f"WARNING: HTML not generated: {html_file}")
            return

        self.notes_browser.setUrl(QUrl.fromLocalFile(str(html_file)))
        self.status_label.setText(f"Rendered: {str(html_file)}")
        log(f"Rendered: {str(html_file)}", "NOTES")

        if self.action_export.isChecked():
            self.save_notes_to_pdf()

    # def update_pdf(self):
    #     """Opens the compiled PDF, ``self.notes_file``, for viewing"""
    #     if not self.notes_file:
    #         return

    #     pdf_file = self.notes_file.with_suffix('.pdf')  # changes .rst to .pdf

    #     if not pdf_file.exists():
    #         print(f"PDF not found at: {pdf_file}")
    #         return

    #     subprocess.run(["open", str(pdf_file)])

    #     self.notes_browser.setUrl(QUrl.fromLocalFile(str(pdf_file)))
    #     print(self.notes_file)

class NoteOptionsDialog(QDialog):
    """Opens when ``Notes.action_options`` is triggered.

    Opens a dialog to change options associated with Notes formatting options.

    Parameters
    ----------
    parent : Notes, optional
        Notes class used to call this dialog, by default None
    """        
    def __init__(self, parent=None):
        super(NoteOptionsDialog, self).__init__(parent)
        self.setWindowTitle("Note Options")

        self.ui = parent

        if parent is None:
            self.options = {'MaxColumns': None, 'MaxVariance': 95}
        else:
            self.options = parent.options.copy()
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Form layout for options
        form_layout = QFormLayout()
        
        # Number of columns input
        self.columns_input = CustomLineEdit(parent=self)
        validator = QDoubleValidator()
        validator.setBottom(0)
        validator.setDecimals(0)
        self.columns_input.setValidator(validator)
        self.columns_input.setPlaceholderText("")
        self.columns_input.setToolTip("Limit table output")
        self.columns_input.value = self.options['MaxColumns']
        self.columns_input.editingFinished.connect(self.update_maxcolumns)
        form_layout.addRow("Max columns:", self.columns_input)
        
        # Cumulative variance input
        self.variance_input = CustomLineEdit(parent=self, validator=QDoubleValidator(0,100,0))
        self.variance_input.setPlaceholderText("")
        self.variance_input.setToolTip("Add columns with cumulative explained variance up to the percentage entered here")
        self.variance_input.value = self.options['MaxVariance']
        self.variance_input.editingFinished.connect(self.update_maxvariance)
        form_layout.addRow("Cumulative variance (%):", self.variance_input)
        
        # Add form layout to main layout
        main_layout.addLayout(form_layout)
        
        # Dialog buttons (Accept and Cancel)
        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.dialog_buttons.accepted.connect(self.update_options_dict)
        self.dialog_buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.dialog_buttons)
        
        # Set layout
        self.setLayout(main_layout)

    def update_maxcolumns(self):
        """Updates maximum number of columns option"""        
        self.options['MaxColumns'] = self.columns_input.value

    def update_maxvariance(self):
        """Updates maximum variance option"""        
        self.options['MaxVariance'] = self.variance_input.value

    def update_options_dict(self):
        """Updates notes option dictionary upon accept """        
        if self.ui is not None:
            self.ui.options = self.options
        self.accept()

    def get_options(self):
        """
        Returns the options set in the dialog.
        """
        columns = self.columns_input.text()
        variance = self.variance_input.text()
        return columns, variance