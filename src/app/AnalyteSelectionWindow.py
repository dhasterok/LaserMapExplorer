from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QEvent)
from PyQt5.QtWidgets import (QMessageBox, QTableWidget, QDialog, QTableWidgetItem, QLabel, QComboBox, QHeaderView, QFileDialog)
from PyQt5.QtGui import (QImage, QColor, QFont, QPixmap, QPainter, QBrush)
from src.ui.AnalyteSelectionDialog import Ui_Dialog
from src.common.rotated import RotatedHeaderView
import os
# Analyte GUI
# -------------------------------
class AnalyteDialog(QDialog, Ui_Dialog):
    """Creates an dialog to select analytes and ratios of analytes

    Creates a dialog with a matrix analytes vs. analytes with a background given by a correlation matrix.
    Selected analytes are identified by yellow highlighting the cell.  Cells on the diagonal (analyte row 
    and column are the same) are automatically selected.  Cells above the diagonal represent ratio of 
    row / column and cells below the diagonal represent the ratio of column / row.  The list of selected
    analytes and rows are displayed in the table along with the ability to change the scaling.

    Parameters
    ----------
    QDialog : 
        _description_
    Ui_Dialog : 
        _description_

    Returns
    -------
    _type_
        _description_
    """    
    listUpdated = pyqtSignal()
    def __init__(self, parent, debug=False):
        if (parent.__class__.__name__ == 'Main'):
            super().__init__() #initialisng with no parent widget
        else:
            super().__init__(parent) #initialise with mainWindow as parentWidget
        self.setupUi(self)

        if parent.sample_id is None or parent.sample_id == '':
            return

        self.debug = debug

        self.data = parent.data[parent.sample_id].processed_data

        self.norm_dict = {}

        self.analytes = self.data.match_attribute('data_type','analyte')
        self.ratio = self.data.match_attribute('data_type','ratio')
        for analyte in self.analytes+self.ratio:
            self.norm_dict[analyte] = self.data.get_attribute(analyte,'norm')

        # Initialize filename and unsaved changes flag
        self.base_title ='LaME: Select Analytes and Ratios'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()
        self.default_dir  = os.path.join(parent.BASEDIR, "resources", "analyte_list")  # Default directory
        # setup scale (norm) combobox
        self.comboBoxScale.clear()
        self.scale_methods = ['linear','log','logit','mixed']
        for scale in self.scale_methods:
            self.comboBoxScale.addItem(scale)
        self.comboBoxScale.currentIndexChanged.connect(self.update_all_combos)


        # setup correlation combobox
        self.correlation_matrix = None

        self.comboBoxCorrelation.clear()
        self.correlation_methods = ["Pearson", "Spearman"]
        for method in self.correlation_methods:
            self.comboBoxCorrelation.addItem(method)
        self.comboBoxCorrelation.activated.connect(self.calculate_correlation)


        # setup selected analyte table
        self.tableWidgetSelected.setColumnCount(2)
        self.tableWidgetSelected.setHorizontalHeaderLabels(['Field', 'Scaling'])


        # setup analyte table
        self.tableWidgetAnalytes.setStyleSheet("")  # Clears the local stylesheet

        self.tableWidgetAnalytes.setRowCount(len(self.analytes))
        self.tableWidgetAnalytes.setColumnCount(len(self.analytes))

        # setup header properties
        self.tableWidgetAnalytes.setObjectName("analyteTable")
        self.tableWidgetAnalytes.setStyleSheet("""
            QTableWidget#analyteTable::item { 
                background-color: white;  /* Default background color for items */
            }
            QHeaderView#analyteTable::section {
                background-color: none;  /* Reset background */
                font-weight: normal;     /* Reset font weight */
            }
            QHeaderView#analyteTable::section:hover {
                background-color: lightblue;  /* Change background on hover */
                font-weight: bold;            /* Bold on hover */
            }
        """)

        # initial font for headers to Normal weight
        header_font = self.tableWidgetAnalytes.horizontalHeader().font()
        header_font.setWeight(QFont.Normal)

        self.tableWidgetAnalytes.setHorizontalHeaderLabels(list(self.analytes))
        self.tableWidgetAnalytes.setHorizontalHeader(RotatedHeaderView(self.tableWidgetAnalytes))
        self.tableWidgetAnalytes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidgetAnalytes.horizontalHeader().setFont(header_font)

        self.tableWidgetAnalytes.setVerticalHeaderLabels(self.analytes)
        self.tableWidgetAnalytes.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidgetAnalytes.verticalHeader().setFont(header_font)

        # highlight diagonal (use analytes)
        self.tableWidgetAnalytes.setStyleSheet("QTableWidget::item:selected {background-color: yellow;}")
        if len(self.norm_dict.keys()) > 0:
            for analyte,norm in self.norm_dict.items():
                self.populate_analyte_list(analyte,norm)
        else:
            # Select diagonal pairs by default
            for i in range(len(self.analytes)):
                row = column = i
                item = self.tableWidgetAnalytes.item(row, column)

                # If the item doesn't exist, create it
                self.toggle_cell_selection(row, column)

        # Variables to track previous row/column for font reset
        self.prev_row = None
        self.prev_col = None

        # Enable mouse tracking to capture hover events
        self.tableWidgetAnalytes.setMouseTracking(True)
        self.tableWidgetAnalytes.viewport().setMouseTracking(True)

        # Connect mouse move event to custom handler
        self.tableWidgetAnalytes.viewport().installEventFilter(self)
        self.tableWidgetAnalytes.cellClicked.connect(self.toggle_cell_selection)


        # UI buttons
        self.pushButtonSaveSelection.clicked.connect(self.save_selection)
        self.pushButtonLoadSelection.clicked.connect(self.load_selection)
        self.pushButtonDone.clicked.connect(self.done_selection)
        self.pushButtonCancel.clicked.connect(self.cancel_selection)


        # compute correlations for background colors
        self.calculate_correlation()
    
    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def done_selection(self):
        """Executes when `Done` button is clicked."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_selection()
                self.update_list()
                self.accept()
            elif reply == QMessageBox.No:
                self.update_list()
                self.accept()
            else:  # Cancel
                pass  # Do nothing, stay in dialog
        else:
            self.update_list()
            self.accept()

    def cancel_selection(self):
        """Handles the Cancel button click."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.No:
                self.reject()
            else:  # Cancel
                pass  # Do nothing, stay in dialog
        else:
            self.reject()

    def closeEvent(self, event):
        """Overrides the close event to check for unsaved changes."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_selection()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()

    def update_all_combos(self):
        """Updates the scale combo box (``comboBoxScale``) and the combo boxes within ``tableWidgetSelected``."""
        # Get the currently selected value in comboBoxScale
        selected_scale = self.comboBoxScale.currentText()

        # Iterate through all rows in tableWidgetSelected to update combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if isinstance(combo,QComboBox):  # Make sure there is a combo box in this cell
                combo.setCurrentText(selected_scale)  # Update the combo box value

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def update_scale(self):
        """_summary_
        """        
        # Initialize a variable to store the first combo box's selection
        first_selection = None
        mixed = False  # Flag to indicate mixed selections

        # Iterate through all rows in tableWidgetSelected to check combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if combo is not None:  # Make sure there is a combo box in this cell
                # If first_selection has not been set, store the current combo box's selection
                if first_selection is None:
                    first_selection = combo.currentText()
                # If the current combo box's selection does not match first_selection, set mixed to True
                elif combo.currentText() != first_selection:
                    mixed = True
                    break  # No need to check further

        # If selections are mixed, set comboBoxScale to 'mixed', else set it to match first_selection
        if mixed:
            self.comboBoxScale.setCurrentText('mixed')
        else:
            self.comboBoxScale.setCurrentText(first_selection)

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def calculate_correlation(self):
        """Calculates correlation coefficient between two analytes.

        The correlation coefficient is used to color the background between two analytes displayed
        in `tableWidgetAnalytes` as a visual aid to help selection of potentially relevant ratios.
        """        
        selected_method = self.comboBoxCorrelation.currentText().lower()
        # Compute the correlation matrix
        self.correlation_matrix = self.data.corr(method=selected_method)
        for i, row_analyte in enumerate(self.analytes):
            for j, col_analyte in enumerate(self.analytes):

                correlation = self.correlation_matrix.loc[row_analyte, col_analyte]
                self.color_cell(i, j, correlation)
        self.create_colorbar()  # Call this to create and display the colorbar

    def color_cell(self, row, column, correlation):
        """Colors cells in the correlation table"""
        color = self.get_color_for_correlation(correlation)
        item = self.tableWidgetAnalytes.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetAnalytes.setItem(row, column, item)
        item.setBackground(color)

    def get_color_for_correlation(self, correlation):
        """Computes color associated with a given correlation value.

        Parameters
        ----------
        correlation : float
            Correlation coefficient for displaying on `tableWidgetAnalytes` with color background.

        Returns
        -------
        QColor
            RGB color triplet associated with correlation
        """        
        #cmap = plt.get_cmap('RdBu')
        #c = cmap((1 + correlation)/2)
        #r = c[1]
        #g = c[2]
        #b = c[3]

        # Map correlation to RGB color
        r = 255 * (1 - (correlation > 0) * ( abs(correlation)))
        g = 255 * (1 - abs(correlation))
        b = 255 * (1 - (correlation < 0) * ( abs(correlation)))
        return QColor(int(r), int(g),int(b))

    def create_colorbar(self):
        """Displays a colorbar for the ``tableWidgetAnalytes``."""        
        colorbar_image = self.generate_colorbar_image(40, 200)  # Width, Height of colorbar
        colorbar_label = QLabel(self)
        colorbar_pixmap = QPixmap.fromImage(colorbar_image)
        self.labelColorbar.setPixmap(colorbar_pixmap)

    def generate_colorbar_image(self, width, height):
        """Creates a colorbar for the ``tableWidgetAnalytes``.

        Parameters
        ----------
        width : int  
            Width of colorbar image.
        height : int
            Height of colorbar image.

        Returns
        -------
        QImage
            Colorbar image to be displayed in UI.
        """        
        image = QImage(width, height, QImage.Format_RGB32)
        painter = QPainter(image)
        painter.fillRect(0, 0, width, height, Qt.white)  # Fill background with white
        pad =20
        # Draw color gradient
        for i in range(pad,height-pad):
            correlation = 1 - (2 * i / height)  # Map pixel position to correlation value
            color = self.get_color_for_correlation(correlation)
            painter.setPen(color)
            painter.drawLine(10, i, width-20, i) # Leave space for ticks
        # Draw tick marks
        tick_positions = [pad, height // 2, height-pad - 1]  # Top, middle, bottom
        tick_labels = ['1', '0', '-1']
        painter.setPen(Qt.black)
        for pos, label in zip(tick_positions, tick_labels):
            painter.drawLine(width - 20, pos, width-18 , pos)  # Draw tick mark
            painter.drawText(width-15 , pos + 5, label)   # Draw tick label
        painter.end()
        return image

    def toggle_cell_selection(self, row, column):
        """Toggles cell selection in `tableWidgetAnalytes` and adds or removes from list of
        analytes and ratios used by `MainWindow` methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to toggle.
        column : int
            Column in `tableWidgetAnalytes` to toggle.
        """        
        item = self.tableWidgetAnalytes.item(row, column)

        # If the item doesn't exist, create it
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetAnalytes.setItem(row, column, item)
            self.add_analyte_to_list(row, column)
        # If the cell is already selected, deselect it
        elif item.isSelected():
            item.setSelected(True)
            self.add_analyte_to_list(row, column)
        else:
            item.setSelected(False)
            self.remove_analyte_from_list(row, column)

    def add_analyte_to_list(self, row, column):
        """Adds an analyte or ratio to the list to use for analyses in ``MainWindow`` related methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to select.
        column : int
            Column in `tableWidgetAnalytes` to select.
        """        
        row_header = self.tableWidgetAnalytes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetAnalytes.horizontalHeaderItem(column).text()

        newRow = self.tableWidgetSelected.rowCount()
        self.tableWidgetSelected.insertRow(newRow)
        if row == column:
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header}"))
        else:
            # Add analyte pair to the first column
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header} / {col_header}"))

        # Add dropdown to the second column
        combo = QComboBox()
        combo.addItems(['linear', 'log'])
        self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
        self.update_list()

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def remove_analyte_from_list(self, row, column):
        """Removes an analyte or ratio from the list to use in ``MainWindow`` related methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to deselect.
        column : int
            Column in `tableWidgetAnalytes` to deselect.
        """        
        row_header = self.tableWidgetAnalytes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetAnalytes.horizontalHeaderItem(column).text()
        if row == column:
            item_text = f"{row_header}"
        else:
            item_text = f"{row_header} / {col_header}"

        # Find the row with the corresponding text and remove it
        for i in range(self.tableWidgetSelected.rowCount()):
            if self.tableWidgetSelected.item(i, 0).text() == item_text:
                self.tableWidgetSelected.removeRow(i)
                self.update_list()
                break
        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def get_selected_data(self):
        """Grabs data from `tableWidgetSelected`.

        Returns
        -------
        list of tuple
            A list of analytes and the selected norm
        """        
        data = []
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            data.append((analyte_pair, selection))
        return data

    def save_selection(self):
        """Saves the list of analytes (and ratios) and their norms so they can be quickly recalled for other samples."""        
        if not self.default_dir:
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", self.default_dir, "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    analyte_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{analyte_pair},{selection}\n")
            self.filename = os.path.basename(file_name)
            self.unsaved_changes = False
            self.update_window_title()

            self.raise_()
            self.activateWindow()
            self.show()
        

    def load_selection(self):
        """Loads a saved analyte (and ratio) list and fill the analyte table"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", self.default_dir, "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.clear_selections()
            with open(file_name, 'r') as f:
                for line in f.readlines():
                    field, norm = line.replace('\n','').split(',')
                    self.populate_analyte_list(field, norm)
            self.filename = os.path.basename(file_name)
            self.unsaved_changes = False
            self.update_window_title()
            self.update_list()
            self.raise_()
            self.activateWindow()
            self.show()
    
    def clear_selections(self):
        """Clears the current selections in the analyte table and selected list."""
        # Clear the selected analytes table
        self.tableWidgetSelected.setRowCount(0)
        self.tableWidgetSelected.clearContents()

        # Clear selection in the analyte table
        self.tableWidgetAnalytes.clearSelection()

        # Unselect any selected items in the analyte table
        for row in range(self.tableWidgetAnalytes.rowCount()):
            for column in range(self.tableWidgetAnalytes.columnCount()):
                item = self.tableWidgetAnalytes.item(row, column)
                if item:
                    item.setSelected(False)

        self.comboBoxScale.setCurrentIndex(0)
        self.comboBoxCorrelation.setCurrentIndex(0)

    def update_list(self):
        """Update the list of selected analytes""" 
        self.norm_dict={}
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            comboBox = self.tableWidgetSelected.cellWidget(i, 1)
            if not isinstance(comboBox, QComboBox):
                return
            self.norm_dict[analyte_pair] = comboBox.currentText()

            # update norm in data
            self.data.set_attribute(analyte_pair,'norm',comboBox.currentText())

    def populate_analyte_list(self, analyte_pair, norm='linear'):
        """Populates the list of selected analytes

        Parameters
        ----------
        analyte_pair : str
            Analyte or ratio, ratios are entered as analyte1 / analyte2.
        norm : str
            Normization method for vector, ``linear``, ``log``, and ``logit``, Defaults to ``linear``
        """        
        if '/' in analyte_pair:
            row_header, col_header = analyte_pair.split(' / ')
        else:
            row_header = col_header = analyte_pair
        # Select the cell in tableWidgetanalyte
        if row_header in self.analytes and col_header in self.analytes:
            row_index = self.analytes.index(row_header)
            col_index = self.analytes.index(col_header)

            item = self.tableWidgetAnalytes.item(row_index, col_index)
            if not item:
                item = QTableWidgetItem()
                self.tableWidgetAnalytes.setItem(row_index, col_index, item)
            item.setSelected(True)

            # Add the loaded data to tableWidgetSelected
            new_row = self.tableWidgetSelected.rowCount()
            self.tableWidgetSelected.insertRow(new_row)
            self.tableWidgetSelected.setItem(new_row, 0, QTableWidgetItem(analyte_pair))
            combo = QComboBox()
            combo.addItems(['linear', 'log', 'logit'])
            combo.setCurrentText(norm)
            self.tableWidgetSelected.setCellWidget(new_row, 1, combo)
            combo.currentIndexChanged.connect(self.update_scale)

    def event_filter(self, obj, event):
        """Highlights row and column header of tableWidgetAnalytes as mouse moves over cells.

        Parameters
        ----------
        obj : widget
            Widget that is currently under the mouse pointer.
        event : QEvent
            Triggered by motion of mouse pointer.

        Returns
        -------
        event_filter
            Updated event_filter.
        """        
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.MouseMove:
            # Get the row and column of the cell under the mouse
            index = self.tableWidgetAnalytes.indexAt(event.pos())
            row = index.row()
            col = index.column()

            # debugging
            if self.debug:
                print(f"Mouse location: ({row}, {col})")

            # Reset the previous row and column to normal font if they exist
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Normal, QBrush())
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Normal, QBrush())

            # Apply bold font to the current row and column headers
            if row >= 0:
                self._set_row_font(row, QFont.Bold, QBrush(QColor("yellow")))
                self.prev_row = row
            if col >= 0:
                self._set_col_font(col, QFont.Bold, QBrush(QColor("yellow")))
                self.prev_col = col

        # Handle resetting when the mouse leaves the widget
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.Leave:
            # Reset any bold headers when the mouse leaves the table
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Normal, QBrush())
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Normal, QBrush())
            self.prev_row = None
            self.prev_col = None

        self.tableWidgetAnalytes.viewport().update()  # Force a repaint

        return super().event_filter(obj, event)

    def _set_row_font(self, row, weight, brush):
        """Set the font weight for the vertical header row."""
        if row is not None:
            header_item = self.tableWidgetAnalytes.verticalHeaderItem(row)
            font = header_item.font()
            font.setWeight(weight)
            header_item.setFont(font)
            header_item.setBackground(brush)
            # Force a repaint
            self.tableWidgetAnalytes.viewport().update()

    def _set_col_font(self, col, weight, brush):
        """Set the font weight for the horizontal header column."""
        if col is not None:
            header_item = self.tableWidgetAnalytes.horizontalHeaderItem(col)
            font = header_item.font()
            font.setWeight(weight)
            header_item.setFont(font)
            header_item.setBackground(brush)
            # Force a repaint
            self.tableWidgetAnalytes.viewport().update()