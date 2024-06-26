import os
import pandas as pd
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidget, QTableWidgetItem, QMenu, QInputDialog, QComboBox, QPushButton, QVBoxLayout, QWidget, QAction
from PyQt5.QtCore import Qt
from src.ui.SpotImportDialog import Ui_SpotImportDialog
from lame_helper import basedir, iconpath

class SpotImporter(QDialog, Ui_SpotImportDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        
        self.setWindowTitle('Spot Importer')
        
        self.tableWidgetSpotData = QTableWidget()
        self.tableWidgetSpotData.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidgetSpotData.customContextMenuRequested.connect(self.contextMenu)
        self.tableWidgetSpotData.horizontalHeader().sectionClicked.connect(self.handleHeaderClicked)
        self.tableWidgetSpotData.setDragDropMode(QTableWidget.InternalMove)
        
        self.toolButtonOpenSpotFile.clicked.connect(self.load_spot_data)
        self.pushButtonCancel.clicked.connect(self.reject)
        self.pushButtonImport.clicked.connect(self.import_spot_table)

        self.pushButtonImport.setEnabled(False)
        
        self.ok = False
        
    def load_spot_data(self):
        """Open file(s) with spot data

        Prompts user to select spot data file with dialog after ``MainWindow.toolButtonSpots`` is clicked.
        """
        self.spotdata = pd.DataFrame()

        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("CSV (*.csv *.xls *.xlsx)")
        if dialog.exec_():
            file_list = dialog.selectedFiles()
            csv_files = [os.path.split(file)[1] for file in file_list if (file.endswith('.csv') | file.endswith('.xls') | file.endswith('.xlsx'))]
            if csv_files == []:
                return

            file_path = os.path.split(file_list[0])[0]
        else:
            return
            
        for filename in csv_files:
            tempdata = pd.read_csv(os.path.join(file_path,filename), engine='c')
            if 'Sample' not in tempdata.columns:
                tempdata['Sample'] = os.path.splitext(filename)[0]

            self.spotdata = pd.concat([self.spotdata, tempdata], axis=0, ignore_index=True)

        # update directory/filename
        if len(csv_files) > 1:
            # show directory if multiple files
            self.labelSpotFile.setText('Root directory')
            self.lineEditSpotFile.setText(file_path)
        else:
            # show filename+path if single file
            self.labelSpotFile.setText('Spot file')
            self.lineEditSpotFile.setText(file_list[0])

        self.tableWidgetSpotData.setColumnCount(len(self.spotdata.columns))
        self.tableWidgetSpotData.setRowCount(len(self.spotdata) + 1)
        
        self.tableWidgetSpotData.setHorizontalHeaderLabels(list(self.spotdata.columns))
        
        for j in range(len(self.spotdata.columns)):
            combobox = QComboBox()
            combobox.addItems(['sample id','spot id','metadata', 'X coordinate', 'Y coordinate', 'annotation', 'analyte', 'ignore'])
            # check column data type
            # if string, set as metadata
            # if number
            # if contains x in header and no number, 'X'
            # if contains y in header and no number, 'Y'
            # if contains number and 'X' or 'Y', analyte
            combobox.setCurrentText('analyte')
            self.tableWidgetSpotData.setCellWidget(0, j, combobox)
        
            for i in range(1, len(self.spotdata) + 1):
                self.tableWidgetSpotData.setItem(i, j, QTableWidgetItem(str(self.spotdata.iat[i-1, j])))

        self.pushButtonImport.setEnabled(True)
        
                
    def contextMenu(self, position):
        menu = QMenu()
        
        insertColumnAction = QAction('Insert column', self)
        deleteColumnAction = QAction('Delete column', self)
        renameColumnAction = QAction('Rename column', self)
        
        insertColumnAction.triggered.connect(self.insertColumn)
        deleteColumnAction.triggered.connect(self.deleteColumn)
        renameColumnAction.triggered.connect(self.renameColumn)
        
        menu.addAction(insertColumnAction)
        menu.addAction(deleteColumnAction)
        menu.addAction(renameColumnAction)
        
        menu.exec_(self.tableWidgetSpotData.mapToGlobal(position))
        
    def handleHeaderClicked(self, index):
        print(f"Header {index} clicked")
        
    def insertColumn(self):
        currentColumn = self.tableWidgetSpotData.currentColumn()
        self.tableWidgetSpotData.insertColumn(currentColumn)
        
    def deleteColumn(self):
        currentColumn = self.tableWidgetSpotData.currentColumn()
        self.tableWidgetSpotData.removeColumn(currentColumn)
        
    def renameColumn(self):
        currentColumn = self.tableWidgetSpotData.currentColumn()
        newName, ok = QInputDialog.getText(self, 'Rename Column', 'Enter new column name:')
        
        if ok and newName:
            self.tableWidgetSpotData.setHorizontalHeaderItem(currentColumn, QTableWidgetItem(newName))
        
    def import_spot_table(self):
        new_columns = [self.tableWidgetSpotData.horizontalHeaderItem(i).text() for i in range(self.tableWidgetSpotData.columnCount())]
        data = []
        
        for i in range(1, self.tableWidgetSpotData.rowCount()):
            row_data = []
            for j in range(self.tableWidgetSpotData.columnCount()):
                item = self.tableWidgetSpotData.item(i, j)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        
        self.import_df = pd.DataFrame(data, columns=new_columns)

        if not('X' in self.import_df.columns):
            self.import_df['X'] = None
        if not('Y' in self.import_df.columns):
            self.import_df['Y'] = None
        if not('visible' in self.import_df.columns):
            self.import_df['visible'] = False
        if not('annotation' in self.import_df.columns):
            self.import_df['annotation'] = ''

        self.ok = True