from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import  QIcon, QFont
from PyQt6.QtWidgets import ( 
        QWidget, QGroupBox, QFormLayout, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QToolBar,
        QComboBox, QCheckBox, QDockWidget, QToolBox, QLineEdit, QLabel, QPushButton,
    )
from src.common.CustomWidgets import CustomDockWidget
from src.app.UITheme import default_font

# Right now, this is just notes
# Need regression codes that handle linear fitting using total Least-Squares or Deming regression or something similar.
# Fix the intercept (for dating) or the slope(?)
# Need to mask or filter selected points?
# Would be good to include leverage analysis.
# Produce regressions for individual clusters.
# Add annotations for certain types of fits?
# Add equations and stats


class RegressionDock(CustomDockWidget):
    """Regression analysis page for the toolbox.
    
    This page allows users to select regression methods, configure outlier detection,
    and tune model parameters. It is designed to be used within a QToolBox in the
    main application window.
    """ 
    def __init__(self, page_index, parent=None):
        super().__init__(parent)

        if parent is None:
            return

        self.parent = parent

        self.setWindowTitle("Regression Analysis")

        # Main layout for the dock widget
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Regression method selection
        regression_group = QGroupBox("Regression Options")
        regression_layout = QFormLayout()
        regression_group.setLayout(regression_layout)

        self.comboBoxRegressionType = QComboBox()
        self.comboBoxRegressionType.setFont(default_font())
        self.comboBoxRegressionType.addItems([
            "Linear", "Polynomial", "Exponential", "Logarithmic"
        ])
        regression_layout.addRow(QLabel("Model Type:"), self.comboBoxRegressionType)

        self.comboBoxRegressionMethod = QComboBox()
        self.comboBoxRegressionMethod.setFont(default_font())
        self.comboBoxRegressionMethod.addItems([
            "Least Squares", "Total Least Squares", "Deming"
        ])
        regression_layout.addRow(QLabel("Regression Method:"), self.comboBoxRegressionMethod)

        # Outlier detection options
        outlier_group = QGroupBox("Outlier Detection")
        outlier_layout = QFormLayout()
        outlier_group.setLayout(outlier_layout)

        self.checkBoxEnableOutlierDetection = QCheckBox("Enable Outlier Detection")
        self.checkBoxEnableOutlierDetection.setFont(default_font())
        outlier_layout.addRow(self.checkBoxEnableOutlierDetection)

        self.comboBoxOutlierMethod = QComboBox()
        self.comboBoxOutlierMethod.setFont(default_font())
        self.comboBoxOutlierMethod.addItems([
            "Z-score", "IQR", "Cook's Distance"
        ])
        outlier_layout.addRow(QLabel("Method:"), self.comboBoxOutlierMethod)

        self.lineEditOutlierThreshold = QLineEdit()
        self.lineEditOutlierThreshold.setPlaceholderText("Threshold (e.g., 2.0)")
        outlier_layout.addRow(QLabel("Threshold:"), self.lineEditOutlierThreshold)

        self.checkBoxFilterOutliers = QCheckBox("Filter Outliers")
        self.checkBoxFilterOutliers.setFont(default_font())
        outlier_layout.addRow(self.checkBoxFilterOutliers)

        # Parameter tuning
        param_group = QGroupBox("Model Parameters")
        param_layout = QFormLayout()
        param_group.setLayout(param_layout)

        self.lineEditParameter1 = QLineEdit()
        self.lineEditParameter1.setPlaceholderText("Parameter 1 (e.g., degree)")
        param_layout.addRow(QLabel("Parameter 1:"), self.lineEditParameter1)

        self.lineEditParameter2 = QLineEdit()
        self.lineEditParameter2.setPlaceholderText("Parameter 2 (optional)")
        param_layout.addRow(QLabel("Parameter 2:"), self.lineEditParameter2)

        # Add all groups to the main layout
        main_layout.addWidget(regression_group)
        main_layout.addWidget(outlier_group)
        main_layout.addWidget(param_group)

        # Add a button to run regression
        self.buttonRunRegression = QPushButton("Run Regression")
        self.buttonRunRegression.setFont(default_font())
        main_layout.addWidget(self.buttonRunRegression)

        toolbar = QToolBar(self)

        self.setGeometry(QRect(0, 0, 264, 248))
        self.setObjectName("StyleRegression")
