from PyQt5.QtCore import (Qt, pyqtSignal)
from PyQt5.QtWidgets import (QDialog, QTableWidgetItem, QLabel, QComboBox, QHeaderView, QFileDialog)
from PyQt5.QtGui import (QImage, QColor, QPixmap, QPainter)
from src.ui.AnalyteSelectionDialog import Ui_Dialog
from src.rotated import RotatedHeaderView

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
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.analytes = self.data.match_attribute('data_type','analyte')
        self.norm_dict = {}
        for analyte in self.analytes:
            self.norm_dict[analyte] = self.data.get_attribute(analyte,'norm')
        self.data = data
        self.correlation_matrix = None
        self.tableWidgetAnalytes.setRowCount(len(self.analytes))
        self.tableWidgetAnalytes.setColumnCount(len(self.analytes))
        self.tableWidgetAnalytes.setHorizontalHeaderLabels(list(self.analytes))
        self.tableWidgetAnalytes.setHorizontalHeader(RotatedHeaderView(self.tableWidgetAnalytes))
        self.tableWidgetAnalytes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableWidgetAnalytes.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.comboBoxScale.currentIndexChanged.connect(self.update_all_combos)

        self.tableWidgetAnalytes.setVerticalHeaderLabels(self.analytes)
        self.correlation_methods = ["Pearson", "Spearman"]

        for method in self.correlation_methods:
            self.comboBoxCorrelation.addItem(method)

        self.calculate_correlation()

        self.tableWidgetAnalytes.cellClicked.connect(self.toggle_cell_selection)

        self.tableWidgetSelected.setColumnCount(2)
        self.tableWidgetSelected.setHorizontalHeaderLabels(['analyte Pair', 'normalisation'])

        self.pushButtonSaveSelection.clicked.connect(self.save_selection)

        self.pushButtonLoadSelection.clicked.connect(self.load_selection)

        self.pushButtonDone.clicked.connect(self.done_selection)

        self.pushButtonCancel.clicked.connect(self.reject)
        self.comboBoxCorrelation.activated.connect(self.calculate_correlation)
        self.tableWidgetAnalytes.setStyleSheet("QTableWidget::item:selected {background-color: yellow;}")
        if len(self.norm_dict.keys())>0:
            for analyte,norm in self.norm_dict.items():
                self.populate_analyte_list(analyte,norm)
        else:
            # Select diagonal pairs by default
            for i in range(len(self.analytes)):
                row=column = i
                item = self.tableWidgetAnalytes.item(row, column)

                # If the item doesn't exist, create it
                if not item:
                    item = QTableWidgetItem()
                    self.tableWidgetAnalytes.setItem(row, column, item)
                    self.add_analyte_to_list(row, column)
                # If the cell is already selected, deselect it
                elif not item.isSelected():
                    item.setSelected(True)
                    self.add_analyte_to_list(row, column)
                else:
                    item.setSelected(False)
                    self.remove_analyte_from_list(row, column)

    def done_selection(self):
        """Executes when `Done` button is clicked."""        
        self.update_list()
        self.accept()

    def update_all_combos(self):
        """_summary_
        """        
        # Get the currently selected value in comboBoxScale
        selected_scale = self.comboBoxScale.currentText()

        # Iterate through all rows in tableWidgetSelected to update combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if combo is not None:  # Make sure there is a combo box in this cell
                combo.setCurrentText(selected_scale)  # Update the combo box value

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

    def calculate_correlation(self):
        """_summary_
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
        """_summary_

        _extended_summary_

        Parameters
        ----------
        correlation : _type_
            _description_

        Returns
        -------
        _type_
            _description_
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
        """_summary_
        """        
        colorbar_image = self.generate_colorbar_image(40, 200)  # Width, Height of colorbar
        colorbar_label = QLabel(self)
        colorbar_pixmap = QPixmap.fromImage(colorbar_image)
        self.labelColorbar.setPixmap(colorbar_pixmap)

    def generate_colorbar_image(self, width, height):
        """_summary_

        Parameters
        ----------
        width : _type_  
            _description_
        height : _type_
            _description_

        Returns
        -------
        _type_
            _description_
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
        """_summary_

        Parameters
        ----------
        row : _type_
            _description_
        column : _type_
            _description_
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
        """_summary_

        Parameters
        ----------
        row : _type_
            _description_
        column : _type_
            _description_
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

    def remove_analyte_from_list(self, row, column):
        """_summary_

        Parameters
        ----------
        row : _type_
            _description_
        column : _type_
            _description_
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

    def get_selected_data(self):
        """_summary_

        Returns
        -------
        _type_
            _description_
        """        
        data = []
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            data.append((analyte_pair, selection))
        return data

    def save_selection(self):
        """_summary_
        """        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    analyte_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{analyte_pair},{selection}\n")

    def load_selection(self):
        """Load a saved analyte lists"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r') as f:
                for line in f.readlines():
                    self.populate_analyte_list(line)
            self.update_list()
            self.raise_()
            self.activateWindow()

    def update_list(self):
        """Update the list of selected analytes""" 
        self.norm_dict={}
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            self.norm_dict[analyte_pair] = selection
        self.listUpdated.emit()

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
        if row_header in self.analytes:
            row_index = self.analytes.index(row_header)
            col_index = self.analytes.index(col_header)

            item = self.tableWidgetAnalytes.item(row_index, col_index)
            if not item:
                item = QTableWidgetItem()
                self.tableWidgetAnalytes.setItem(row_index, col_index, item)
            item.setSelected(True)

            # Add the loaded data to tableWidgetSelected
            newRow = self.tableWidgetSelected.rowCount()
            self.tableWidgetSelected.insertRow(newRow)
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(analyte_pair))
            combo = QComboBox()
            combo.addItems(['linear', 'log', 'logit'])
            combo.setCurrentText(norm)
            self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
            combo.currentIndexChanged.connect(self.update_scale)

