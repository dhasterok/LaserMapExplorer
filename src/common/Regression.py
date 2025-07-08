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
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QToolBar
    )
from src.app.UITheme import default_font

class RegressionPage(CustomDockWidget):
    """Regression"""
    def __init__(self, page_index, parent=None):
        super().__init__(parent)

        if parent is None:
            return

        self.parent = parent

        toolbar = QToolbar(self)

        self.setGeometry(QtCore.QRect(0, 0, 264, 248))
        self.setObjectName("StyleRegression")

        page_layout = QtWidgets.QFormLayout(self)
        page_layout.setContentsMargins(3, 3, 3, 3)


        self.comboBoxRegressionMethod = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContentsRegression)
        self.comboBoxRegressionMethod.setFont(default_font())
        self.comboBoxRegressionMethod.addItems(['least squares', 'total least squares'])

        self.checkBox = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContentsRegression)
        self.checkBox.setFont(default_font())
        self.checkBox_2 = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContentsRegression)
        self.formLayout_13.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.checkBox_2)
        self.verticalLayout_78.addLayout(self.formLayout_13)
        spacerItem18 = QtWidgets.QSpacerItem(20, 257, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_78.addItem(spacerItem18)
        self.scrollAreaRegression.setWidget(self.scrollAreaWidgetContentsRegression)
        page_layout.addWidget(self.scrollAreaRegression)

        regression_icon = QtGui.QIcon(":/resources/icons/icon-regression-64.svg")
        self.toolBoxStyle.addItem(self.StyleRegression, regression_icon, "")
        self.verticalLayout_13.addWidget(self.toolBoxStyle)