import os, pickle
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
import src.app.SpotImporter as SpotImporter
import src.app.MapImporter as MapImporter
from src.app.config import BASEDIR, DEBUG_IO
import src.common.CustomMplCanvas as mplc
# -------------------------------------
# File I/O related functions
# -------------------------------------
class LameIO():
    """Handles most I/O for the main window of LaME

    Parameters
    ----------
    parent : QObject, optional
        MainWindow UI, by default None
    """        
    def __init__(self, parent=None):
        if parent is None:
            return

        parent.actionOpenSample.triggered.connect(self.open_sample)
        parent.actionOpenDirectory.triggered.connect(lambda: self.open_directory(path=None))
        parent.actionImportSpots.triggered.connect(self.import_spots)
        parent.actionOpenProject.triggered.connect(lambda: self.open_project())
        parent.actionSaveProject.triggered.connect(lambda: self.save_project())
        parent.actionImportFiles.triggered.connect(lambda: self.import_files())

        self.parent = parent

    def open_sample(self, path =None):
        """Opens a single \\*.lame.csv file.

        Opens files created by MapImporter.
        Parameters
        ----------
        path : str
            Path to datafile, if ``None``, an open directory dialog is openend, by default ``None``
        """
        if DEBUG_IO:
            print("open_sample")

        parent = self.parent
        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.ExistingFiles)
            dialog.setNameFilter("LaME CSV (*.csv)")
            if dialog.exec_():
                file_list = dialog.selectedFiles()
                parent.selected_directory = os.path.dirname(os.path.abspath(file_list[0]))
            else:
                return
        else:
            parent.selected_directory = os.path.dirname(os.path.abspath(path))
        parent.csv_files = [os.path.split(file)[1] for file in file_list if file.endswith('.csv')]
        if parent.csv_files == []:
            # warning dialog
            parent.statusBar.showMessage("No valid csv file found.")
            return
            
        self.initialize_samples_and_tabs()


    def open_directory(self, path=None):
        """Open directory with samples in \\*.lame.csv files.

        Executes on ``MainWindow.actionOpen`` and ``MainWindow.actionOpenDirectory``.  Opening a directory, enables
        the toolboxes.

        Alternatively, *open_dicrectory* is called after ``MapImporter`` successfully completes an import and the tool
        is closed.

        Opens a dialog to select directory filled with samples.  Updates sample list in
        ``MainWindow.comboBoxSampleID`` and comboBoxes associated with analyte lists.  The first sample
        in list is loaded by default.

        Parameters
        ----------
        path : str
            Path to datafiles, if ``None``, an open directory dialog is openend, by default ``None``
        """
        if DEBUG_IO:
            print("open_directory")

        parent = self.parent 

        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.Directory)
            # Set the default directory to the current working directory
            # dialog.setDirectory(os.getcwd())
            dialog.setDirectory(BASEDIR)
            if dialog.exec_():
                parent.selected_directory = dialog.selectedFiles()[0]
            else:
                parent.statusBar.showMessage("Open directory canceled.")
                return
        else:
            parent.selected_directory = path

        file_list = os.listdir(parent.selected_directory)
        parent.csv_files = [file for file in file_list if file.endswith('.lame.csv')]
        if parent.csv_files == []:
            # warning dialog
            parent.statusBar.showMessage("No valid csv files found.")
            return
                #clear the current analysis
        self.parent.reset_analysis()
        self.initialize_samples_and_tabs()


    def import_spots(self):
        """Import a data file with spot data."""
        if DEBUG_IO:
            print("import_spots")

        # import spot dialog
        self.spotDialog = SpotImporter.SpotImporter(self.parent)
        self.spotDialog.show()

        if not self.spotDialog.ok:
            return

        self.populate_spot_table()

    def populate_spot_table(self):
        """Populates spot table when spot file is opened or sample is changed

        Populates ``MainWindow.tableWidgetSpots``.
        """
        if DEBUG_IO:
            print("populate_spot_table")

        parent = self.parent

        if parent.sample_id == '':
            return
        
        filtered_df = parent.spotdata[parent.sample_id==parent.spotdata['sample_id']]
        filtered_df = filtered_df['sample_id','X','Y','visible','display_text']

        parent.tableWidgetSpots.clearContents()
        parent.tableWidgetSpots.setRowCount(len(filtered_df))
        header = parent.tableWidgetSpots.horizontalHeader()

        for row_index, row in filtered_df.iterrows():
            for col_index, value in enumerate(row):
                parent.tableWidgetSpots.setItem(row_index, col_index, QTableWidgetItem(str(value)))

    def save_project(self):
        """Save a project session

        Saves (mostly) everything for recalling later.
        """
        if DEBUG_IO:
            print("save_project")

        parent = self.parent
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Ensure the projects directory exists
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir)
        
        # Open QFileDialog to enter a new project name
        file_dialog = QFileDialog(parent, "Save Project", projects_dir)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if file_dialog.exec_() == QFileDialog.Accepted:
            selected_dir = file_dialog.selectedFiles()[0]
            
            # Ensure a valid directory name is selected
            if selected_dir:
                project_name = os.path.basename(selected_dir)
                project_dir = os.path.join(projects_dir, project_name)
                
                # Creating the required directory structure and store raw data
                if not os.path.exists(project_dir):
                    os.makedirs(project_dir)
                    for sample_id in parent.data.keys():
                        # create directory for each sample in self.data
                        os.makedirs(os.path.join(project_dir, sample_id))
                        # store raw data
                        parent.data[sample_id].raw_data.to_csv(os.path.join(project_dir, sample_id, 'lame.csv'), index = False)
                        # create rest of directories
                        os.makedirs(os.path.join(project_dir, sample_id, 'figure_data'))
                        os.makedirs(os.path.join(project_dir, sample_id, 'figures'))
                        os.makedirs(os.path.join(project_dir, sample_id, 'tables'))
                
                # Saving data to the directory structure
                data_dict = {
                    'data': parent.data,
                    'styles': parent.styles,
                    'plot_infos': parent.plot_tree.get_plot_info_from_tree(parent.treeModel),
                    'sample_id': parent.sample_id,
                    'sample_ids': parent.sample_ids
                }
                
                # Save the main data dictionary as a pickle file
                pickle_path = os.path.join(project_dir, f'{project_name}.pkl')
                with open(pickle_path, 'wb') as file:
                    pickle.dump(data_dict, file)
                
                for sample_id in parent.data.keys():
                    parent.profiling.save_profiles(project_dir, sample_id)
                    parent.polygon.save_polygons(project_dir, sample_id)
                
                parent.statusBar.showMessage("Analysis saved successfully")

    def open_project(self):
        """Open a project session.

        Restores a project session: data, analysis, and plots.
        """        
        if DEBUG_IO:
            print("open_project")

        parent = self.parent

        if parent.data:
            # Create and configure the QMessageBox
            messageBoxChangeSample = QMessageBox()
            iconWarning = QIcon()
            iconWarning.addPixmap(QPixmap(":/resources/icons/icon-warning-64.svg"), QIcon.Normal, QIcon.Off) # type: ignore

            messageBoxChangeSample.setWindowIcon(iconWarning)  # Set custom icon
            messageBoxChangeSample.setText("Do you want to save current analysis?")
            messageBoxChangeSample.setWindowTitle("Save analysis")
            messageBoxChangeSample.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)

            # Display the dialog and wait for user action
            response = messageBoxChangeSample.exec_()

            if response == QMessageBox.Save:
                self.save_project()
                parent.reset_analysis('full')
            elif response == QMessageBox.Discard:
                parent.reset_analysis('full')
            else:  # user pressed cancel
                parent.comboBoxSampleId.setCurrentText(parent.sample_id)
                return
        
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Open QFileDialog to select the project folder
        file_dialog = QFileDialog(parent, "Open Project", projects_dir)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if file_dialog.exec_() == QFileDialog.Accepted:
            selected_dir = file_dialog.selectedFiles()[0]
            
            # Ensure a valid directory is selected
            if selected_dir:
                project_name = os.path.basename(selected_dir)
                project_dir = os.path.join(projects_dir, project_name)
                
                # Path to the pickle file
                pickle_path = os.path.join(project_dir, f'{project_name}.pkl')
                if os.path.exists(pickle_path):
                    with open(pickle_path, 'rb') as file:
                        data_dict = pickle.load(file)
                    if data_dict:
                        parent.data = data_dict['data']
                        parent.styles = data_dict['styles']
                        parent.sample_ids = data_dict['sample_ids']
                        parent.sample_id = data_dict['sample_id']
                        
                        parent.plot_tree.create_tree(parent.sample_id)
                        # Update tree with selected analytes
                        ####
                        # THIS LINE IS WRONG
                        parent.plot_tree.update_tree(parent.data[parent.sample_id]['norm'], norm_update=False)
                        ####

                        # Add plot info to tree
                        for plot_info in data_dict['plot_infos']:
                            if plot_info:
                                canvas = mplc.MplCanvas(fig=plot_info['figure'])
                                plot_info['figure'] = canvas
                                parent.plot_tree.add_tree_item(plot_info)
                        
                        # Update sample id combo
                        parent.comboBoxSampleId.clear()
                        parent.comboBoxSampleId.addItems(parent.data.keys())
                        # set the comboBoxSampleId with the correct sample id
                        parent.comboBoxSampleId.setCurrentIndex(0)
                        parent.sample_id = data_dict['sample_id']

                        # Initialize tabs
                        parent.init_tabs()
                        
                        # Reset flags
                        parent.update_cluster_flag = True
                        parent.update_pca_flag = True
                        parent.plot_flag = False

                        parent.update_all_field_comboboxes()
                        parent.update_filter_values()

                        parent.histogram_update_bin_width()

                        # add sample id to self.profiles, self.polygons and load saved profiles and polygons
                        #self.profiling.add_samples()
                        for sample_id in parent.data.keys():
                            # profiles
                            parent.profiling.add_profiles(project_dir, sample_id)
                            parent.profiling.load_profiles(project_dir, sample_id)

                            # polygons
                            parent.polygon.add_samples()
                            parent.polygon.load_polygons(project_dir, sample_id)

                        # Plot first analyte as lasermap
                        parent.styles['analyte map']['Colors']['ColorByField'] = 'Analyte'
                        parent.comboBoxColorByField.setCurrentText(parent.styles['analyte map']['Colors']['ColorByField'])
                        parent.color_by_field_callback()
                        fields = parent.get_field_list('Analyte')
                        parent.styles['analyte map']['Colors']['Field'] = fields[0]
                        parent.comboBoxColorField.setCurrentText(fields[0])
                        parent.color_field_callback()

                        parent.plot_flag = True
                        parent.update_SV()

                        parent.statusBar.showMessage("Project loaded successfully")

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
        if DEBUG_IO:
            print("initialize_samples_and_tabs")

        ###
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
        #add sample ids to workflow and activate sample id dependent blocks
        self.parent.workflow.store_sample_ids()

    def import_files(self):
        """Opens an import dialog from ``MapImporter`` to open selected data directories."""
        if DEBUG_IO:
            print("import_files")

        # import data dialog
        self.importDialog = MapImporter.MapImporter(self.parent)
        self.importDialog.show()

        # read directory
        #if self.importDialog.ok:
        #    self.open_directory(path=self.importDialog.root_path)

        # change sample