import os, re, json, darkdetect
from collections import defaultdict
import pandas as pd
import numpy as np
import matplotlib as mpl
from matplotlib.colors import LogNorm
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QTableWidget, QTableWidgetItem, QInputDialog, QComboBox, QToolBar,
    QWidget, QCheckBox, QHeaderView, QProgressBar, QLineEdit, QMessageBox, QVBoxLayout, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QUrl
from lame_core.CustomWidgets import CustomAction
import src.common.csvdict as csvdict
from src.common.CustomMplCanvas import SimpleMplCanvas
from src.ui.MapImportDialog import Ui_MapImportDialog
from src.ui.FileSelectorDialog import Ui_FileSelectorDialog
from lame_core.config import BASEDIR, ICONPATH

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
        self.preview_index = None
        
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

        # sample preview
        preview_layout = QVBoxLayout(self.framePreviewSample)
        preview_layout.setContentsMargins(2, 2, 2, 2)
        self.preview_canvas = SimpleMplCanvas(parent=self, width=4, height=4)
        preview_layout.addWidget(self.preview_canvas)
        self.checkBoxPreview.setChecked(True)
        self.checkBoxPreview.toggled.connect(self.update_preview)
        self.update_preview()

        # connect bottom buttons
        self.pushButtonImport.clicked.connect(self.import_data)
        self.pushButtonImport.setEnabled(False)
        self.pushButtonLoad.clicked.connect(self.load_metadata)
        self.pushButtonSave.clicked.connect(self.save_metadata)
        self.pushButtonSave.setEnabled(False)
        self.pushButtonCancel.clicked.connect(self.reject)
        self.pushButtonCancel.setEnabled(True)

        self.tableWidgetMetadata.currentItemChanged.connect(self.on_item_changed)

        # Computed dX/dY preview columns, added at runtime (rather than in
        # the Designer .ui file) so they survive regeneration of
        # MapImportDialog.py from designer/MapImportDialog.ui.
        self.tableWidgetMetadata.insertColumn(11)
        self.tableWidgetMetadata.setHorizontalHeaderItem(11, QTableWidgetItem('dX\n(µm)'))
        self.tableWidgetMetadata.insertColumn(12)
        self.tableWidgetMetadata.setHorizontalHeaderItem(12, QTableWidgetItem('dY\n(µm)'))
        self.tableWidgetMetadata.itemChanged.connect(self.on_item_content_changed)

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
        data = data.rename(columns={
            'X\nreverse':'Reverse X', 'Y\nreverse': 'Reverse Y', 'Spot size\n(µm)': 'Spot size',
            'Sweep\n(s)': 'Sweep', 'Speed\n(µm/s)':'Speed',
            'Length\n(µm)': 'Length', 'Width\n(µm)': 'Width',
        })

        return data

    def change_preview(self,next=True):
        # Get indexes of samples that are selected for analysis
        selected = []
        for i in range(len(self.sample_ids)):
            if self.tableWidgetMetadata.cellWidget(i,0).isChecked():
                selected.append(i)

        if not selected:
            self.labelSampleID.setText("None selected")
            self.preview_index = None
            self.update_preview()
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
        self.update_preview()

    def update_preview(self):
        """Renders a map preview of the currently previewed sample in ``framePreviewSample``.

        Falls back to a placeholder message when preview is disabled, no sample is
        selected for preview, or its data can't be read yet (e.g. no files chosen).
        """
        if not hasattr(self, 'preview_canvas'):
            return

        ax = self.preview_canvas.axes
        ax.clear()
        ax.set_xticks([])
        ax.set_yticks([])

        if not self.checkBoxPreview.isChecked():
            ax.text(0.5, 0.5, 'Preview disabled', ha='center', va='center', transform=ax.transAxes, wrap=True)
            self.labelResolution.setText('')
            self.preview_canvas.draw_idle()
            return

        array, label = None, None
        if self.preview_index is not None and self.sample_ids:
            sample_id = self.sample_ids[self.preview_index]
            array, label = self.get_preview_array(sample_id)

        if array is None:
            ax.text(0.5, 0.5, '[Preview not available]', ha='center', va='center', transform=ax.transAxes, wrap=True)
            self.labelResolution.setText('')
        else:
            # Geochemical maps often span orders of magnitude, so color on a log
            # scale; LogNorm masks non-positive/NaN values instead of erroring.
            # Clip to the 2.5-97.5 percentile range so a few outlier pixels (e.g.
            # inclusions, edge artifacts) don't wash out the rest of the map.
            positive = array[np.isfinite(array) & (array > 0)]
            if positive.size:
                vmin, vmax = np.percentile(positive, [2.5, 97.5])
                norm = LogNorm(vmin=vmin, vmax=vmax)
            else:
                norm = None

            cmap = mpl.colormaps['viridis'].copy()
            cmap.set_bad('lightgray')

            ax.imshow(array, cmap=cmap, aspect='auto', origin='upper', norm=norm)
            if label:
                ax.set_title(f"{label} (log scale)" if norm else label, fontsize=8)
            self.labelResolution.setText(f"Resolution: {array.shape[1]} x {array.shape[0]}")

        self.preview_canvas.draw_idle()

    def apply_row_orientation(self, array, row_idx):
        """Applies a row's Swap XY / Reverse X / Reverse Y settings to a 2D array.

        Mirrors the transform ``read_matrix_folder``/``read_raw_folder`` apply
        to the real imported data, so the preview (including the reported
        "Resolution: W x H") reflects what will actually be imported instead
        of always showing the raw file's untransformed shape.

        Parameters
        ----------
        array : numpy.ndarray
            2D preview array, rows=Y, columns=X, in the file's native orientation.
        row_idx : int
            Row index into ``tableWidgetMetadata`` for the owning sample.

        Returns
        -------
        numpy.ndarray
            ``array``, transposed/flipped to match the row's settings.
        """
        cols = {self.tableWidgetMetadata.horizontalHeaderItem(c).text(): c
                for c in range(self.tableWidgetMetadata.columnCount())}

        def checked(col_name):
            col = cols.get(col_name)
            if col is None:
                return False
            widget = self.tableWidgetMetadata.cellWidget(row_idx, col)
            return widget.isChecked() if widget else False

        swap_xy = checked('Swap XY')
        reverse_x = checked('X\nreverse')
        reverse_y = checked('Y\nreverse')

        # Match read_matrix_folder's ordering: reverses are applied in the
        # file's native orientation, before the swap (transpose).
        if reverse_x:
            array = array[:, ::-1]
        if reverse_y:
            array = array[::-1, :]
        if swap_xy:
            array = array.T

        return array

    def get_preview_array(self, sample_id):
        """Builds a rough 2D preview array from a sample's currently selected import files.

        For matrix-style exports (e.g. XMapTools) the first selected file already *is* the
        map grid, so it's read and shown directly. For per-line exports (e.g. Iolite/LADr,
        where the filename encodes a line number) the selected files are sorted by line
        number and stacked into a grid, using the first data column of each file.

        Parameters
        ----------
        sample_id : str
            Sample to preview; a key in ``MapImporter.metadata``.

        Returns
        -------
        tuple(numpy.ndarray or None, str or None)
            Map values to render and a label for the previewed field, or ``(None, None)``
            if there isn't enough data yet (e.g. no files selected for this sample).
        """
        df = self.metadata.get(sample_id)
        if df is None or df.empty or 'Import' not in df.columns:
            return None, None

        selected = df[df['Import'].astype(bool)]
        if selected.empty:
            return None, None

        standard_list = getattr(self, 'standard_list', [])
        if standard_list:
            selected = selected[~selected['Filename'].apply(lambda f: any(std in f for std in standard_list))]
        if selected.empty:
            return None, None

        row_idx = self.sample_ids.index(sample_id)
        path = self.paths[row_idx]

        numeric_check = pd.to_numeric(df['Analyte 1'], errors='coerce')
        is_numeric = numeric_check.notna().all()

        try:
            if is_numeric:
                selected = selected.copy()
                selected['_line_no'] = pd.to_numeric(selected['Analyte 1'], errors='coerce')
                selected = selected.sort_values('_line_no')

                # Cap the number of lines read so the preview stays responsive on large maps.
                max_preview_lines = 200
                if len(selected) > max_preview_lines:
                    step = max(1, len(selected) // max_preview_lines)
                    selected = selected.iloc[::step]

                rows = []
                label = None
                for _, file_row in selected.iterrows():
                    file_path = os.path.join(path, file_row['Filename'])
                    line_df = pd.read_csv(file_path, skiprows=3)
                    if line_df.empty:
                        continue
                    if label is None:
                        label = str(line_df.columns[0])
                    rows.append(pd.to_numeric(line_df.iloc[:, 0], errors='coerce').to_numpy())

                if not rows:
                    return None, None

                max_len = max(len(r) for r in rows)
                grid = np.full((len(rows), max_len), np.nan)
                for i, r in enumerate(rows):
                    grid[i, :len(r)] = r
                return self.apply_row_orientation(grid, row_idx), label
            else:
                file_row = selected.iloc[0]
                file_path = os.path.join(path, file_row['Filename'])

                if file_path.endswith('.csv'):
                    grid_df = pd.read_csv(file_path, header=None)
                elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    grid_df = pd.read_excel(file_path, header=None)
                else:
                    return None, None

                grid_df = grid_df.dropna(how='all', axis=0).dropna(how='all', axis=1)
                grid = grid_df.apply(pd.to_numeric, errors='coerce').to_numpy()

                analyte1 = file_row.get('Analyte 1')
                analyte2 = file_row.get('Analyte 2')
                label = f"{analyte1} / {analyte2}" if analyte2 else str(analyte1)
                return self.apply_row_orientation(grid, row_idx), label
        except Exception as e:
            self.statusBar.showMessage(f"Preview unavailable: {e}")
            return None, None

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
        self.update_preview()
    
    def update_method_columns(self):
        """Swaps the Sweep/Speed metadata columns for Length/Width when TOF is selected.

        Quadrupole/SF instruments only report spot size, sweep time, and stage speed, from
        which per-pixel spacing (dx, dy) must be derived. TOF instruments report the raster's
        physical length (X) and width (Y) directly, so those replace Sweep/Speed instead.
        """
        method = self.comboBoxMethod.currentText()
        col_sweep = self.tableWidgetMetadata.horizontalHeaderItem(9)
        col_speed = self.tableWidgetMetadata.horizontalHeaderItem(10)
        if method == 'TOF':
            col_sweep.setText('Length\n(µm)')
            col_speed.setText('Width\n(µm)')
        else:
            col_sweep.setText('Sweep\n(s)')
            col_speed.setText('Speed\n(µm/s)')

    def populate_la_icp_ms_table(self):
        """Populates table with LA-ICP-MS sample metadata

        Several fields are made into checkboxes.
        """
        self.update_method_columns()
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
                    case 'Spot size\n(µm)' | 'Sweep\n(s)' | 'Speed\n(µm/s)' | 'Length\n(µm)' | 'Width\n(µm)':
                        self.add_numeric_item(row, col)
                    case 'dX\n(µm)' | 'dY\n(µm)':
                        self.add_computed_item(row, col)
                    # case _:
                    #     self.add_lineedit(row, col)
                    # case 'Filename\nformat':
                    #     self.add_combobox(row, col, ['SampleID-LineNum','LineNum-SampleID'], 0)

        self.update_all_computed_spacing()

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
        cb.toggled.connect(lambda _, r=row, c=col: self.on_checkbox_changed(r, c))
        self.tableWidgetMetadata.setCellWidget(row, col, cb)

    def on_checkbox_changed(self, row, column):
        """Refreshes the sample preview when a checkbox affecting its
        orientation (Swap XY / X reverse / Y reverse) is toggled for the
        currently-previewed row -- otherwise the preview (and its reported
        "Resolution: W x H") keeps showing the file's raw, untransformed
        shape until something else happens to trigger a redraw.
        """
        col_name = self.tableWidgetMetadata.horizontalHeaderItem(column).text()
        if col_name in ('Swap XY', 'X\nreverse', 'Y\nreverse') and row == self.preview_index:
            self.update_preview()

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

    def add_numeric_item(self, row, col):
        """Adds an empty, editable, right-aligned numeric cell to a QTableWidget

        Used for metadata fields (Spot size, Sweep, Speed, Length, Width) that the user
        types in directly, rather than a checkbox or comboBox.

        Parameters
        ----------
        row, col : int
            Row and column indices
        """
        item = QTableWidgetItem('')
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tableWidgetMetadata.setItem(row, col, item)

    def add_computed_item(self, row, col):
        """Adds a read-only, right-aligned display cell to a QTableWidget

        Used for the computed dX/dY preview columns -- not editable, since
        they're derived from Spot size/Sweep/Speed (or Length/Width for TOF)
        and Scan axis rather than typed in directly.

        Parameters
        ----------
        row, col : int
            Row and column indices
        """
        item = QTableWidgetItem('')
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.tableWidgetMetadata.setItem(row, col, item)

    def compute_pixel_spacing(self, spot_size, sweep_time, speed, scan_axis=None):
        """Computes per-pixel spacing (dx, dy) for quadrupole/SF instruments.

        Shared by the live dX/dY preview columns and the actual import step
        (``import_la_icp_ms_data``), so they can never diverge.

        Not applicable to TOF: TOF's true per-pixel spacing is derived from
        the raster's physical Length/Width divided by the file's actual pixel
        grid dimensions, which aren't known until a file is read (see
        ``read_matrix_folder``) -- there's no table-only preview to compute here.

        Parameters
        ----------
        spot_size : float
            Laser spot diameter (µm).
        sweep_time : float or None
            Detector sweep/cycle time (s).
        speed : float or None
            Stage scan speed (µm/s).
        scan_axis : str, optional
            ``'Xc'`` or ``'Yc'`` -- which axis is the fast, continuous-motion
            scan direction; swaps dx/dy when not ``'Xc'``. Pass ``None``
            (default) to skip the swap, e.g. when the caller applies its own
            swap separately (``import_la_icp_ms_data``'s ``swap_axis`` step).

        Returns
        -------
        dx, dy : float
            Per-pixel spacing along X and Y (µm).
        """
        dx = spot_size
        if not speed or not sweep_time:
            dy = dx
        else:
            dy = float(speed) * float(sweep_time)

        if scan_axis and scan_axis != 'Xc':
            dx, dy = dy, dx

        return dx, dy

    def build_sample_metadata(self, row_index, method, dx, dy, n_files):
        """Assembles the sample-level acquisition metadata dict for one imported sample.

        Only includes keys that are actually available for ``method`` -- no filenames
        or paths, those live in the separate per-analyte ``analytes`` list.

        Parameters
        ----------
        row_index : int
            Row into ``self.metadata['directory_data']`` for this sample.
        method : str
            ``'quadrupole'``, ``'TOF'``, or ``'SF'``.
        dx, dy : float
            Final (post scan-axis-swap) per-pixel spacing, µm.
        n_files : int
            Number of non-standard files actually imported for this sample.

        Returns
        -------
        dict
            Flat key/value acquisition metadata, suitable for ``json.dump``.
        """
        directory_data = self.metadata['directory_data']

        meta = {
            'Number of files': n_files,
            'Standard': directory_data['Standard'][row_index],
        }

        spot_size = directory_data['Spot size'][row_index]
        meta['Spot size (um)'] = float(spot_size) if spot_size else None

        if method == 'TOF':
            length = directory_data['Length'][row_index]
            width = directory_data['Width'][row_index]
            meta['Length (um)'] = float(length) if length else None
            meta['Width (um)'] = float(width) if width else None
        else:
            sweep = directory_data['Sweep'][row_index]
            speed = directory_data['Speed'][row_index]
            meta['Sweep (s)'] = float(sweep) if sweep else None
            meta['Speed (um/s)'] = float(speed) if speed else None

        meta['dX (um)'] = dx
        meta['dY (um)'] = dy
        meta['Scan axis'] = directory_data['Scan axis'][row_index]
        meta['Swap XY'] = bool(directory_data['Swap XY'][row_index])
        meta['Reverse X'] = bool(directory_data['Reverse X'][row_index])
        meta['Reverse Y'] = bool(directory_data['Reverse Y'][row_index])

        return meta

    def update_computed_spacing(self, row):
        """Recomputes and redisplays the dX/dY preview cells for one row."""
        cols = {self.tableWidgetMetadata.horizontalHeaderItem(c).text(): c
                for c in range(self.tableWidgetMetadata.columnCount())}
        if 'dX\n(µm)' not in cols or 'dY\n(µm)' not in cols:
            return

        def cell_text(col_name):
            col = cols.get(col_name)
            if col is None:
                return ''
            item = self.tableWidgetMetadata.item(row, col)
            return item.text() if item else ''

        def cell_float(col_name):
            text = cell_text(col_name)
            try:
                return float(text) if text else None
            except ValueError:
                return None

        dx_item = self.tableWidgetMetadata.item(row, cols['dX\n(µm)'])
        dy_item = self.tableWidgetMetadata.item(row, cols['dY\n(µm)'])
        if dx_item is None or dy_item is None:
            # Cells not created yet -- e.g. mid-population, before
            # add_computed_item() has reached these columns for this row.
            # update_all_computed_spacing() re-runs once population finishes.
            return

        method = self.comboBoxMethod.currentText()

        # blockSignals: writing these cells must not re-trigger
        # on_item_content_changed (which would recompute this same row again).
        self.tableWidgetMetadata.blockSignals(True)
        if method == 'TOF':
            # TOF's true per-pixel spacing = Length/Width divided by the
            # file's actual pixel grid, unknown until a file is read -- no
            # honest table-only preview to show here.
            dx_item.setText('—')
            dy_item.setText('—')
            tooltip = 'Computed from Length/Width and the file\'s actual pixel grid once files are selected.'
            dx_item.setToolTip(tooltip)
            dy_item.setToolTip(tooltip)
        else:
            spot_size = cell_float('Spot size\n(µm)')
            if spot_size is None:
                spot_size = 1.0

            scan_axis_combo = self.tableWidgetMetadata.cellWidget(row, cols['Scan axis'])
            scan_axis = scan_axis_combo.currentText() if scan_axis_combo else 'Xc'

            dx, dy = self.compute_pixel_spacing(
                spot_size, cell_float('Sweep\n(s)'), cell_float('Speed\n(µm/s)'), scan_axis)
            dx_item.setText(f'{dx:.3g}')
            dy_item.setText(f'{dy:.3g}')
            dx_item.setToolTip('')
            dy_item.setToolTip('')
        self.tableWidgetMetadata.blockSignals(False)

    def update_all_computed_spacing(self):
        """Recomputes the dX/dY preview cells for every row in the table."""
        for row in range(self.tableWidgetMetadata.rowCount()):
            self.update_computed_spacing(row)

    def on_item_content_changed(self, item):
        """Recomputes the dX/dY preview for a row when a relevant cell is edited.

        Connected to ``tableWidgetMetadata.itemChanged``, which fires on any
        cell content change -- including the dX/dY cells' own updates, so
        ``update_computed_spacing`` blocks signals while writing them to
        avoid recursing back into this handler.
        """
        col_name = self.tableWidgetMetadata.horizontalHeaderItem(item.column()).text()
        if col_name in ('Spot size\n(µm)', 'Sweep\n(s)', 'Speed\n(µm/s)', 'Length\n(µm)', 'Width\n(µm)'):
            self.update_computed_spacing(item.row())

    def on_item_changed(self, curr_item, prev_item):
        if prev_item:
            if self.checkBoxApplyAll.isChecked() and prev_item.column() != 0:
                column = prev_item.column()
                for row in range(self.tableWidgetMetadata.rowCount()):
                    if row != prev_item.row():
                        new_item = QTableWidgetItem(prev_item.text())
                        self.tableWidgetMetadata.setItem(row, column, new_item)

    def on_combobox_changed(self, row, column):
        if self.checkBoxApplyAll.isChecked():
            combo = self.tableWidgetMetadata.cellWidget(row, column)
            selected_text = combo.currentText()
            for r in range(self.tableWidgetMetadata.rowCount()):
                if r != row:
                    self.tableWidgetMetadata.cellWidget(r, column).setCurrentText(selected_text)

        col_name = self.tableWidgetMetadata.horizontalHeaderItem(column).text()
        if col_name == 'Scan axis':
            self.update_computed_spacing(row)


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

            # Strip a "total" qualifier (e.g. "PbTotal") so the remaining text is just
            # the element symbol; `filename` is already lowercased (via `file` above),
            # so this comparison is case-insensitive.
            if 'total' in filename:
                filename = filename.replace('total', '')

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
                elif possible_elements and not possible_masses:
                    # No isotope mass anywhere in the filename, but exactly one recognized
                    # element symbol (e.g. "Pb_tot", "Pb Total") -- instruments sometimes
                    # report an element total without a specific isotope mass. Treat it as
                    # a valid Analyte for that element rather than leaving it unrecognized.
                    unique_elements = list(dict.fromkeys(possible_elements))
                    if len(unique_elements) == 1 and not analyte1:
                        analyte1 = unique_elements[0]


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

    def prefer_std_corrected(self, files, results):
        """Prefers standard-corrected files over uncorrected duplicates.

        Some export pipelines produce both a raw file and a "StdCorr"
        (standard-corrected) file for the same analyte/ratio, e.g.
        ``Hf178.csv`` and ``Hf178_StdCorr.csv``. Both parse to the same
        (fieldtype, analyte1, analyte2) key in `results` and, left alone,
        both default to selected -- producing duplicate columns downstream.
        When a "StdCorr" file (matched case-insensitively) is present
        alongside an uncorrected one for the same key, only the StdCorr
        file is left checked by default; the user can still re-check the
        uncorrected file by hand in the file-selection dialog.

        Parameters
        ----------
        files : list of str
            Filenames parallel to `results` (as passed to `parse_filenames`).
        results : list of tuple
            Output of `parse_filenames`.

        Returns
        -------
        list of tuple
            `results` with the leading "valid"/import-default flag cleared
            on non-StdCorr files that lose to a StdCorr duplicate.
        """
        groups = defaultdict(list)
        for i, result in enumerate(results):
            valid, _extension, _filetype, fieldtype, analyte1, analyte2, _unit = result
            if not valid or fieldtype not in ('Analyte', 'Ratio'):
                continue
            groups[(fieldtype, analyte1, analyte2)].append(i)

        for idxs in groups.values():
            if len(idxs) < 2:
                continue
            std_corr_idxs = {i for i in idxs if 'stdcorr' in files[i].lower()}
            if not std_corr_idxs or len(std_corr_idxs) == len(idxs):
                # No StdCorr variant present, or every copy is StdCorr --
                # nothing to prefer between.
                continue
            for i in idxs:
                if i not in std_corr_idxs:
                    results[i] = (False,) + results[i][1:]

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
            # Reimporting a sample that's already loaded overwrites its
            # .lame.csv file on disk, but if the set of sample IDs in the
            # directory is unchanged (the common case), neither
            # AppData.sample_list's nor .sample_id's setter fires a change
            # notification -- both explicitly no-op when the *identifiers*
            # haven't changed, even though the underlying file content has.
            # The stale in-memory SampleObj cached from the previous load
            # would otherwise never get refreshed. Evict any reimported
            # sample from the cache so change_sample() (which only reloads
            # a sample when it isn't already in self.data) re-reads it.
            for sample_id in self.sample_ids:
                self.parent.data.pop(sample_id, None)

            self.parent.io.open_directory(path=self.root_path)

            if self.parent.app_data.sample_id in self.sample_ids:
                self.parent.change_sample()

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

            spot_size = self.metadata['directory_data']['Spot size'][i]
            spot_size = float(spot_size) if spot_size else 1.0

            # TOF instruments report the raster's physical length (X) and width (Y)
            # directly, rather than sweep time and stage speed. dx, dy (per-pixel
            # spacing) are derived from these once the file's raster shape is known --
            # see read_matrix_folder/read_raw_folder below. Spot size remains relevant
            # as metadata and as a fallback if length/width weren't provided.
            raster_length = raster_width = None
            if method == 'TOF':
                length_val = self.metadata['directory_data']['Length'][i]
                width_val = self.metadata['directory_data']['Width'][i]
                raster_length = float(length_val) if length_val else None
                raster_width = float(width_val) if width_val else None
                dx = spot_size
                dy = spot_size
            else:
                sweep_time = self.metadata['directory_data']['Sweep'][i]
                speed = self.metadata['directory_data']['Speed'][i]
                dx, dy = self.compute_pixel_spacing(spot_size, sweep_time, speed)

            if swap_axis:
                tmp = dx
                dx = dy
                dy = tmp

            data_frames = []

            # Convert to numeric, coercing errors (non-numeric values become NaN)
            numeric_check = pd.to_numeric(self.metadata[sample_id]['Analyte 1'], errors='coerce')

            # Check if a value is numeric (True for numeric values, False for non-numeric)
            is_numeric = all(numeric_check.notna())

            # non-standard, Import=True files for this sample -- used both to refine
            # TOF's per-line dy spacing below and as the 'Number of files' metadata field
            selected_files = self.metadata[sample_id].loc[self.metadata[sample_id]['Import'], 'Filename']
            n_files = sum(1 for f in selected_files if not any(std in f for std in self.standard_list))

            if method == 'TOF' and is_numeric and raster_width is not None and n_files:
                # Per-line spacing (dy): total map width divided by the number of lines
                # actually being imported for this sample.
                dy = raster_width / n_files

            try:
                file_name = os.path.join(save_path, sample_id+'.lmdf.json')
                sample_meta = {
                    'data_type': 'LA-ICP-MS',
                    'method': method,
                    'metadata': self.build_sample_metadata(i, method, dx, dy, n_files),
                    'analytes': self.metadata[sample_id].to_dict(orient='records'),
                }
                with open(file_name, 'w') as f:
                    json.dump(sample_meta, f, indent=2, default=str)
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
                    if method == 'TOF' and raster_length is not None:
                        df = self.read_raw_folder(analyte1, file_path, swap_xy, dx, dy, length=raster_length)
                    else:
                        df = self.read_raw_folder(analyte1, file_path, swap_xy, dx, dy)
                    data_frames.append(df)
                else:
                    # matrix data
                    if not analyte2:
                        analyte = analyte1
                    else:
                        analyte = f"{analyte1} / {analyte2}"

                    if first:
                        if method == 'TOF' and raster_length is not None and raster_width is not None:
                            df = self.read_matrix_folder(analyte, file_path, swap_xy, reverse_x, reverse_y, length=raster_length, width=raster_width)
                        else:
                            df = self.read_matrix_folder(analyte, file_path, swap_xy, reverse_x, reverse_y, dx, dy)
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
            
    def read_raw_folder(self,line_no,file_path, swap_xy, dx, dy, length=None):
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
        length : float, optional
            Physical length of this raster line in µm (TOF instruments report this
            directly). When given, ``dx`` is derived from it instead of being used as-is.

        Returns
        -------
        pd.DataFrame
            Data in the current file, ``file_path``.
        """
        df = pd.read_csv(file_path, skiprows=3)
        if length is not None and len(df):
            dx = length / len(df)
        if swap_xy:
            df.insert(1,'Yc',(int(line_no)-1)*dy)
            df.insert(0,'Xc',np.arange(len(df))*dx)
        else:
            df.insert(0,'Xc',(int(line_no)-1)*dx)
            df.insert(1,'Yc',np.arange(len(df))*dy)
        return df
   
    def read_matrix_folder(self, analyte, file_path, swap_xy, reverse_x, reverse_y, dx=None, dy=None, length=None, width=None):
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
        length, width : float, optional
            Physical length (X) and width (Y) of the raster in µm (TOF instruments report
            these directly). When given, ``dx``/``dy`` are derived from them and the grid's
            pixel counts instead of being used as-is.

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
        if dx is None and length is not None and width is not None:
            # TOF instruments report the raster's physical length/width directly;
            # derive per-pixel spacing from the map extent and the grid's pixel counts.
            M, N = df.shape
            dx = length / N
            dy = width / M

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
        parsed_results = self.prefer_std_corrected(file_list, parsed_results)

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

        # if this is the first sample with files selected, make it the preview
        if import_count > 0 and self.preview_index is None:
            self.preview_index = row
            self.labelSampleID.setText(sample_id)
            self.toolButtonPrevSample.setEnabled(True)
            self.toolButtonNextSample.setEnabled(True)

        if row == self.preview_index:
            self.update_preview()


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

        self.actionSelectAll = CustomAction(
            text="Select All",
            light_icon_unchecked="icon-select-all-64.svg",
            dark_icon_unchecked="icon-select-all-dark-64.svg",
            parent=toolbar
        )
        self.actionSelectAll.setToolTip("Select all files")

        self.actionSelectNone = CustomAction(
            text="Select None",
            light_icon_unchecked="icon-select-none-64.svg",
            dark_icon_unchecked="icon-select-none-dark-64.svg",
            parent=toolbar,
        )
        self.actionSelectNone.setToolTip("Deselect all files")

        toolbar.addAction(self.actionSelectAll)
        toolbar.addAction(self.actionSelectNone)

        layout.insertWidget(0, toolbar)

        self.actionSelectAll.triggered.connect(self.select_all)
        self.actionSelectNone.triggered.connect(self.select_none)

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
