from pathlib import Path
import pandas as pd
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import (
    QFileDialog, QTableWidgetItem, QMessageBox, QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QComboBox, QDialogButtonBox, QToolButton, QPushButton, QCheckBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSettings, QDir, Qt
import src.importers.SpotImporter as SpotImporter
import src.importers.MapImporter as MapImporter
from lame_core.config import BASEDIR
from src.app.config import get_top_parent
from src.data.DataHandling import LaserSampleObj, XRFSampleObj
from src.plotting.CustomMplCanvas import MplCanvas
from src.app.Status import StatusMessageManager
from src.control.Logger import LoggerConfig, auto_log_methods, log
from src.project.ProjectModel import load_calibration_sidecar, is_calibration_stale
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
            # OpenSample/OpenDirectory/OpenProject/SaveProject are now
            # AddSampleFiles/AddSampleDirectory/OpenProject/SaveProject,
            # wired directly to ProjectManager in MainActions.connect_actions()
            # (see src/app/MainToolBar.py) rather than here.
            ui.lame_action.ImportSpots.triggered.connect(self.import_spots)
            ui.lame_action.ImportFiles.triggered.connect(lambda: self.import_files())

        self.ui = ui

        self.status_manager = StatusMessageManager(self.ui)

    def open_directory(self, path=None):
        """Add all ``*.lame.csv`` samples in a directory to the current project.

        The Blockly-generated code for the workflow's "Load Directory" block
        calls this directly (``self.io.open_directory(...)``) -- with no
        argument it opens a directory picker, with one it adds that
        directory's samples right away. Delegates to
        ``ProjectManager.add_samples``/``add_sample_directory_dialog``, the
        same code path the toolbar/menu "Add Sample Directory" action uses.

        Parameters
        ----------
        path : str or Path, optional
            Directory to add samples from. If None, opens a directory picker.

        Returns
        -------
        list of str
            Sample IDs actually added; ``[]`` if cancelled or none found.
        """
        if path is None:
            return self.ui.project_manager.add_sample_directory_dialog()
        return self.ui.project_manager.add_samples([Path(path)])

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

    def import_files(self):
        """Opens an import dialog from ``MapImporter`` to open selected data directories.

        ``MapImporter`` is non-modal (``.show()``, not ``.exec()``); it adds
        the imported sample(s) to the current project itself, on success,
        via ``self.parent.project_manager.add_samples(...)`` (see
        ``MapImporter.import_data`` / its post-import handler) -- there's
        nothing further to chain here once the dialog is shown.
        """
        self.importDialog = MapImporter.MapImporter(self.ui)
        self.importDialog.show()

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
            # Prefer the project's own record of this sample's absolute path
            # (set by ProjectManager.add_samples()) so a project spanning
            # multiple directories still resolves correctly -- AppData's
            # selected_directory/csv_files can only reflect one directory at
            # a time. Falls back to the old directory/csv_files[index]
            # lookup when there's no project entry (e.g. samples staged
            # without going through ProjectManager).
            project = self.ui.project_manager.current_project
            entry = project.samples.get(self.ui.app_data.sample_id) if project else None
            if entry is not None:
                file_path = entry.sample_path

                # Tier 1 calibration: auto-load the `.calib.json` sidecar next
                # to the sample's raw data the first time this project entry
                # sees it (a previous project save may already have cached
                # it). Staleness is deliberately recomputed here rather than
                # cached on the entry -- one source of truth (source_hash vs.
                # the file's current fingerprint), same as `is_calibration_stale`
                # will be called again by the Project Files dock for display.
                # No UI exists yet to surface this -- log only for now.
                if entry.calibration is None:
                    entry.calibration = load_calibration_sidecar(file_path)
                if entry.calibration is not None and is_calibration_stale(entry.calibration, file_path):
                    log(
                        f"initialize_sample_object: calibration for '{self.ui.app_data.sample_id}' "
                        f"is stale (source file changed since calibrated_at="
                        f"{entry.calibration.calibrated_at.isoformat()})",
                        prefix='IO',
                    )
            else:
                index = self.ui.app_data.sample_list.index(self.ui.app_data.sample_id)
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

            # Tier 2: replay this project's saved filters/masks/computed
            # fields onto the freshly (re)loaded sample. field_calculator is
            # optional -- omitted rather than crashing if the Calculator
            # dock hasn't been created yet (e.g. in a lighter-weight test
            # harness).
            if entry is not None:
                field_calculator = getattr(getattr(self.ui, 'calculator', None), 'cfc', None)
                self.ui.data[self.ui.app_data.sample_id].apply_processing_state(
                    entry.processing,
                    ref_chem=self.ui.app_data.ref_chem,
                    field_calculator=field_calculator,
                )

                # Profile/polygon geometry lives in its own per-sample
                # sidecar files, not the processing-state JSON -- load this
                # sample's on first touch, same as calibration/processing
                # state above. Both are tolerant of a missing directory
                # (nothing saved yet for this sample). project_dir is None
                # for an unsaved project, in which case there's nothing on
                # disk to load yet either.
                project_dir = self.ui.project_manager.project_dir
                if project_dir is not None:
                    if hasattr(self.ui, 'profile_dock'):
                        self.ui.profile_dock.profiling.load_profiles(project_dir, self.ui.app_data.sample_id)
                        self.ui.profile_dock.profiling.project_dir = project_dir
                    if hasattr(self.ui, 'mask_dock'):
                        self.ui.mask_dock.polygon_tab.polygon_manager.load_polygons(project_dir, self.ui.app_data.sample_id)

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

    def add_figure_to_notes(self, fig_path, caption=None):
        """Inserts a just-saved figure into the Notes dock as a reST figure.

        Opens the Notes dock first if it isn't already (creating it on first
        use, per ``open_notes()``), then reuses ``NotesWidget.insert_image``
        directly with a known path -- passing a path (rather than ``None``)
        skips its file-picker dialog, and it already handles cross-platform
        path formatting/space-escaping.

        Parameters
        ----------
        fig_path : str or Path
            Path to the already-saved figure image.
        caption : str, optional
            Caption/alt text for the figure, by default the file's basename.
        """
        self.ui.open_notes()
        if caption is None:
            caption = Path(fig_path).stem
        self.ui.notes_dock.notes.insert_image(filename=fig_path, alt_text=caption, caption=caption)
        self.status_manager.show_message("Figure added to Notes")

    def save_plot(self, canvas: MplCanvas, save_figure_flag=True, save_data_flag=True, parent=None, settings=None):
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
        settings : dict | None
            If provided, bypass the SavePlotDialog and use these values directly:
        {
            "directory": str | Path,
            "basename": str,
            "fig_type": str,   # e.g. "png", "pdf", "svg"
            "data_type": str   # e.g. "csv", "npy", "parquet"
        }
        """
        if canvas is None:
            self.status_manager.show_message("Save failed: no active canvas")
            return

        if settings is None:
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

                if settings.get('add_to_notes'):
                    self.add_figure_to_notes(fig_path, settings['basename'])

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
        last_notes_checked = self.settings.value("save_notes_checked", False, type=bool)

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

        # Add to Notes -- requires a saved figure to reference, so it's
        # enabled/disabled in lockstep with the figure checkbox.
        self.notes_checkbox = QCheckBox("Add to Notes")
        self.notes_checkbox.setChecked(last_notes_checked and self.figure_checkbox.isChecked())
        self.notes_checkbox.setEnabled(self.figure_checkbox.isChecked())
        self.figure_checkbox.toggled.connect(self.notes_checkbox.setEnabled)

        notes_layout = QHBoxLayout()
        notes_layout.addWidget(self.notes_checkbox)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        dialog_layout.addLayout(path_layout)
        dialog_layout.addLayout(change_path_layout)
        dialog_layout.addLayout(filename_layout)
        dialog_layout.addLayout(figure_layout)
        dialog_layout.addLayout(data_layout)
        dialog_layout.addLayout(notes_layout)
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
        self.settings.setValue("save_notes_checked", self.notes_checkbox.isChecked())

        return {
            "save_figure": self.figure_checkbox.isChecked(),
            "save_data": self.data_checkbox.isChecked(),
            "add_to_notes": self.notes_checkbox.isChecked(),
            "directory": self.path_label.text(),
            "basename": self.filename_line_edit.text(),
            "fig_type": self.figure_combobox.currentText(),
            "data_type": self.data_combobox.currentText()
        }
