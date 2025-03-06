# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MapImportDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QStatusBar, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_MapImportDialog(object):
    def setupUi(self, MapImportDialog):
        if not MapImportDialog.objectName():
            MapImportDialog.setObjectName(u"MapImportDialog")
        MapImportDialog.resize(1300, 691)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MapImportDialog.sizePolicy().hasHeightForWidth())
        MapImportDialog.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(11)
        MapImportDialog.setFont(font)
        self.statusBar = QStatusBar(MapImportDialog)
        self.statusBar.setObjectName(u"statusBar")
        self.statusBar.setGeometry(QRect(0, 660, 1301, 31))
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.statusBar.sizePolicy().hasHeightForWidth())
        self.statusBar.setSizePolicy(sizePolicy1)
        self.layoutWidget = QWidget(MapImportDialog)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(12, 12, 1281, 644))
        self.verticalLayout_3 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.label.setFont(font1)

        self.horizontalLayout_7.addWidget(self.label)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_5)

        self.toolButton = QToolButton(self.layoutWidget)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(28, 28))
        self.toolButton.setMaximumSize(QSize(28, 28))
        self.toolButton.setStyleSheet(u"border : none;")
        icon = QIcon()
        icon.addFile(u":/resources/icons/icon-question-64.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon)
        self.toolButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_7.addWidget(self.toolButton)


        self.verticalLayout_3.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.labelDataType = QLabel(self.layoutWidget)
        self.labelDataType.setObjectName(u"labelDataType")

        self.horizontalLayout_2.addWidget(self.labelDataType)

        self.comboBoxDataType = QComboBox(self.layoutWidget)
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.addItem("")
        self.comboBoxDataType.setObjectName(u"comboBoxDataType")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.comboBoxDataType.sizePolicy().hasHeightForWidth())
        self.comboBoxDataType.setSizePolicy(sizePolicy2)

        self.horizontalLayout_2.addWidget(self.comboBoxDataType)

        self.labelMethod = QLabel(self.layoutWidget)
        self.labelMethod.setObjectName(u"labelMethod")

        self.horizontalLayout_2.addWidget(self.labelMethod)

        self.comboBoxMethod = QComboBox(self.layoutWidget)
        self.comboBoxMethod.setObjectName(u"comboBoxMethod")
        sizePolicy2.setHeightForWidth(self.comboBoxMethod.sizePolicy().hasHeightForWidth())
        self.comboBoxMethod.setSizePolicy(sizePolicy2)

        self.horizontalLayout_2.addWidget(self.comboBoxMethod)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.labelRootDirectory = QLabel(self.layoutWidget)
        self.labelRootDirectory.setObjectName(u"labelRootDirectory")

        self.horizontalLayout_5.addWidget(self.labelRootDirectory)

        self.lineEditRootDirectory = QLineEdit(self.layoutWidget)
        self.lineEditRootDirectory.setObjectName(u"lineEditRootDirectory")
        self.lineEditRootDirectory.setReadOnly(True)

        self.horizontalLayout_5.addWidget(self.lineEditRootDirectory)

        self.toolButtonOpenDirectory = QToolButton(self.layoutWidget)
        self.toolButtonOpenDirectory.setObjectName(u"toolButtonOpenDirectory")
        self.toolButtonOpenDirectory.setMinimumSize(QSize(28, 28))
        self.toolButtonOpenDirectory.setMaximumSize(QSize(28, 28))
        self.toolButtonOpenDirectory.setStyleSheet(u"border : none;")
        icon1 = QIcon()
        icon1.addFile(u":/resources/icons/icon-add-directory-64.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButtonOpenDirectory.setIcon(icon1)
        self.toolButtonOpenDirectory.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.toolButtonOpenDirectory)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)

        self.labelAddStandard = QLabel(self.layoutWidget)
        self.labelAddStandard.setObjectName(u"labelAddStandard")

        self.horizontalLayout_5.addWidget(self.labelAddStandard)

        self.toolButtonAddStandard = QToolButton(self.layoutWidget)
        self.toolButtonAddStandard.setObjectName(u"toolButtonAddStandard")
        self.toolButtonAddStandard.setMinimumSize(QSize(28, 28))
        self.toolButtonAddStandard.setMaximumSize(QSize(28, 28))
        self.toolButtonAddStandard.setStyleSheet(u"border : none;")
        icon2 = QIcon()
        icon2.addFile(u":/resources/icons/icon-accept-64.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButtonAddStandard.setIcon(icon2)
        self.toolButtonAddStandard.setIconSize(QSize(24, 24))

        self.horizontalLayout_5.addWidget(self.toolButtonAddStandard)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.horizontalLayout_8.addWidget(self.label_2)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_6)

        self.checkBoxPreview = QCheckBox(self.layoutWidget)
        self.checkBoxPreview.setObjectName(u"checkBoxPreview")

        self.horizontalLayout_8.addWidget(self.checkBoxPreview)


        self.verticalLayout_3.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.verticalLayoutMetadataTable = QVBoxLayout()
        self.verticalLayoutMetadataTable.setObjectName(u"verticalLayoutMetadataTable")
        self.tableWidgetMetadata = QTableWidget(self.layoutWidget)
        if (self.tableWidgetMetadata.columnCount() < 11):
            self.tableWidgetMetadata.setColumnCount(11)
        __qtablewidgetitem = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.tableWidgetMetadata.setHorizontalHeaderItem(10, __qtablewidgetitem10)
        self.tableWidgetMetadata.setObjectName(u"tableWidgetMetadata")
        self.tableWidgetMetadata.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidgetMetadata.horizontalHeader().setHighlightSections(False)

        self.verticalLayoutMetadataTable.addWidget(self.tableWidgetMetadata)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.checkBoxApplyAll = QCheckBox(self.layoutWidget)
        self.checkBoxApplyAll.setObjectName(u"checkBoxApplyAll")

        self.horizontalLayout_4.addWidget(self.checkBoxApplyAll)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_4)

        self.checkBoxSaveToRoot = QCheckBox(self.layoutWidget)
        self.checkBoxSaveToRoot.setObjectName(u"checkBoxSaveToRoot")

        self.horizontalLayout_4.addWidget(self.checkBoxSaveToRoot)


        self.verticalLayoutMetadataTable.addLayout(self.horizontalLayout_4)


        self.horizontalLayout_6.addLayout(self.verticalLayoutMetadataTable)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.framePreviewSample = QFrame(self.layoutWidget)
        self.framePreviewSample.setObjectName(u"framePreviewSample")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.framePreviewSample.sizePolicy().hasHeightForWidth())
        self.framePreviewSample.setSizePolicy(sizePolicy3)
        self.framePreviewSample.setMinimumSize(QSize(350, 350))
        self.framePreviewSample.setMaximumSize(QSize(350, 350))
        self.framePreviewSample.setFrameShape(QFrame.StyledPanel)
        self.framePreviewSample.setFrameShadow(QFrame.Raised)

        self.verticalLayout_2.addWidget(self.framePreviewSample)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.toolButtonPrevSample = QToolButton(self.layoutWidget)
        self.toolButtonPrevSample.setObjectName(u"toolButtonPrevSample")
        self.toolButtonPrevSample.setEnabled(False)
        self.toolButtonPrevSample.setMinimumSize(QSize(28, 28))
        self.toolButtonPrevSample.setMaximumSize(QSize(28, 28))
        self.toolButtonPrevSample.setStyleSheet(u"border : none;")
        icon3 = QIcon()
        icon3.addFile(u":/resources/icons/icon-back-arrow-64.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButtonPrevSample.setIcon(icon3)
        self.toolButtonPrevSample.setIconSize(QSize(24, 24))

        self.horizontalLayout_3.addWidget(self.toolButtonPrevSample)

        self.labelSampleID = QLabel(self.layoutWidget)
        self.labelSampleID.setObjectName(u"labelSampleID")
        self.labelSampleID.setMinimumSize(QSize(125, 0))
        self.labelSampleID.setMaximumSize(QSize(125, 16777215))
        self.labelSampleID.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.labelSampleID)

        self.toolButtonNextSample = QToolButton(self.layoutWidget)
        self.toolButtonNextSample.setObjectName(u"toolButtonNextSample")
        self.toolButtonNextSample.setEnabled(False)
        self.toolButtonNextSample.setMinimumSize(QSize(28, 28))
        self.toolButtonNextSample.setMaximumSize(QSize(28, 28))
        self.toolButtonNextSample.setStyleSheet(u"border : none;")
        icon4 = QIcon()
        icon4.addFile(u":/resources/icons/icon-forward-arrow-64.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButtonNextSample.setIcon(icon4)
        self.toolButtonNextSample.setIconSize(QSize(24, 24))

        self.horizontalLayout_3.addWidget(self.toolButtonNextSample)

        self.labelResolution = QLabel(self.layoutWidget)
        self.labelResolution.setObjectName(u"labelResolution")
        self.labelResolution.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.labelResolution)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)


        self.horizontalLayout_6.addLayout(self.verticalLayout_2)


        self.verticalLayout_3.addLayout(self.horizontalLayout_6)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.pushButtonLoad = QPushButton(self.layoutWidget)
        self.pushButtonLoad.setObjectName(u"pushButtonLoad")

        self.horizontalLayout.addWidget(self.pushButtonLoad)

        self.pushButtonSave = QPushButton(self.layoutWidget)
        self.pushButtonSave.setObjectName(u"pushButtonSave")

        self.horizontalLayout.addWidget(self.pushButtonSave)

        self.pushButtonImport = QPushButton(self.layoutWidget)
        self.pushButtonImport.setObjectName(u"pushButtonImport")
        self.pushButtonImport.setFont(font)

        self.horizontalLayout.addWidget(self.pushButtonImport)

        self.pushButtonCancel = QPushButton(self.layoutWidget)
        self.pushButtonCancel.setObjectName(u"pushButtonCancel")

        self.horizontalLayout.addWidget(self.pushButtonCancel)


        self.verticalLayout_3.addLayout(self.horizontalLayout)


        self.retranslateUi(MapImportDialog)

        QMetaObject.connectSlotsByName(MapImportDialog)
    # setupUi

    def retranslateUi(self, MapImportDialog):
        MapImportDialog.setWindowTitle(QCoreApplication.translate("MapImportDialog", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("MapImportDialog", u"Step 1 \u2013 Select data type for import", None))
#if QT_CONFIG(tooltip)
        self.toolButton.setToolTip(QCoreApplication.translate("MapImportDialog", u"Open help page", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton.setText(QCoreApplication.translate("MapImportDialog", u"...", None))
        self.labelDataType.setText(QCoreApplication.translate("MapImportDialog", u"Data type", None))
        self.comboBoxDataType.setItemText(0, "")
        self.comboBoxDataType.setItemText(1, QCoreApplication.translate("MapImportDialog", u"LA-ICP-MS", None))
        self.comboBoxDataType.setItemText(2, QCoreApplication.translate("MapImportDialog", u"MLA", None))
        self.comboBoxDataType.setItemText(3, QCoreApplication.translate("MapImportDialog", u"XRF", None))
        self.comboBoxDataType.setItemText(4, QCoreApplication.translate("MapImportDialog", u"CL", None))
        self.comboBoxDataType.setItemText(5, QCoreApplication.translate("MapImportDialog", u"SEM", None))
        self.comboBoxDataType.setItemText(6, QCoreApplication.translate("MapImportDialog", u"Petrography photo", None))

#if QT_CONFIG(tooltip)
        self.comboBoxDataType.setToolTip(QCoreApplication.translate("MapImportDialog", u"Select data type", None))
#endif // QT_CONFIG(tooltip)
        self.labelMethod.setText(QCoreApplication.translate("MapImportDialog", u"Method", None))
#if QT_CONFIG(tooltip)
        self.comboBoxMethod.setToolTip(QCoreApplication.translate("MapImportDialog", u"Select method of collection for data type", None))
#endif // QT_CONFIG(tooltip)
        self.labelRootDirectory.setText(QCoreApplication.translate("MapImportDialog", u"Root directory", None))
#if QT_CONFIG(tooltip)
        self.lineEditRootDirectory.setToolTip(QCoreApplication.translate("MapImportDialog", u"Base directory filled with sample directories", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.toolButtonOpenDirectory.setToolTip(QCoreApplication.translate("MapImportDialog", u"Open directory", None))
#endif // QT_CONFIG(tooltip)
        self.toolButtonOpenDirectory.setText(QCoreApplication.translate("MapImportDialog", u"...", None))
        self.labelAddStandard.setText(QCoreApplication.translate("MapImportDialog", u"Add standard", None))
#if QT_CONFIG(tooltip)
        self.toolButtonAddStandard.setToolTip(QCoreApplication.translate("MapImportDialog", u"Add standard", None))
#endif // QT_CONFIG(tooltip)
        self.toolButtonAddStandard.setText(QCoreApplication.translate("MapImportDialog", u"...", None))
        self.label_2.setText(QCoreApplication.translate("MapImportDialog", u"Step 2 \u2013 Set import metadata", None))
#if QT_CONFIG(tooltip)
        self.checkBoxPreview.setToolTip(QCoreApplication.translate("MapImportDialog", u"Show preview map", None))
#endif // QT_CONFIG(tooltip)
        self.checkBoxPreview.setText(QCoreApplication.translate("MapImportDialog", u"Show preview", None))
        ___qtablewidgetitem = self.tableWidgetMetadata.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MapImportDialog", u"Import", None));
        ___qtablewidgetitem1 = self.tableWidgetMetadata.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MapImportDialog", u"Sample ID", None));
        ___qtablewidgetitem2 = self.tableWidgetMetadata.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MapImportDialog", u"Select files", None));
        ___qtablewidgetitem3 = self.tableWidgetMetadata.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MapImportDialog", u"Standard", None));
        ___qtablewidgetitem4 = self.tableWidgetMetadata.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MapImportDialog", u"Scan axis", None));
        ___qtablewidgetitem5 = self.tableWidgetMetadata.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MapImportDialog", u"Swap XY", None));
        ___qtablewidgetitem6 = self.tableWidgetMetadata.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MapImportDialog", u"X\n"
"reverse", None));
        ___qtablewidgetitem7 = self.tableWidgetMetadata.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MapImportDialog", u"Y\n"
"reverse", None));
        ___qtablewidgetitem8 = self.tableWidgetMetadata.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("MapImportDialog", u"Spot size\n"
"(\u00b5m)", None));
        ___qtablewidgetitem9 = self.tableWidgetMetadata.horizontalHeaderItem(9)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("MapImportDialog", u"Sweep\n"
"(s)", None));
        ___qtablewidgetitem10 = self.tableWidgetMetadata.horizontalHeaderItem(10)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("MapImportDialog", u"Speed\n"
"(\u00b5m/s)", None));
#if QT_CONFIG(tooltip)
        self.tableWidgetMetadata.setToolTip(QCoreApplication.translate("MapImportDialog", u"Add missing metadata.  If left blank, quick import assumes square pixel dimensions", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBoxApplyAll.setToolTip(QCoreApplication.translate("MapImportDialog", u"<html><head/><body><p>Apply changes to a single row in a column to all rows in the column</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.checkBoxApplyAll.setText(QCoreApplication.translate("MapImportDialog", u"Apply to all rows", None))
#if QT_CONFIG(tooltip)
        self.checkBoxSaveToRoot.setToolTip(QCoreApplication.translate("MapImportDialog", u"Save import files to root directory, otherwise files are saved in $basedir/data/datatype", None))
#endif // QT_CONFIG(tooltip)
        self.checkBoxSaveToRoot.setText(QCoreApplication.translate("MapImportDialog", u"Save import to root directory", None))
#if QT_CONFIG(tooltip)
        self.toolButtonPrevSample.setToolTip(QCoreApplication.translate("MapImportDialog", u"Previous sample", None))
#endif // QT_CONFIG(tooltip)
        self.toolButtonPrevSample.setText(QCoreApplication.translate("MapImportDialog", u"left", None))
        self.labelSampleID.setText(QCoreApplication.translate("MapImportDialog", u"No data", None))
#if QT_CONFIG(tooltip)
        self.toolButtonNextSample.setToolTip(QCoreApplication.translate("MapImportDialog", u"Next sample", None))
#endif // QT_CONFIG(tooltip)
        self.toolButtonNextSample.setText(QCoreApplication.translate("MapImportDialog", u"right", None))
        self.labelResolution.setText(QCoreApplication.translate("MapImportDialog", u"Resolution: x x y", None))
#if QT_CONFIG(tooltip)
        self.pushButtonLoad.setToolTip(QCoreApplication.translate("MapImportDialog", u"Load metadata", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonLoad.setText(QCoreApplication.translate("MapImportDialog", u"Load", None))
#if QT_CONFIG(tooltip)
        self.pushButtonSave.setToolTip(QCoreApplication.translate("MapImportDialog", u"Save metadata", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonSave.setText(QCoreApplication.translate("MapImportDialog", u"Save", None))
#if QT_CONFIG(tooltip)
        self.pushButtonImport.setToolTip(QCoreApplication.translate("MapImportDialog", u"Import selected data", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonImport.setText(QCoreApplication.translate("MapImportDialog", u"Import", None))
#if QT_CONFIG(tooltip)
        self.pushButtonCancel.setToolTip(QCoreApplication.translate("MapImportDialog", u"Cancel/Close window", None))
#endif // QT_CONFIG(tooltip)
        self.pushButtonCancel.setText(QCoreApplication.translate("MapImportDialog", u"Cancel", None))
    # retranslateUi

