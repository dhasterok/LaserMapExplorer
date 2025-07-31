from pathlib import Path
import pickle
import pandas as pd
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap
import src.app.SpotImporter as SpotImporter
import src.app.MapImporter as MapImporter
from src.app.config import BASEDIR
import src.common.CustomMplCanvas as mplc
from src.common.DataHandling import LaserSampleObj, XRFSampleObj
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
    def __init__(self, ui=None, connect_actions=True):
        if ui is None:
            return

        self.logger_key = 'IO'


        self.connect_actions = connect_actions
        if self.connect_actions:
            ui.actionOpenSample.triggered.connect(lambda: self.open_sample())
            ui.actionOpenDirectory.triggered.connect(lambda: self.open_directory(path=None))
            ui.actionImportSpots.triggered.connect(self.import_spots)
            ui.actionOpenProject.triggered.connect(lambda: self.open_project())
            ui.actionSaveProject.triggered.connect(lambda: self.save_project())
            ui.actionImportFiles.triggered.connect(lambda: self.import_files())

        self.ui = ui

        self.status_manager = StatusMessageManager(self.ui)

    def open_sample(self, path=None):
        """
        Opens a single *.lame.csv file created by MapImporter.

        Parameters
        ----------
        path : str or Path, optional
            Path to datafile. If None, an open file dialog is shown. Default is None.
        """
        ui = self.ui

        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("LaME CSV (*.csv)")
            if dialog.exec():
                file_list = dialog.selectedFiles()
                file_list = [Path(f) for f in file_list]
                ui.app_data.selected_directory = file_list[0].resolve().parent
            else:
                return
        else:
            path = Path(path).resolve()
            ui.app_data.selected_directory = path.parent
            file_list = [path]

        # Collect just the filename (with extension)
        ui.app_data.csv_files = [f.name for f in file_list if f.suffix == '.csv']
        if not ui.app_data.csv_files:
            self.status_manager.show_message("No valid csv file found.")
            return

        # Create a list of sample names (without .lame and .csv)
        ui.app_data.sample_list = [
            f.stem.replace('.lame', '') for f in map(Path, ui.app_data.csv_files)
        ]

    def open_directory(self, path=None):
        """Open directory with samples in \\*.lame.csv files.

        Executes on ``MainWindow.actionOpen`` and ``MainWindow.actionOpenDirectory``.  Opening a directory, enables
        the toolboxes.

        Alternatively, *open_directory* is called after ``MapImporter`` successfully completes an import and the tool
        is closed.

        Opens a dialog to select directory filled with samples.  Updates sample list in
        ``MainWindow.comboBoxSampleID`` and comboBoxes associated with analyte lists.  The first sample
        in list is loaded by default.

        Parameters
        ----------
        path : str or Path
            Path to datafiles, if ``None``, an open directory dialog is opened, by default ``None``
        """
        ui = self.ui

        if path is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setDirectory(str(BASEDIR))  # QFileDialog expects a str
            if dialog.exec():
                selected_dir = Path(dialog.selectedFiles()[0])
                ui.app_data.selected_directory = selected_dir
            else:
                self.status_manager.show_message("Open directory canceled.")
                return
        else:
            ui.app_data.selected_directory = Path(path)

        selected_dir = ui.app_data.selected_directory
        file_list = list(selected_dir.iterdir())
        ui.app_data.csv_files = [f.name for f in file_list if f.is_file() and f.suffix == '.csv' and f.name.endswith('.lame.csv')]

        if not ui.app_data.csv_files:
            self.status_manager.show_message("No valid csv files found.")
            return

        ui.app_data.sample_list = [f.stem.replace('.lame', '') for f in map(Path, ui.app_data.csv_files)]
        self.status_manager.show_message("Sample list updated.")    

    def import_spots(self):
        """Import a data file with spot data."""
        # import spot dialog
        self.spotDialog = SpotImporter.SpotImporter(self.ui)
        self.spotDialog.show()

        if not self.spotDialog.ok:
            return

        self.populate_spot_table()

    def populate_spot_table(self):
        """Populates spot table when spot file is opened or sample is changed

        Populates ``MainWindow.tableWidgetSpots``.
        """
        ui = self.ui

        if ui.sample_id == '':
            return
        
        filtered_df = ui.spotdata[ui.sample_id==ui.spotdata['sample_id']]
        filtered_df = filtered_df['sample_id','X','Y','visible','display_text']

        ui.tableWidgetSpots.clearContents()
        ui.tableWidgetSpots.setRowCount(len(filtered_df))
        header = ui.tableWidgetSpots.horizontalHeader()

        for row_index, row in filtered_df.iterrows():
            for col_index, value in enumerate(row):
                ui.tableWidgetSpots.setItem(row_index, col_index, QTableWidgetItem(str(value)))

    def save_project(self):
        """Save a project session

        Saves (mostly) everything for recalling later.
        """
        ui = self.ui
        projects_dir = BASEDIR / "projects"
        
        # Ensure the projects directory exists
        projects_dir.mkdir(parents=True, exist_ok=True)
        
        # Open QFileDialog to enter a new project name
        file_dialog = QFileDialog(parent, "Save Project", str(projects_dir))
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_dir = Path(file_dialog.selectedFiles()[0])
            
            if selected_dir:
                project_name = selected_dir.name
                project_dir = projects_dir / project_name
                
                # Create the required directory structure and store raw data
                if not project_dir.exists():
                    for sample_id in ui.data.keys():
                        sample_dir = project_dir / sample_id
                        sample_dir.mkdir(parents=True, exist_ok=True)
                        # store raw data
                        ui.data[sample_id].raw_data.to_csv(sample_dir / 'lame.csv', index=False)
                        # create rest of directories
                        (sample_dir / 'figure_data').mkdir()
                        (sample_dir / 'figures').mkdir()
                        (sample_dir / 'tables').mkdir()
                
                # Saving data to the directory structure
                data_dict = {
                    'data': ui.data,
                    'styles': ui.plot_style,
                    'plot_infos': ui.plot_tree.get_plot_info_from_tree(ui.treeModel),
                    'sample_id': ui.sample_id,
                    'sample_list': ui.app_data.sample_list
                }
                
                # Save the main data dictionary as a pickle file
                pickle_path = project_dir / f'{project_name}.pkl'
                with open(pickle_path, 'wb') as file:
                    pickle.dump(data_dict, file)
                
                for sample_id in ui.data.keys():
                    ui.profiling.save_profiles(project_dir, sample_id)
                    ui.polygon.save_polygons(project_dir, sample_id)
                
                self.status_manager.show_message("Analysis saved successfully")

    def open_project(self):
        """Open a project session.

        Restores a project session: data, analysis, and plots.
        """        
        ui = self.ui

        if ui.data:
            # Prompt to save current analysis
            response = QMessageBox.warning(
                parent,
                "Save analysis",
                "Do you want to save the current analysis?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save
            )

            if response == QMessageBox.StandardButton.Save:
                self.save_project()
                ui.reset_analysis('full')
            elif response == QMessageBox.StandardButton.Discard:
                ui.reset_analysis('full')
            else:  # Cancel
                ui.comboBoxSampleId.setCurrentText(ui.sample_id)
                return

        projects_dir = BASEDIR / "projects"

        # QFileDialog to select project folder
        file_dialog = QFileDialog(parent, "Open Project", str(projects_dir))
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_dir = Path(file_dialog.selectedFiles()[0])

            if selected_dir:
                project_name = selected_dir.name
                project_dir = projects_dir / project_name

                pickle_path = project_dir / f'{project_name}.pkl'
                if pickle_path.exists():
                    with open(pickle_path, 'rb') as file:
                        data_dict = pickle.load(file)
                    if data_dict:
                        ui.data = data_dict['data']
                        ui.plot_style = data_dict['styles']
                        ui.app_data.sample_list = data_dict['sample_ids']
                        ui.sample_id = data_dict['sample_id']

                        ui.plot_tree.create_tree(ui.sample_id)
                        
                        # NOTE: Adjust this line according to actual data structure
                        ui.plot_tree.update_tree(ui.data[ui.sample_id]['norm'], norm_update=False)

                        for plot_info in data_dict['plot_infos']:
                            if plot_info:
                                canvas = mplc.MplCanvas(fig=plot_info['figure'])
                                plot_info['figure'] = canvas
                                ui.plot_tree.add_tree_item(plot_info)

                        ui.comboBoxSampleId.clear()
                        ui.comboBoxSampleId.addItems(ui.data.keys())
                        ui.comboBoxSampleId.setCurrentIndex(0)
                        ui.sample_id = data_dict['sample_id']

                        ui.init_tabs()

                        ui.update_cluster_flag = True
                        ui.update_pca_flag = True
                        ui.plot_flag = False

                        ui.update_all_field_comboboxes()
                        if hasattr(parent, "mask_dock"):
                            ui.update_filter_values()

                        ui.histogram_update_bin_width()

                        for sample_id in ui.data.keys():
                            ui.profiling.add_profiles(project_dir, sample_id)
                            ui.profiling.load_profiles(project_dir, sample_id)

                            ui.polygon.add_samples()
                            ui.polygon.load_polygons(project_dir, sample_id)

                        ui.plot_style.color_field_type = 'Analyte'
                        ui.comboBoxColorByField.setCurrentText(ui.plot_style.color_field_type)
                        ui.color_by_field_callback()

                        fields = ui.get_field_list('Analyte')
                        ui.plot_style.color_field = fields[0]
                        ui.comboBoxColorField.setCurrentText(fields[0])
                        ui.color_field_callback()

                        ui.plot_flag = True
                        ui.update_SV()

                        self.status_manager.show_message("Project loaded successfully")

    def import_files(self):
        """Opens an import dialog from ``MapImporter`` to open selected data directories."""
        # import data dialog
        self.importDialog = MapImporter.MapImporter(self.ui)
        self.importDialog.show()

        # read directory
        #if self.importDialog.ok:
        #    self.open_directory(path=self.importDialog.root_path)

        # change sample


    def initialize_sample_object(self, outlier_method, negative_method):
        """
        Initializes a `LaserSampleObj` for the current sample and stores it in the application's data dictionary.

        This method:
        - Checks whether the current sample ID exists in the data dictionary.
        - If not, loads the associated `.lame` file and creates a `LaserSampleObj`.
        - Optionally connects data observers if required.

        Parameters
        ----------
        outlier_method : str
            The name of the method to be used for outlier detection.
        negative_method : str
            The name of the method to be used for handling negative values.
        """
        # Add sample to sample dictionary
        if self.ui.app_data.sample_id and self.ui.app_data.sample_id not in self.ui.data:
            # Obtain index of current sample
            index = self.ui.app_data.sample_list.index(self.ui.app_data.sample_id)

            # Load sample's *.lame file using pathlib
            directory = self.ui.app_data.selected_directory
            file_path = directory / self.ui.app_data.csv_files[index]

            self.ui.data[self.ui.app_data.sample_id] = LaserSampleObj(
                sample_id=self.ui.app_data.sample_id,
                file_path=str(file_path),  # Ensure compatibility if `LaserSampleObj` expects a string path
                outlier_method=outlier_method,
                negative_method=negative_method,
                ref_chem=self.ui.app_data.ref_chem,
                ui=self.ui,
            )

            # Connect data observers if required
            if self.connect_actions:
                self.ui.preprocess.connect_data_observers(self.ui.data[self.ui.app_data.sample_id])

    
    def images_to_dataframe(self, directory):
        """
        Converts image files in a given directory into a DataFrame suitable for LaME analysis.

        This method:
        - Loads each image file from the directory.
        - Converts it to grayscale intensity (via the RGB max value).
        - Normalizes the intensity to a 0–100 scale.
        - Flattens the data to form columns in a DataFrame.
        - Adds X and Y coordinate columns.
        - Writes the result to a `.lame.xrf.csv` file.

        Parameters
        ----------
        directory : str
            Path to the directory containing image files.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the X, Y coordinates and intensity values from each image.

        Raises
        ------
        ValueError
            If no image files are found in the specified directory.
        """
        directory = Path(directory)
        
        # Get base directory name for output CSV
        output_filename = f"{directory.name}.lame.xrf.csv"
        
        # Get sorted list of image files
        image_files = sorted([
            f for f in directory.iterdir()
            if f.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        ])
        
        if not image_files:
            raise ValueError("No image files found in the directory.")
        
        all_columns = {}
        
        # Load the first image to get dimensions
        first_image = Image.open(image_files[0]).convert('RGB')
        width, height = first_image.size
        
        # Create X and Y coordinate columns
        x_coords, y_coords = np.meshgrid(range(width), range(height))
        all_columns['X'] = x_coords.flatten()
        all_columns['Y'] = y_coords.flatten()
        
        for image_path in image_files:
            # Open and convert to grayscale intensity
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img).astype(np.float32)
            
            # Convert RGB to intensity (simple average)
            intensity = img_array.max(axis=2)  # Shape: (H, W)
            
            # Normalize intensity to 0-100
            normalized = (intensity / 255.0) * 100
            
            # Derive safe column name
            base_name = image_path.stem
            column_name = 'Yt' if base_name == 'Y' else base_name
            
            # Add to columns
            all_columns[column_name] = normalized.flatten(order='F')
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(all_columns)
        df.to_csv(directory / output_filename, index=False)
        
        return df
    
    def save_data(self, data, filename=None):
        """Saves data to a file

        Parameters
        ----------
        data : pandas.DataFrame
            Data to be saved
        filename : str
            Filename to save data to

        Returns
        -------
        None
        """ 
        if filename is None:
            #open dialog to get name of file
            file_name, _ = QFileDialog.getSaveFileName(self.ui, "Save File", "", "CSV Files (*.csv);;All Files (*)")
        if file_name:
            with open(file_name, 'wb') as file:
                # self.save_data holds data used for current plot 
                data.to_csv(file,index = False)
            
            self.status_manager.show_message("Plot Data saved successfully")
            return
        
        self.status_manager.show_message("Plot Data save failed")