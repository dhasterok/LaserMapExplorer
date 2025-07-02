import os, pickle
import pandas as pd
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap
import src.app.SpotImporter as SpotImporter
import src.app.MapImporter as MapImporter
from src.app.config import BASEDIR
import src.common.CustomMplCanvas as mplc
from src.common.DataHandling import SampleObj
from src.common.Status import StatusMessageManager
from src.common.Logger import LoggerConfig, auto_log_methods
# -------------------------------------
# File I/O related functions
# -------------------------------------

@auto_log_methods(logger_key='IO')
class LameIO():
    """Handles most I/O for the main window of LaME

    Parameters
    ----------
    parent : QObject, optional
        MainWindow UI, by default None
    """        
    def __init__(self, parent=None, connect_actions=True):
        if parent is None:
            return

        self.logger_key = 'IO'


        self.connect_actions = connect_actions
        if self.connect_actions:
            parent.actionOpenSample.triggered.connect(lambda: self.open_sample())
            parent.actionOpenDirectory.triggered.connect(lambda: self.open_directory(path=None))
            parent.actionImportSpots.triggered.connect(self.import_spots)
            parent.actionOpenProject.triggered.connect(lambda: self.open_project())
            parent.actionSaveProject.triggered.connect(lambda: self.save_project())
            parent.actionImportFiles.triggered.connect(lambda: self.import_files())

        self.parent = parent

        self.status_manager = StatusMessageManager(self.parent)

    def open_sample(self, path=None):
        """Opens a single \\*.lame.csv file.

        Opens files created by MapImporter.
        Parameters
        ----------
        path : str
            Path to datafile, if ``None``, an open directory dialog is openend, by default ``None``
        """
        parent = self.parent
        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("LaME CSV (*.csv)")
            if dialog.exec():
                file_list = dialog.selectedFiles()
                parent.app_data.selected_directory = os.path.dirname(os.path.abspath(file_list[0]))
            else:
                return
        else:
            parent.app_data.selected_directory = os.path.dirname(os.path.abspath(path))
        parent.app_data.csv_files = [os.path.split(file)[1] for file in file_list if file.endswith('.csv')]
        if parent.app_data.csv_files == []:
            # warning dialog
            self.status_manager.show_message("No valid csv file found.")
            return
        
        self.parent.app_data.sample_list = [os.path.splitext(file)[0].replace('.lame','') for file in self.parent.app_data.csv_files]


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
        parent = self.parent 

        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            # Set the default directory to the current working directory
            # dialog.setDirectory(os.getcwd())
            dialog.setDirectory(BASEDIR)
            if dialog.exec():
                parent.app_data.selected_directory = dialog.selectedFiles()[0]
            else:
                self.status_manager.show_message("Open directory canceled.")
                return
        else:
            parent.app_data.selected_directory = path

        file_list = os.listdir(parent.app_data.selected_directory)
        parent.app_data.csv_files = [file for file in file_list if file.endswith('.lame.csv')]
        if parent.app_data.csv_files == []:
            # warning dialog
            self.status_manager.show_message("No valid csv files found.")
                #clear the current analysis
        # update sample_list
        self.parent.app_data.sample_list = [os.path.splitext(file)[0].replace('.lame','') for file in self.parent.app_data.csv_files]
        self.status_manager.show_message("Sample list updated.")

    def import_spots(self):
        """Import a data file with spot data."""
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
        parent = self.parent
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Ensure the projects directory exists
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir)
        
        # Open QFileDialog to enter a new project name
        file_dialog = QFileDialog(parent, "Save Project", projects_dir)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
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
                    'styles': parent.plot_style,
                    'plot_infos': parent.plot_tree.get_plot_info_from_tree(parent.treeModel),
                    'sample_id': parent.sample_id,
                    'sample_list': parent.app_data.sample_list
                }
                
                # Save the main data dictionary as a pickle file
                pickle_path = os.path.join(project_dir, f'{project_name}.pkl')
                with open(pickle_path, 'wb') as file:
                    pickle.dump(data_dict, file)
                
                for sample_id in parent.data.keys():
                    parent.profiling.save_profiles(project_dir, sample_id)
                    parent.polygon.save_polygons(project_dir, sample_id)
                
                self.status_manager.show_message("Analysis saved successfully")

    def open_project(self):
        """Open a project session.

        Restores a project session: data, analysis, and plots.
        """        
        parent = self.parent

        if parent.data:
            # Create and configure the QMessageBox
            response = QMessageBox.warning(
                parent,
                "Save analysis",
                "Do you want to save the current analysis?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save
            )

            if response == QMessageBox.StandardButton.Save:
                self.save_project()
                parent.reset_analysis('full')
            elif response == QMessageBox.StandardButton.Discard:
                parent.reset_analysis('full')
            else:  # user pressed cancel
                parent.comboBoxSampleId.setCurrentText(parent.sample_id)
                return
        
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Open QFileDialog to select the project folder
        file_dialog = QFileDialog(parent, "Open Project", projects_dir)
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
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
                        parent.plot_style = data_dict['styles']
                        parent.app_data.sample_list = data_dict['sample_ids']
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
                        if hasattr(parent,"mask_dock"):
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
                        parent.plot_style.color_field_type = 'Analyte'
                        parent.comboBoxColorByField.setCurrentText(parent.plot_style.color_field_type)
                        parent.color_by_field_callback()
                        fields = parent.get_field_list('Analyte')
                        parent.plot_style.color_field = fields[0]
                        parent.comboBoxColorField.setCurrentText(fields[0])
                        parent.color_field_callback()

                        parent.plot_flag = True
                        parent.update_SV()

                        self.status_manager.show_message("Project loaded successfully")

    def import_files(self):
        """Opens an import dialog from ``MapImporter`` to open selected data directories."""
        # import data dialog
        self.importDialog = MapImporter.MapImporter(self.parent)
        self.importDialog.show()

        # read directory
        #if self.importDialog.ok:
        #    self.open_directory(path=self.importDialog.root_path)

        # change sample


    def initialize_sample_object(self, outlier_method, negative_method):
        """Initializes sample objects for each sample in the application.

        This method creates a sample object for each sample in the application and stores it in the
        ``MainWindow.data`` dictionary.
        """
        # add sample to sample dictionary
        if self.parent.app_data.sample_id and self.parent.app_data.sample_id not in self.parent.data:
            # obtain index of current sample
            index = self.parent.app_data.sample_list.index(self.parent.app_data.sample_id)

            # load sample's *.lame file
            file_path = os.path.join(self.parent.app_data.selected_directory, self.parent.app_data.csv_files[index])
            self.parent.data[self.parent.app_data.sample_id] = SampleObj(
                sample_id = self.parent.app_data.sample_id,
                file_path = file_path,
                outlier_method = outlier_method,
                negative_method =negative_method,
                ref_chem = self.parent.app_data.ref_chem
            )

            # connect data observers if required
            if self.connect_actions:
                self.parent.connect_data_observers(self.parent.data[self.parent.app_data.sample_id])

    
    def images_to_dataframe(self, directory):
        """Reads image files into a data structure and saves in LaME format."""
        # Get base directory name for output CSV
        dir_name = os.path.basename(os.path.normpath(directory))
        output_filename = f"{dir_name}.lame.xrf.csv"
        
        # Get sorted list of image files
        image_files = sorted([
            f for f in os.listdir(directory)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
        ])
        
        if not image_files:
            raise ValueError("No image files found in the directory.")
        
        all_columns = {}
        
        # Load the first image to get dimensions
        first_image = Image.open(os.path.join(directory, image_files[0])).convert('RGB')
        width, height = first_image.size
        
        # Create X and Y coordinate columns
        x_coords, y_coords = np.meshgrid(range(width), range(height))
        all_columns['X'] = x_coords.flatten()
        all_columns['Y'] = y_coords.flatten()
        
        for image_file in image_files:
            # Open and convert to grayscale intensity
            img = Image.open(os.path.join(directory, image_file)).convert('RGB')
            img_array = np.array(img).astype(np.float32)
            
            # Convert RGB to intensity (simple average)
            intensity = img_array.max(axis=2)  # Shape: (H, W)
            
            # Normalize intensity to 0-100
            normalized = (intensity / 255.0) * 100
            
            # Derive safe column name
            base_name = os.path.splitext(image_file)[0]
            column_name = 'Yt' if base_name == 'Y' else base_name
            
            # Add to columns
            all_columns[column_name] = normalized.flatten(order='F')
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(all_columns)
        df.to_csv(os.path.join(directory, output_filename), index=False)
        
        return df