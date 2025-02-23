# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/a1638626/Documents/GitHub/LaserMapExplorer/designer/WorkflowDesigner.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1024, 551)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(5, 10, 1016, 420))
        self.layoutWidget.setObjectName("layoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.layoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frameNavigation = QtWidgets.QFrame(self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frameNavigation.sizePolicy().hasHeightForWidth())
        self.frameNavigation.setSizePolicy(sizePolicy)
        self.frameNavigation.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameNavigation.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frameNavigation.setObjectName("frameNavigation")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.frameNavigation)
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.toolButtonActions = QtWidgets.QToolButton(self.frameNavigation)
        self.toolButtonActions.setObjectName("toolButtonActions")
        self.verticalLayout_2.addWidget(self.toolButtonActions)
        self.toolButtonFilters = QtWidgets.QToolButton(self.frameNavigation)
        self.toolButtonFilters.setObjectName("toolButtonFilters")
        self.verticalLayout_2.addWidget(self.toolButtonFilters)
        self.toolButtonControls = QtWidgets.QToolButton(self.frameNavigation)
        self.toolButtonControls.setObjectName("toolButtonControls")
        self.verticalLayout_2.addWidget(self.toolButtonControls)
        self.toolButtonStyles = QtWidgets.QToolButton(self.frameNavigation)
        self.toolButtonStyles.setObjectName("toolButtonStyles")
        self.verticalLayout_2.addWidget(self.toolButtonStyles)
        spacerItem = QtWidgets.QSpacerItem(16, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.horizontalLayout.addWidget(self.frameNavigation)
        self.frameWidgets = QtWidgets.QFrame(self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frameWidgets.sizePolicy().hasHeightForWidth())
        self.frameWidgets.setSizePolicy(sizePolicy)
        self.frameWidgets.setMinimumSize(QtCore.QSize(200, 0))
        self.frameWidgets.setMaximumSize(QtCore.QSize(200, 16777215))
        self.frameWidgets.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameWidgets.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frameWidgets.setObjectName("frameWidgets")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frameWidgets)
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.scrollAreaWidgets = QtWidgets.QScrollArea(self.frameWidgets)
        self.scrollAreaWidgets.setWidgetResizable(True)
        self.scrollAreaWidgets.setObjectName("scrollAreaWidgets")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 192, 410))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.scrollAreaWidgets.setWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout.addWidget(self.scrollAreaWidgets)
        self.horizontalLayout.addWidget(self.frameWidgets)
        self.frameCanvas = QtWidgets.QFrame(self.layoutWidget)
        self.frameCanvas.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameCanvas.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frameCanvas.setObjectName("frameCanvas")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frameCanvas)
        self.verticalLayout_3.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.scrollAreaCanvas = QtWidgets.QScrollArea(self.frameCanvas)
        self.scrollAreaCanvas.setWidgetResizable(True)
        self.scrollAreaCanvas.setObjectName("scrollAreaCanvas")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 367, 410))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scrollAreaCanvas.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_3.addWidget(self.scrollAreaCanvas)
        self.horizontalLayout.addWidget(self.frameCanvas)
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        self.verticalLayout_6.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_6.setSpacing(0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.frame_4 = QtWidgets.QFrame(self.layoutWidget)
        self.frame_4.setMaximumSize(QtCore.QSize(250, 16777215))
        self.frame_4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.frame_4)
        self.verticalLayout_4.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.textEdit = QtWidgets.QTextEdit(self.frame_4)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout_4.addWidget(self.textEdit)
        self.verticalLayout_6.addWidget(self.frame_4)
        self.frame_5 = QtWidgets.QFrame(self.layoutWidget)
        self.frame_5.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_5.setMaximumSize(QtCore.QSize(250, 16777215))
        self.frame_5.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_5.setObjectName("frame_5")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.frame_5)
        self.verticalLayout_5.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.tableWidget = QtWidgets.QTableWidget(self.frame_5)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        self.verticalLayout_5.addWidget(self.tableWidget)
        self.verticalLayout_6.addWidget(self.frame_5)
        self.horizontalLayout.addLayout(self.verticalLayout_6)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        self.toolBar.setIconSize(QtCore.QSize(24, 24))
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1024, 37))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.actionRun = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/resources/icons/icon-run-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRun.setIcon(icon)
        self.actionRun.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.actionRun.setObjectName("actionRun")
        self.actionSave = QtWidgets.QAction(MainWindow)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/resources/icons/icon-save-file-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionSave.setIcon(icon1)
        self.actionSave.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.actionSave.setIconVisibleInMenu(False)
        self.actionSave.setObjectName("actionSave")
        self.actionStop = QtWidgets.QAction(MainWindow)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/resources/icons/icon-stop-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionStop.setIcon(icon2)
        self.actionStop.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.actionStop.setObjectName("actionStop")
        self.actionOpen = QtWidgets.QAction(MainWindow)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/resources/icons/icon-open-file-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionOpen.setIcon(icon3)
        self.actionOpen.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.actionOpen.setObjectName("actionOpen")
        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionSave)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionRun)
        self.toolBar.addAction(self.actionStop)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.toolButtonActions.setText(_translate("MainWindow", "Actions"))
        self.toolButtonFilters.setText(_translate("MainWindow", "Filters"))
        self.toolButtonControls.setText(_translate("MainWindow", "Controls"))
        self.toolButtonStyles.setText(_translate("MainWindow", "Styles"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Attribute"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Value"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.actionRun.setText(_translate("MainWindow", "Run"))
        self.actionRun.setToolTip(_translate("MainWindow", "Run"))
        self.actionRun.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setToolTip(_translate("MainWindow", "Save workflow"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionStop.setText(_translate("MainWindow", "Stop"))
        self.actionStop.setToolTip(_translate("MainWindow", "Stop process"))
        self.actionStop.setShortcut(_translate("MainWindow", "Ctrl+T"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setToolTip(_translate("MainWindow", "Open workflow"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
import resources_rc
