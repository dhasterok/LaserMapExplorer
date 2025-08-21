from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QComboBox, QLineEdit, QLabel
)
import matplotlib.pyplot as plt
import cmcrameri.cm as cmr
import sys

# --- Collect colormap names ---
def get_cmr_colormap_names():
    """Return a flat list of all Crameri colormap names."""
    names = []
    for attr in dir(cmr):
        if attr.startswith("_cmap_names"):
            val = getattr(cmr, attr)
            if isinstance(val, (list, tuple)):
                names.extend(val)
    return sorted(set(names))


class ColormapSelector(QWidget):
    def __init__(self, custom_maps=None, parent=None):
        super().__init__(parent)

        # --- Data sources ---
        self.maps = {
            "Matplotlib": sorted(
                name for name in plt.colormaps()
                if not name.endswith("_r") and not name.startswith("cmc.")
            ),
            "Crameri": get_cmr_colormap_names(),
            "Custom": custom_maps or []
        }

        # --- Widgets ---
        layout = QVBoxLayout(self)

        self.source_combo = QComboBox()
        self.source_combo.addItems(self.maps.keys())

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search colormaps...")

        self.cmap_combo = QComboBox()

        layout.addWidget(QLabel("Colormap Source:"))
        layout.addWidget(self.source_combo)
        layout.addWidget(QLabel("Search:"))
        layout.addWidget(self.search_box)
        layout.addWidget(QLabel("Colormap:"))
        layout.addWidget(self.cmap_combo)

        # --- Signals ---
        self.source_combo.currentTextChanged.connect(self.update_cmap_combo)
        self.search_box.textChanged.connect(self.update_cmap_combo)

        # --- Initialize ---
        self.update_cmap_combo()

    def update_cmap_combo(self):
        """Update colormap combobox based on current source and search."""
        source = self.source_combo.currentText()
        all_items = self.maps[source]

        filter_text = self.search_box.text().lower()
        filtered = [name for name in all_items if filter_text in name.lower()]

        self.cmap_combo.clear()
        self.cmap_combo.addItems(filtered)

    def get_selected_cmap(self):
        """Return the currently selected colormap name."""
        return self.cmap_combo.currentText()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colormap Selector Example")
        self.setCentralWidget(ColormapSelector(custom_maps=["my_custom_1", "my_custom_2"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())