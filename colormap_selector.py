from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit
import matplotlib.pyplot as plt
import cmcrameri.cm as cmr
import sys

class ColormapSelector(QWidget):
    def __init__(self, custom_maps=None):
        super().__init__()
        self.setWindowTitle("Colormap Selector")
        layout = QVBoxLayout(self)

        # --- Colormap sets ---
        self.set_combo = QComboBox()
        self.set_combo.addItems(["All", "Matplotlib", "Crameri", "Custom"])
        layout.addWidget(QLabel("Set:"))
        layout.addWidget(self.set_combo)

        # --- Search box ---
        self.search_box = QLineEdit()
        layout.addWidget(QLabel("Search:"))
        layout.addWidget(self.search_box)

        # --- Colormap combobox ---
        self.cmap_combo = QComboBox()
        layout.addWidget(self.cmap_combo)

        # --- Store maps ---
        self.maps = {
            "Matplotlib": [name for name in plt.colormaps() if not name.endswith('_r')],
            "Crameri": list(cmr.keys()),
            "Custom": custom_maps or []
        }

        # --- Connect signals ---
        self.set_combo.currentTextChanged.connect(self.update_maps)
        self.search_box.textChanged.connect(self.update_maps)

        # Initial population
        self.update_maps()

    def update_maps(self):
        set_name = self.set_combo.currentText()
        search = self.search_box.text().lower()

        # Aggregate maps based on set
        if set_name == "All":
            names = sum(self.maps.values(), [])
        else:
            names = self.maps.get(set_name, [])

        # Apply search filter
        filtered = [n for n in names if search in n.lower()]

        # Update combobox
        self.cmap_combo.clear()
        self.cmap_combo.addItems(filtered)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ColormapSelector(custom_maps=["mymap1", "mymap2"])
    window.show()
    sys.exit(app.exec())