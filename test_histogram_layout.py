from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QVBoxLayout,
    QDoubleSpinBox, QSpinBox, QToolButton, QComboBox, QApplication
)
from PyQt6.QtCore import Qt
import sys


class HistogramGroupBox(QWidget):
    def __init__(self):
        super().__init__()
        self.setupUI()

    def setupUI(self):
        self.setObjectName("groupBoxHistogram")

        form_layout = QFormLayout(self)
        form_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(form_layout)

        # --- Bin width row ---
        self.doubleSpinBoxBinWidth = QDoubleSpinBox(parent=self)
        self.doubleSpinBoxBinWidth.setMaximum(100000.0)
        self.doubleSpinBoxBinWidth.setObjectName("doubleSpinBoxBinWidth")
        form_layout.addRow("Bin width", self.doubleSpinBoxBinWidth)

        # --- Number of bins row (with Reset button and link button) ---
        bin_widget = QWidget(parent=self)
        bin_layout = QHBoxLayout(bin_widget)
        bin_layout.setContentsMargins(0, 0, 0, 0)
        bin_layout.setSpacing(6)

        # Vertical layout for spin box + optional other controls stacked
        spin_layout = QVBoxLayout()
        spin_layout.setContentsMargins(0, 0, 0, 0)
        spin_layout.setSpacing(6)
        self.spinBoxNBins = QSpinBox(parent=self)
        self.spinBoxNBins.setMinimum(1)
        self.spinBoxNBins.setMaximum(500)
        self.spinBoxNBins.setObjectName("spinBoxNBins")

        # Optional Reset button
        self.toolButtonHistogramReset = QToolButton(parent=self)
        self.toolButtonHistogramReset.setText("Reset")
        self.toolButtonHistogramReset.setToolTip("Reset number of bins to default value.")
        self.toolButtonHistogramReset.setObjectName("toolButtonHistogramReset")
        self.toolButtonHistogramReset.setFixedHeight(self.spinBoxNBins.sizeHint().height())

        spin_layout.addWidget(self.spinBoxNBins)
        bin_layout.addLayout(spin_layout)

        # Add Reset button next to the spin box
        bin_layout.addWidget(self.toolButtonHistogramReset, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Add link button (centered vertically between the spin box and Reset button if needed)
        self.linkButton = QToolButton(parent=bin_widget)
        self.linkButton.setCheckable(True)
        self.linkButton.setChecked(True)
        self.linkButton.setText("🔗")
        self.linkButton.setFixedSize(30, 30)

        # Use a vertical layout with stretch to center the button
        link_layout = QVBoxLayout()
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.addStretch()
        link_layout.addWidget(self.linkButton, alignment=Qt.AlignmentFlag.AlignCenter)
        link_layout.addStretch()
        bin_layout.addLayout(link_layout)

        form_layout.addRow("No. Bins", bin_widget)

        # --- Histogram type combo ---
        self.comboBoxHistType = QComboBox(parent=self)
        self.comboBoxHistType.setObjectName("comboBoxHistType")
        form_layout.addRow("Histogram type", self.comboBoxHistType)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = HistogramGroupBox()
    w.resize(400, 200)
    w.show()
    sys.exit(app.exec())
