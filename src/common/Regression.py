# Right now, this is just notes
# Need regression codes that handle linear fitting using total Least-Squares or Deming regression or something similar.
# Fix the intercept (for dating) or the slope(?)
# Need to mask or filter selected points?
# Would be good to include leverage analysis.
# Produce regressions for individual clusters.
# Add annotations for certain types of fits?
# Add equations and stats

from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import ( 
        QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView
    )

class RegressionPage(QWidget):
    def __init__(self, page_index, parent=None):
        super().__init__(parent)

        if parent is None:
            return

        self.parent = parent