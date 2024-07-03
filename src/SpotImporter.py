import os
import pandas as pd
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidgetItem, QMenu, QInputDialog, QComboBox, QAction, QHeaderView
from PyQt5.QtCore import Qt
from src.ui.SpotImportDialog import Ui_SpotImportDialog
from lame_helper import basedir, iconpath
from src.ExtendedDF import AttributeDataFrame

class SpotImporter(QDialog, Ui_SpotImportDialog):
    """A dialog for importing spot data into LaME

    Import spot data.  Import format requires csv file(s) with one row per spot and columns with metadata and analyses.

    Attributes
    ----------
    main_window : MainWindow
        See parent below.
    ok : bool
        Flag indicating successful import.

    Parameters
    ----------
    parent : MainWindow
        Parent window
    """    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.main_window = parent
        
        self.setWindowTitle('Spot Importer')
        
        # context menu
        self.tableWidgetSpotData.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidgetSpotData.customContextMenuRequested.connect(self.open_context_menu)
        self.tableWidgetSpotData.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidgetSpotData.horizontalHeader().customContextMenuRequested.connect(self.open_context_menu)

        # drag and drop columns
        self.tableWidgetSpotData.horizontalHeader().setSectionsMovable(True)
        self.tableWidgetSpotData.horizontalHeader().setDragEnabled(True)
        self.tableWidgetSpotData.horizontalHeader().setDragDropMode(QHeaderView.InternalMove)
        #self.tableWidgetSpotData.setDragDropMode(QTableWidget.InternalMove)
        
        self.toolButtonOpenSpotFile.clicked.connect(self.load_spot_data)
        self.pushButtonCancel.clicked.connect(self.reject)
        self.pushButtonImport.clicked.connect(self.import_spot_table)

        self.pushButtonImport.setEnabled(False)
        
        self.ok = False
        
    def load_spot_data(self):
        """Load spot data file(s) when ``toolButtonOpenSpotFile``

        Loads csv data into ``tableWidgetSpotData`` for the user to view and update before importing.  A row of comboboxes are added to the
        first row that defines the type of column data.  An attempt is made to determine the type, but the user will need to verify.
        """        
        self.spotdata = pd.DataFrame()

        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("CSV (*.csv *.xls *.xlsx)")
        if dialog.exec_():
            file_list = dialog.selectedFiles()
            csv_files = [os.path.split(file)[1] for file in file_list if (file.endswith('.csv') | file.endswith('.xls') | file.endswith('.xlsx'))]
            if not csv_files:
                return

            file_path = os.path.split(file_list[0])[0]
        else:
            return
            
        for filename in csv_files:
            tempdata = pd.read_csv(os.path.join(file_path,filename), engine='c')
            if 'Sample' not in tempdata.columns:
                tempdata.insert(0, 'Sample', os.path.splitext(filename)[0])

            self.spotdata = pd.concat([self.spotdata, tempdata], axis=0, ignore_index=True)

        # clean the spot data column names
        self.spotdata.columns = self.spotdata.columns.str.replace('(int)','')
        self.spotdata.columns = self.spotdata.columns.str.replace('(prop)','')
        columns = list(self.spotdata.columns.str.lower())

        self.spotdata.columns = self.spotdata.columns.str.replace('__','_')
        self.spotdata.columns = self.spotdata.columns.str.replace('_ ','_')
        self.spotdata.columns = self.spotdata.columns.str.replace(' _','_')
        self.spotdata.columns = self.spotdata.columns.str.replace('  ','_')

        self.spotdata.columns = self.spotdata.columns.str.strip()

        print(self.spotdata.columns)

        # update directory/filename
        if len(csv_files) > 1:
            # show directory if multiple files
            self.labelSpotFile.setText('Root directory')
            self.lineEditSpotFile.setText(file_path)
        else:
            # show filename+path if single file
            self.labelSpotFile.setText('Spot file')
            self.lineEditSpotFile.setText(file_list[0])

        self.update_spot_table()

    def update_spot_table(self):
        """Update the ``tableWidgetSpotData`` with data from csv file(s) now in ``spot_data``."""        
        # initialize table (add row for combobox in row 1)
        self.tableWidgetSpotData.clear()
        self.tableWidgetSpotData.setColumnCount(len(self.spotdata.columns))
        self.tableWidgetSpotData.setRowCount(len(self.spotdata) + 1)
        
        # set header
        self.tableWidgetSpotData.setHorizontalHeaderLabels(list(self.spotdata.columns))
        self.tableWidgetSpotData.update()
        
        for col in range(len(self.spotdata.columns)):
            # add combobox to column
            self.add_combobox(col)
        
            # add spot_data column to tableWidgetSpotData
            for row in range(1, len(self.spotdata) + 1):
                self.tableWidgetSpotData.setItem(row, col, QTableWidgetItem(str(self.spotdata.iat[row-1, col])))

        # enable importing of data
        self.pushButtonImport.setEnabled(True)
        self.tableWidgetSpotData.update()

    def add_combobox(self,col):
        """Adds a combobox with column data types to the first row.

        The user can use the combobox to select the type of data given column.  These types are used to develop a standard format for importing into *LaME*.
        An attempt is made to determine the type, but the user will need to verify.

        Parameters
        ----------
        col : int
            Column to add the combobox to
        """        
        combobox = QComboBox()
        combobox.addItems(['analyte', 'annotation', 'ignore', 'metadata', 'sample id', 'spot size', 'spot id', 'x coordinate', 'y coordinate', 'uncertainty', 'units'])

        # check column data type
        header = self.tableWidgetSpotData.horizontalHeaderItem(col).text()
        if header not in self.spotdata.columns:
            # initialize unknown columns as metadata
            col_type = 'metadata'
        else:
            col_dtype = self.spotdata[header].dtype
            if col_dtype == 'object':
                # initalize str columns
                if 'sample' in header.lower():
                    col_type = 'sample id'
                elif 'analysis' in header.lower():
                    col_type = 'spot id'
                else:
                    col_type = 'metadata'
            else:
                # initialize numeric columns
                if 'x' == header.lower():
                    col_type = 'x coordinate'
                elif 'y' == header.lower():
                    col_type = 'y coordinate'
                elif (('sd' in header.lower()) or ('se' in header.lower()) or ('sigma' in header.lower())) and ('Se' not in header):
                    col_type = 'uncertainty'
                elif 'spot size' in header.lower():
                    col_type = 'spot size'
                else:
                    col_type = 'analyte'
        combobox.setCurrentText(col_type)
        self.tableWidgetSpotData.setCellWidget(0, col, combobox)



    def open_context_menu(self, position):
        """Context menu for header functions

        Adds a context menu for adding, removing and deleting columns from ``tableWidgetSpotData``.

        Parameters
        ----------
        position : QPoint
            Location into ``tableWidgetSpotData``
        """        
        index = self.tableWidgetSpotData.indexAt(position)
        if not index.isValid():
            return

        context_menu = QMenu()
        
        actionInsertColumn = QAction('Insert column', self)
        actionRenameColumn = QAction('Rename column', self)
        actionDeleteColumn = QAction('Delete column', self)
        
        currentColumn = self.tableWidgetSpotData.currentColumn()
        actionInsertColumn.triggered.connect(lambda: self.insert_column(currentColumn))
        actionRenameColumn.triggered.connect(lambda: self.rename_column(currentColumn))
        actionDeleteColumn.triggered.connect(lambda: self.tableWidgetSpotData.removeColumn(currentColumn))
        
        context_menu.addAction(actionInsertColumn)
        context_menu.addAction(actionRenameColumn)
        context_menu.addAction(actionDeleteColumn)
        
        context_menu.exec_(self.tableWidgetSpotData.viewport().mapToGlobal(position))
    
    def insert_column(self, currentColumn):
        """Insert a column into ``tableWidgetSpotData``

        Parameters
        ----------
        currentColumn : int
            Column to rename
        """        
        # insert column and set new column header text
        self.tableWidgetSpotData.insertColumn(currentColumn)
        self.tableWidgetSpotData.setHorizontalHeaderItem(currentColumn,QTableWidgetItem('New Column'))

        # add combobox to first row
        self.add_combobox(currentColumn)
        
    def rename_column(self, currentColumn):
        """Rename a column in ``tableWidgetSpotData``

        Parameters
        ----------
        currentColumn : int
            Column to rename
        """        
        header = self.tableWidgetSpotData.horizontalHeaderItem(currentColumn).text()
        newName, ok = QInputDialog.getText(self, 'Rename Column', 'Enter new column name:', text=header)
        
        if ok and newName:
            self.tableWidgetSpotData.setHorizontalHeaderItem(currentColumn, QTableWidgetItem(newName))
    
    

    def import_spot_table(self):
        """Update the ``MainWindow.tableWidgetSpots`` and update ``MainWindow.spot_data``

        Add spot data to *LaME* when pushButtonImport is clicked.
        """
        # need to tweak header names, put into AttributeDataFrame
        # separate units from names, determine analytes, statistic, set column types etc.
        columns = [self.tableWidgetSpotData.horizontalHeaderItem(i).text() for i in range(self.tableWidgetSpotData.columnCount())]
        data = []
        
        # combobox column types
        # 'analyte', 'annotation', 'ignore', 'metadata', 'sample id', 'spot size', 'spot id', 'x coordinate', 'y coordinate', 'uncertainty', 'units'
        
        ignore = []
        ianalyte = []
        iuncertainty = []
        for row in range(1, self.tableWidgetSpotData.rowCount()+1):
            row_data = []
            for col in range(self.tableWidgetSpotData.columnCount()):
                if row == 1:
                    # read combobox
                    widget_text = self.tableWidgetSpotData.cellWidget(0,col).currentText()

                    match widget_text:
                        case 'analyte':
                            ianalyte.append(col)
                        case 'annotation':
                            columns[col] = 'display_text'
                        case 'ignore':
                            ignore.append(col)
                        case 'metadata':
                            pass
                        case 'sample id':
                            columns[col] = 'sample_id'
                        case 'spot id':
                            columns[col] = 'spot_id'
                        case 'spot size':
                            columns[col] = 'spot_size'
                        case 'x coordinate':
                            columns[col] = 'X'
                        case 'y coordinate':
                            columns[col] = 'Y'
                        case 'uncertainty':
                            iuncertainty.append(col)
                        case 'units':
                            columns[col] = 'units'

                item = self.tableWidgetSpotData.item(row, col)
                row_data.append(item.text() if item else '')
            data.append(row_data)

        columns = list(self.spotdata.columns.str.lower())
        
        self.import_df = AttributeDataFrame(data, columns=columns)

        # insert missing columns
        if 'X' not in self.import_df.columns:
            self.import_df['X'] = None
        if 'Y' not in self.import_df.columns:
            self.import_df['Y'] = None
        if 'visible' not in self.import_df.columns:
            self.import_df['visible'] = False
        if 'display_text' not in self.import_df.columns:
            if 'spot_id' in self.import_df.columns:
                self.import_df['display_text'] = self.import_df['spot_id']
            else:
                self.import_df['display_text'] = ''

        for i in ianalyte + iuncertainty:
            if 'cps' in columns[i]:
                unit_text = 'cps'
            elif 'ppm' in columns:
                unit_text = 'ppm'
            elif 'ppb' in columns:
                unit_text = 'ppb'
            elif 'ppt' in columns:
                unit_text = 'ppt'

            self.import_df.setattribute(i, 'unit', unit_text)
            
            if i in ianalyte:
                if 'mean' in self.import_df.columns.str.lower():
                    self.import_df.setattribute(i, 'average', 'mean')
                elif 'median' in self.spotdata.columns.str.lower():
                    self.import_df.setattribute(i, 'average', 'median')
            if i in iuncertainty:
                if 'sd' in self.import_df.columns.str.lower():
                    self.import_df.setattribute(i, 'uncertainty', 'sd')
                elif 'se' in self.import_df.columns.str.lower():
                    self.import_df.setattribute(i, 'uncertainty', 'se')

        self.main_window.spot_data = self.import_df

        self.ok = True