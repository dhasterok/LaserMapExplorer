from pathlib import Path
import pickle
import pandas as pd
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import (
    QFileDialog, QTableWidgetItem, QMessageBox, QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QComboBox, QDialogButtonBox, QToolButton, QPushButton, QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSettings, QDir, Qt
import src.app.SpotImporter as SpotImporter
import src.app.MapImporter as MapImporter
from src.app.config import BASEDIR, get_top_parent
import src.common.CustomMplCanvas as mplc
from src.common.DataHandling import LaserSampleObj, XRFSampleObj
from src.common.CustomMplCanvas import MplCanvas
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
            ui.lame_action.OpenSample.triggered.connect(lambda: self.open_sample())
            ui.lame_action.OpenDirectory.triggered.connect(lambda: self.open_directory(path=None))
            ui.lame_action.ImportSpots.triggered.connect(self.import_spots)
            ui.lame_action.OpenProject.triggered.connect(lambda: self.open_project())
            ui.lame_action.SaveProject.triggered.connect(lambda: self.save_project())
            ui.lame_action.ImportFiles.triggered.connect(lambda: self.import_files())

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
                    'styles': ui.style_data,
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
                        ui.style_data = data_dict['styles']
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

                        ui.style_data.color_field_type = 'Analyte'
                        ui.comboBoxColorByField.setCurrentText(ui.style_data.color_field_type)
                        ui.color_by_field_callback()

                        fields = ui.get_field_list('Analyte')
                        ui.style_data.color_field = fields[0]
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
                self.ui.control_dock.preprocess.connect_data_observers(self.ui.data[self.ui.app_data.sample_id])

    
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
    
    # def save_data(self, data, filename=None):
    #     """
    #     Saves data to a file in CSV, Excel, or Parquet format.

    #     Parameters
    #     ----------
    #     data : pandas.DataFrame
    #         Data to be saved
    #     filename : str or Path, optional
    #         Filename to save data to

    #     Returns
    #     -------
    #     None
    #     """
    #     save_dir = BASEDIR / "saved" / "data"
    #     save_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    #     filters = "CSV Files (*.csv);;Excel Files (*.xlsx);;Parquet Files (*.parquet);;All Files (*)"

    #     # Always work with Path
    #     if filename is None:
    #         file_name_str, selected_filter = QFileDialog.getSaveFileName(
    #             self.ui, "Save File", str(save_dir), filters)
    #         file_name = Path(file_name_str) if file_name_str else None
    #     elif str(filename).endswith(('.csv', '.xlsx', '.parquet')):
    #         file_name = Path(filename)
    #         selected_filter = None
    #         # If filename has no parent directory, save to save_dir
    #         if not file_name.is_absolute() and not file_name.parent or str(file_name.parent) == ".":
    #             file_name = save_dir / file_name

    #     else:
    #         file_name_str, selected_filter = QFileDialog.getSaveFileName(
    #             self.ui, "Save File", str(save_dir / filename), filters)
    #         file_name = Path(file_name_str) if file_name_str else None

    #     if file_name and file_name.name != '':
    #         ext = file_name.suffix.lower()
    #         # Enforce extension based on selected filter (optional)
    #         if selected_filter:
    #             if "CSV" in selected_filter and ext != '.csv':
    #                 file_name = file_name.with_suffix('.csv')
    #             elif "Excel" in selected_filter and ext != '.xlsx':
    #                 file_name = file_name.with_suffix('.xlsx')
    #             elif "Parquet" in selected_filter and ext != '.parquet':
    #                 file_name = file_name.with_suffix('.parquet')

    #         try:
    #             if file_name.suffix == '.csv':
    #                 data.to_csv(file_name, index=False)
    #             elif file_name.suffix == '.xlsx':
    #                 data.to_excel(file_name, index=False)
    #             elif file_name.suffix == '.parquet':
    #                 data.to_parquet(file_name, index=False)
    #             else:
    #                 # Default to CSV if unknown format
    #                 data.to_csv(file_name, index=False)

    #             self.status_manager.show_message("Plot Data saved successfully")
    #             return
    #         except Exception as e:
    #             self.status_manager.show_message(f"Plot Data save failed: {e}")
    #             return

    #     self.status_manager.show_message("Plot Data save failed")


    # def save_figure(self, fig, filename=None):
    #     """
    #     Saves a matplotlib figure to file in PNG, SVG, or PDF format.

    #     Parameters
    #     ----------
    #     fig : matplotlib.figure.Figure
    #         The Matplotlib figure object to be saved.
    #     filename : str or Path, optional
    #         The filename to save the figure to.

    #     Returns
    #     -------
    #     None
    #     """
    #     save_dir = BASEDIR / "saved" / "figure"
    #     save_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    #     filters = "PNG Files (*.png);;SVG Files (*.svg);;PDF Files (*.pdf);;All Files (*)"

    #     # Always work with Path
    #     if filename is None:
    #         file_name_str, selected_filter = QFileDialog.getSaveFileName(
    #             self.ui, "Save Figure", str(save_dir), filters)
    #         file_name = Path(file_name_str) if file_name_str else None
    #     elif str(filename).endswith(('.png', '.svg', '.pdf')):
    #         file_name = Path(filename)
    #         selected_filter = None
    #         # If filename has no parent directory, save to save_dir
    #         if not file_name.is_absolute() and not file_name.parent or str(file_name.parent) == ".":
    #             file_name = save_dir / file_name

    #     else:
    #         file_name_str, selected_filter = QFileDialog.getSaveFileName(
    #             self.ui, "Save Figure", str(save_dir / filename), filters)
    #         file_name = Path(file_name_str) if file_name_str else None

    #     if file_name and file_name.name != '':
    #         ext = file_name.suffix.lower()
    #         # Enforce extension based on selected filter (optional)
    #         if selected_filter:
    #             if "PNG" in selected_filter and ext != '.png':
    #                 file_name = file_name.with_suffix('.png')
    #             elif "SVG" in selected_filter and ext != '.svg':
    #                 file_name = file_name.with_suffix('.svg')
    #             elif "PDF" in selected_filter and ext != '.pdf':
    #                 file_name = file_name.with_suffix('.pdf')

    #         try:
    #             fig.savefig(file_name)
    #             self.status_manager.show_message("Figure saved successfully")
    #             return
    #         except Exception as e:
    #             self.status_manager.show_message(f"Figure save failed: {e}")
    #             return

    #     self.status_manager.show_message("Figure save failed")

    # ----------------------------------------------
    # Common helper for file save path
    # ----------------------------------------------
    def _get_save_path(self, base_dir, default_name, filters, selected_ext=None):
        base_dir.mkdir(parents=True, exist_ok=True)
        file_str, selected_filter = QFileDialog.getSaveFileName(
            self.ui, "Save File", str(base_dir / default_name), filters
        )
        if not file_str:
            return None
        file_path = Path(file_str)
        # Force extension if needed
        if selected_filter:
            for pattern in filters.split(";;"):
                ext = pattern.split("*.")[-1].strip(")")
                if pattern.startswith(selected_filter.split()[0]) and file_path.suffix.lower() != f".{ext}":
                    file_path = file_path.with_suffix(f".{ext}")
                    break
        elif selected_ext and file_path.suffix.lower() != selected_ext:
            file_path = file_path.with_suffix(selected_ext)
        return file_path

    # ----------------------------------------------
    # Updated save functions
    # ----------------------------------------------
    def save_data(self, data, filename=None):
        """
        Saves data to a file in CSV, Excel, or Parquet format.

        Parameters
        ----------
        data : pandas.DataFrame
            Data to be saved
        filename : str or Path, optional
            Filename to save data to
        """
        filters = "CSV Files (*.csv);;Excel Files (*.xlsx);;Parquet Files (*.parquet);;All Files (*)"
        save_dir = BASEDIR / "saved" / "data"
        if filename is None:
            file_path = self._get_save_path(self, save_dir, "data", filters)
        else:
            file_path = Path(filename)
        if not file_path:
            self.status_manager.show_message("Plot Data save cancelled")
            return
        try:
            match file_path.suffix:
                case '.csv':
                    data.to_csv(file_path, index=False)
                case '.xlsx':
                    data.to_excel(file_path, index=False)
                case '.parquet':
                    data.to_parquet(file_path, index=False)
            self.status_manager.show_message(f"Data saved: {file_path.name}")
        except Exception as e:
            self.status_manager.show_message(f"Data save failed: {e}")

    def save_figure(self, fig, filename=None):
        filters = "PNG Files (*.png);;SVG Files (*.svg);;PDF Files (*.pdf);;All Files (*)"
        save_dir = BASEDIR / "saved" / "figures"
        if filename is None:
            file_path = self._get_save_path(self, save_dir, "figure", filters)
        else:
            file_path = Path(filename)
        if not file_path:
            self.status_manager.show_message("Figure save cancelled")
            return
        try:
            fig.savefig(file_path)
            self.status_manager.show_message(f"Figure saved: {file_path.name}")
        except Exception as e:
            self.status_manager.show_message(f"Figure save failed: {e}")

    def save_plot(self, canvas: MplCanvas, save_figure_flag=True, save_data_flag=True, parent=None):
        """
        Open SaveDialog and save figure, data, or both from the given canvas.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas containing the figure and data to save.
        save_figure_flag : bool
            If True, allow saving figure.
        save_data_flag : bool
            If True, allow saving data.
        parent : QWidget | None
            Parent widget for SavePlotDialog
        """
        dlg = SavePlotDialog(parent, basename=canvas.plot_name)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.status_manager.show_message("Save cancelled")
            return

        settings = dlg.get_values()

        save_dir = Path(settings['directory'])
        if not settings['basename']:
            self.status_manager.show_message("Save failed: empty filename")
            return
        try:
            if save_figure_flag:
                fig_folder = save_dir / "figures"
                fig_folder.mkdir(parents=True, exist_ok=True)  # ensure folder exists
                fig_path = fig_folder / f"{settings['basename']}.{settings['fig_type']}"
                self.save_figure(canvas.figure, fig_path)

            if save_data_flag:
                data_folder = save_dir / "data"
                data_folder.mkdir(parents=True, exist_ok=True)  # ensure folder exists
                data_path = data_folder / f"{settings['basename']}.{settings['data_type']}"
                self.save_data(canvas.data, data_path)

            self.status_manager.show_message(f"Saved to {save_dir}")

        except Exception as e:
            self.status_manager.show_message(f"Save failed: {e}")

class SavePlotDialog(QDialog):
    def __init__(self, parent=None, save_figure=True, save_data=True, basename=None):
        super().__init__(parent)
        self.setWindowTitle("Save Plot Options")
        self.settings = QSettings("Adelaide University", "LaME")

        self.setMinimumSize(450,250)

        # Restore saved state
        ui = get_top_parent(self)
        last_dir = self.settings.value("save_dir", str(ui.app_data.selected_directory))
        if not basename:
            basename = self.settings.value("save_basename", "output")

        last_fig_type = self.settings.value("save_fig_type", "png")
        last_data_type = self.settings.value("save_data_type", "csv")
        last_fig_checked = self.settings.value("save_fig_checked", True, type=bool)
        last_data_checked = self.settings.value("save_data_checked", True, type=bool)

        dialog_layout = QVBoxLayout(self)

        # Directory selector
        self.path_label = QLineEdit(last_dir)
        self.path_label.setReadOnly(True)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Base path:"))
        path_layout.addWidget(self.path_label, 1)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        change_path_button = QPushButton("Change Path")
        change_path_button.clicked.connect(self.change_directory)

        change_path_layout = QHBoxLayout()
        change_path_layout.addItem(spacer)
        change_path_layout.addWidget(change_path_button)

        # Base filename
        self.filename_line_edit = QLineEdit(basename)

        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Base filename:"))
        filename_layout.addWidget(self.filename_line_edit)

        # File type selectors
        self.figure_combobox = QComboBox()
        self.figure_combobox.addItems(["png", "jpg", "svg", "pdf"])
        self.figure_combobox.setCurrentText(last_fig_type)

        self.figure_checkbox = QCheckBox("Save Figure")
        self.figure_checkbox.setChecked(last_fig_checked and save_figure)
        self.figure_checkbox.setEnabled(save_figure)

        self.figure_path_label = QLabel()
        self.figure_path_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignBottom)

        figure_layout = QHBoxLayout()
        figure_layout.addWidget(QLabel("Figure type:"))
        figure_layout.addWidget(self.figure_path_label)
        figure_layout.addWidget(self.figure_combobox)
        figure_layout.addWidget(self.figure_checkbox)

        self.data_combobox = QComboBox()
        self.data_combobox.addItems(["csv", "xlsx", "parquet"])
        self.data_combobox.setCurrentText(last_data_type)

        self.data_checkbox = QCheckBox("Save Data")
        self.data_checkbox.setChecked(last_data_checked and save_data)
        self.data_checkbox.setEnabled(save_data)

        self.data_path_label = QLabel()
        self.data_path_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignBottom)

        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("Data type:"))
        data_layout.addWidget(self.data_path_label)
        data_layout.addWidget(self.data_combobox)
        data_layout.addWidget(self.data_checkbox)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        dialog_layout.addLayout(path_layout)
        dialog_layout.addLayout(change_path_layout)
        dialog_layout.addLayout(filename_layout)
        dialog_layout.addLayout(figure_layout)
        dialog_layout.addLayout(data_layout)
        dialog_layout.addWidget(btns)

        self.filename_line_edit.editingFinished.connect(self.update_path_preview)
        self.update_path_preview()

    def update_path_preview(self):
        basename = self.filename_line_edit.text()
        self.figure_path_label.setText(f"./figures/{basename}.")
        self.data_path_label.setText(f"./data/{basename}.")


    def change_directory(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.path_label.text())
        if new_dir:
            self.path_label.setText(new_dir)

    def get_values(self):
        # Save settings for persistence
        self.settings.setValue("save_dir", self.path_label.text())
        self.settings.setValue("save_basename", self.filename_line_edit.text())
        self.settings.setValue("save_fig_type", self.figure_combobox.currentText())
        self.settings.setValue("save_data_type", self.data_combobox.currentText())
        self.settings.setValue("save_fig_checked", self.figure_checkbox.isChecked())
        self.settings.setValue("save_data_checked", self.data_checkbox.isChecked())

        return {
            "save_figure": self.figure_checkbox.isChecked(),
            "save_data": self.data_checkbox.isChecked(),
            "directory": self.path_label.text(),
            "basename": self.filename_line_edit.text(),
            "fig_type": self.figure_combobox.currentText(),
            "data_type": self.data_combobox.currentText()
        }
