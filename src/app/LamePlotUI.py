
import re
from PyQt6.QtCore import ( Qt )
from PyQt6.QtWidgets import ( QCheckBox, QTableWidgetItem, QMessageBox, QInputDialog )
from src.common.TableFunctions import TableFcn
import src.common.csvdict as csvdict
from src.common.Logger import log, auto_log_methods

@auto_log_methods(logger_key="Plot")
class HistogramUI():
    """ Handles histogram plot settings and updates.

    This class manages the histogram bin width, number of bins, and plot style.
    It connects the UI widgets to the appropriate methods and updates the plot style accordingly.

    Attributes
    ----------
    ui : MainWindow
        The main window instance containing the UI elements.
    logger_key : str
        The key used for logging messages related to this class.
    _histogram_type_options : list
        A list of available histogram plot styles.  Options include 'PDF', 'CDF', and 'log-scaling'.

    Methods
    -------
    connect_widgets()
        Connects the histogram widgets to their respective methods.
    connect_observer()
        Connects the properties to observer functions for updates.
    connect_logger()
        Connects the widgets to the logger for logging changes.
    update_hist_bin_width(value=None)
        Updates the histogram bin width.
    update_hist_num_bins(value=None)
        Updates the histogram number of bins.
    update_hist_plot_style(new_plot_style=None)
        Updates the histogram plot style combobox and triggers a plot update.
    """
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self._histogram_type_options = ['PDF','CDF','log-scaling']

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects histogram widgets to methods."""
        self.ui.doubleSpinBoxBinWidth.valueChanged.connect(lambda _: self.update_hist_bin_width(self.ui.doubleSpinBoxBinWidth.value()))
        self.ui.spinBoxNBins.valueChanged.connect(lambda _: self.update_hist_num_bins(self.ui.spinBoxNBins.value()))
        self.ui.toolButtonHistogramReset.clicked.connect(lambda: self.ui.spinBox)

        self.ui.comboBoxHistType.clear()
        self.ui.comboBoxHistType.addItems(self._histogram_type_options)
        self.ui.comboBoxHistType.setCurrentText(self._histogram_type_options[0])
        self.ui.app_data.hist_plot_style = self._histogram_type_options[0]
        self.ui.comboBoxHistType.activated.connect(lambda _: self.update_hist_plot_style())

        self.ui.toolButtonHistogramReset.clicked.connect(self.ui.app_data.histogram_reset_bins)

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("hist_bin_width", self.update_hist_bin_width)
        self.ui.app_data.add_observer("hist_num_bins", self.update_hist_num_bins)
        self.ui.app_data.add_observer("hist_plot_style", self.update_hist_plot_style)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.doubleSpinBoxBinWidth.valueChanged.connect(lambda: log(f"doubleSpinBoxBinWidth value=[{self.ui.doubleSpinBoxBinWidth.value()}]", prefix="UI"))
        self.ui.spinBoxNBins.valueChanged.connect(lambda: log(f"spinBoxNBins value=[{self.ui.spinBoxNBins.value()}]", prefix="UI"))
        self.ui.toolButtonHistogramReset.clicked.connect(lambda: log("toolButtonHistogramReset", prefix="UI"))

    def update_hist_bin_width(self, value=None):
        """ Updates histogram bin width.
        
        If `value` is None, it uses the current value of `doubleSpinBoxBinWidth`.
        If `value` is provided, it updates the `doubleSpinBoxBinWidth` state accordingly.

        Parameters
        ----------
        value : float, optional
            New value for the histogram bin width, by default None
        """
        if value is None:
            # use current value of doubleSpinBoxBinWidth
            self.ui.app_data.hist_bin_width = self.ui.doubleSpinBoxBinWidth.value()
        else:
            # update doubleSpinBoxBinWidth with new value
            if self.ui.doubleSpinBoxBinWidth.value() == value:
                return
            # block signals to prevent infinite loop
            self.ui.doubleSpinBoxBinWidth.blockSignals(True)
            self.ui.doubleSpinBoxBinWidth.setValue(value)
            self.ui.doubleSpinBoxBinWidth.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()

    def update_hist_num_bins(self, value=None):
        """ Updates histogram number of bins.
        
        If `value` is None, it uses the current value of `spinBoxNBins`.
        If `value` is provided, it updates the `spinBoxNBins` state accordingly.
        
        Parameters
        ----------
        value : int, optional
            New value for the histogram number of bins, by default None
        """
        if value is None:
            # use current value of spinBoxNBins
            self.ui.app_data.hist_num_bins = self.ui.spinBoxNBins.value()
        else:
            # if value is 0, set to default number of bins
            if value == 0:
                self.ui.app_data.reset_hist_num_bins()

            # update spinBoxNBins with new value
            if self.ui.spinBoxNBins.value() == value:
                return

            # block signals to prevent infinite loop
            self.ui.spinBoxNBins.blockSignals(True)
            self.ui.spinBoxNBins.setValue(value)
            self.ui.spinBoxNBins.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()

    def update_hist_plot_style(self, new_plot_style=None):
        """
        Updates histogram plot style combobox and triggers plot update.

        If `new_plot_style` is None, it uses the current text of the combobox to set `ui.app_data.hist_plot_style`.
        If `new_plot_style` is provided, it updates the `ui.comboBoxHistType` state accordingly.

        Parameters
        ----------
        new_plot_style : str, optional
            New style for the histogram plot, by default None
        """
        if new_plot_style is None:
            # use current text of combobox
            self.ui.app_data.hist_plot_style = self.ui.comboBoxHistType.currentText()
        else:
            # update combobox with new plot style
            if self.ui.comboBoxHistType.currentText() == new_plot_style:
                return
            # block signals to prevent infinite loop
            self.ui.comboBoxHistType.blockSignals(True)
            self.ui.comboBoxHistType.setCurrentText(new_plot_style)
            self.ui.comboBoxHistType.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()

@auto_log_methods(logger_key="Plot")
class CorrelationUI():
    """ Handles correlation plot settings and updates.
    This class manages the correlation method selection and squared correlation checkbox.
    It connects the UI widgets to the appropriate methods and updates the plot style accordingly.
    
    Attributes
    ----------
    ui : MainWindow
        The main window instance containing the UI elements.
    logger_key : str
        The key used for logging messages related to this class.
    _correlation_method_options : list
        A list of available correlation methods.  Methods include 'Pearson', 'Spearman', and 'Kendall'.
    
    Methods
    -------
    connect_widgets()
        Connects the correlation widgets to their respective methods.
    connect_observer()
        Connects the properties to observer functions for updates.
    connect_logger()
        Connects the widgets to the logger for logging changes.
    update_corr_method(new_method=None)
        Updates the correlation method combobox and triggers a plot update.
    update_corr_squared(new_state=None)
        Updates the correlation squared checkbox and triggers a plot update.
    correlation_method_callback()
        Updates the colorbar label for correlation plots based on the current method.
    correlation_squared_callback()
        Produces a plot of the squared correlation and updates the color limits and colormap.
    """
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self._correlation_method_options = ['Pearson','Spearman','Kendall']
        
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects correlation widgets to methods."""
        self.ui.comboBoxCorrelationMethod.clear()
        self.ui.comboBoxCorrelationMethod.addItems(self._correlation_method_options)
        self.ui.comboBoxCorrelationMethod.setCurrentText(self._correlation_method_options[0])
        self.ui.app_data.corr_method = self._correlation_method_options[0]
        self.ui.comboBoxCorrelationMethod.activated.connect(lambda _: self.update_corr_method())

        self.ui.checkBoxCorrelationSquared.stateChanged.connect(lambda _: self.update_corr_squared())

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("corr_method", self.update_corr_method)
        self.ui.app_data.add_observer("corr_squared", self.update_corr_squared)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxCorrelationMethod.activated.connect(lambda: log(f"comboBoxCorrelationMethod value=[{self.ui.comboBoxCorrelationMethod.currentText()}]", prefix="UI"))
        self.ui.checkBoxCorrelationSquared.checkStateChanged.connect(lambda: log(f"checkBoxCorrelationSquared value=[{self.ui.checkBoxCorrelationSquared.isChecked()}]", prefix="UI"))


    def update_corr_method(self, new_method=None):
        """ Updates correlation method combobox and triggers plot update.

        If `new_method` is None, it uses the current text of the combobox to set `ui.app_data.corr_method`.
        If `new_method` is provided, it updates the `ui.comboBoxCorrelationMethod` state accordingly.

        Parameters
        ----------
        new_method : int, optional
            New index for the correlation method, by default None
        """
        if new_method is None:
            # use current text of combobox
            self.ui.app_data.corr_method = self.ui.comboBoxCorrelationMethod.currentText()
        else:
            # update combobox with new method
            if self.ui.comboBoxCorrelationMethod.currentText() == new_method:
                return
            # block signals to prevent infinite loop
            self.ui.comboBoxCorrelationMethod.blockSignals(True)
            self.ui.comboBoxCorrelationMethod.setCurrentText(new_method)
            self.ui.comboBoxCorrelationMethod.blockSignals(False)

        # update the other plot style settings related to correlation method
        self.correlation_method_callback()

    def update_corr_squared(self, new_state=None):
        """
        Updates correlation squared checkbox and triggers plot update.

        If `new_state` is None, it uses the current state of the checkbox to set `ui.app_data.corr_squared`.
        If `new_state` is provided, it updates the `ui.checkBoxCorrelationSquared` state accordingly.

        Parameters
        ----------
        new_state : bool, optional
            New state for the correlation squared checkbox, by default None
        """
        if new_state is None:
            self.ui.app_data.corr_squared = self.ui.checkBoxCorrelationSquared.isChecked()
        else:
            if self.ui.checkBoxCorrelationSquared.isChecked() == new_state:
                return
            # block signals to prevent infinite loop
            self.ui.checkBoxCorrelationSquared.blockSignals(True)
            self.ui.checkBoxCorrelationSquared.setChecked(new_state)
            self.ui.checkBoxCorrelationSquared.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "correlation":
            self.ui.plot_style.schedule_update()

        # update the color limits and colormap based on whether the correlation is squared or not
        self.correlation_squared_callback()

    def correlation_method_callback(self):
        """
        Updates colorbar label for correlation plots.
        
        Checks the current correlation method and updates the colorbar label accordingly.
        If the method has changed, it updates the color limits and colormap based on whether the correlation is squared or not.
        Also ensures that the plot type is set to 'correlation'.
        """
        method = self.ui.app_data.corr_method
        if self.ui.plot_style.clabel == method:
            return

        if self.ui.app_data.corr_squared:
            power = '^2'
        else:
            power = ''

        # update colorbar label for change in method
        match method:
            case 'Pearson':
                self.ui.plot_style.clabel = method + "'s $r" + power + "$"
            case 'Spearman':
                self.ui.plot_style.clabel = method + "'s $\\rho" + power + "$"
            case 'Kendall':
                self.ui.plot_style.clabel = method + "'s $\\tau" + power + "$"

        if self.ui.plot_style.plot_type != 'correlation':
            self.ui.plot_style.plot_type = 'correlation'

        # trigger update to plot
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "correlation":
            self.ui.plot_style.schedule_update()

    def correlation_squared_callback(self):
        """
        Produces a plot of the squared correlation.
        
        Updates the color limits and colormap based on whether the correlation is squared or not.
        Also updates the colorbar label based on the current correlation method.
        """
        # update color limits and colorbar
        if self.ui.app_data.corr_squared:
            self.ui.plot_style.clim = [0,1]
            self.ui.plot_style.cmap = 'cmc.oslo'
        else:
            self.ui.plot_style.clim = [-1,1]
            self.ui.plot_style.cmap = 'RdBu'

        # update label
        self.correlation_method_callback()

        # trigger update to plot
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "correlation":
            self.ui.plot_style.schedule_update()
    
@auto_log_methods(logger_key="Plot")
class ScatterUI():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self._heatmap_options = ['counts','median','median, MAD','MAD','mean','mean, std','std']

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects scatter and heatmap widgets to methods."""
        self.ui.comboBoxHeatmaps.clear()
        self.ui.comboBoxHeatmaps.addItems(self._heatmap_options)
        self.ui.comboBoxHeatmaps.activated.connect(self.update_heatmap_style_combobox)


    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("scatter_preset", self.update_scatter_preset_combobox)
        self.ui.app_data.add_observer("heatmap_style", self.update_heatmap_style_combobox)
        self.ui.app_data.add_observer("ternary_colormap", self.update_ternary_colormap_combobox)
        self.ui.app_data.add_observer("ternary_color_x", self.update_ternary_color_x_toolbutton)
        self.ui.app_data.add_observer("ternary_color_y", self.update_ternary_color_y_toolbutton)
        self.ui.app_data.add_observer("ternary_color_z", self.update_ternary_color_z_toolbutton)
        self.ui.app_data.add_observer("ternary_color_m", self.update_ternary_color_m_toolbutton)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxScatterPreset.activated.connect(lambda: log(f"comboBoxScatterPreset value=[{self.ui.comboBoxScatterPreset.currentText()}]", prefix="UI"))
        self.ui.toolButtonScatterSavePreset.clicked.connect(lambda: log("toolButtonScatterSavePreset", prefix="UI"))
        self.ui.comboBoxHeatmaps.activated.connect(lambda: log(f"comboBoxHeatmaps value=[{self.ui.comboBoxHeatmaps.currentText()}]", prefix="UI"))
        self.ui.comboBoxTernaryColormap.activated.connect(lambda: log(f"comboBoxTernaryColormap value=[{self.ui.comboBoxTernaryColormap.currentText()}]", prefix="UI"))
        self.ui.toolButtonTCmapXColor.clicked.connect(lambda: log("toolButtonTCmapXColor", prefix="UI"))
        self.ui.toolButtonTCmapYColor.clicked.connect(lambda: log("toolButtonTCmapYColor", prefix="UI"))
        self.ui.toolButtonTCmapZColor.clicked.connect(lambda: log("toolButtonTCmapZColor", prefix="UI"))
        self.ui.toolButtonTCmapMColor.clicked.connect(lambda: log("toolButtonTCmapMColor", prefix="UI"))
        self.ui.toolButtonSaveTernaryColormap.clicked.connect(lambda: log("toolButtonSaveTernaryColormap", prefix="UI"))
        self.ui.toolButtonTernaryMap.clicked.connect(lambda: log("toolButtonTernaryMap", prefix="UI"))

    def update_scatter_preset_combobox(self, new_scatter_preset):
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_heatmap_style_combobox(self, new_heatmap_style):
        self.ui.comboBoxHeatmaps.setCurrentText(new_heatmap_style)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_ternary_colormap_combobox(self, new_ternary_colormap):
        self.ui.comboBoxTernaryColormap.setCurrentText(new_ternary_colormap)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_ternary_color_x_toolbutton(self, new_color):
        self.ui.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_ternary_color_y_toolbutton(self, new_color):
        self.ui.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_ternary_color_z_toolbutton(self, new_color):
        self.ui.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()

    def update_ternary_color_m_toolbutton(self, new_color):
        self.ui.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.ui.plot_style.schedule_update()


@auto_log_methods(logger_key="Plot")
class NDimUI():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self.table_fcn = TableFcn(self)

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects n-dimensional widgets to methods."""
        self.ui.comboBoxNDimQuantiles.setCurrentIndex(self.ui.app_data.ndim_quantile_index)
        self.ui.comboBoxNDimQuantiles.activated.connect(lambda _: self.update_ndim_quantile_index())
        
        self.ui.toolButtonNDimAnalyteAdd.clicked.connect(lambda: self.update_ndim_table('analyteAdd'))
        self.ui.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: self.update_ndim_table('analyteSetAdd'))
        self.ui.toolButtonNDimUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.ui.tableWidgetNDim))
        self.ui.toolButtonNDimDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.ui.tableWidgetNDim))
        self.ui.toolButtonNDimSelectAll.clicked.connect(self.ui.tableWidgetNDim.selectAll)
        self.ui.toolButtonNDimRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.ui.tableWidgetNDim))
        self.ui.toolButtonNDimSaveList.clicked.connect(self.save_ndim_list)

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("ndim_analyte_set", self.update_ndim_analyte_set_combobox)
        self.ui.app_data.add_observer("ndim_quantile_index", self.update_ndim_quantile_index)

    def connect_logger(self):
        """Connects widgets to logger."""
        pass

    def update_ndim_analyte_set_combobox(self, new_ndim_analyte_set):
        self.ui.comboBoxNDimAnalyteSet.setCurrentText(new_ndim_analyte_set)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['ndim']:
            self.ui.plot_style.schedule_update()

    def update_ndim_table(self,calling_widget):
        """Updates tableWidgetNDim based on the calling widget.

        If the calling widget is 'analyteAdd', it adds a new row for the selected analyte.
        If the calling widget is 'analyteSetAdd', it adds rows for all analytes in the selected set.

        Parameters
        ----------
        calling_widget : str
            The widget that triggered the update, either 'analyteAdd' or 'analyteSetAdd'.
        """
        def on_use_checkbox_state_changed(row, state):
            """Callback for checkbox state change in the 'use' column.
            Updates the 'use' value in the filter_df for the given row.

            Parameters
            ----------
            row : int
                The row index of the checkbox that was changed.
            state : Qt.CheckState
                The new state of the checkbox (Checked or Unchecked).
            """
            # Update the 'use' value in the filter_df for the given row
            self.ui.data[self.ui.app_data.sample_id].filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.ui.comboBoxNDimAnalyte.currentText().lower()]
            self.ui.comboBoxNDimAnalyteSet.setCurrentText('user defined')
        elif calling_widget == 'analyteSetAdd':
            el_list = self.ui.app_data.ndim_list_dict[self.ui.comboBoxNDimAnalyteSet.currentText()]

        analytes_list = self.ui.data[self.ui.app_data.sample_id].processed_data.match_attribute('data_type','Analyte')

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.ui.app_data.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.ui.tableWidgetNDim.rowCount()
            self.ui.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.CheckState.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            self.ui.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.ui.tableWidgetNDim.setItem(row, 1, QTableWidgetItem(analyte))
    
    def update_ndim_quantile_index(self, new_index=None):
        """Updates quantiles displayed for NDim plots.

        Updates quantile index for ``self.comboBoxNDimQuantiles`` or updates ``self.app_data.dim_quantile_index``
        if new_index is not supplied.  Call plot update after updating quantiles.

        Parameters
        ----------
        new_index : int, optional
            New index into ``self.app_data.ndim_quantile_index``, by default None
        """

        if new_index is None:
            self.ui.app_data.ndim_quantile_index = self.ui.comboBoxNDimQuantiles.currentIndex()
        else:
            self.ui.comboBoxNDimQuantiles.blockSignals(True)
            self.ui.comboBoxNDimQuantiles.setCurrentIndex(new_index)
            self.ui.comboBoxNDimQuantiles.blockSignals(False)

        if self.ui.toolbox.currentIndex() == self.ui.left_tab['ndim']:
            self.ui.plot_style.schedule_update()

    def save_ndim_list(self):
        """
        Saves the current NDim list to a file.

        This method prompts the user for a name for the new list, saves the current NDim list to the
        application's data dictionary, and exports the dictionary to a CSV file.

        If the user cancels the input dialog or an error occurs during saving, a warning message is displayed.
        """
        # get the list name from the user
        name, ok = QInputDialog.getText(self.ui, 'Save custom TEC list', 'Enter name for new list:')
        if ok:
            try:
                self.ui.app_data.ndim_list_dict[name] = self.ui.tableWidgetNDim.column_to_list('Analyte')

                # export the csv
                csvdict.export_dict_to_csv(self.ui.app_data.ndim_list_dict, self.ui.app_data.ndim_list_filename)
            except:
                QMessageBox.warning(self.ui,'Error','could not save TEC file.')
                
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.ui,'Error','could not save TEC list.')

            return