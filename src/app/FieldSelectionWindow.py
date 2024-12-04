from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QEvent)
from PyQt5.QtWidgets import (QMessageBox, QTableWidget, QDialog, QTableWidgetItem, QLabel, QComboBox, QHeaderView, QFileDialog)
from PyQt5.QtGui import (QImage, QColor, QFont, QPixmap, QPainter, QBrush)
from src.ui.FieldSelectionDialog import Ui_FieldDialog
from src.common.rotated import RotatedHeaderView
from src.app.config import DEBUG_ANALYTE_UI
import os
# Analyte GUI
# -------------------------------
class FieldDialog(QDialog, Ui_FieldDialog):
    """Creates an dialog to select fields and create custom field lists

    Consist of a field type dropdown and a field dropdown which will be populated based on field type drowpdown

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
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

        if parent.sample_id is None or parent.sample_id == '':
            return

        self.data = parent.data[parent.sample_id].processed_data

                # Initialize filename and unsaved changes flag
        self.base_title ='LaME: Create custom field list'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()
        self.default_dir  = os.path.join(parent.BASEDIR, "resources", "field list")  

        self.field_type_combo.addItems(self.field_types)
        self.field_type_combo.currentIndexChanged.connect(self.update_field_dropdown)

    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def update_field_dropdown(self):
        # Get selected field type
        field_type = self.field_type_combo.currentText()
        # Update field dropdown
        self.field_combo.clear()
        self.field_combo.addItems(self.fields.get(field_type, []))

    def add_field(self):
        field = self.field_combo.currentText()
        if field and field not in self.selected_fields:
            self.selected_fields.append(field)
            self.update_table()
        else:
            QMessageBox.warning(self, 'Warning', 'Field already selected or invalid.')

    def delete_field(self):
        selected_row = self.table_widget.currentRow()
        if selected_row >= 0:
            field = self.table_widget.item(selected_row, 0).text()
            self.selected_fields.remove(field)
            self.table_widget.removeRow(selected_row)
        else:
            QMessageBox.warning(self, 'Warning', 'No field selected to delete.')

    def update_table(self):
        self.table_widget.setRowCount(0)
        for field in self.selected_fields:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(field))

    def load_fields(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Field List", self.default_dir, "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'r') as file:
                fields = file.read().splitlines()
                self.selected_fields = fields
                self.update_table()

    def save_fields(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Field List", self.default_dir, "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'w') as file:
                for field in self.selected_fields:
                    file.write(f"{field}\n")
            QMessageBox.information(self, 'Success', 'Field list saved successfully.')

    def done_selection(self):
        # Emit the selected fields
        self.listUpdated.emit(self.selected_fields)
        self.accept()

    def cancel_selection(self):
        self.reject()