from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QEvent)
from PyQt5.QtWidgets import (
    QMessageBox, QTableWidget, QDialog, QTableWidgetItem, QLabel, QComboBox,
    QHeaderView, QFileDialog, QListWidget, QAbstractItemView
)
from PyQt5.QtGui import (QImage, QColor, QFont, QPixmap, QPainter, QBrush)
from src.ui.FieldSelectionDialog import Ui_FieldDialog
from src.common.rotated import RotatedHeaderView
from src.app.config import BASEDIR
import os

class FieldDialog(QDialog, Ui_FieldDialog):
    """
    Creates a dialog to select fields (with their types) and create custom field lists.

    - The user selects a field type from comboBoxFieldType.
    - listWidgetFieldList is populated with all available fields for that field type.
    - The user can multi-select from listWidgetFieldList and add them to tableWidgetSelectedFields,
      which stores pairs of (field_name, field_type).
    - The user can also remove multiple selected fields from tableWidgetSelectedFields.

    A Save/Load mechanism allows storing/loading field name/type pairs in a text file.
    """

    def __init__(self, parent):
        if (parent.__class__.__name__ == 'Main'):
            super().__init__() #initialisng with no parent widget
        else:
            super().__init__(parent) #initialise with mainWindow as parentWidget
        self.setupUi(self)

        # Example: only continue if sample_id is given in the parent (this is your existing logic).
        if not getattr(parent, 'sample_id', None):
            return
        self.parent = parent
        # Store the reference to BASEDIR from parent (if needed).
        self.default_dir = os.path.join(parent.BASEDIR, "resources", "field_list") \
                           if hasattr(parent, "BASEDIR") else os.getcwd()

        # Initialize fields dictionary: { field_type: [field1, field2, ...], ... }
        # You might already have this dictionary in your class.
        # Adjust it as needed. This is just an example structure.
        self.fields = {
            "Type A": ["Field A1", "Field A2", "Field A3"],
            "Type B": ["Field B1", "Field B2"],
            "Type C": ["Field C1", "Field C2", "Field C3", "Field C4"]
        }

        # Set up the UI elements for multi-selection:
        self.listWidgetFieldList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tableWidgetSelectedFields.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidgetSelectedFields.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Configure tableWidgetSelectedFields with two columns: Field and Field Type
        self.tableWidgetSelectedFields.setColumnCount(2)
        self.tableWidgetSelectedFields.setHorizontalHeaderLabels(["Field", "Field Type"])
        self.tableWidgetSelectedFields.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Data structure to store selected fields as tuples: (field_type, field_name)
        self.selected_fields = []

        # Initialize file-related variables
        self.base_title = 'LaME: Create custom field list'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()

        # Connect signals/slots
        # You should have a comboBoxFieldType in your .ui for selecting the field type.
        # If you named it differently, adjust accordingly.
        
        self.update_field_type_list() 
        self.comboBoxFieldType.currentIndexChanged.connect(self.update_field_list)

        self.toolButtonAddField.clicked.connect(self.add_fields)
        self.toolButtonRemoveField.clicked.connect(self.delete_fields)
        self.pushButtonSave.clicked.connect(self.save_selection)
        self.pushButtonLoad.clicked.connect(self.load_selection)
        self.pushButtonDone.clicked.connect(self.done_selection)
        self.pushButtonCancel.clicked.connect(self.cancel_selection)

        # Initialize the field list with the first field type.
        self.update_field_list()


    # --------------------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------------------
    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def update_field_type_list(self):
        """Populate the comboBoxfieldTypes with available field types."""
        self.comboBoxFieldType.clear()
        field_type_list = self.parent.field_type_list
        for f in field_type_list:
            self.comboBoxFieldType.addItem(f)
    
    def update_field_list(self):
        """Populate the listWidgetFieldList with fields for the current field type."""
        self.listWidgetFieldList.clear()
        field_type = self.comboBoxFieldType.currentText()
        
        field_list = self.parent.get_field_list(field_type)
        for f in field_list:
            self.listWidgetFieldList.addItem(f)

    def update_table(self):
        """Refresh the tableWidgetSelectedFields to match self.selected_fields."""
        self.tableWidgetSelectedFields.setRowCount(0)
        for row_idx, (field_type, field_name) in enumerate(self.selected_fields):
            self.tableWidgetSelectedFields.insertRow(row_idx)
            self.tableWidgetSelectedFields.setItem(row_idx, 0, QTableWidgetItem(field_name))
            self.tableWidgetSelectedFields.setItem(row_idx, 1, QTableWidgetItem(field_type))

    # --------------------------------------------------------------------------
    # Add / Remove
    # --------------------------------------------------------------------------
    def add_fields(self):
        """
        Add the currently selected fields (from listWidgetFieldList) to tableWidgetSelectedFields.
        Each added entry is a tuple (field_type, field_name).
        """
        field_type = self.comboBoxFieldType.currentText()

        selected_items = self.listWidgetFieldList.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Warning', 'No fields selected to add.')
            return

        # For each selected item, add to self.selected_fields if not already present
        added_any = False
        for item in selected_items:
            field_name = item.text()
            if (field_type, field_name) not in self.selected_fields:
                self.selected_fields.append((field_type, field_name))
                added_any = True

        if added_any:
            self.update_table()
            self.unsaved_changes = True
            self.update_window_title()
        else:
            QMessageBox.information(self, 'Info', 'Selected field(s) already in the list.')

    def delete_fields(self):
        """
        Remove the selected row(s) from tableWidgetSelectedFields (and self.selected_fields).
        """
        selected_ranges = self.tableWidgetSelectedFields.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, 'Warning', 'No fields selected to remove.')
            return

        # Collect all selected row indices
        rows_to_remove = []
        for selection_range in selected_ranges:
            top = selection_range.topRow()
            bottom = selection_range.bottomRow()
            rows_to_remove.extend(range(top, bottom + 1))

        # Remove from self.selected_fields in descending order (to keep indices valid)
        for row_idx in sorted(rows_to_remove, reverse=True):
            if 0 <= row_idx < len(self.selected_fields):
                del self.selected_fields[row_idx]

        self.update_table()
        self.unsaved_changes = True
        self.update_window_title()

    # --------------------------------------------------------------------------
    # Load / Save
    # --------------------------------------------------------------------------
    def load_selection(self):
        """
        Loads field name/type pairs from a text file.

        Each line is expected to be in the format:
            field_type,field_name
        (You can change the delimiter to anything else you prefer.)
        """
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        loaded_fields = []
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                # Example format: Type A,Field A2
                if ',' in line:
                    f_type, f_name = line.split(',', 1)
                    loaded_fields.append((f_type, f_name))
                else:
                    # If the file doesn't have the correct format,
                    # you could handle it here or skip.
                    pass

        self.selected_fields = loaded_fields
        self.update_table()

        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        # Bring the dialog to front
        self.raise_()
        self.activateWindow()
        self.show()

    def save_selection(self):
        """
        Saves the current selected fields (field_type, field_name) into a text file.

        Each line will be in the format:
            field_type,field_name
        """
        if not self.selected_fields:
            QMessageBox.warning(self, 'Warning', 'No fields to save.')
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        with open(file_name, 'w', encoding='utf-8') as file:
            for (field_type, field_name) in self.selected_fields:
                file.write(f"{field_type},{field_name}\n")

        QMessageBox.information(self, 'Success', 'Field list saved successfully.')
        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        self.raise_()
        self.activateWindow()
        self.show()

    # --------------------------------------------------------------------------
    # Done / Cancel
    # --------------------------------------------------------------------------
    def done_selection(self):
        """
        Executes when 'Done' button is clicked.  
        If unsaved changes exist, prompt the user to save or discard.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_selection()
                self.accept()
            elif reply == QMessageBox.No:
                self.accept()
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.accept()

    def cancel_selection(self):
        """
        Handles the 'Cancel' button click.
        If unsaved changes exist, prompt user to save or discard.
        """
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
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.reject()

    # --------------------------------------------------------------------------
    # Close event override (X button)
    # --------------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Overrides the close event to check for unsaved changes.
        """
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
            else:
                event.ignore()
        else:
            event.accept()
