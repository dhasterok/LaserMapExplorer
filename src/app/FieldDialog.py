from pathlib import Path
from PyQt6.QtWidgets import (
    QMessageBox, QDialog, QComboBox, QFileDialog, QVBoxLayout, QHBoxLayout,
    QDialogButtonBox, QToolButton, QMenu
)
from src.app.config import BASEDIR, ICONPATH, RESOURCE_PATH
from src.common.CustomWidgets import CustomToolButton
from src.common.DualWidgetList import DualListWidget
from src.common.SortAnalytes import sort_analytes

class FieldDialog(QDialog):
    """
    Dialog for selecting fields by type and creating custom field lists.

    This dialog allows the user to:
      - Select a field type (e.g., Analyte, Ratio, Metadata).
      - Move fields between available and selected lists.
      - Sort fields according to type-specific methods.
      - Save and load field selections from a text file.

    Parameters
    ----------
    parent : QWidget
        The parent widget, typically the main application window.
    """

    def __init__(self, parent):
        if parent.__class__.__name__ == 'Main':
            super().__init__()  # detached
        else:
            super().__init__(parent)

        # Only initialize if parent has valid sample_id
        if not getattr(parent, "sample_id", None):
            return

        self.parent = parent
        self.setup_ui()

        # Default directory for load/save
        self.default_dir = (parent.RESOURCE_PATH / "field_list"
                            if hasattr(parent, "RESOURCE_PATH")
                            else Path.cwd())

        # Initialize state from attribute dictionary
        self.field_state = self.init_field_lists(
            parent.app_data.current_data.column_attributes
        )
        self.selected_state = {ftype: [] for ftype in self.field_state}

        # File-related variables
        self.base_title = "LaME: Create custom field list"
        self.filename = "untitled"
        self.unsaved_changes = False
        self.update_window_title()

        # Connect signals/slots
        self.comboBoxFieldType.currentTextChanged.connect(self.load_fields)
        self.dual_list.movedRight.connect(self._update_selected)
        self.dual_list.movedLeft.connect(self._update_selected)
        self.dual_list.movedLeft.connect(
            lambda _: self.sort_left_list(
                self.comboBoxFieldType.currentText(),
                self.field_state[self.comboBoxFieldType.currentText()]["sort"]
            )
        )

        self.button_box.accepted.connect(self.done_selection)
        self.button_box.rejected.connect(self.cancel_selection)
        self.button_box.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.save_selection)
        self.button_box.button(QDialogButtonBox.StandardButton.Open).clicked.connect(self.load_selection)

        # Initialize with current field type
        self.load_fields(self.comboBoxFieldType.currentText())

    # --------------------------------------------------------------------------
    # UI setup
    # --------------------------------------------------------------------------
    def setup_ui(self):
        """Initialize dialog widgets and layout."""
        self.resize(550, 300)

        self.comboBoxFieldType = QComboBox(parent=self)

        self.toolButtonSort = CustomToolButton(
            text="Sort Menu",
            light_icon_unchecked="icon-sort-64.svg",
            dark_icon_unchecked="icon-sort-dark-64.svg",
            parent=self,
        )
        self.toolButtonSort.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.dual_list = DualListWidget()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Open
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )

        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(12, 12, 12, 12)
        self.setLayout(dialog_layout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.comboBoxFieldType)
        hlayout.addWidget(self.toolButtonSort)

        dialog_layout.addLayout(hlayout)
        dialog_layout.addWidget(self.dual_list)
        dialog_layout.addWidget(self.button_box)

        self.show()

    # --------------------------------------------------------------------------
    # State initialization
    # --------------------------------------------------------------------------
    def init_field_lists(self, attribute_dict: dict):
        """
        Initialize the field state from a column attribute dictionary.

        Parameters
        ----------
        attribute_dict : dict
            Mapping of field name → metadata, where metadata includes 'data_type'.

        Returns
        -------
        dict
            Nested dict of the form:
            {
                field_type: {
                    "fields": [field_name, ...],
                    "sort": default_sort_method
                }
            }
        """
        field_state = {}

        for field_name, meta in attribute_dict.items():
            data_type = meta.get("data_type")
            if not data_type or data_type.lower() == "coordinates":
                continue  # skip coordinates

            if data_type not in field_state:
                if data_type in ["Analyte", "Analyte (normalized)", "Ratio", "Ratio (normalized)"]:
                    field_state[data_type] = {"fields": [], "sort": "mass"}
                else:
                    field_state[data_type] = {"fields": [], "sort": "alphanumeric"}

            field_state[data_type]["fields"].append(field_name)

        # Populate combobox
        self.comboBoxFieldType.clear()
        self.comboBoxFieldType.addItems(sorted(field_state.keys()))

        return field_state

    # --------------------------------------------------------------------------
    # UI helpers
    # --------------------------------------------------------------------------
    def update_window_title(self):
        """Update the window title with filename and unsaved marker."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += "*"
        self.setWindowTitle(title)

    # --------------------------------------------------------------------------
    # Add / Remove
    # --------------------------------------------------------------------------
    def load_fields(self, field_type: str):
        """
        Populate the dual list with available/selected items for a field type.

        Parameters
        ----------
        field_type : str
            The type of field to display (e.g., 'Analyte', 'Metadata').
        """
        selected = self.selected_state[field_type]
        available = [f for f in self.field_state[field_type]["fields"]
                     if f not in selected]

        self.dual_list.set_available_items(available)
        self.dual_list.set_selected_items(selected)
        self.update_sort_menu(field_type)

    def _update_selected(self, _):
        """Update selection state when items are moved left/right."""
        field_type = self.comboBoxFieldType.currentText()
        self.selected_state[field_type] = self.dual_list.selected_items()
        self.unsaved_changes = True
        self.update_window_title()

    def update_sort_menu(self, field_type: str):
        """Update the sort menu based on field type."""
        menu = QMenu(self)

        def sort_fields(method: str):
            self.field_state[field_type]["sort"] = method
            self.sort_left_list(field_type, method)
            self.unsaved_changes = True
            self.update_window_title()

        if field_type in ["Analyte", "Analyte (normalized)", "Ratio", "Ratio (normalized)"]:
            sortmenu_items = [
                ("Alphabetical", "alphabetical"),
                ("Atomic number", "atomic number"),
                ("Mass", "mass"),
                ("Compatibility", "compatibility"),
                ("Radius", "radius"),
            ]
        else:
            sortmenu_items = [("Alphanumeric", "alphanumeric")]

        for text, method in sortmenu_items:
            act = menu.addAction(text, lambda m=method: sort_fields(m))
            if method == self.field_state[field_type]["sort"]:
                act.setCheckable(True)
                act.setChecked(True)

        self.toolButtonSort.setMenu(menu)

    def sort_left_list(self, field_type: str, method: str):
        """
        Sort the available list for a given field type.

        Parameters
        ----------
        field_type : str
            Field type to sort.
        method : str
            Sorting method.
        """
        items = self.dual_list.available_items()
        if field_type in ["Analyte", "Analyte (normalized)", "Ratio", "Ratio (normalized)"]:
            sorted_items = sort_analytes(method, items, order="a")
        else:
            sorted_items = sorted(items, key=str.lower)

        self.dual_list.set_available_items(sorted_items)

    # --------------------------------------------------------------------------
    # Save / Load
    # --------------------------------------------------------------------------
    def flatten_selected(self):
        """Return a flat list of (field_type, field_name) from selected_state."""
        result = []
        for ftype, fields in self.selected_state.items():
            for f in fields:
                result.append((ftype, f))
        return result

    def restore_selected(self, selected_fields):
        """Restore selected_state from a list of (field_type, field_name)."""
        self.selected_state = {ftype: [] for ftype in self.field_state}
        for ftype, fname in selected_fields:
            if ftype in self.selected_state:
                self.selected_state[ftype].append(fname)

    def load_selection(self):
        """Load field selections from a text file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Field List", str(self.default_dir),
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_path:
            return

        file_path = Path(file_path)
        loaded_fields = []

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and "," in line:
                    f_type, f_name = line.split(",", 1)
                    loaded_fields.append((f_type, f_name))

        self.restore_selected(loaded_fields)
        self.load_fields(self.comboBoxFieldType.currentText())
        self.filename = file_path.name
        self.unsaved_changes = False
        self.update_window_title()
        self.raise_()
        self.activateWindow()
        self.show()

    def save_selection(self):
        """Save current selections to a text file."""
        if not any(self.selected_state.values()):
            QMessageBox.warning(self, "Warning", "No fields to save.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Field List", str(self.default_dir),
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_path:
            return

        file_path = Path(file_path)
        with file_path.open("w", encoding="utf-8") as file:
            for ftype, fname in self.flatten_selected():
                file.write(f"{ftype},{fname}\n")

        QMessageBox.information(self, "Success", "Field list saved successfully.")
        self.filename = file_path.name
        self.unsaved_changes = False
        self.update_window_title()
        self.raise_()
        self.activateWindow()
        self.show()

    # --------------------------------------------------------------------------
    # Done / Cancel
    # --------------------------------------------------------------------------
    def done_selection(self):
        """Handle 'OK/Done' button with unsaved check."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.accept()
        else:
            self.accept()

    def cancel_selection(self):
        """Handle 'Cancel' button with unsaved check."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
        else:
            self.reject()

    def closeEvent(self, event):
        """Override close event with unsaved check."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()