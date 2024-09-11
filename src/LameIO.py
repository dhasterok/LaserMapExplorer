import os
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem
import src.SpotImporter as SpotImporter
from lame_helper import BASEDIR

# -------------------------------------
# File I/O related functions
# -------------------------------------
class LameIO():
    def __init__(self, parent=None):
        if parent is None:
            return

        self.parent = parent

        self.parent.actionOpenSample.triggered.connect(self.open_sample)
        self.parent.actionOpenDirectory.triggered.connect(lambda: self.open_directory(dir_name=None))
        self.parent.actionImportSpots.triggered.connect(self.import_spots)

    def open_sample(self):
        """Opens a single *.lame.csv file.

        Opens files created by MapImporter.
        """        
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("LaME CSV (*.csv)")
        if dialog.exec_():
            file_list = dialog.selectedFiles()
            self.parent.selected_directory = os.path.dirname(os.path.abspath(file_list[0]))
            
            self.parent.csv_files = [os.path.split(file)[1] for file in file_list if file.endswith('.csv')]
            if self.parent.csv_files == []:
                # warning dialog
                self.parent.statusBar.showMessage("No valid csv files found.")
                return
        else:
            return
        self.parent.initialise_samples_and_tabs()


    def open_directory(self, dir_name=None):
        """Open directory with samples in *.lame.csv files.

        Executes on ``MainWindow.actionOpen`` and ``MainWindow.actionOpenDirectory``.  Opening a directory, enables
        the toolboxes.

        Alternatively, *open_dicrectory* is called after ``MapImporter`` successfully completes an import and the tool
        is closed.

        Opens a dialog to select directory filled with samples.  Updates sample list in
        ``MainWindow.comboBoxSampleID`` and comboBoxes associated with analyte lists.  The first sample
        in list is loaded by default.

        Parameters
        ----------
        dir_name : str
            Path to datafiles, if ``None``, an open directory dialog is openend, by default ``None``
        """
        if dir_name is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.Directory)
            # Set the default directory to the current working directory
            # dialog.setDirectory(os.getcwd())
            dialog.setDirectory(BASEDIR)
            if dialog.exec_():
                self.parent.selected_directory = dialog.selectedFiles()[0]
            else:
                self.parent.statusBar.showMessage("Open directory canceled.")
                return
        else:
            self.parent.selected_directory = dir_name

        file_list = os.listdir(self.parent.selected_directory)
        self.parent.csv_files = [file for file in file_list if file.endswith('.lame.csv')]
        if self.parent.csv_files == []:
            # warning dialog
            self.parent.statusBar.showMessage("No valid csv files found.")
            return

        self.initialize_samples_and_tabs()


    def import_spots(self):
        """Import a data file with spot data."""
        # import spot dialog
        self.spotDialog = SpotImporter.SpotImporter(self)
        self.spotDialog.show()

        if not self.spotDialog.ok:
            return

        self.populate_spot_table()

    def populate_spot_table(self):
        """Populates spot table when spot file is opened or sample is changed

        Populates ``MainWindow.tableWidgetSpots``.
        """        
        if self.parent.sample_id == '':
            return
        
        filtered_df = self.parent.spotdata[self.parent.sample_id==self.parent.spotdata['sample_id']]
        filtered_df = filtered_df['sample_id','X','Y','visible','display_text']

        self.parent.tableWidgetSpots.clearContents()
        self.parent.tableWidgetSpots.setRowCount(len(filtered_df))
        header = self.parent.tableWidgetSpots.horizontalHeader()

        for row_index, row in filtered_df.iterrows():
            for col_index, value in enumerate(row):
                self.parent.tableWidgetSpots.setItem(row_index, col_index, QTableWidgetItem(str(value)))

    def initialize_samples_and_tabs(self):
        """
        Initialize samples and tabs in the application.

        This method performs the following tasks:
        - Clears the current analysis
        - Sets up sample IDs
        - Populates the sample ID combobox
        - Changes to the first sample
        - Initializes tabs
        - Sets up profiling and polygon samples
        
        Initializes ``MainWindow.treeView``.  The ``tree`` is intialized for each of the plot groups.
        ``Analyte`` its normalized counterpart are initialized with the full list of analytes.  Table
        data are stored in ``MainWindow.treeModel``.
        """

        ###
        #clear the current analysis
        self.parent.reset_analysis()
        self.parent.sample_ids = [os.path.splitext(file)[0].replace('.lame','') for file in self.parent.csv_files]
        # set first sample id as default
        self.parent.comboBoxSampleId.addItems(self.parent.sample_ids)
        self.parent.comboBoxSampleId.setCurrentIndex(0)
        # Populate the sampleidcomboBox with the file names
        self.parent.canvasWindow.setCurrentIndex(self.parent.canvas_tab['sv'])
        self.parent.change_sample(0)
        self.parent.init_tabs()
        self.parent.profiling.add_samples()
        self.parent.polygon.add_samples()