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
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

        if parent.sample_id is None or parent.sample_id == '':
            return

        # Initialize filename and unsaved changes flag
        self.base_title ='LaME: Create custom field list'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()
        self.default_dir  = os.path.join(parent.BASEDIR, "resources", "field_list")  
        self.selected_fields = []
        self.comboBoxField.addItems(self.field_types)
        self.comboBoxField.currentIndexChanged.connect(self.update_field_dropdown)

         # UI buttons
        self.toolButtonAddField.clicked.connect(self.add_field)
        self.toolButtonRemoveField.clicked.connect(self.delete_field)
        self.pushButtonSave.clicked.connect(self.save_selection)
        self.pushButtonLoad.clicked.connect(self.load_selection)
        self.pushButtonDone.clicked.connect(self.done_selection)
        self.pushButtonCancel.clicked.connect(self.cancel_selection)


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
        field = self.comboBoxField.currentText()
        if field and field not in self.selected_fields:
            self.selected_fields.append(field)
            self.update_table()
            self.unsaved_changes = True
            self.update_window_title()
        else:
            QMessageBox.warning(self, 'Warning', 'Field already selected or invalid.')

    def delete_field(self):
        selected_items = self.listWidgetFieldList.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Warning', 'No field selected to delete.')
            return
        for item in selected_items:
            field = item.text()
            self.selected_fields.remove(field)
            self.listWidgetFieldList.takeItem(self.listWidgetFieldList.row(item))
        self.unsaved_changes = True
        self.update_window_title()

    def update_table(self):
        self.listWidgetFieldList.setRowCount(0)
        for field in self.selected_fields:
            row = self.listWidgetFieldList.rowCount()
            self.listWidgetFieldList.insertRow(row)
            self.listWidgetFieldList.setItem(row, 0, QTableWidgetItem(field))

    def load_selection(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Field List", self.default_dir, "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'r') as file:
                fields = file.read().splitlines()
                self.selected_fields = fields
                self.update_table()
            self.filename = os.path.basename(file_name)
            self.unsaved_changes = False
            self.update_window_title()

            self.raise_()
            self.activateWindow()
            self.show()

    def save_selection(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Field List", self.default_dir, "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'w') as file:
                for field in self.selected_fields:
                    file.write(f"{field}\n")
            QMessageBox.information(self, 'Success', 'Field list saved successfully.')

            self.filename = os.path.basename(file_name)
            self.unsaved_changes = False
            self.update_window_title()
            self.raise_()
            self.activateWindow()
            self.show()

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