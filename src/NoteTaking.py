import re
from PyQt5.QtCore import ( QTimer )
from PyQt5.QtWidgets import ( QMessageBox, QMenu, QFileDialog)
from PyQt5.QtGui import ( QFont, QTextCursor )
from datetime import datetime
import numpy as np
import pandas as pd   
from rst2pdf.createpdf import RstToPdf
from docutils.core import publish_string
import src.format as fmt

# -------------------------------
# Notes functions
# -------------------------------
class Notes():
    def __init__(self, parent=None):

        self.parent = parent

        self.notes_file = None

        self.parent.textEditNotes.setFont(QFont("Monaco", 10))
        self.parent.toolButtonNotesImage.clicked.connect(self.notes_add_image)

        # heading menu
        hmenu_items = ['H1','H2','H3']
        formatHeadingMenu = QMenu()
        formatHeadingMenu.triggered.connect(lambda x:self.add_header_line(x.text()))
        self.add_menu(hmenu_items,formatHeadingMenu)
        self.parent.toolButtonNotesHeading.setMenu(formatHeadingMenu)

        # info menu
        infomenu_items = ['Sample info','List analytes used','Current plot details','Filter table','PCA results','Cluster results']
        notesInfoMenu = QMenu()
        notesInfoMenu.triggered.connect(lambda x:self.add_info_note(x.text()))
        self.add_menu(infomenu_items,notesInfoMenu)
        self.parent.toolButtonNotesInfo.setMenu(notesInfoMenu)

        self.parent.toolButtonNotesBold.clicked.connect(lambda: self.format_note_text('bold'))
        self.parent.toolButtonNotesItalic.clicked.connect(lambda: self.format_note_text('italics'))

        # compile rst
        self.parent.toolButtonNotesSave.clicked.connect(self.save_notes_to_pdf)

        # autosave notes
        self.autosaveTimer = QTimer()
        self.autosaveTimer.setInterval(300000)
        self.autosaveTimer.timeout.connect(self.save_notes_file)

    def add_menu(self, menu_items, menu_obj):
        """Adds items to a context menu

        :param menu_items: Names of the menu text to add
        :type menu_items: list
        :param menu_obj: context menu object
        :type menu_obj: QMenu
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
            file.write(str(self.parent.textEditNotes.toPlainText()))

        self.parent.statusbar.clearMessage()

    def notes_add_image(self):
        """Adds placeholder image to notes

        Uses the reStructured Text figure format
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("Image Files (*.jpg *.png *.tif)")
        filenames = []

        if dialog.exec_():
            filenames = dialog.selectedFiles()
        else:
            return

        for fn in filenames:
            self.parent.textEditNotes.insertPlainText(f"\n\n.. figure:: {fn}\n")
            self.parent.textEditNotes.insertPlainText("    :align: center\n")
            self.parent.textEditNotes.insertPlainText("    :alt: alternate text\n")
            self.parent.textEditNotes.insertPlainText("    :width: 150mm\n")
            self.parent.textEditNotes.insertPlainText("\n    Caption goes here.\n")

    def add_header_line(self, level):
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
        cursor = self.parent.textEditNotes.textCursor()

        # Get the current line number and position
        line_number = cursor.blockNumber()

        # Move the cursor to the end of the selected line
        cursor.movePosition(QTextCursor.EndOfLine)
        #cursor.movePosition(QTextCursor.NextBlock)

        # Insert the line of "="
        cursor.insertText('\n' + f'{symbol}' * (cursor.block().length() - 1))

    def format_note_text(self, style):
        """Formats the text

        Formats selected text as bold, italic or literal in restructured text format.

        Parameters
        ----------
        style : str
            Type of formatting
        """
        cursor = self.parent.textEditNotes.textCursor()
        selected_text = cursor.selectedText()

        match style:
            case 'italics':
                modified_text = f"*{selected_text}*"
            case 'bold':
                modified_text = f"**{selected_text}**"
            case 'literal':
                modified_text = f"``{selected_text}``"

        cursor.insertText(modified_text)

    def add_info_note(self, infotype):
        """Adds preformatted notes

        Parameters
        ----------
        infotype : str
            Name of preformatted information
        """
        match infotype:
            case 'Sample info':
                self.parent.textEditNotes.insertPlainText(f'**Sample ID: {self.parent.sample_id}**\n')
                self.parent.textEditNotes.insertPlainText('*' * (len(self.parent.sample_id) + 15) + '\n')
                self.parent.textEditNotes.insertPlainText(f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n')
                # width/height
                # list of all analytes
                self.parent.textEditNotes.insertPlainText(':User: Your name here\n')
                pass
            case 'List analytes used':
                fields = self.parent.get_field_list()
                self.parent.textEditNotes.insertPlainText('\n\n:analytes used: '+', '.join(fields))
            case 'Current plot details':
                text = ['\n\n:plot type: '+self.parent.plot_info['plot_type'],
                        ':plot name: '+self.parent.plot_info['plot_name']+'\n']
                self.parent.textEditNotes.insertPlainText('\n'.join(text))
            case 'Filter table':
                filter_table = self.parent.data[self.parent.sample_id]['filter_info']
                rst_table = self.to_rst_table(filter_table)

                self.parent.textEditNotes.insertPlainText(rst_table)
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

        self.parent.textEditNotes.insertPlainText(table)


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
            QMessageBox.warning(self.parent, "Error", "Could not save to pdf.\n"+str(e))

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
