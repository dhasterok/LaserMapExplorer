from PyQt6.QtWidgets import QDialog, QMessageBox

class BaseSelectionDialog(QDialog):
    """
    Base dialog class for selection dialogs with common save/load/close/unsaved logic.
    Subclasses should implement:
        - save_selection()
        - load_selection()
        - update_table() or similar UI refresh
    """
    def __init__(self, parent=None, base_title='Dialog', filename='untitled'):
        super().__init__(parent)
        self.base_title = base_title
        self.filename = filename
        self.unsaved_changes = False
        self.update_window_title()

    def update_window_title(self):
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def mark_unsaved(self, unsaved=True):
        self.unsaved_changes = unsaved
        self.update_window_title()

    def done_selection(self):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.accept()
            else:
                pass  # Cancel: do nothing
        else:
            self.accept()

    def cancel_selection(self):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
            else:
                pass  # Cancel: do nothing
        else:
            self.reject()

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
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

    # The following should be implemented by subclasses:
    def save_selection(self):
        raise NotImplementedError

    def load_selection(self):
        raise NotImplementedError
