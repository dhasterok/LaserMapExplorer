"""
Color selector dialog and standalone application.
Provides a dialog for selecting colors with history and preview.

Author: Derrick Hasterok
Date: 2024-06-20
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog

from src.common.ColorSelector import ColorSelectorDialog
from src.common.ColorManager import convert_color

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Selector")
        self.current_color = (1.0, 1.0, 1.0)
        self.setupUI()

    def setupUI(self):
        # Create the dialog content as central widget
        self.dialog = ColorSelectorDialog()
        self.setCentralWidget(self.dialog)
        
        # Override the dialog buttons for main window
        self.dialog.btn_ok.setText("Apply")
        self.dialog.btn_cancel.setText("Exit")
        
        # Connect buttons differently
        self.dialog.btn_ok.clicked.disconnect()
        self.dialog.btn_cancel.clicked.disconnect()
        self.dialog.btn_ok.clicked.connect(self.apply_color)
        self.dialog.btn_cancel.clicked.connect(self.close)

    def apply_color(self):
        """Handle Apply button in standalone mode"""
        print("Selected color:", convert_color(self.dialog.current_color, "rgb", "hex", norm_in=True))

def select_color(initial_color=None, parent=None):
    """
    Show color selector dialog and return selected color.
    
    Args:
        initial_color: Initial color as hex string (e.g., "#FF0000") or None for white
        parent: Parent widget for the dialog
        
    Returns:
        Selected color as hex string (e.g., "#FF0000") or None if cancelled
    """
    dialog = ColorSelectorDialog(initial_color, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.selected_color
    return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Example of using as dialog
    if len(sys.argv) > 1 and sys.argv[1] == "--dialog":
        initial_color = "#FF5733" if len(sys.argv) > 2 else None
        result = select_color(initial_color)
        if result:
            print(f"Selected color: {result}")
        else:
            print("No color selected")
    else:
        # Run as standalone application
        w = MainWindow()
        w.show()
        sys.exit(app.exec())
