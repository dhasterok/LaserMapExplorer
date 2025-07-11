
import re
from PyQt6.QtCore import ( Qt )
from PyQt6.QtWidgets import ( QCheckBox, QTableWidgetItem, QMessageBox, QInputDialog, )
from src.common.TableFunctions import TableFcn
import src.common.csvdict as csvdict
from src.common.Logger import log, auto_log_methods

@auto_log_methods(logger_key="Plot")
class HistogramUI():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects histogram widgets to methods."""
        self.ui.doubleSpinBoxBinWidth.valueChanged.connect(lambda: self.update_hist_bin_width_spinbox(self.ui.doubleSpinBoxBinWidth.value()))
        self.ui.spinBoxNBins.valueChanged.connect(lambda: self.update_hist_num_bins_spinbox(self.ui.spinBoxNBins.value()))
        self.ui.toolButtonHistogramReset.clicked.connect(lambda: self.ui.spinBox)
        self.ui.comboBoxHistType.activated.connect(lambda: self.ui.comboBoxHistType.currentText())

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("hist_bin_width", self.update_hist_bin_width_spinbox)
        self.ui.app_data.add_observer("hist_num_bins", self.update_hist_num_bins_spinbox)
        self.ui.app_data.add_observer("hist_plot_style", self.update_hist_plot_style_combobox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.doubleSpinBoxBinWidth.valueChanged.connect(lambda: log(f"doubleSpinBoxBinWidth value=[{self.ui.doubleSpinBoxBinWidth.value()}]", prefix="UI"))
        self.ui.spinBoxNBins.valueChanged.connect(lambda: log(f"spinBoxNBins value=[{self.ui.spinBoxNBins.value()}]", prefix="UI"))
        self.ui.toolButtonHistogramReset.clicked.connect(lambda: log("toolButtonHistogramReset", prefix="UI"))

    def update_hist_bin_width_spinbox(self, value):
        self.ui.doubleSpinBoxBinWidth.setValue(value)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()

    def update_hist_num_bins_spinbox(self, value):
        self.ui.spinBoxNBins.setValue(value)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()

    def update_hist_plot_style_combobox(self, new_hist_plot_style):
        self.ui.comboBoxHistType.setCurrentText(new_hist_plot_style)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "histogram":
            self.ui.plot_style.schedule_update()


@auto_log_methods(logger_key="Plot")
class CorrelationUI():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"
        
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects correlation widgets to methods."""
        pass

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("corr_method", self.update_corr_method_combobox)
        self.ui.app_data.add_observer("corr_squared", self.update_corr_squared_checkbox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxCorrelationMethod.activated.connect(lambda: log(f"comboBoxCorrelationMethod value=[{self.ui.comboBoxCorrelationMethod.currentText()}]", prefix="UI"))
        self.ui.checkBoxCorrelationSquared.checkStateChanged.connect(lambda: log(f"checkBoxCorrelationSquared value=[{self.ui.checkBoxCorrelationSquared.isChecked()}]", prefix="UI"))

    def update_corr_method_combobox(self, new_corr_method):
        self.ui.comboBoxCorrelationMethod.setCurrentText(new_corr_method)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "correlation":
            self.ui.plot_style.schedule_update()

    def update_corr_squared_checkbox(self, new_corr_squared):
        self.ui.checkBoxCorrelationSquared.setChecked(new_corr_squared)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample'] and self.ui.plot_style.plot_type == "correlation":
            self.ui.plot_style.schedule_update()

    def update_corr_method(self):
        self.ui.app_data.corr_method = self.ui.comboBoxCorrelationMethod.currentText()
        self.correlation_method_callback()

    def update_corr_squared(self):
        self.ui.app_data.corr_squared = self.ui.checkBoxCorrelationSquared.isChecked()
        self.correlation_squared_callback()

    def correlation_method_callback(self):
        """Updates colorbar label for correlation plots"""
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
        self.ui.plot_style.schedule_update()

    def correlation_squared_callback(self):
        """Produces a plot of the squared correlation."""        
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
        self.ui.plot_style.schedule_update()

    
@auto_log_methods(logger_key="Plot")
class ScatterUI():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Plot"

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        """Connects scatter and heatmap widgets to methods."""
        pass

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
        """Updates tableWidgetNDim"""
        def on_use_checkbox_state_changed(row, state):
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