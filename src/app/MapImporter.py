import os, re, darkdetect
from collections import defaultdict
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QTableWidget, QTableWidgetItem, QInputDialog, QComboBox, QToolBar,
    QWidget, QCheckBox, QHeaderView, QProgressBar, QLineEdit, QMessageBox, QVBoxLayout, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QUrl
import src.common.csvdict as csvdict
from src.ui.MapImportDialog import Ui_MapImportDialog
from src.ui.FileSelectorDialog import Ui_FileSelectorDialog
from src.app.config import BASEDIR, ICONPATH

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
    QDialog : QDialog
        Inherits the properties of the QDialog
    Ui_MapImportDialog : UI
        UI interface design.  Note this interface was created in QtCreator, though it requires replacing
        of ``QtWidgets.TableWidget`` with ``CustomWidgets.CustomTableWidget``.  The custom widget adds a
        ``.to_dataframe()`` simplify data extraction tables (especially complex tables).
    """    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        if parent is None:
            return
        self.parent = parent

        if darkdetect.isDark():
            self.toolButtonNextSample.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-dark-64.svg')))
            self.toolButtonPrevSample.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-dark-64.svg')))
        
        # dictionary with standards (files to ignore or use as calibration...once we add that capability)
        self.standards_dict = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/app_data/standards_list.csv'))

        self.toolButtonAddStandard.clicked.connect(self.add_standard)
        self.sample_ids = []
        self.paths = []
        self.metadata = {'directory_data': pd.DataFrame()}
        
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
        self.pushButtonCancel.setEnabled(True)

        self.tableWidgetMetadata.currentItemChanged.connect(self.on_item_changed)

        # size columns
        header = self.tableWidgetMetadata.horizontalHeader()
        for col in range(self.tableWidgetMetadata.columnCount()):
            if self.tableWidgetMetadata.horizontalHeaderItem(col).text() == 'Sample_ID':
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)

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
    
    def get_metadata(self):
        """Gets data in ``MapImporter.tableWidgetMetadata`` and formats it for the dataframe.

        Returns
        -------
        pandas.DataFrame
            Contents of ``tableWidgetMetadata``.
        """        
        data = self.tableWidgetMetadata.to_dataframe()
        data['Select files'] = data['Select files'].str.extract(r'(\d+)').astype(int)
        data = data.rename(columns={'X\nreverse':'Reverse X', 'Y\nreverse': 'Reverse Y', 'Spot size\n(µm)': 'Spot size', 'Sweep\n(s)': 'Sweep', 'Speed\n(µm/s)':'Speed'})

        return data

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
                index = cell_widget.findText(str(value), Qt.MatchFlag.MatchFixedString)
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
            #self.metadata['directory_data'] = self.qtablewidget_to_dataframe(self.tableWidgetMetadata)
            self.metadata['directory_data'] = self.get_metadata()
            
            # save DataFrame to CSV
            try:
                self.metadata['directory_data'].to_csv(file_name, index=False)  # Save DataFrame to CSV without the index
                self.statusBar.showMessage("Metadata saved successfully")
            except Exception as e:
                QMessageBox.warning(self,'Error',f"Could not save metadata table.\n{e}")


    def open_directory(self):
        """Reads sample IDs for import from directory list

        Assumes directories within selected directory are sample available for opening.
        """        
        root_path = QFileDialog.getExistingDirectory(None, "Select a folder", options=QFileDialog.Option.ShowDirsOnly)
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
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
            
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

        # create an empty dictionary of metadata for each
        self.metadata = {'directory_data': self.get_metadata()}
        for sample_id in self.sample_ids:
            self.metadata[sample_id] = pd.DataFrame()

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
                        self.add_checkbox(row, col, False)
                    case 'Sample ID':
                        item = QTableWidgetItem(sample_id)
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.tableWidgetMetadata.setItem(row, col, item)
                    case 'Select files':
                        self.add_pushbutton(row, col)
                    case 'Standard':
                        self.add_combobox(row, col, self.standard_list, 0)
                    case 'Scan axis':
                        self.add_combobox(row,col, ['Xc', 'Yc'], 0)
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
    #     self.tableWidgetMetadata.setCellWidget(row,col,le)

    def add_pushbutton(self, row, col):
        pb = QPushButton()
        pb.setText("0 files")
        pb.setToolTip("Click to select files for import.")
        pb.clicked.connect(lambda: self.select_sample_files(row))
        self.tableWidgetMetadata.setCellWidget(row, col, pb)

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

    def on_item_changed(self, curr_item, prev_item):
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
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.tableWidgetMetadata.setItem(row, col, item)
                    case 'Line Dir.':
                        item = QTableWidgetItem(self.line_dir[row])
                    #case 'Filename\nformat':
                    #    self.add_combobox(row, col, ['SampleID-LineNum','LineNum-SampleID'], 0)

    def parse_filenames(self, sample_id, files):
        """Parses a list of filenames to predict file type and extract analyte, unit, and line number information.

        Parameters
        ----------
        sample_id : str
            The sample ID to remove from filenames.
        files : list of str
            List of file paths to be parsed.

        Returns
        -------
        list of tuples
            A list where each tuple contains:
            - boolean indicating if the file is valid
            - file type (either 'matrix', 'line', or None)
            - the extracted analyte, ratio, or line number
        """
        # Load the Excel file with element symbols and isotope masses
        df = pd.read_csv(os.path.join(BASEDIR, 'resources/app_data/isotope_info.csv'))
        elements = df['symbol'].str.lower().tolist()
        masses = df['atomic_mass'].astype(str).tolist()
        
        # Initialize defaultdict with list
        isotopes = defaultdict(list)
        for element, mass_list in zip(elements, masses):
            isotopes[element].append(mass_list)

        delimiters = r' |-|_|,|\.'
        units = ['CPS', 'cps', 'PPM', 'ppm', 'PPB', 'ppb']
        valid_extensions = ['csv', 'xlsx', 'xls']

        results = []

        for file in files:
            valid = False
            filetype = None
            fieldtype = None
            unit = None
            analyte1, analyte2 = None, None
            lineno = None

            # Extract the filename without the directory path
            file = file.split('/')[-1].lower()
            extension = file.split('.')[-1]

            if extension in valid_extensions:
                valid = True

            if not valid:
                results.append((valid, extension, filetype, fieldtype, analyte1, analyte2, unit))
                continue

            # Remove extension and sample_id
            filename = file.replace('.' + extension, '').replace(sample_id, '')

            # Remove units
            for u in units:
                if u in filename:
                    unit = u
                    filename = filename.replace(u, '')

            # Check if matrix file type
            if 'matrix' in filename:
                filetype = 'matrix'
                filename = filename.replace('matrix', '')

            # Step 1: Split the filename by the specified delimiters
            filename_lower = filename.lower()

            parts = re.split(delimiters, filename_lower)

            # Convert isotopes dictionary keys to lowercase for case-insensitive matching
            isotopes_lower = {k.lower(): [m.lower() for m in v] for k, v in isotopes.items()}

            # Track used masses
            used_masses = set()

            # Process combined patterns
            for part in parts:
                combined_pattern = re.match(r'([a-z]+)(\d+)_(\d+)', part)
                if combined_pattern:
                    # Extract the element and the two isotopes
                    element, mass1, mass2 = combined_pattern.groups()
                    if element in isotopes_lower:
                        if mass1 in isotopes_lower[element] and mass1 not in used_masses:
                            if not analyte1:
                                analyte1 = element + mass1
                                used_masses.add(mass1)
                        if mass2 in isotopes_lower[element] and mass2 not in used_masses:
                            if not analyte2:
                                analyte2 = element + mass2
                                used_masses.add(mass2)
                        continue  # Skip to the next part since we've already handled this part

            # If analytes are still not assigned, check remaining parts
            if not analyte1 or not analyte2:
                possible_elements = []
                possible_masses = []

                for part in parts:
                    if any(char.isdigit() for char in part) and any(char.isalpha() for char in part):
                        split_parts = re.findall(r'[a-z]+|\d+', part)
                        for sp in split_parts:
                            if sp.isdigit():
                                possible_masses.append(sp)
                            elif sp in isotopes_lower:
                                possible_elements.append(sp)
                    elif part.isdigit():
                        possible_masses.append(part)
                    elif part in isotopes_lower:
                        possible_elements.append(part)

                # Assign analytes if they aren't assigned yet
                if possible_elements and possible_masses:
                    for element in possible_elements:
                        valid_isotopes = isotopes_lower.get(element, [])
                        for number in possible_masses:
                            if number in valid_isotopes and number not in used_masses:
                                if not analyte1:
                                    analyte1 = element + number
                                    used_masses.add(number)
                                elif not analyte2:
                                    analyte2 = element + number
                                    used_masses.add(number)
                                if analyte1 and analyte2:
                                    break


            # Debugging: Print analytes
            print(f"Analyte 1: {analyte1}")
            print(f"Analyte 2: {analyte2}")

            # If all numbers, probably a line number            
            if filetype is None and analyte1 is None and analyte2 is None:
                if possible_masses:
                    filetype = 'line'
                    lineno = possible_masses[0]

            if analyte2 is not None:
                analyte1 = analyte1.capitalize()
                analyte2 = analyte2.capitalize()
                fieldtype = 'Ratio'
            elif analyte1 is not None:
                analyte1 = analyte1.capitalize()
                fieldtype = 'Analyte'

            # Final validity check
            if filetype is None:
                valid = False
            else:
                valid = True

            if valid and lineno is not None:
                results.append((valid, extension, filetype, fieldtype, lineno, None, unit))
            else:
                results.append((valid, extension, filetype, fieldtype, analyte1, analyte2, unit))

        return results

    def import_data(self): 
        """Import data associated with each *Sample Id* using metadata to define important structural parameters

        A wrapper for importing data associated with different data types, instruments and other file types.
        """
        self.ok = False

        data_type = self.comboBoxDataType.currentText()
        #self.metadata['directory_data'] = self.qtablewidget_to_dataframe(self.tableWidgetMetadata)
        self.metadata['directory_data'] = self.get_metadata()

        if not self.checkBoxSaveToRoot.isChecked():
            save_path = QFileDialog.getExistingDirectory(None, "Select a folder to Save imports", options=QFileDialog.Option.ShowDirsOnly)
            if not save_path:
                return
        else:
            save_path = self.root_path

        match data_type:
            case 'LA-ICP-MS':
                method = self.comboBoxMethod.currentText()
                match method:
                    case 'quadrupole':
                        self.import_la_icp_ms_data(save_path)
                    case 'TOF':
                        # for now, require iolite or xmaptools output.  In future, allow for 
                        # TOF raw format.
                        self.import_la_icp_ms_data(save_path)
                        #df = pd.read_hdf(file_path, key='dataset_1')
                    case 'SF':
                        self.import_la_icp_ms_data(save_path)
            case 'MLA':
                pass
            case 'XRF':
                pass
            case 'petrography':
                pass
            case 'SEM':
                pass

        if self.ok:
            self.parent.io.open_directory(path=self.root_path)
        
    def import_la_icp_ms_data(self, save_path):
        """Reads LA-ICP-MS data into a DataFrame

        Parameters
        ----------
        save_path : str
            Location to save DataFrame reformatted into CSV for use in LaME
        """
        # The total number of files to parse are the number of selected files for samples with the import checkbox set to True.
        total_files = self.metadata['directory_data'].loc[self.metadata['directory_data']['Import'],'Select files'].sum()
        if total_files == 0:
            return
        
        # Initialize progress bar
        current_progress = 0
        self.progressBar.setMaximum(total_files)

        method = self.comboBoxMethod.currentText()
        
        final_data = pd.DataFrame([])
        num_imported = 0

#        try:
        # import all directories with samples
        for i,path in enumerate(self.paths):
            # if Import is False, skip directory
            if not self.metadata['directory_data']['Import'][i]:
                continue

            sample_id = self.sample_ids[i]

            # scan axis
            if self.metadata['directory_data']['Scan axis'][i] == 'Xc':
                swap_axis = False
            else:
                swap_axis = True

            # swapping x and y is handled at end
            swap_xy = self.metadata['directory_data']['Swap XY'][i]
            
            # reversing is handled at end
            reverse_x = self.metadata['directory_data']['Reverse X'][i]
            reverse_y = self.metadata['directory_data']['Reverse Y'][i]

            dx = self.metadata['directory_data']['Spot size'][i]
            if dx is None:
                dx = 1
            else:
                dx = float(dx)
            sweep_time = self.metadata['directory_data']['Sweep'][i]
            speed = self.metadata['directory_data']['Speed'][i]
            if speed is None or sweep_time is None:
                dy = dx
            else:
                dy = float(speed)*float(sweep_time)

            if swap_axis == 'Y':
                tmp = dx
                dx = dy
                dy = tmp

            data_frames = []

            # Convert to numeric, coercing errors (non-numeric values become NaN)
            numeric_check = pd.to_numeric(self.metadata[sample_id]['Analyte 1'], errors='coerce')

            # Check if a value is numeric (True for numeric values, False for non-numeric)
            is_numeric = all(numeric_check.notna())

            try:
                file_name = os.path.join(save_path, sample_id+'.lmdf.csv')
                self.metadata[sample_id].to_csv(file_name,index=False)
            except Exception as e:
                QMessageBox.warning(self,'Error',f"Could not save LaME metadata file associated with sample {sample_id}.\n{e}")


            first = True
            for i, file in enumerate(self.metadata[sample_id]['Filename']):
                if not self.metadata[sample_id]['Import'][i]:
                    continue

                file_path = os.path.join(path, file)
                if any(std in file for std in self.standard_list):
                    continue  # skip standard files

                analyte1 = self.metadata[sample_id]['Analyte 1'][i]
                analyte2 = self.metadata[sample_id]['Analyte 2'][i]
                if is_numeric:
                    # line data
                    df = self.read_raw_folder(analyte1, file_path, swap_xy, reverse_x, reverse_y)
                    data_frames.append(df)
                else:
                    # matrix data
                    if not analyte2:
                        analyte = analyte1
                    else:
                        analyte = f"{analyte1} / {analyte2}"

                    if first:
                        df = self.read_matrix_folder(analyte, file_path, swap_xy, reverse_x, reverse_y,dx,dy)
                        first = False
                    else:
                        df = self.read_matrix_folder(analyte, file_path, swap_xy, reverse_x, reverse_y)
                    
                    data_frames.append(df)

                current_progress += 1
                self.progressBar.setValue(current_progress)
                self.statusBar.showMessage(f"{sample_id}: {current_progress}/{total_files} files imported.")
                QApplication.processEvents()  # Process GUI events to update the progress bar

            if not data_frames:
                continue

            self.statusBar.showMessage(f'Formatting {sample_id}...')
            QApplication.processEvents()  # Process GUI events to update the progress bar
            if is_numeric:
                final_data = pd.concat(data_frames, ignore_index=True)
                
                # reverse x and/or y if needed
                if reverse_x:
                    final_data['Xc'] = -final_data['Xc']
                if reverse_y:
                    final_data['Yc'] = -final_data['Yc']
                
                # Adjust coordinates based on the reading direction and make upper left corner as (0,0)
                final_data['Xc'] = final_data['Xc'] - final_data['Xc'].min()
                final_data['Yc'] = final_data['Yc'] - final_data['Yc'].min()
            else:
                final_data = pd.concat(data_frames, axis = 1)
            
            if not data_frames:
                continue

            self.statusBar.showMessage(f'Formatting {sample_id}...')
            QApplication.processEvents()
            if is_numeric:
                final_data = pd.concat(data_frames, ignore_index=True)
                final_data['Xc'] -= final_data['Xc'].min() if reverse_x else 0
                final_data['Yc'] -= final_data['Yc'].min() if reverse_y else 0
            else:
                final_data = pd.concat(data_frames, axis=1)

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
        """Reads laser data formatted into files with separate lines, each with all analytes.

        Parameters
        ----------
        line_no : int
            Line number.
        file_path : str
            Full file path and name to be parsed.
        swap_xy : bool
            Flag indicating whether to swap the orientation of the file (``False`` = no swap).
        dx : float
            Size of pixel in x-direction
        dy : float
            Size of pixel in y-direction

        Returns
        -------
        pd.DataFrame
            Data in the current file, ``file_path``.
        """        
        df = pd.read_csv(file_path, skiprows=3)
        if swap_xy:
            df.insert(1,'Yc',(int(line_no)-1)*dy)
            df.insert(0,'Xc',range(0, len(df))*dx)
        else:
            df.insert(0,'Xc',(int(line_no)-1)*dx)
            df.insert(1,'Yc',range(0, len(df))*dy)
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
        # match = re.search(r' (\w+)_ppm', file_name)
        # match2 = re.search(r'(\D+)(\d+).csv', file_name) or re.search(r'(\d+)(\D+).csv', file_name)
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
        # test = re.search(r'(\d+)(\D+)', analyte)
        # if test:
        #     analyte = f"{test.group(2)}{test.group(1)}"
        
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
            new_df.insert(0,'Xc', X.flatten('F'))
            new_df.insert(1,'Yc', Y.flatten('F'))

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
        data.columns = ['Xc', 'Yc'] + list(data.columns[2:])
    
        # Calculate unique counts to define the grid
        nr = data['Xc'].nunique()
        nc = data['Yc'].nunique()
    
        # Generate ScanNum and SpotNum
        ScanNum = pd.DataFrame((1 + i for i in range(nc)).repeat(nr)).reset_index(drop=True)
        SpotNum = pd.DataFrame((1 + i for i in range(nr)).repeat(nc)).reset_index(drop=True)
        
        # Insert ScanNum and SpotNum as the first columns
        data.insert(0, 'ScanNum', ScanNum)
        data.insert(1, 'SpotNum', SpotNum)
    
        # Insert a NaN column for Time_Sec_ after 'Y'
        data.insert(data.columns.get_loc('Yc') + 1, 'Time_Sec_', pd.Series([float('nan')] * len(data)))
        return data

    def guess_analyte_from_filename(self, filename):
        # Implement your logic to guess the analyte from the filename
        # Example: Extract a portion of the filename as the guessed analyte
        return filename.split("_")[0]  # A simple placeholder example

    def process_file(self, filepath, analyte, units):
        # Implement the logic to process each file according to your specific needs
        print(f"Processing file: {filepath} with analyte {analyte} and units {units}")
        # Implement your file handling logic here

    def select_sample_files(self, row):
        """Calls ``FileSelectDialog`` for the user to select files for import and to update metadata.

        Executes when a push button in the *Select file* column of ``MapImporter.tableWidgetMetadata``.
        When the user accepts the state of the table in ``FileSelectDialog``, the text of the push button
        updates with the number of files to import for the sample and changes the Import check box to ``True``
        the number of files selected for import is greater than 0 and ``False`` otherwise.

        Parameters
        ----------
        row : int
            Row number associated with selected push button in ``MapImporter.tableWidgetMetadata``.
        """
        sample_id = self.sample_ids[row]
        # get current dataframe
        #self.metadata['directory_data'] = self.qtablewidget_to_dataframe(self.tableWidgetMetadata)
        self.metadata['directory_data'] = self.get_metadata()

        directory = self.paths[row]

        # Get a list of files in the directory
        file_list = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

        # Guess the analytes from filenames and allow user to change them and select files
        parsed_results = self.parse_filenames(sample_id, file_list)

        # Show the dialog to confirm or edit the file import details
        dialog = FileSelectData(sample_id, file_list, parsed_results, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Retrieve the updated data from the dialog
            self.metadata[sample_id] = dialog.get_data()
        else:
            return

        # Number of files in the sample directory to import
        import_count = sum(self.metadata[sample_id]['Import'])

        # Get the column index for "Sample files"
        for col in range(self.tableWidgetMetadata.columnCount()):
            col_name = self.tableWidgetMetadata.horizontalHeaderItem(col).text()
            match col_name:
                case 'Import':
                    # Get the button widget in the specific cell
                    widget = self.tableWidgetMetadata.cellWidget(row, col)
                    
                    if isinstance(widget, QCheckBox):
                        # Update the button's text with the import_count
                        widget.setChecked(import_count > 0)
                case 'Select files':
                    # Get the button widget in the specific cell
                    widget = self.tableWidgetMetadata.cellWidget(row, col)
                    
                    if isinstance(widget, QPushButton):
                        # Update the button's text with the import_count
                        widget.setText(f"{import_count} files")
                case _:
                    pass


class FileSelectData(QDialog, Ui_FileSelectorDialog):
    """

    _extended_summary_

    Parameters
    ----------
    QDialog : QDialog
        Inherits the properties of the QDialog
    Ui_FileSelectorDialog : UI
        UI interface design.  Note this interface was created in QtCreator, though it requires replacing
        of ``QtWidgets.TableWidget`` with ``CustomWidgets.CustomTableWidget``.  The custom widget adds a
        ``.to_dataframe()`` simplify data extraction tables (especially complex tables).
    """    
    def __init__(self, sample_id, file_list, parsed_results, parent=None):
        """Initializes a file selection dialog.

        Use the file selection dialog to pick the files for import and correcting parsing errors of individual files.

        Parameters
        ----------
        sample_id : str
            Sample id.
        file_list : list
            A list of files within the sample directory.
        parsed_results : list
            A multidimensional list of metadata and parsed information from the filenames in file_list.
        parent : _type_, optional
            Parent object, by default None
        """        
        super().__init__(parent)
        self.setupUi(self)

        self.parent = parent

        if not self.layout():
            layout = QVBoxLayout(self)
            self.setLayout(layout)
        else:
            layout = self.layout()

        toolbar = QToolBar(self)

        self.actionSelectAll = QAction(toolbar)
        select_all_icon = QIcon(":resources/icons/icon-select-all-64.svg")
        self.actionSelectAll.setIcon(select_all_icon)
        self.actionSelectAll.setToolTip("Select all files")

        self.actionSelectNone = QAction(toolbar)
        select_none_icon = QIcon(":resources/icons/icon-select-none-64.svg")
        self.actionSelectNone.setIcon(select_none_icon)
        self.actionSelectNone.setToolTip("Select all files")

        toolbar.addAction(self.actionSelectAll)
        toolbar.addAction(self.actionSelectNone)

        layout.insertWidget(0, toolbar)

        self.actionSelectAll.triggered.connect(self.select_all)
        self.actionSelectNone.triggered.connect(self.select_all)

        self.lineEditDirectory.setText(self.parent.root_path+"/"+sample_id)

        valid_extensions = ['csv', 'xlsx', 'xls']

        # Filter file_list and parsed_results based on valid extensions
        filtered_files = []
        filtered_results = []

        for file, result in zip(file_list, parsed_results):
            # Get the file extension (assume the extension is after the last dot in the filename)
            extension = file.split('.')[-1].lower()

            if extension in valid_extensions:
                filtered_files.append(file)
                filtered_results.append(result)

        # Initialize the table widget
        self.tableWidgetFileMetadata.setRowCount(len(filtered_files))

        # Populate the table with data
        for row, (filename, result) in enumerate(zip(filtered_files, filtered_results)):
            # Checkbox for import
            import_checkbox = QCheckBox()
            import_checkbox.setStyleSheet("text-align: center; margin-left:25%; margin-right:25%;")
            import_checkbox.setChecked(result[0])
            self.tableWidgetFileMetadata.setCellWidget(row, 0, import_checkbox)

            # Filename (non-editable)
            filename_item = QTableWidgetItem(filename)
            filename_item.setFlags(filename_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableWidgetFileMetadata.setItem(row, 1, filename_item)

            # Analyte Type ComboBox (editable)
            analyte_type_combo = QComboBox()
            analyte_type_combo.addItems(['Analyte', 'Ratio', 'computed'])
            analyte_type_combo.setCurrentText(result[3])
            self.tableWidgetFileMetadata.setCellWidget(row, 2, analyte_type_combo)

            # Guessed analyte (editable)
            analyte_item1 = QTableWidgetItem(result[4])
            self.tableWidgetFileMetadata.setItem(row, 3, analyte_item1)

            analyte_item2 = QTableWidgetItem(result[5])
            self.tableWidgetFileMetadata.setItem(row, 4, analyte_item2)

            # Units (editable)
            units_item = QTableWidgetItem("Unit")  # Default or guessed units
            units_item.setText(result[6])
            self.tableWidgetFileMetadata.setItem(row, 5, units_item)

        header = self.tableWidgetFileMetadata.horizontalHeader()
        for col in range(self.tableWidgetFileMetadata.columnCount()):
            if self.tableWidgetFileMetadata.horizontalHeaderItem(col).text() == 'Filename':
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)

        # Add buttons for OK and Cancel
        self.buttonBox.ok_button = QPushButton("OK")
        self.buttonBox.cancel_button = QPushButton("Cancel")

        # Connect buttons to actions
        self.buttonBox.ok_button.clicked.connect(self.accept)
        self.buttonBox.cancel_button.clicked.connect(self.reject)

    def select_all(self):
        for row in range(self.tableWidgetFileMetadata.rowCount()):
            # Checkbox for import
            widget = self.tableWidgetFileMetadata.cellWidget(row, 0)

            # Check if the widget exists and is a checkbox
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def select_none(self):
        for row in range(self.tableWidgetFileMetadata.rowCount()):
            # Checkbox for import
            widget = self.tableWidgetFileMetadata.cellWidget(row, 0)

            # Check if the widget exists and is a checkbox
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def get_data(self):
        """Returns the updated information from ``tableWidgetFileMetadata``."""
        data = self.tableWidgetFileMetadata.to_dataframe()

        return data
