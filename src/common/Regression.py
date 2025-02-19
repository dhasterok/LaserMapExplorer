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

        self.setGeometry(QtCore.QRect(0, 0, 264, 248))
        self.setObjectName("StyleRegression")

        page_layout = QtWidgets.QVBoxLayout(self.StyleRegression)
        page_layout.setContentsMargins(3, 3, 3, 3)

        self.formLayout_13 = QtWidgets.QFormLayout()
        self.formLayout_13.setObjectName("formLayout_13")
        self.label_4 = QtWidgets.QLabel(parent=self.scrollAreaWidgetContentsRegression)
        self.label_4.setObjectName("label_4")
        self.formLayout_13.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.label_4)
        self.label_2 = QtWidgets.QLabel(parent=self.scrollAreaWidgetContentsRegression)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.formLayout_13.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.label_2)
        self.comboBoxRegressionMethod = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContentsRegression)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.comboBoxRegressionMethod.setFont(font)
        self.comboBoxRegressionMethod.setObjectName("comboBoxRegressionMethod")
        self.comboBoxRegressionMethod.addItem("")
        self.comboBoxRegressionMethod.addItem("")
        self.formLayout_13.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.comboBoxRegressionMethod)
        self.label_3 = QtWidgets.QLabel(parent=self.scrollAreaWidgetContentsRegression)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.formLayout_13.setWidget(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.label_3)
        self.checkBox = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContentsRegression)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.checkBox.setFont(font)
        self.checkBox.setText("")
        self.checkBox.setObjectName("checkBox")
        self.formLayout_13.setWidget(2, QtWidgets.QFormLayout.ItemRole.FieldRole, self.checkBox)
        self.checkBox_2 = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContentsRegression)
        self.checkBox_2.setText("")
        self.checkBox_2.setObjectName("checkBox_2")
        self.formLayout_13.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.checkBox_2)
        self.verticalLayout_78.addLayout(self.formLayout_13)
        spacerItem18 = QtWidgets.QSpacerItem(20, 257, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_78.addItem(spacerItem18)
        self.scrollAreaRegression.setWidget(self.scrollAreaWidgetContentsRegression)
        page_layout.addWidget(self.scrollAreaRegression)

        regression_icon = QtGui.QIcon(":/resources/icons/icon-regression-64.svg")
        self.toolBoxStyle.addItem(self.StyleRegression, regression_icon, "")
        self.verticalLayout_13.addWidget(self.toolBoxStyle)