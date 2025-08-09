from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import ( 
        QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView
    )
from src.app.UITheme import default_font
from src.common.CustomWidgets import CustomPage
from src.app.config import ICONPATH
import resources_rc

class SpotPage(CustomPage):
    def __init__(self, page_index, dock=None):
        if dock is None:
            return
        super().__init__(dock)

        self.dock = dock
        self.page_index = page_index

        self.setupUI()

    def setupUI(self):
        self.setGeometry(QRect(0, 0, 300, 321))
        self.setObjectName("SpotDataPage")

        self.setContentsMargins(0, 0, 0, 0)

        self.groupBox = QGroupBox(self)
        self.groupBox.setTitle("")

        self.verticalLayout_44 = QVBoxLayout(self.groupBox)
        self.verticalLayout_44.setContentsMargins(3, 3, 3, 3)

        self.tableWidgetSpots = QTableWidget(self.groupBox)
        self.tableWidgetSpots.setFont(default_font())
        self.tableWidgetSpots.setObjectName("tableWidgetSpots")
        self.tableWidgetSpots.setColumnCount(5)
        self.tableWidgetSpots.setRowCount(0)
        item = QTableWidgetItem()
        self.tableWidgetSpots.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self.tableWidgetSpots.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        self.tableWidgetSpots.setHorizontalHeaderItem(2, item)
        item = QTableWidgetItem()
        self.tableWidgetSpots.setHorizontalHeaderItem(3, item)
        item = QTableWidgetItem()
        self.tableWidgetSpots.setHorizontalHeaderItem(4, item)
        self.tableWidgetSpots.horizontalHeader().setDefaultSectionSize(55)
        self.tableWidgetSpots.horizontalHeader().setStretchLastSection(True)
        self.verticalLayout_44.addWidget(self.tableWidgetSpots)

        # spot table
        header = self.tableWidgetSpots.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch)

        self.toolbar = QHBoxLayout()

        self.toolbar.setObjectName("toolbar")
        self.toolButtonSpotLocate = QToolButton(self.groupBox)
        self.toolButtonSpotLocate.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotLocate.setMaximumSize(QSize(32, 32))
        locate_icon = QIcon(":resources/icons/icon-spot-locate-64.svg")
        self.toolButtonSpotLocate.setIcon(locate_icon)
        self.toolButtonSpotLocate.setIconSize(QSize(24, 24))
        self.toolButtonSpotLocate.setCheckable(True)
        self.toolButtonSpotLocate.setObjectName("toolButtonSpotLocate")
        self.toolbar.addWidget(self.toolButtonSpotLocate)

        self.toolButtonSpotMove = QToolButton(self.groupBox)
        self.toolButtonSpotMove.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotMove.setMaximumSize(QSize(32, 32))
        move_icon = QIcon(":resources/icons/icon-move-point-64.svg")
        self.toolButtonSpotMove.setIcon(move_icon)
        self.toolButtonSpotMove.setIconSize(QSize(24, 24))
        self.toolButtonSpotMove.setCheckable(True)
        self.toolButtonSpotMove.setObjectName("toolButtonSpotMove")
        self.toolbar.addWidget(self.toolButtonSpotMove)

        self.toolButtonSpotToggle = QToolButton(self.groupBox)
        self.toolButtonSpotToggle.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotToggle.setMaximumSize(QSize(32, 32))
        show_hide_icon = QIcon(":resources/icons/icon-show-hide-64.svg")
        self.toolButtonSpotToggle.setIcon(show_hide_icon)
        self.toolButtonSpotToggle.setIconSize(QSize(24, 24))
        self.toolButtonSpotToggle.setCheckable(True)
        self.toolButtonSpotToggle.setObjectName("toolButtonSpotToggle")

        self.toolbar.addWidget(self.toolButtonSpotToggle)
        self.toolButtonSpotSelectAll = QToolButton(self.groupBox)
        self.toolButtonSpotSelectAll.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotSelectAll.setMaximumSize(QSize(32, 32))
        select_all_icon = QIcon(":resources/icons/icon-select-all-64.svg")
        self.toolButtonSpotSelectAll.setIcon(select_all_icon)
        self.toolButtonSpotSelectAll.setIconSize(QSize(24, 24))
        self.toolButtonSpotSelectAll.setObjectName("toolButtonSpotSelectAll")

        self.toolbar.addWidget(self.toolButtonSpotSelectAll)
        self.toolButtonSpotAnalysis = QToolButton(self.groupBox)
        self.toolButtonSpotAnalysis.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotAnalysis.setMaximumSize(QSize(32, 32))
        analysis_icon = QIcon(":/resources/icons/icon-analysis-64.svg")
        self.toolButtonSpotAnalysis.setIcon(analysis_icon)
        self.toolButtonSpotAnalysis.setIconSize(QSize(24, 24))
        self.toolButtonSpotAnalysis.setObjectName("toolButtonSpotAnalysis")
        self.toolbar.addWidget(self.toolButtonSpotAnalysis)

        spacerItem4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.toolbar.addItem(spacerItem4)

        self.toolButtonSpotRemove = QToolButton(self.groupBox)
        self.toolButtonSpotRemove.setMinimumSize(QSize(32, 32))
        self.toolButtonSpotRemove.setMaximumSize(QSize(32, 32))
        delete_icon = QIcon(":/resources/icons/icon-delete-64.svg")
        self.toolButtonSpotRemove.setIcon(delete_icon)
        self.toolButtonSpotRemove.setIconSize(QSize(24, 24))
        self.toolButtonSpotRemove.setObjectName("toolButtonSpotRemove")
        self.toolbar.addWidget(self.toolButtonSpotRemove)

        self.addLayout(self.toolbar)
        self.addWidget(self.groupBox)

        page_icon = QIcon(str(ICONPATH / "icon-spot-64.svg"))
        page_name = "Spot Data"
        self.dock.toolbox.insertItem(self.page_index+1, self, page_icon, page_name)

        self.dock.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-spot-64.svg",
            dark_icon = ICONPATH / "icon-spot-dark-64.svg"
        )