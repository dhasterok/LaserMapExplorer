import os, re, darkdetect
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFileDialog, QTableWidget, QTableWidgetItem, QInputDialog, QComboBox,
    QWidget, QCheckBox, QHeaderView, QProgressBar, QLineEdit, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QUrl
import src.lame_fileio as lameio
from src.ui.MapImportDialog import Ui_MapImportDialog
from lame_helper import BASEDIR, ICONPATH

# Import Tool Dialog
# -------------------------------
class MapImporter(QDialog, Ui_MapImportDialog):       
    """Data import tool for map-form geochemical and mineral data

    Loads data that is processed and exported by Iolite, XMapTools and LADr.

    Attributes
    ----------
    standard_list : list
        Standards used to calibrate CPS data.
    sample_ids : list
        Sample IDs (directory names) with sample data.
    paths : list
        Path to each data file.

    Parameters
    ----------
    QtWidgets : QMainWindow
        Window for import tool
    Ui_ImportDialog : Ui_ImportDialog
        Import window design
    """    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.main_window = parent

        if darkdetect.isDark():
            self.toolButtonNextSample.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-dark-64.svg')))
            self.toolButtonPrevSample.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-dark-64.svg')))
        
        # dictionary with standards (files to ignore or use as calibration...once we add that capability)
        self.standards_dict = lameio.import_csv_to_dict(os.path.join(BASEDIR,'resources/app_data/standards_list.csv'))

        self.toolButtonAddStandard.clicked.connect(self.add_standard)
        self.sample_ids = []
        self.paths = []
        
        # Set a message that will be displayed in the status bar
        self.statusBar.showMessage('Ready')
        
        # Adding a progress bar to the status bar
        self.progressBar = QProgressBar()
        self.statusBar.addPermanentWidget(self.progressBar)

        self.toolButtonOpenDirectory.clicked.connect(self.open_directory)
        self.checkBoxSaveToRoot.setChecked(True)

        self.toolButtonPrevSample.clicked.connect(lambda: self.change_preview(next=False))
        self.toolButtonNextSample.clicked.connect(lambda: self.change_preview(next=True))
        self.toolButtonPrevSample.setEnabled(False)
        self.toolButtonNextSample.setEnabled(False)

        # image resolution
        self.labelResolution.setText('')
        
        # connect bottom buttons
        self.pushButtonImport.clicked.connect(self.import_data)
        self.pushButtonImport.setEnabled(False)
        self.pushButtonLoad.clicked.connect(self.load_metadata)
        self.pushButtonSave.clicked.connect(self.save_metadata)
        self.pushButtonSave.setEnabled(False)
        self.pushButtonCancel.clicked.connect(self.reject)

        self.tableWidgetMetadata.currentItemChanged.connect(self.on_item_changed)

        # size columns
        header = self.tableWidgetMetadata.horizontalHeader()
        for col in range(self.tableWidgetMetadata.columnCount()):
            if self.tableWidgetMetadata.horizontalHeaderItem(col).text() == 'Sample_ID':
                header.setSectionResizeMode(col,QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col,QHeaderView.ResizeToContents)

        self.comboBoxDataType.currentIndexChanged.connect(self.data_type_changed)
        self.comboBoxMethod.currentIndexChanged.connect(self.method_changed)

        self.ok = False
    
    def help(self):
        """Loads the help webpage associated with the ImportTool in the Help tab"""
        filename = os.path.join(BASEDIR,"docs/build/html/import.html")

        self.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.browser.setUrl(QUrl.fromLocalFile(filename))
    
    def change_preview(self,next=True):
        # Get indexes of samples that are selected for analysis
        selected = []
        for i in range(len(self.sample_ids)):
            if self.tableWidgetMetadata.cellWidget(i,0).isChecked():
                selected.append(i)

        if not selected:
            self.labelSampleID.setText("None selected")
            return

        selected = np.array(selected)

        # next
        if next:
            test = selected > self.preview_index
            # next
            if any(test):
                self.preview_index = min(selected[test])
            # start back at beginning
            else:
                self.preview_index = selected[0]

        # previous
        else:
            test = selected < self.preview_index
            if any(test):
                self.preview_index = max(selected[test])
            # go back to end
            else:
                self.preview_index = selected[-1]

        self.labelSampleID.setText(self.sample_ids[self.preview_index])

    def add_standard(self):
        """Adds a standard to the standard dictionary

        Updates standard dictionary and associated file.  If ``ImportTool.tableWidgetMetadata`` has data, then it needs
        to update the comboBoxes within the *Standards* column
        """        
        data_type = self.comboBoxDataType.currentText()
        
        # get new standard name
        standard_name, ok = QInputDialog.getText(self, 'Add standard', f'Enter new standard name to {data_type}:')
        if not ok:
            return
        
        # add new standard to list
        self.standards_dict[data_type].append(standard_name)
        self.standard_list = self.standards_dict[data_type]

        # save updated standards dictionary
        lameio.export_dict_to_csv(self.standards_dict,os.path.join(BASEDIR,'resources/app_data/standards_list.csv'))

        # if tableWidgetMetadata has information and a Standards column, update with new standards list
        n_rows = self.tableWidgetMetadata.rowCount()
        if n_rows == 0:
            return
    
        # find column index with name Standard
        col = next((c for c in range(self.tableWidgetMetadata.columnCount()) 
                if self.tableWidgetMetadata.horizontalHeaderItem(c).text() == 'Standard'), None)

        if col is None:
            return
        else:
            self.statusBar.showMessage("Failed to add new standard, no 'Standard' column")

        # update standard comboboxes
        for row in range(n_rows):
            widget = self.tableWidgetMetadata.cellWidget(row,col)
            if isinstance(widget, QComboBox):
                widget.addItem(standard_name)
            else:
                self.statusBar.showMessage("Failed to add new standard, wrong column or missing comboBox?")

    def data_type_changed(self):
        data_type = self.comboBoxDataType.currentText()
        match data_type:
            case 'LA-ICP-MS':
                methods = ['quadrupole','TOF','SF']
            case 'MLA':
                methods = ['']
                pass
            case 'XRF':
                methods = ['']
                pass
            case 'SEM':
                methods = ['']
                pass
            case 'CL':
                methods = ['']
                pass
            case 'petrography':
                methods = ['']
                pass

        # used to populate table
        self.standard_list = self.standards_dict[data_type]

        self.comboBoxMethod.clear()
        self.comboBoxMethod.addItems(methods)
        self.populate_table()

    def method_changed(self):
        self.populate_table()
        pass
        
    def load_metadata(self):
        """Loads table with sample metadata

        Save time by prepreparing the metadata as you collect them.  Open the csv, and then update the UI table for the user to make any modifications prior to importing data.
        """        
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;All Files (*)")
        status = True
        if file_name:
            data = pd.read_csv(file_name)
    
            # Assuming 'Sample ID' is the column to match sample IDs
            for index, row in data.iterrows():
                sample_id = row['Sample ID']
                if sample_id in self.sample_ids:
                    row_pos = self.sample_ids.index(sample_id)
                    self.update_table_row(row_pos, row)
                else:
                    status = False
              
            if status:
                self.statusBar.showMessage("Metadata loaded successfully")
            else:
                self.statusBar.showMessage("Some metadata sample IDs do not match sample IDs in directory")
    
    def update_table_row(self, row_pos, row_data):
        # Ensure the table has enough rows
        if self.tableWidgetMetadata.rowCount() <= row_pos:
            self.tableWidgetMetadata.insertRow(row_pos)
    
        for col_index, (col_name, value) in enumerate(row_data.items()):
            if col_name == 'Sample ID':
                continue  # Skip the sample ID since it's just a reference, not to be edited
    
            # Handling different widget types in the table
            cell_widget = self.tableWidgetMetadata.cellWidget(row_pos, col_index)
            if isinstance(cell_widget, QComboBox):
                # Set the current index for combo box if the value exists in its options
                index = cell_widget.findText(str(value), Qt.MatchFixedString)
                if index >= 0:
                    cell_widget.setCurrentIndex(index)
                else:
                    self.statusBar.showMessage(f"Value {value} not found in ComboBox options at column {col_index}")
            else:
                # For QTableWidgetItem, just set the text
                item = QTableWidgetItem(str(value))
                self.tableWidgetMetadata.setItem(row_pos, col_index, item)
                        
    def save_metadata(self):
        """Save table widget metadata to a csv file

        Opens a dialog, prompting the user to provide a filename for saving a copy data from ``ImportTool.tableWidgetMetadata`` to a csv file.
        """        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save sample metadata", "", "CSV Files (*.csv);;All Files (*)")
        if file_name:
            # read data from QTableWidget and place in DataFrame
            table_df = self.qtablewidget_to_dataframe(self.tableWidgetMetadata)
            
            # save DataFrame to CSV
            table_df.to_csv(file_name, index=False)  # Save DataFrame to CSV without the index
            self.statusBar.showMessage("Metadata saved successfully")

    def open_directory(self):
        """Reads sample IDs for import from directory list

        Assumes directories within selected directory are sample available for opening.
        """        
        root_path = QFileDialog.getExistingDirectory(None, "Select a folder", options=QFileDialog.ShowDirsOnly)
        if not root_path:
            return
        
        self.root_path = root_path 
        self.lineEditRootDirectory.setText(root_path)  # Set the directory path in the QTextEdit
        
        #clear existing contents in tableWidgetMetadata
        self.tableWidgetMetadata.clearContents()
        self.tableWidgetMetadata.setRowCount(0)
        
        self.fill_sample_id_path(root_path)
        
        self.pushButtonImport.setEnabled(True)
        self.pushButtonSave.setEnabled(True)
        
        #fill column with column name 'Sample ID' of  self.tableMetaData with sample ids
        self.populate_table()
        
        self.raise_()
        self.activateWindow()
    
    def fill_sample_id_path(self,root_path):
        """Gets sample ids and path names from a root directory

        Adds subdirectory names to ``ImportTool.sample_ids`` and full paths to ``ImportTool.paths``

        Parameters
        ----------
        root_path : str
            Generates path name for each sample directory within *root_path*
        """        
        # List all entries in the directory given by root_path
        entries = os.listdir(root_path)
        subdirectories = [name for name in entries if os.path.isdir(os.path.join(root_path, name))]
        
        if subdirectories:
            # If there are subdirectories, use them as sample IDs
            self.sample_ids = subdirectories
            self.paths = [os.path.join(root_path, name) for name in subdirectories]
        else:
            # If no subdirectories, use the directory name itself as the sample ID
            self.sample_ids = [os.path.basename(root_path)]
            self.paths = [root_path]

    def populate_table(self):
        """Wrapper function for populates metadata table of different data types

        Calls various functions for pupulating ``ImportTool.tableWidgetMetadata`` depending on the data type and method.
        """
        if not self.sample_ids:
            return

        data_type = self.comboBoxDataType.currentText()
        match data_type:
            case 'LA-ICP-MS':
                self.populate_la_icp_ms_table()
            case 'MLA':
                pass
            case 'XRF':
                pass
            case 'petrography':
                pass
            case 'SEM':
                pass

        # resize the table
        header = self.tableWidgetMetadata.horizontalHeader()
        for col in range(self.tableWidgetMetadata.columnCount()):
            if self.tableWidgetMetadata.horizontalHeaderItem(col).text() == 'Sample_ID':
                header.setSectionResizeMode(col,QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col,QHeaderView.ResizeToContents)
            
        self.table_update = True
        for i in range(len(self.sample_ids)):
            if self.tableWidgetMetadata.cellWidget(i,0).isChecked():
                self.preview_index = i
                break
            self.preview_index = None

        if self.preview_index is None:
            self.labelSampleID.setText("None selected")
        else: 
            self.labelSampleID.setText(self.sample_ids[self.preview_index])
            self.toolButtonPrevSample.setEnabled(True)
            self.toolButtonNextSample.setEnabled(True)
        
        self.pushButtonImport.setDefault(True)
    
    def populate_la_icp_ms_table(self):
        """Populates table with LA-ICP-MS sample metadata

        Several fields are made into checkboxes.
        """    
        self.tableWidgetMetadata.setRowCount(len(self.sample_ids))
        for col in range(self.tableWidgetMetadata.columnCount()):
            col_name = self.tableWidgetMetadata.horizontalHeaderItem(col).text()
            for row, sample_id in enumerate(self.sample_ids):
                match col_name:
                    case 'Import':
                        self.add_checkbox(row, col, True)
                    case 'Sample ID':
                        item = QTableWidgetItem(sample_id)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.tableWidgetMetadata.setItem(row, col, item)
                    case 'Standard':
                        self.add_combobox(row, col, self.standard_list, 0)
                    case 'Line Dir.':
                        self.add_combobox(row,col, ['X', 'Y'], 0)
                    case 'X\nreverse' | 'Y\nreverse' | 'Swap XY':
                        self.add_checkbox(row, col, False)
                    # case _:
                    #     self.add_lineedit(row, col)
                    # case 'Filename\nformat':
                    #     self.add_combobox(row, col, ['SampleID-LineNum','LineNum-SampleID'], 0)

    # def add_lineedit(self, row, col):
    #     """Adds a line edit to a QTableWidget
        
    #     Adds lineEdit to ``ImportTool.tableWidgetMetadata``

    #     Parameters
    #     ----------
    #     row, col : int
    #         Row and column indices
    #     """
    #     le = QLineEdit()
    #     le.setValidator(QDoubleValidator)
    #     le.setStyleSheet("text-align: right;")
    #     self.tableWidgetMetadata.setCellWidget(row,col,cb)

    def add_checkbox(self, row, col, state):
        """Adds a check box to a QTableWidget

        Adds checkBox to ``ImportTool.tableWidgetMetadata``

        Parameters
        ----------
        row, col : int
            Row and column indices
        state : bool
            Variable used to set check state
        """        
        cb = QCheckBox()
        cb.setChecked(state)
        cb.setStyleSheet("text-align: center; margin-left:25%; margin-right:25%;")
        self.tableWidgetMetadata.setCellWidget(row, col, cb)

    def add_combobox(self, row, col, items, default_index=0):
        """Adds a combo box to QTableWidget

        Adds comboBox to ``ImportTool.tableWidgetMetadata``

        Parameters
        ----------
        row : int
            Row index
        col : int
            Column index
        items : list
            Item text to add to comboBox
        default_index : int, optional
            Default comboBox index, by default 0
        """        
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(default_index)
        combo.currentIndexChanged.connect(lambda _, r=row, c=col: self.on_combobox_changed(r, c))
        self.tableWidgetMetadata.setCellWidget(row, col, combo)

    def on_item_changed(self , curr_item, prev_item):
        if prev_item:
            if self.checkBoxApplyAll.isChecked() and prev_item.column() != 0:
                column = prev_item.column()
                for row in range(self.tableWidgetMetadata.rowCount()):
                    if row != prev_item.row():
                        new_item = QTableWidgetItem(prev_item.text())
                        self.tableWidgetMetadata.setItem(row, column, new_item)
            
            # Always check and compute intraline distance when columns 7 or 8 change
            row = prev_item.row()
            sweep_time_item = self.tableWidgetMetadata.item(row, 8)
            sweep_speed_item = self.tableWidgetMetadata.item(row, 9)
        
            if sweep_time_item and sweep_speed_item and sweep_time_item.text().isdigit() and sweep_speed_item.text().isdigit():
                sweep_time = float(sweep_time_item.text())
                sweep_speed = float(sweep_speed_item.text())
                if sweep_time > 0 and sweep_speed > 0:
                    intraline_dist = sweep_time * sweep_speed
                    if self.checkBoxApplyAll.isChecked():
                        for row in range(self.tableWidgetMetadata.rowCount()):
                                self.tableWidgetMetadata.setItem(row, 10, QTableWidgetItem(str(intraline_dist)))
                    else:
                        self.tableWidgetMetadata.setItem(row, 10, QTableWidgetItem(str(intraline_dist)))
            elif sweep_time_item and sweep_speed_item:
                self.statusBar.showMessage('Sweep time and sweep speed should be postive')

    def on_combobox_changed(self, row, column):
        if self.checkBoxApplyAll.isChecked():
            combo = self.tableWidgetMetadata.cellWidget(row, column)
            selected_text = combo.currentText()
            for r in range(self.tableWidgetMetadata.rowCount()):
                if r != row:
                    self.tableWidgetMetadata.cellWidget(r, column).setCurrentText(selected_text)
            
    def read_metadata_table(self):
        ### READ TABLE DATA ###

        cols = self.tableWidgetMetadata.columnCount()
        table_data = {self.tableWidgetMetadata.horizontalHeaderItem(col).text(): [] for col in range(cols)}

        for col in range(cols):
            col_name = self.tableWidgetMetadata.horizontalHeaderItem(col).text()
            for row in range(self.tableWidgetMetadata.rowCount()):
                
                match col_name:
                    case 'Import':
                        self.add_checkbox(row, col, True)
                    case 'X\nreverse' | 'Y\nreverse' | 'Swap XY':
                        self.add_checkbox(row, col, False)
                    case 'Sample ID':
                        item = QTableWidgetItem(self.sample_ids[row])
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.tableWidgetMetadata.setItem(row, col, item)
                    case 'Line Dir.':
                        item = QTableWidgetItem(self.line_dir[row])
                    #case 'Filename\nformat':
                    #    self.add_combobox(row, col, ['SampleID-LineNum','LineNum-SampleID'], 0)

    def extract_widget_data(self, widget: QWidget):
        """Extracts relevant information from a widget for placing in a DataFrame

        _extended_summary_

        Parameters
        ----------
        widget : QWidget
            A widget stored in ``ImportTool.tableWidgetMetadata``

        Returns
        -------
        str or bool
            Returns key value of widget item to be added to a DataFrame
        """        
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        # Add more widget types as needed
        else:
            return None

    def qtablewidget_to_dataframe(self, table_widget: QTableWidget) -> pd.DataFrame:
        """Takes the data from a tableWidget and places it into a DataFrame

        Parameters
        ----------
        table_widget : QTableWidget
            Table with data for copying to dataframe.
            
        Returns
        -------
        pd.DataFrame
            Data frame with data from ``ImportTool.tableWidgetMetadata``
        """        
        # Get number of rows and columns in the QTableWidget
        row_count = table_widget.rowCount()
        column_count = table_widget.columnCount()
        
        # Create a dictionary to store the data with column headers
        table_data = {table_widget.horizontalHeaderItem(col).text(): [] for col in range(column_count)}
        
        # Iterate over all rows and columns to retrieve the data
        for row in range(row_count):
            for col in range(column_count):
                item = table_widget.item(row, col)
                if item is not None:
                    table_data[table_widget.horizontalHeaderItem(col).text()].append(item.text())
                else:
                    # Check for a widget in the cell
                    widget = table_widget.cellWidget(row, col)
                    if widget is not None:
                        table_data[table_widget.horizontalHeaderItem(col).text()].append(self.extract_widget_data(widget))
                    else:
                        table_data[table_widget.horizontalHeaderItem(col).text()].append(None)
        
        # Convert the dictionary to a pandas DataFrame
        df = pd.DataFrame(table_data)
        
        return df

    def parse_filenames(self, sample_id, file):
        """Cleans file names to determine file type and identifier for reading

        Removes sample names, file types, units and delimiters from file names.  If a valid file type, then
        the remaining string should be the line number, element or isotope symbol.

        Parameters
        ----------
        sample_id : str
            Current sample ID
        files : list of str
            List of file names for *sample_id*

        Returns
        -------
        list, list, list
            Returns a list of boolean values ``True`` is believed to be a valid file format and ``False`` is thought to be invalid.
            The second list includes the type of file that it expects to read, either ``line`` for all analytes for each scan line or
            ``matrix`` for each analyte stored as a matrix in a separate file.  The third list is the file name stripped down to line
            numbers or analytes.
        """        
        el_list =['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
                'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr',
                'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br',
                'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd',
                'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La',
                'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er',
                'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au',
                'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
                'Pa', 'U', 'Np', 'Pu']

        delimiters = [' ','-','_','.']
        units = ['CPS','cps','PPM','ppm']
        formats = ['matrix','csv','xlsx','xls']

        # remove sample_id from filename
        fid = file.replace(sample_id,'')

        # remove delimiters
        for d in delimiters:
            fid = fid.replace(d,'')

        # remove units
        for u in units:
            fid = fid.replace(u,'')

        for fmt in formats:
            fid = fid.replace(fmt,'')

        text = ''.join(re.findall('[a-zA-Z]',fid))
        # if all numbers, probably a line number
        if fid.isdigit():
            ftype = 'line'            
            valid = True
        # if includes text, see if it matches the list of element symbols
        elif text in el_list:
            ftype = 'matrix'
            valid = True
        # probably not a valid file name
        else:
            ftype = None
            fid = None
            valid = False

        return valid, ftype, fid

    def import_data(self): 
        """Import data associated with each *Sample Id* using metadata to define important structural parameters

        A wrapper for importing data associated with different data types, instruments and other file types.
        """
        self.ok = False

        data_type = self.comboBoxDataType.currentText()
        table_df = self.qtablewidget_to_dataframe(self.tableWidgetMetadata)

        if not self.checkBoxSaveToRoot.isChecked():
            save_path = QFileDialog.getExistingDirectory(None, "Select a folder to Save imports", options=QFileDialog.ShowDirsOnly)
            if not save_path:
                return
        else:
            save_path = self.root_path

        match data_type:
            case 'LA-ICP-MS':
                method = self.comboBoxMethod.currentText()
                match method:
                    case 'quadrupole':
                        self.import_la_icp_ms_data(table_df, save_path)
                    case 'TOF':
                        # for now, require iolite or xmaptools output.  In future, allow for 
                        # TOF raw format.
                        self.import_la_icp_ms_data(table_df, save_path)
                        #df = pd.read_hdf(file_path, key='dataset_1')
                    case 'SF':
                        self.import_la_icp_ms_data(table_df, save_path)
            case 'MLA':
                pass
            case 'XRF':
                pass
            case 'petrography':
                pass
            case 'SEM':
                pass

        if self.ok:
            self.main_window.open_directory(dir_name=self.root_path)
        
    def import_la_icp_ms_data(self, table_df, save_path):
        """Reads LA-ICP-MS data into a DataFrame

        _extended_summary_

        Parameters
        ----------
        table_df : pandas.DataFrame
            Input parameters and options
        save_path : str
            Location to save DataFrame reformatted into CSV for use in LaME
        """        
        method = self.comboBoxMethod.currentText()

        total_files = sum(len(files) for path in self.paths for r, d, files in os.walk(path))
        current_progress = 0
        self.progressBar.setMaximum(total_files)
        
        final_data = pd.DataFrame([])
        num_imported = 0

#        try:
        for i,path in enumerate(self.paths):
            # if Import is False, skip sample
            if not table_df['Import'][i]:
                continue

            sample_id = self.sample_ids[i]

            # swapping x and y is handled at end
            swap_xy = table_df['Swap XY'][i]
            
            # reversing is handled at end
            reverse_x = table_df['X\nreverse'][i]
            reverse_y = table_df['Y\nreverse'][i]

            dx = table_df['Spot size\n(µm)'][i]
            if dx is None:
                dx = 1
            else:
                dx = float(dx)
            sweep_time = table_df['Sweep\n(s)'][i]
            speed = table_df['Speed\n(µm/s)'][i]
            if speed is None or sweep_time is None:
                dy = dx
            else:
                dy = float(speed)*float(sweep_time)

            first = True
            for subdir, dirs, files in os.walk(path):

                data_frames = []
                for file in files:
                    valid, ftype, fid = self.parse_filenames(sample_id, file)
                    if not valid:
                        continue

                    if file.endswith('.csv') or file.endswith('.xls') or file.endswith('.xlsx'):
                        file_path = os.path.join(subdir, file)
                        save_prefix = os.path.basename(subdir)
                        if any(std in file for std in self.standard_list):
                            continue  # skip standard files

                        if first:
                            self.ftype = ftype
                        
                        match self.ftype:
                            case 'line':
                                df = self.read_raw_folder(fid, file_path, swap_xy, reverse_x, reverse_y)
                                data_frames.append(df)
                            case 'matrix':
                                if first:
                                    df = self.read_matrix_folder(fid, file_path, swap_xy, reverse_x, reverse_y,dx,dy)
                                    first = False
                                else:
                                    df = self.read_matrix_folder(fid, file_path, swap_xy, reverse_x, reverse_y)
                                
                                data_frames.append(df)
                            case _:
                                #df = self.read_ladr_ppm_folder(file_path)
                                #data_frames.append(df)
                                Exception('Unknown file type for import.')

                    current_progress += 1
                    self.progressBar.setValue(current_progress)
                    self.statusBar.showMessage(f"{sample_id}: {current_progress}/{total_files} files imported.")
                    QApplication.processEvents()  # Process GUI events to update the progress bar

                if not data_frames:
                    continue

                self.statusBar.showMessage(f'Formatting {sample_id}...')
                QApplication.processEvents()  # Process GUI events to update the progress bar
                match self.ftype:
                    case 'lines':
                        final_data = pd.concat(data_frames, ignore_index=True)
                        
                        # reverse x and/or y if needed
                        if reverse_x:
                            final_data['X'] = -final_data['X']
                        if reverse_y:
                            final_data['Y'] = -final_data['Y']
                        
                        # Adjust coordinates based on the reading direction and make upper left corner as (0,0)
                        final_data['X'] = final_data['X'] - final_data['X'].min()
                        final_data['Y'] = final_data['Y'] - final_data['Y'].min()
                    case 'matrix':
                        final_data = pd.concat(data_frames, axis = 1)
                    case _:
                        Exception('Unknown file type format. Submit bug request and sample file for testing.')
                
                if not data_frames:
                    continue

                file_name = os.path.join(save_path, sample_id+'.lame.csv')
                self.statusBar.showMessage(f'Saving {sample_id}.lame.csv...')
                QApplication.processEvents()  # Process GUI events to update the progress bar
                final_data.to_csv(file_name, index= False)
                num_imported += 1

        # except Exception as e:
        #     self.statusBar.showMessage(f"Error during import: {str(e)}")
        #     return
        # self.statusBar.showMessage("Import completed successfully!")

        self.statusBar.showMessage(f'Successfully imported {num_imported} samples.')
        self.pushButtonCancel.setText('Close')
        self.pushButtonCancel.setDefault(True)
        self.progressBar.setValue(total_files)  # Ensure the progress bar reaches full upon completion

        self.ok = True
            
    def read_raw_folder(self,line_no,file_path, swap_xy, dx, dy):
        df = pd.read_csv(file_path, skiprows=3)
        if swap_xy:
            df.insert(1,'Y',(int(line_no)-1)*dy)
            df.insert(0,'X',range(0, len(df))*dx)
        else:
            df.insert(0,'X',(int(line_no)-1)*dx)
            df.insert(1,'Y',range(0, len(df))*dy)
        return df
   
    def read_matrix_folder(self, analyte, file_path, swap_xy, reverse_x, reverse_y, dx=None, dy=None):
        """Reads analyte data in matrix form

        Parameters
        ----------
        analyte : str
            Analyte of current file
        file_path : str
            File to open
        swap_xy : bool
            ``True`` indicates whether x and y dimensions should be swapped
        reverse_x, reverse_y : bool
            ``True`` indicates whether to reverse the direction of x and y dimensions
        dx, dy : float, optional
            Dimensions in x and y directions, by default None

        Returns
        -------
        pandas.DataFrame
            Results from a single analyte with X and Y values if dx and dy are not None
        """        
        #match = re.search(r' (\w+)_ppm', file_name)
        #match2 = re.search(r'(\D+)(\d+).csv', file_name) or re.search(r'(\d+)(\D+).csv', file_name)
        # if match:
        #     analyte_name =  match.group(1)  # Returns the captured group, which is the text of interest
        # elif  match2:
        #     name = match2.group(2)  # First group: analyte name
        #     number = match2.group(1)  # Second group: analyte number
        #     # Create the variable combining name and number
        #     analyte_name = f"{name}{number}"
        # else:
        #     self.statusBar.showMessage('Analyte name not part of filename')
        #     return []

        # if analyte has isotope mass first and symbol second, swap order
        test = re.search(r'(\d+)(\D+)', analyte)
        if test:
            analyte = f"{test.group(2)}{test.group(1)}"
        
        # drop rows and columns with all nans 
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, header=None).dropna(how='all', axis=0).dropna(how='all', axis=1)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path, header=None).dropna(how='all', axis=0).dropna(how='all', axis=1)
        else:
            QMessageBox.warning(self,'Error','Could not load file, must be a *.csv, *.xls, or *.xlsx file type.')
       
        #print(df.shape)
        # produce X and Y values
        if dx is not None:
            M, N = df.shape

            # Create an array with constant column values from 1 to N
            col_values = np.tile(np.arange(1, N + 1), (M, 1))*dx

            # Create an array with constant row values from 1 to M, multiply by dy
            row_values = np.tile(np.arange(1, M + 1).reshape(M, 1), (1, N))*dy

        # swap x and y (transpose matrix)
        if swap_xy:
            # reverse x-direction
            if reverse_x:
                df = df[df.columns[::-1]]
            # reverse y-direction
            if reverse_y:
                df = df.iloc[::-1].reset_index(drop=True)

            # swap x and y
            if dx is not None: 
                Y = row_values
                X = col_values

            new_df = pd.DataFrame(df.values.T.flatten(), columns=[analyte])
        else:
            # reverse x-direction
            if reverse_x:
                df = df.iloc[::-1].reset_index(drop=True)
            # reverse y-direction
            if reverse_y:
                df = df[df.columns[::-1]]
            
            if dx is not None: 
                Y = col_values
                X = row_values

            new_df = pd.DataFrame(df.values.flatten(), columns=[analyte])

        if dx is not None:
            new_df.insert(0,'X', X.flatten('F'))
            new_df.insert(1,'Y', Y.flatten('F'))

        return new_df
   
    def read_ladr_ppm_folder(self,file_name,file_path):
        match = re.search(r' (\w+)_ppm', file_name)
        if match:
            analyte_name =  match.group(1)  # Returns the captured group, which is the text of interest
        else:
            self.statusBar.showMessage('Iolite name not part of filename')
            return []
        data = pd.read_csv(file_path)
        
        # Rename the first two columns to X and Y
        data.columns = ['X', 'Y'] + list(data.columns[2:])
    
        # Calculate unique counts to define the grid
        nr = data['X'].nunique()
        nc = data['Y'].nunique()
    
        # Generate ScanNum and SpotNum
        ScanNum = pd.DataFrame((1 + i for i in range(nc)).repeat(nr)).reset_index(drop=True)
        SpotNum = pd.DataFrame((1 + i for i in range(nr)).repeat(nc)).reset_index(drop=True)
        
        # Insert ScanNum and SpotNum as the first columns
        data.insert(0, 'ScanNum', ScanNum)
        data.insert(1, 'SpotNum', SpotNum)
    
        # Insert a NaN column for Time_Sec_ after 'Y'
        data.insert(data.columns.get_loc('Y') + 1, 'Time_Sec_', pd.Series([float('nan')] * len(data)))
        return data