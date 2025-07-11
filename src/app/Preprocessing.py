import numpy as np
from src.common.Logger import log, auto_log_methods

@auto_log_methods(logger_key="Data")
class PreprocessingUI():
    """
    Manages the preprocessing interface and links data updates to the MainWindow UI.

    The `PreprocessingUI` class connects UI elements in the application's "Process" tab
    to corresponding data-handling logic. It listens for changes in spatial resolution,
    quantile thresholds, outlier and negative value handling methods, and applies those
    settings to the active dataset.

    The class also ensures that the UI is updated dynamically when the underlying data
    model changes, and that scheduled plot updates are triggered when required.

    Parameters
    ----------
    parent : QMainWindow
        The main application window that contains all relevant widgets, plot styles,
        and application data.

    Attributes
    ----------
    main_window : QMainWindow
        Reference to the main window for accessing UI widgets and application state.
    schedule_update : callable
        Function that triggers a scheduled plot update, typically used after data changes.
    
    Methods
    -------
    connect_data_observers(data)
        Connects property observers on the data object to update UI widgets accordingly.
    
    update_* methods
        A wide range of update methods handle syncing UI fields (e.g. resolution, quantiles,
        outlier methods) to backend data and vice versa. Most of these also trigger plot updates.

    update_outlier_method(method)
        Updates the outlier removal method for the dataset and adjusts the UI widget state.
    
    update_negative_handling_method(method)
        Updates the method used to handle negative values in the data.
    
    update_labels()
        Refreshes the label showing invalid values (negatives and NaNs) in the status bar.
    
    update_swap_resolution()
        Swaps x and y resolution in the dataset and triggers a re-render.
    
    reset_crop(), reset_pixel_resolution()
        Resets the cropped region or the pixel resolution for the current dataset.
    """
    def __init__(self, parent):
        self.ui = parent
        self.schedule_update = parent.plot_style.schedule_update()
        
        self.ui.toolButtonSwapResolution.clicked.connect(self.update_swap_resolution)

        self.ui.comboBoxOutlierMethod.addItems(self.ui.app_data.outlier_methods)
        if 'Chauvenet criterion' in self.ui.app_data.outlier_methods:
            self.ui.comboBoxOutlierMethod.setCurrentText('Chauvenet criterion')
        self.ui.comboBoxOutlierMethod.activated.connect(
            lambda: self.update_outlier_removal(self.ui.comboBoxOutlierMethod.currentText())
        )

        self.ui.comboBoxNegativeMethod.addItems(self.ui.app_data.negative_methods)
        self.ui.comboBoxNegativeMethod.activated.connect(
            lambda: self.update_neg_handling(self.ui.comboBoxNegativeMethod.currentText())
        )

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        self.ui.lineEditDX.editingFinished.connect(self.update_dx)
        self.ui.lineEditDY.editingFinished.connect(self.update_dy)
        self.ui.lineEditResolutionNx.editingFinished.connect(self.update_nx_lineedit)
        self.ui.lineEditResolutionNx.editingFinished.connect(self.update_ny_lineedit)

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("apply_process_to_all_data", self.update_autoscale_checkbox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.lineEditResolutionNx.editingFinished.connect(lambda: log(f"lineEditResolutionNx value=[{self.ui.lineEditResolutionNx.value}]", prefix="UI"))
        self.ui.lineEditResolutionNy.editingFinished.connect(lambda: log(f"lineEditResolutionNy value=[{self.ui.lineEditResolutionNy.value}]", prefix="UI"))
        self.ui.toolButtonPixelResolutionReset.clicked.connect(lambda: log("toolButtonSwapResolution",prefix="UI"))
        self.ui.lineEditDX.editingFinished.connect(lambda: log(f"lineEditDX, value=[{self.ui.lineEditDX.value}]",prefix="UI"))
        self.ui.lineEditDY.editingFinished.connect(lambda: log(f"lineEditDY, value=[{self.ui.lineEditDY.value}]",prefix="UI"))
        self.ui.toolButtonResolutionReset.clicked.connect(lambda: log("toolButtonsRolutionReset",prefix="UI"))
        self.ui.toolButtonSwapResolution.clicked.connect(lambda: log("toolButtonSwapResolution",prefix="UI"))
        self.ui.toolButtonAutoScale.clicked.connect(lambda: log(f"toolButtonAutoScale value=[{self.ui.toolButtonAutoScale.isChecked()}]", prefix="UI"))
        self.ui.checkBoxApplyAll.checkStateChanged.connect(lambda: log(f"checkBoxApplyAll value=[{self.ui.checkBoxApplyAll.isChecked()}]", prefix="UI"))
        self.ui.toolButtonOutlierReset.clicked.connect(lambda: log("toolButtonOutlierReset", prefix="UI"))
        self.ui.comboBoxOutlierMethod.activated.connect(lambda: log(f"comboBoxOutlierMethod value=[{self.ui.comboBoxOutlierMethod.currentText()}]", prefix="UI"))
        self.ui.comboBoxNegativeMethod.activated.connect(lambda: log(f"comboBoxNegativeMethod value=[{self.ui.comboBoxNegativeMethod.currentText()}]", prefix="UI"))
        self.ui.lineEditLowerQuantile.editingFinished.connect(lambda: log(f"lineEditLowerQuantile value=[{self.ui.lineEditLowerQuantile.value}]", prefix="UI"))
        self.ui.lineEditUpperQuantile.editingFinished.connect(lambda: log(f"lineEditUpperQuantile value=[{self.ui.lineEditUpperQuantile.value}]", prefix="UI"))
        self.ui.lineEditDifferenceLowerQuantile.editingFinished.connect(lambda: log(f"lineEditDifferenceLowerQuantile value=[{self.ui.lineEditDifferenceLowerQuantile.value}]", prefix="UI"))
        self.ui.lineEditDifferenceUpperQuantile.editingFinished.connect(lambda: log(f"lineEditDifferenceUpperQuantile value=[{self.ui.lineEditDifferenceUpperQuantile.value}]", prefix="UI"))

    def connect_data_observers(self, data):
        """Connects data notifiers to preprocess observer functions

        The ``DataHandling.SampleObj`` has properties that send notifications when the
        values are changed.  These values are then connected to methods in this class
        that update the MainWindow UI.

        Parameters
        ----------
        data : SampleObj
            Connects data notifiers to preprocess observer functions
        """
        data.add_observer("nx", self.update_nx_lineedit)
        data.add_observer("ny", self.update_ny_lineedit)
        data.add_observer("dx", self.update_dx_lineedit)
        data.add_observer("dy", self.update_dy_lineedit)
        data.add_observer("data_min_quantile", self.update_data_min_quantile)
        data.add_observer("data_max_quantile", self.update_data_max_quantile)
        data.add_observer("data_min_diff_quantile", self.update_data_min_diff_quantile)
        data.add_observer("data_max_diff_quantile", self.update_data_max_diff_quantile)
        data.add_observer("data_auto_scale_value", self.update_auto_scale_value)
        data.add_observer("apply_outlier_to_all", self.update_apply_outlier_to_all)
        data.add_observer("outlier_method", self.update_outlier_method)
        data.add_observer("outlier_method", self.update_negative_handling_method)

    def update_nx_lineedit(self,value):
        """Updates ``MainWindow.lineEditResolutionNx.value``
        Called as an update to ``app_data.n_x``.  Updates Nx and  Schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.ui.lineEditResolutionNx.value = value
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()

    def update_ny_lineedit(self,value):
        """
        Updates ``MainWindow.lineEditResolutionNy.value``

        Called when ``app_data.n_y`` changes. Updates the Ny resolution
        input field and schedules a plot update if the process tab is active.

        Parameters
        ----------
        value : str
            y dimension.
        """
        self.ui.lineEditResolutionNy.value = value
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()

    def update_dx_lineedit(self,value):
        """Updates ``MainWindow.lineEditDX.value``
        Called as an update to ``app_data.dx``.  Updates dx and schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.ui.lineEditDX.value = value
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()
            field = 'Xc'
            if isinstance(self.ui.plot_info, dict) \
                and 'field_type' in self.ui.plot_info \
                and 'field' in self.ui.plot_info:
                # update x axis limits in style_dict 
                self.ui.plot_style.initialize_axis_values(self.ui.data, self.ui.plot_info['field_type'], self.ui.plot_info['field'])
                # update limits in styling tabs
                self.ui.plot_style.set_axis_widgets("x",field)

    def update_dy_lineedit(self,value):
        """Updates ``MainWindow.lineEditDY.value``
        Called as an update to ``app_data.dy``.  Updates dy and schedules a plot update.

        Parameters
        ----------
        value : str
            y dimension.
        """
        self.ui.lineEditDY.value = value
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()
            field = 'Yc'
            if isinstance(self.ui.plot_info, dict) \
                and 'field_type' in self.ui.plot_info \
                and 'field' in self.ui.plot_info:
                # update x axis limits in style_dict 
                self.ui.plot_style.initialize_axis_values(self.ui.plot_info['field_type'], self.ui.plot_info['field'])
                # update limits in styling tabs
                self.ui.plot_style.set_axis_widgets("y",field)


    def update_data_min_quantile(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 

        Parameters
        ----------
        value : float
            Lower quantile value.
        """
        self.ui.lineEditLowerQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.scheduler.schedule_update()


    def update_data_max_quantile(self,value):
        """
        Updates ``MainWindow.lineEditUpperQuantile.value``

        Called when the upper quantile threshold changes.

        Parameters
        ----------
        value : float
            Upper quantile value.
        """
        self.ui.lineEditUpperQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()

    def update_data_min_diff_quantile(self,value):
        """
        Updates ``MainWindow.lineEditDifferenceLowerQuantile.value``

        Called when the lower difference quantile threshold changes.

        Parameters
        ----------
        value : float
            Lower difference quantile value.
        """
        self.ui.lineEditDifferenceLowerQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()

    def update_data_max_diff_quantile(self,value):
        """
        Updates ``MainWindow.lineEditDifferenceUpperQuantile.value``

        Called when the upper difference quantile threshold changes.

        Parameters
        ----------
        value : float
            Upper difference quantile value.
        """
        self.ui.lineEditDifferenceUpperQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()


    def update_auto_scale_value(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.ui.toolButtonAutoScale.setChecked(value)
        if value:
            self.ui.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.ui.lineEditDifferenceUpperQuantile.setEnabled(True)
        else:
            self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.plot_style.schedule_update()

    def update_apply_outlier_to_all(self,value):
        """
        Updates the 'Apply to all' checkbox state and clears plot trees if needed.

        Called when the data attribute ``apply_outlier_to_all`` changes. Updates the checkbox
        and optionally clears analyte and ratio plot trees to force re-evaluation with new settings.

        Parameters
        ----------
        value : bool
            Whether to apply outlier removal to all analytes.
        """
        self.ui.checkBoxApplyAll.setChecked(value)
        ratio = ('/' in self.ui.app_data.plot_info['field'])
        if value and not ratio: 
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.ui.plot_tree.clear_tree_data(tree)
        elif value and not ratio:
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in [ 'Ratio', 'Ratio (normalized)']:
                self.ui.plot_tree.clear_tree_data(tree) 
        
    def update_outlier_method(self,method):
        """Updates ``MainWindow.comboBoxOutlierMethod.currentText()``

        Called as an update to ``DataHandling.outlier_method``.  Resets data bound widgets visibility upon change.

        Parameters
        ----------
        method : str
             Method used to remove outliers.
        """
        if self.ui.data[self.ui.app_data.sample_id].outlier_method == method:
            return

        self.ui.data[self.ui.app_data.sample_id].outlier_method = method

        match method.lower():
            case 'none':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.ui.lineEditLowerQuantile.setEnabled(True)
                self.ui.lineEditUpperQuantile.setEnabled(True)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.ui.lineEditLowerQuantile.setEnabled(True)
                self.ui.lineEditUpperQuantile.setEnabled(True)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_negative_handling_method(self,method):
        """Auto-scales pixel values in map

        Executes when the value ``MainWindow.comboBoxNegativeMethod`` is changed.

        Changes how negative values are handled for each analyte, the following options are available:
            Ignore negative values, Minimum positive value, Gradual shift, Yeo-Johnson transformation

        Parameters
        ----------
        method : str
            Method for dealing with negatives
        """
        data = self.ui.data[self.ui.app_data.sample_id]

        if self.ui.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed_data.match_attribute('data_type', 'Analyte') + data.processed_data.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.ui.plot_tree.clear_tree_data(tree)
            data.prep_data()
        else:
            data.negative_method = method
            data.prep_data(self.ui.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.ui.plot_style.schedule_update()

    def update_autoscale_checkbox(self, value):
        """
        Updates the autoscale checkbox state and triggers a plot update.

        Enables or disables the 'apply to all' checkbox depending on the value
        of the global `apply_process_to_all_data` flag.

        Parameters
        ----------
        value : bool or None
            If None, checkbox is set True. Otherwise, set to False.
        """
        if value is None:
            self.ui.checkBoxApplyAll.setChecked(True)
        else:
            self.ui.checkBoxApplyAll.setChecked(False)

        self.ui.plot_style.schedule_update()

    def update_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.ui.data[self.ui.app_data.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.ui.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")


    def update_invalid_data_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.ui.data[self.ui.app_data.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.ui.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")

    def update_outlier_removal(self, method):
        """Removes outliers from one or all analytes.
        
        Parameters
        ----------
        method : str
            Method used to remove outliers.
        """        
        data = self.ui.data[self.ui.app_data.sample_id]

        if data.outlier_method == method:
            return

        data.outlier_method = method

        match method.lower():
            case 'none':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.ui.lineEditLowerQuantile.setEnabled(True)
                self.ui.lineEditUpperQuantile.setEnabled(True)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.ui.lineEditLowerQuantile.setEnabled(True)
                self.ui.lineEditUpperQuantile.setEnabled(True)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.ui.lineEditLowerQuantile.setEnabled(False)
                self.ui.lineEditUpperQuantile.setEnabled(False)
                self.ui.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.ui.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_neg_handling(self, method):
        """Auto-scales pixel values in map

        Executes when the value ``MainWindow.comboBoxNegativeMethod`` is changed.

        Changes how negative values are handled for each analyte, the following options are available:
            Ignore negative values, Minimum positive value, Gradual shift, Yeo-Johnson transformation

        Parameters
        ----------
        method : str
            Method for dealing with negatives
        """
        data = self.ui.data[self.ui.app_data.sample_id]

        if self.ui.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed_data.match_attribute('data_type', 'Analyte') + data.processed_data.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.ui.plot_tree.clear_tree_data(tree)
            data.prep_data()
        else:
            data.negative_method = method

            assert self.ui.app_data.c_field == self.ui.comboBoxFieldC.currentText(), f"AppData.c_field {self.ui.app_data.c_field} and MainWindow.comboBoxFieldC.currentText() {self.ui.comboBoxFieldC.currentText()} do not match"
            data.prep_data(self.ui.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.ui.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.ui.plot_style.schedule_update()

    def update_dx(self):
        """Updates the x-resolution (`dx`) of the current sample and triggers a plot update."""
        self.ui.data[self.ui.app_data.sample_id].update_resolution('x', self.ui.lineEditDX.value)
        self.ui.plot_style.schedule_update()

    def update_dy(self):
        """Updates the y-resolution (`dy`) of the current sample and triggers a plot update."""
        self.ui.data[self.ui.app_data.sample_id].update_resolution('y', self.ui.lineEditDY.value)
        self.ui.plot_style.schedule_update()

    def reset_crop(self):
        """Resets the cropping of the current sample and triggers a plot update."""
        self.ui.data[self.ui.app_data.sample_id].reset_crop
        self.ui.plot_style.schedule_update()

    def update_swap_resolution(self):
        """Resets the pixel resolution of the current sample to original values and triggers a plot update."""
        if not self.ui.data or self.ui.app_data.sample_id != '':
            return

        self.ui.data[self.ui.app_data.sample_id].swap_resolution 
        self.ui.plot_style.schedule_update()

    def reset_pixel_resolution(self):
        """
        Swaps the x and y resolutions in the current dataset and schedules a plot update.

        Does nothing if no data is loaded or the sample ID is empty.
        """
        self.ui.data[self.ui.app_data.sample_id].reset_resolution
        self.ui.plot_style.schedule_update()