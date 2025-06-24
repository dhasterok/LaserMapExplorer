import re, os
from PyQt6.QtCore import ( Qt, QTimer, QSize, QUrl )
from PyQt6.QtWidgets import (
        QMainWindow, QMessageBox, QFileDialog, QWidget, QVBoxLayout, QFormLayout, QTextEdit, QSizePolicy,
        QLabel, QDialog, QDialogButtonBox, QToolBar, QHBoxLayout
    )
from PyQt6.QtGui import ( QFont, QTextCursor, QIcon, QCursor, QDoubleValidator, QAction )
from PyQt6.QtWebEngineWidgets import QWebEngineView
from datetime import datetime
import numpy as np
import pandas as pd   
from rst2pdf.createpdf import RstToPdf
from docutils.core import publish_string
import src.common.format as fmt
from src.common.CustomWidgets import CustomLineEdit, CustomActionMenu, CustomDockWidget
from src.common.SearchTool import SearchWidget
from src.common.Logger import auto_log_methods

# -------------------------------
# Notes functions
# -------------------------------
@auto_log_methods(logger_key='Notes', prefix="NOTE: ", show_args=True)
class Notes(CustomDockWidget):
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
    def __init__(self, parent=None, filename=None, title='Notes', logger_options=None, logger_key=None):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(parent)
        self.logger_options = logger_options
        self.logger_key = logger_key

        self.parent = parent

        self._notes_file = None
        self.options = {'MaxColumns': None, 'MaxVariance': 95}

        container = QWidget()

        # Create the layout within parent.tabWorkflow
        dock_layout = QVBoxLayout()   

        # Create toolbar
        toolbar = QToolBar("Notes Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # header button and menu
        header_icon = ":resources/icons/icon-heading-64.svg"
        header_menu_items = [
            ('H1', lambda: self.format_header('H1')),
            ('H2', lambda: self.format_header('H2')),
            ('H3', lambda: self.format_header('H3'))
        ]
        self.action_header = CustomActionMenu(header_icon, "Header", header_menu_items)
        self.action_header.setToolTip("Format a heading")

        # bold button
        self.action_bold = QAction()
        bold_icon = QIcon(":resources/icons/icon-bold-64.svg")
        if not bold_icon.isNull():
            self.action_bold.setIcon(bold_icon)
        else:
            self.action_bold.setText("Bold")
        self.action_bold.setToolTip("Bold selected text")

        # italic button
        self.action_italic = QAction()
        italic_icon = QIcon(":resources/icons/icon-italics-64.svg")
        if not italic_icon.isNull():
            self.action_italic.setIcon(italic_icon)
        else:
            self.action_italic.setText("Italic")
        self.action_italic.setToolTip("Italicize selected text")

        # literal button
        self.action_literal = QAction()
        literal_icon = QIcon(":resources/icons/icon-literal-64.svg")
        if not literal_icon.isNull():
            self.action_literal.setIcon(literal_icon)
        else:
            self.action_literal.setText("Literal")
        self.action_literal.setToolTip("Display selected text as a literal")

        # superscript button
        self.action_superscript = QAction()
        superscript_icon = QIcon(":resources/icons/icon-superscript-64.svg")
        if not superscript_icon.isNull():
            self.action_superscript.setIcon(superscript_icon)
        else:
            self.action_superscript.setText("Subscript")
        self.action_superscript.setToolTip("Superscript selected text")

        # subscript button
        self.action_subscript = QAction()
        subscript_icon = QIcon(":resources/icons/icon-subscript-64.svg")
        if not subscript_icon.isNull():
            self.action_subscript.setIcon(subscript_icon)
        else:
            self.action_subscript.setText("Subscript")
        self.action_subscript.setToolTip("Subscript selected text")

        toolbar.addSeparator()

        # bulleted list button
        self.action_bullet = QAction()
        bullet_icon = QIcon(":resources/icons/icon-bullet-list-64.svg")
        if not bullet_icon.isNull():
            self.action_bullet.setIcon(bullet_icon)
        else:
            self.action_bullet.setText("Bulleted List")
        self.action_bullet.setToolTip("Format bulleted list")

        # numbered list button
        self.action_enumerate = QAction()
        enumerate_icon = QIcon(":resources/icons/icon-numbered-list-64.svg")
        if not enumerate_icon.isNull():
            self.action_enumerate.setIcon(enumerate_icon)
        else:
            self.action_enumerate.setText("Numbered List")
        self.action_enumerate.setToolTip("Format enumerated list")

        # citation button
        self.action_cite = QAction()
        cite_icon = QIcon(":resources/icons/icon-cite-64.svg")
        if not cite_icon.isNull():
            self.action_cite.setIcon(cite_icon)
        else:
            self.action_cite.setText("Cite")
        self.action_cite.setToolTip("Insert citation")

        # hyperlink button
        self.action_hyperlink = QAction()
        hyperlink_icon = QIcon(":resources/icons/icon-hyperlink-64.svg")
        if not hyperlink_icon.isNull():
            self.action_hyperlink.setIcon(hyperlink_icon)
        else:
            self.action_hyperlink.setText("Hyperlink")
        self.action_hyperlink.setToolTip("Insert hyperlink")

        # math button and menu
        math_icon = ":resources/icons/icon-equation-64.svg"
        math_menu_items = [
            ('Inline math', lambda: self.format_text('inline math')),
            ('Display math', lambda: self.format_text('display math')),
            ('Calculated field', [
                (eq_name, callback) for eq_name, callback in self.parent.calc_dict.items()
            ])
        ]
        self.action_math = CustomActionMenu(math_icon, "Insert equation", math_menu_items, self)
        self.action_math.setToolTip("Insert equation")


        # image button
        self.action_image = QAction()
        image_icon = QIcon(":resources/icons/icon-image-dark-64.svg")
        if not image_icon.isNull():
            self.action_image.setIcon(image_icon)
        else:
            self.action_image.setText("Figure")
        self.action_image.setToolTip("Insert figure")

        # info button and menu
        info_icon = ":resources/icons/icon-formatted-output-64.svg"
        info_menu_items = [
            ('Sample info', lambda: self.insert_info('sample info')),
            ('List analytes used', lambda: self.insert_info('analytes')),
            ('Current plot details', lambda: self.insert_info('plot info')),
            ('Filter table', lambda: self.insert_info('filters')),
            ('PCA results', lambda: self.insert_info('pca results')),
            ('Cluster results', lambda: self.insert_info('cluster results'))
        ]
        self.action_info = CustomActionMenu(info_icon, "Formatted Info", info_menu_items)
        self.action_info.setToolTip("Insert formatted info")

        # options button, opens options dialog
        self.action_options = QAction()
        options_icon = QIcon(":resources/icons/icon-gear-64.svg")
        if not options_icon.isNull():
            self.action_options.setIcon(options_icon)
        else:
            self.action_options.setText("Options")
        self.action_options.setToolTip("Options")
        # export as rst2pdf button
        self.action_export = QAction()
        export_icon = QIcon(":resources/icons/icon-pdf-64.svg")
        if not export_icon.isNull():
            self.action_export.setIcon(export_icon)
        else:
            self.action_export.setText("Save")
        self.action_export.setToolTip("Save notes as PDF (must have rst2pdf installed)")

        # pdf previewer
        self.action_preview_pdf = QAction()
        preview_icon = QIcon(":resources/icons/icon-show-hide-64.svg")
        if not preview_icon.isNull():
            self.action_preview_pdf.setIcon(preview_icon)
        else:
            self.action_preview_pdf.setText("Preview")
        self.action_preview_pdf.setToolTip("Preview PDF")
        self.action_preview_pdf.setCheckable(True)
        self.action_preview_pdf.setChecked(False)
        self.action_preview_pdf.setEnabled(False)

        # Create Text Edit region for ReST Notes
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Monaco", 10))
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text_edit.setMaximumSize(QSize(524287, 524287))
        self.text_edit.viewport().setProperty("cursor", QCursor(Qt.CursorShape.IBeamCursor))

        # Create search
        self.search_widget = SearchWidget(self.text_edit, self, enable_replace=True, realtime=False)

        # add buttons to toolbar
        toolbar.addAction(self.action_header)
        toolbar.addAction(self.action_bold)
        toolbar.addAction(self.action_italic)
        toolbar.addAction(self.action_literal)
        toolbar.addAction(self.action_superscript)
        toolbar.addAction(self.action_subscript)
        toolbar.addAction(self.action_bullet)
        toolbar.addAction(self.action_enumerate)

        toolbar.addSeparator()
        toolbar.addAction(self.action_cite)
        toolbar.addAction(self.action_hyperlink)

        toolbar.addSeparator()
        toolbar.addAction(self.action_math)
        toolbar.addAction(self.action_image)
        toolbar.addAction(self.action_info)
        toolbar.addAction(self.action_options)

        toolbar.addSeparator()
        toolbar.addWidget(self.search_widget)
        toolbar.addSeparator()

        toolbar.addAction(self.action_export)
        toolbar.addAction(self.action_preview_pdf)

        widget_layout = QHBoxLayout()

        if self._notes_file is None:
            self.file_label = QLabel("File: [load sample to display file]")
        else:
            self.file_label = QLabel("File: "+self._notes_file)

        # Create a QWebEngineView
        self.pdf_browser = QWebEngineView()

        # Load the PDF file
        self.pdf_browser.setUrl(QUrl(self.notes_file))

        # Add the web view to the layout
        widget_layout.addWidget(self.text_edit)
        widget_layout.addWidget(self.pdf_browser)

        dock_layout.addWidget(toolbar)
        dock_layout.addLayout(widget_layout)
        dock_layout.addWidget(self.file_label)

        # Connect resize event
        #parent.resizeEvent = self.handleResizeEvent

        # Set layout to the container
        container.setLayout(dock_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        self.action_bold.triggered.connect(lambda: self.format_text('bold'))
        self.action_italic.triggered.connect(lambda: self.format_text('italic'))
        self.action_literal.triggered.connect(lambda: self.format_text('literal'))
        self.action_superscript.triggered.connect(lambda: self.format_text('superscript'))
        self.action_subscript.triggered.connect(lambda: self.format_text('subscript'))
        self.action_bullet.triggered.connect(lambda: self.format_list('bullet'))
        self.action_enumerate.triggered.connect(lambda: self.format_list('enumerate'))
        self.action_cite.triggered.connect(lambda: self.format_text('citation'))
        self.action_hyperlink.triggered.connect(lambda: self.format_text('hyperlink'))
        self.action_image.triggered.connect(self.insert_image)
        self.action_options.triggered.connect(self.open_note_options)
        self.action_export.triggered.connect(self.save_notes_to_pdf) # compile rst
        self.action_preview_pdf.triggered.connect(self.toggle_preview_notes) # compile rst
        self.action_export.triggered.connect(lambda: self.action_preview_pdf.setEnabled(True)) # compile rst

        # autosave notes
        self.autosaveTimer = QTimer()
        self.autosaveTimer.setInterval(300000)

        if self.notes_file is not None:
            try:
                self.autosaveTimer.timeout.connect(self.notes_file)
            except:
                QMessageBox.warning(self, "Warning", f"Autosave could not save notes to file ({self.notes_file}).")

        self.notes_file = filename


    @property
    def notes_file(self):
        """str : File name associated with the current sample.  When set, the current file will be
        saved before changing files.  If the new file name is not ``None``, an autosave timer will
        be set.
        """        
        return self._notes_file

    @notes_file.setter
    def notes_file(self, filename):
        # no need to do anything if the filename is the same
        if self._notes_file == filename:
            return

        # open notes file if it exists
        if self._notes_file is not None:
            self.save_notes_file()
            self.autosaveTimer.stop()

        # update filename
        self._notes_file = filename

        if self._notes_file is None:
            self.file_label = QLabel("File: [load sample to display file]")
            return
        else:
            self.file_label = QLabel("File: "+self._notes_file)

        # start autosave
        try:
            self.autosaveTimer.timeout.connect(self.save_notes_file)
        except:
            QMessageBox.warning(self, "Warning", f"Autosave could not save notes to file ({self._notes_file}).")

        if os.path.exists(self._notes_file):
            try:
                with open(self._notes_file,'r') as file:
                    self.text_edit.setText(file.read())
            except:
                file_name = os.path.basename(self._notes_file)
                self.parent.statusbar.showMessage(f'Cannot read {file_name}')
                pass

        self.autosaveTimer.start()

    def update_equation_menu(self):
        new_items = [
                (eq_name, lambda: self.write_equation(equation)) for eq_name, equation in self.parent.calc_dict.items()
            ]
        self.math_action.update_submenu("Calculated field", new_items)

    def write_equation(self, equation):
        cursor = self.text_edit.textCursor()
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

        self.parent.statusbar.showMessage('Saving notes...')

        # write file
        with open(self.notes_file,'w') as file:
            file.write(str(self.text_edit.toPlainText()))

        self.parent.statusbar.clearMessage()

    def _insert_image(self, filenames, halign, width, alt_text, caption):
        for fn in filenames:
            self.text_edit.insertPlainText(f"\n\n.. figure:: {fn}\n")
            self.text_edit.insertPlainText(f"    :align: {halign}\n")
            self.text_edit.insertPlainText(f"    :alt: {alt_text}\n")
            self.text_edit.insertPlainText(f"    :width: {width}mm\n")
            self.text_edit.insertPlainText(f"\n    {caption}\n")

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
            dialog.setFileMode(QFileDialog.ExistingFiles)
            dialog.setNameFilter("Image Files (*.jpg *.png *.tif)")
            filename = []

            if dialog.exec_():
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

        # Get the current text cursor
        cursor = self.text_edit.textCursor()

        # Get the current line number and position
        line_number = cursor.blockNumber()

        # Move the cursor to the end of the selected line
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)

        #cursor.movePosition(QTextCursor.NextBlock)

        # Insert the line of "="
        cursor.insertText('\n' + f'{symbol}' * (cursor.block().length() - 1))

    def format_list(self, style):
        """Formats a list in the text, either bulleted or enumerated

        Formats selected text as bulleted or enumerated in restructured text format.

        Parameters
        ----------
        style : str
            Type of formatting, ``bullet`` or ``enumerate``
        """

        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText()

        match style:
            case 'bullet':
                symbol = '*'
            case 'enumerate':
                symbol = '#'

        #code to make bulleted list here
        # Split the selected text into lines
        lines = selected_text.split('\u2029')  # QTextEdit uses Unicode Paragraph Separator for newlines

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
        cursor = self.text_edit.textCursor()
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
            defined by ``self.text_edit.textCursor()``
        key : str
            selected text to be used for the citation key
        """        
        cursor = self.text_edit.textCursor()
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
        full_text = self.text_edit.toPlainText()
        
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
            defined by ``self.text_edit.textCursor()``
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
        plain_text = self.text_edit.toPlainText()
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

        self.text_edit.setPlainText(updated_text)

    def insert_info(self, infotype):
        """Adds preformatted notes

        Parameters
        ----------
        infotype : str
            Name of preformatted information
        """

        data = self.parent.data[self.parent.app_data.sample_id]

        match infotype:
            case 'sample info':
                self.text_edit.insertPlainText(f'**Sample ID: {self.parent.app_data.sample_id}**\n')
                self.text_edit.insertPlainText('*' * (len(self.parent.app_data.sample_id) + 15) + '\n')
                self.text_edit.insertPlainText(f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n')
                # width/height
                # list of all analytes
                self.text_edit.insertPlainText(':User: Your name here\n')
                pass
            case 'analytes':
                analytes = data.processed_data.match_attribute('data_type', 'Analyte')
                ratios = data.processed_data.match_attribute('data_type', 'Ratio')
                if analytes:
                    self.text_edit.insertPlainText('\n\n:analytes used: '+', '.join(analytes))
                if ratios:
                    self.text_edit.insertPlainText('\n\n:ratios used: '+', '.join(ratios))
            case 'plot info':
                text = ['\n\n:plot type: '+self.parent.plot_info['plot_type'],
                        ':plot name: '+self.parent.plot_info['plot_name']+'\n']
                self.text_edit.insertPlainText('\n'.join(text))
            case 'filters':
                rst_table = self.to_rst_table(data.filter_df)

                self.text_edit.insertPlainText(rst_table)
            case 'pca results':
                if not self.parent.pca_results:
                    return

                # Retrieve analytes matching specified attributes
                analytes = data.processed_data.match_attributes({'data_type': 'Analyte', 'use': True})
                analytes = np.insert(analytes, 0, 'lambda')  # Insert 'lambda' at the start of the analytes array

                # Calculate explained variance in percentage
                explained_variance = self.parent.pca_results.explained_variance_ratio_ * 100

                # Retrieve PCA score headers matching the attribute condition
                header = data.processed_data.match_attributes({'data_type': 'PCA score'})

                # Create a matrix with explained variance and PCA components
                matrix = np.vstack([explained_variance, self.parent.pca_results.components_])

                # Filter matrix and header based on the MaxVariance option
                variance_mask = np.cumsum(explained_variance) <= self.options['MaxVariance']
                matrix = matrix[:, variance_mask]  # Keep columns where variance is <= MaxVariance
                header = np.array(header)[variance_mask]  # Apply the same filter to the header

                # Limit the number of columns based on MaxColumns option
                if self.options['MaxColumns'] is not None and  matrix.shape[1] > self.options['MaxColumns']:
                    header = np.concatenate([[analytes[0]], header[:self.options['MaxColumns']]])  # Include 'lambda' in header
                    matrix = matrix[:, :self.options['MaxColumns']]  # Limit matrix columns

                # add PCA results to table
                self.add_table_note(matrix, row_labels=analytes, col_labels=header)
            case 'cluster results':
                if not self.parent.cluster_results:
                    return

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

        self.text_edit.insertPlainText(table)


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
            return

        self.save_notes_file()

        # replace all spaces with \ space
        filename = self.notes_file
        try:
            pdf_file_path = filename.replace('.rst', '.pdf')

            # use rst2pdf on the command line to export the file as a pdf
            #os.system(f"cat {filename} | rst2pdf -o --use-floating-images {os.path.splitext(filename)[0]+'.pdf'}")
       
            with open(filename, 'r') as file:
                rst_content = file.read()
            
            pdf = RstToPdf()
            pdf_content = pdf.createPdf(text=rst_content, output=pdf_file_path)
            
            #with open(pdf_file_path, 'wb') as pdf_file:
            #    pdf_file.write(pdf_content)
            
            self.parent.statusBar.showMessage("PDF successfully generated...")
            
            # view pdf
            if self.action_preview_pdf.isChecked():
                self.update_pdf()

        except Exception as e:
            # if it doesn't work
            QMessageBox.warning(self, "Error", "Could not save to pdf.\n"+str(e))

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
        if dialog.exec_() == QDialog.Accepted:
            columns, variance = dialog.get_options()
            if columns:
                print(f"Number of Columns: {columns}")
            if variance:
                print(f"Cumulative Variance: {variance}%")

    def toggle_preview_notes(self):
        """Shows/hides the PDF preview browser"""
        if self.action_preview_pdf.isChecked():
            # show previewer
            self.pdf_browser.show()

            self.update_pdf()
        else:
            # hide previewer
            self.pdf_browser.hide()

    def update_pdf(self):
        """Opens the compiled PDF, ``self.notes_file``, for viewing"""
        self.pdf_browser.setUrl(QUrl(self.notes_file))

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

        self.parent = parent

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
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
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
        if self.parent is not None:
            self.parent.options = self.options
        self.accept()

    def get_options(self):
        """
        Returns the options set in the dialog.
        """
        columns = self.columns_input.text()
        variance = self.variance_input.text()
        return columns, variance