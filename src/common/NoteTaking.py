import re
from PyQt5.QtCore import ( Qt, QTimer, QSize )
from PyQt5.QtWidgets import ( QMainWindow, QMessageBox, QMenu, QFileDialog, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QToolButton, QTextEdit, QSizePolicy, QSpacerItem, QLabel )
from PyQt5.QtGui import ( QFont, QTextCursor, QIcon, QCursor )
from datetime import datetime
import numpy as np
import pandas as pd   
from rst2pdf.createpdf import RstToPdf
from docutils.core import publish_string
import src.common.format as fmt

# -------------------------------
# Notes functions
# -------------------------------
class Notes(QDockWidget):
    def __init__(self, parent=None, filename=None):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__("Workflow Method Design", parent)
        self.parent = parent

        self._notes_file = filename

        container = QWidget()

        # Create the layout within parent.tabWorkflow
        dock_layout = QVBoxLayout()   

        # Creat a toolbar using a groupbox
        toolbar = QGroupBox("")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        toolbar_layout.setSpacing(5)  # Spacing between buttons

        # header button and menu
        self.header_button = QToolButton()
        header_icon = QIcon(":resources/icons/icon-heading-64.svg")
        if not header_icon.isNull():
            self.header_button.setIcon(header_icon)
        else:
            self.header_button.setText("Header")
        self.header_button.setToolTip("Save notes as PDF (must have rst2pdf installed)")
        self.header_button.setToolTip("Format the heading level")

        hmenu_items = ['H1','H2','H3']
        format_header_menu = QMenu()
        format_header_menu.triggered.connect(lambda x:self.format_header(x.text()))
        self.add_menu(hmenu_items,format_header_menu)
        self.header_button.setMenu(format_header_menu)
        self.header_button.setToolTip("Format selected line as header")

        # bold button
        self.bold_button = QToolButton()
        bold_icon = QIcon(":resources/icons/icon-bold-64.svg")
        if not bold_icon.isNull():
            self.bold_button.setIcon(bold_icon)
        else:
            self.bold_button.setText("Bold")
        self.bold_button.setToolTip("Bold selected text")

        # italic button
        self.italic_button = QToolButton()
        italic_icon = QIcon(":resources/icons/icon-italics-64.svg")
        if not italic_icon.isNull():
            self.italic_button.setIcon(italic_icon)
        else:
            self.italic_button.setText("Italic")
        self.italic_button.setToolTip("Italicize selected text")

        # literal button
        self.literal_button = QToolButton()
        literal_icon = QIcon(":resources/icons/icon-literal-64.svg")
        if not literal_icon.isNull():
            self.literal_button.setIcon(literal_icon)
        else:
            self.literal_button.setText("Literal")
        self.literal_button.setToolTip("Display selected text as a literal")

        # subscript button
        self.subscript_button = QToolButton()
        subscript_icon = QIcon(":resources/icons/icon-subscript-64.svg")
        if not subscript_icon.isNull():
            self.subscript_button.setIcon(subscript_icon)
        else:
            self.subscript_button.setText("Subscript")
        self.subscript_button.setToolTip("Subscript selected text")

        # superscript button
        self.superscript_button = QToolButton()
        superscript_icon = QIcon(":resources/icons/icon-superscript-64.svg")
        if not superscript_icon.isNull():
            self.superscript_button.setIcon(superscript_icon)
        else:
            self.superscript_button.setText("Subscript")
        self.superscript_button.setToolTip("Superscript selected text")

        # bulleted list button
        self.bullet_button = QToolButton()
        bullet_icon = QIcon(":resources/icons/icon-bullet-list-64.svg")
        if not bullet_icon.isNull():
            self.bullet_button.setIcon(bullet_icon)
        else:
            self.bullet_button.setText("Bulleted List")
        self.bullet_button.setToolTip("Format bulleted list")

        # numbered list button
        self.number_button = QToolButton()
        number_icon = QIcon(":resources/icons/icon-numbered-list-64.svg")
        if not number_icon.isNull():
            self.number_button.setIcon(number_icon)
        else:
            self.number_button.setText("Numbered List")
        self.number_button.setToolTip("Format enumerated list")

        # citation button
        self.cite_button = QToolButton()
        cite_icon = QIcon(":resources/icons/icon-cite-64.svg")
        if not cite_icon.isNull():
            self.cite_button.setIcon(cite_icon)
        else:
            self.cite_button.setText("Cite")
        self.cite_button.setToolTip("Insert citation")

        # hyperlink button
        self.hyperlink_button = QToolButton()
        hyperlink_icon = QIcon(":resources/icons/icon-hyperlink-64.svg")
        if not hyperlink_icon.isNull():
            self.hyperlink_button.setIcon(hyperlink_icon)
        else:
            self.hyperlink_button.setText("Hyperlink")
        self.hyperlink_button.setToolTip("Insert hyperlink")

        # math button and menu
        self.math_button = QToolButton()
        math_icon = QIcon(":resources/icons/icon-equation-64.svg")
        if not math_icon.isNull():
            self.math_button.setIcon(math_icon)
        else:
            self.math_button.setText("Math")
        self.math_button.setToolTip("Insert equation")

        # image button
        self.image_button = QToolButton()
        image_icon = QIcon(":resources/icons/icon-image-dark-64.svg")
        if not image_icon.isNull():
            self.image_button.setIcon(image_icon)
        else:
            self.image_button.setText("Figure")
        self.image_button.setToolTip("Insert figure")

        # info button and menu
        self.info_button = QToolButton()
        info_icon = QIcon(":resources/icons/icon-info-64.svg")
        if not info_icon.isNull():
            self.info_button.setIcon(info_icon)
        else:
            self.info_button.setText("Info")
        self.info_button.setToolTip("Insert formatted info")

        info_menu_items = ['Sample info','List analytes used','Current plot details','Filter table','PCA results','Cluster results']
        info_menu = QMenu()
        info_menu.triggered.connect(lambda x:self.insert_info(x.text()))
        self.add_menu(info_menu_items,info_menu)
        self.info_button.setMenu(info_menu)

        # export as rst2pdf button
        self.export_button = QToolButton()
        export_icon = QIcon(":resources/icons/icon-pdf-64.svg")
        if not export_icon.isNull():
            self.export_button.setIcon(export_icon)
        else:
            self.export_button.setText("Save")
        self.export_button.setToolTip("Save notes as PDF (must have rst2pdf installed)")

        spacer1 = QSpacerItem(10, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
        spacer2 = QSpacerItem(10, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
        spacer3 = QSpacerItem(10, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
        spacer4 = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # add buttons to toolbar
        toolbar_layout.addWidget(self.header_button)
        toolbar_layout.addWidget(self.bold_button)
        toolbar_layout.addWidget(self.italic_button)
        toolbar_layout.addWidget(self.literal_button)
        toolbar_layout.addWidget(self.superscript_button)
        toolbar_layout.addWidget(self.subscript_button)
        toolbar_layout.addItem(spacer1)
        toolbar_layout.addWidget(self.bullet_button)
        toolbar_layout.addWidget(self.number_button)
        toolbar_layout.addItem(spacer2)
        toolbar_layout.addWidget(self.cite_button)
        toolbar_layout.addWidget(self.hyperlink_button)
        toolbar_layout.addWidget(self.math_button)
        toolbar_layout.addWidget(self.image_button)
        toolbar_layout.addWidget(self.info_button)
        toolbar_layout.addItem(spacer3)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addItem(spacer4)


        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Monaco", 10))
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text_edit.setMaximumSize(QSize(524287, 524287))
        self.text_edit.viewport().setProperty("cursor", QCursor(Qt.IBeamCursor))
        self.text_edit.setObjectName("textEditNotes")

        if self._notes_file is None:
            self.file_label = QLabel("File: [load sample to display file]")
        else:
            self.file_label = QLabel("File: "+self._notes_file)

        dock_layout.addWidget(toolbar)
        dock_layout.addWidget(self.text_edit)
        dock_layout.addWidget(self.file_label)

        # Connect resize event
        #parent.resizeEvent = self.handleResizeEvent

        # Set layout to the container
        container.setLayout(dock_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("Workflow Method Design")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        parent.addDockWidget(Qt.BottomDockWidgetArea, self)

        # Button signals
        self.bold_button.clicked.connect(lambda: self.format_text('bold'))
        self.italic_button.clicked.connect(lambda: self.format_text('italics'))
        self.literal_button.clicked.connect(lambda: self.format_text('literal'))
        self.subscript_button.clicked.connect(lambda: self.format_text('subscript'))
        self.superscript_button.clicked.connect(lambda: self.format_text('superscript'))
        self.math_button.clicked.connect(lambda: self.format_text('inline math'))
        self.cite_button.clicked.connect(lambda: self.format_text('citation'))
        self.hyperlink_button.clicked.connect(lambda: self.format_text('hyperlink'))
        self.image_button.clicked.connect(self.insert_image)
        self.export_button.clicked.connect(self.save_notes_to_pdf) # compile rst

        # autosave notes
        if self.notes_file is not None:
            try:
                self.autosaveTimer = QTimer()
                self.autosaveTimer.setInterval(300000)
                self.autosaveTimer.timeout.connect(self.notes_file)
            except:
                QMessageBox.warning(self, "Warning", f"Autosave could not save notes to file ({self.notes_file}).")

    # For creating a submenu, useful for math
    #     # Create the tool button
    #     self.tool_button = QToolButton(self)
    #     self.tool_button.setText("Math Options")
    #     self.tool_button.setPopupMode(QToolButton.MenuButtonPopup)

    #     # Main menu
    #     main_menu = QMenu(self)

    #     # Add "Inline" and "Display Math" options
    #     inline_action = QAction("Inline", self)
    #     display_action = QAction("Display Math", self)
    #     inline_action.triggered.connect(lambda: self.handle_option("Inline"))
    #     display_action.triggered.connect(lambda: self.handle_option("Display Math"))
    #     main_menu.addAction(inline_action)
    #     main_menu.addAction(display_action)

    #     # Add "From Calculator" submenu
    #     from_calculator_menu = QMenu("From Calculator", self)

    #     # Dictionary of calculator equations
    #     equations = {
    #         "Equation 1": "a^2 + b^2 = c^2",
    #         "Equation 2": "E = mc^2",
    #         "Equation 3": "F = ma"
    #     }

    #     # Dynamically populate submenu
    #     for key, value in equations.items():
    #         action = QAction(key, self)
    #         action.triggered.connect(lambda checked, eq=value: self.handle_calculator_option(eq))
    #         from_calculator_menu.addAction(action)

    #     # Add the submenu to the main menu
    #     main_menu.addMenu(from_calculator_menu)

    #     # Set the menu to the tool button
    #     self.tool_button.setMenu(main_menu)

    #     # Add the tool button to the main window
    #     self.setCentralWidget(self.tool_button)

    # def handle_option(self, option):
    #     print(f"Selected option: {option}")

    # def handle_calculator_option(self, equation):
    #     print(f"Selected equation: {equation}")


    @property
    def notes_file(self):
        return self._notes_file

    @notes_file.setter
    def notes_file(self, filename):
        self._notes_file = filename


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
        if filenames is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.ExistingFiles)
            dialog.setNameFilter("Image Files (*.jpg *.png *.tif)")
            filenames = []

            if dialog.exec_():
                filenames = dialog.selectedFiles()
            else:
                return

        if isinstance(filenames,str):
            filenames = list(filenames)
        elif not isinstance(filenames,list):
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

        self._insert_image(filenames, halign, width, alt_text, caption)


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
        cursor.movePosition(QTextCursor.EndOfLine)
        #cursor.movePosition(QTextCursor.NextBlock)

        # Insert the line of "="
        cursor.insertText('\n' + f'{symbol}' * (cursor.block().length() - 1))

    def format_text(self, style):
        """Formats the text

        Formats selected text as bold, italic or literal in restructured text format.

        Parameters
        ----------
        style : str
            Type of formatting
        """
        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText()

        match style:
            case 'italics':
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
            cursor.movePosition(QTextCursor.NextBlock)  # Move to the block after "References"

            # Move to the last non-empty block in the "References" section
            while cursor.block().text().strip() != "" and not cursor.atEnd():
                cursor.movePosition(QTextCursor.NextBlock)

            # Insert the citation at the end of the "References" section
            cursor.insertBlock()
            cursor.insertText(f"{citation_text}\n")
        else:
            # "References" section doesn't exist, create it at the end
            cursor.movePosition(QTextCursor.End)
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
        match infotype:
            case 'Sample info':
                self.text_edit.insertPlainText(f'**Sample ID: {self.parent.sample_id}**\n')
                self.text_edit.insertPlainText('*' * (len(self.parent.sample_id) + 15) + '\n')
                self.text_edit.insertPlainText(f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n')
                # width/height
                # list of all analytes
                self.text_edit.insertPlainText(':User: Your name here\n')
                pass
            case 'List analytes used':
                fields = self.parent.get_field_list()
                self.text_edit.insertPlainText('\n\n:analytes used: '+', '.join(fields))
            case 'Current plot details':
                text = ['\n\n:plot type: '+self.parent.plot_info['plot_type'],
                        ':plot name: '+self.parent.plot_info['plot_name']+'\n']
                self.text_edit.insertPlainText('\n'.join(text))
            case 'Filter table':
                filter_table = self.parent.data[self.parent.sample_id]['filter_info']
                rst_table = self.to_rst_table(filter_table)

                self.text_edit.insertPlainText(rst_table)
            case 'PCA results':
                if not self.parent.pca_results:
                    return
                analytes = self.parent.data[self.parent.sample_id]['analyte_info'].loc[:,'analytes'].values
                analytes = np.insert(analytes,0,'lambda')

                matrix = np.vstack([self.parent.pca_results.explained_variance_ratio_, self.parent.pca_results.components_])

                header = self.parent.data[self.parent.sample_id]['computed_data']['PCA Score'].columns[2:].to_numpy()

                #print(type(analytes))
                #print(type(header))
                #print(type(matrix))
                self.add_table_note(matrix, row_labels=analytes, col_labels=header)
            case 'Cluster results':
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
