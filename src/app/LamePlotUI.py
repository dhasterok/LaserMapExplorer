import re
import pandas as pd
from PyQt6.QtCore import ( Qt, QRect, QSize )
from PyQt6.QtWidgets import ( 
    QCheckBox, QTableWidgetItem, QMessageBox, QInputDialog, QGroupBox, QFormLayout, QVBoxLayout,
    QHBoxLayout, QAbstractSpinBox, QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QWidget, QScrollArea,
    QFrame, QToolButton, QSpacerItem, QSizePolicy, QAbstractItemView, QHeaderView
)
from PyQt6.QtGui import ( QIcon )
from src.common.TableFunctions import TableFcn
from src.common.CustomWidgets import CustomPage, CustomComboBox, CustomToolButton, CustomTableWidget, ColorButton
import src.common.csvdict as csvdict
from src.common.colorfunc import get_hex_color, get_rgb_color
from src.common.Logger import log, auto_log_methods
from src.app.config import ICONPATH


@auto_log_methods(logger_key="Plot")
class HistogramUI(QGroupBox):
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
    def __init__(self, dock=None):
        super().__init__(dock)

        self.dock = dock
        self.logger_key = "Plot"

        self.setupUI()

        self._histogram_type_options = ['PDF','CDF','log-scaling']

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self):
        self.setTitle("Histogram")
        self.setObjectName("groupBoxHistogram")

        form_layout = QFormLayout(self)
        form_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(form_layout)

        self.doubleSpinBoxBinWidth = QDoubleSpinBox(parent=self)
        self.doubleSpinBoxBinWidth.setMaximum(100000.0)
        self.doubleSpinBoxBinWidth.setStepType(QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
        self.doubleSpinBoxBinWidth.setObjectName("doubleSpinBoxBinWidth")
        form_layout.addRow("Bin width", self.doubleSpinBoxBinWidth)


        no_bin_layout = QHBoxLayout()
        no_bin_layout.setContentsMargins(0, 0, 0, 0)

        self.toolButtonHistogramReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self,
        )
        self.toolButtonHistogramReset.setToolTip("Reset number of bins to default value.")
        self.toolButtonHistogramReset.setObjectName("toolButtonHistogramReset")
        no_bin_layout.addWidget(self.toolButtonHistogramReset)

        self.spinBoxNBins = QSpinBox(parent=self)
        self.spinBoxNBins.setMinimum(1)
        self.spinBoxNBins.setMaximum(500)
        self.spinBoxNBins.setStepType(QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
        self.spinBoxNBins.setObjectName("spinBoxNBins")
        no_bin_layout.addWidget(self.spinBoxNBins)

        form_layout.addRow("No. Bins", no_bin_layout)

        self.comboBoxHistType = QComboBox(parent=self)
        self.comboBoxHistType.setObjectName("comboBoxHistType")
        form_layout.addRow("Histogram type", self.comboBoxHistType)

    def connect_widgets(self):
        """Connects histogram widgets to methods."""
        self.doubleSpinBoxBinWidth.valueChanged.connect(lambda _: self.update_hist_bin_width(self.doubleSpinBoxBinWidth.value()))
        self.spinBoxNBins.valueChanged.connect(lambda _: self.update_hist_num_bins(self.spinBoxNBins.value()))
        self.toolButtonHistogramReset.clicked.connect(lambda: self.ui.spinBox)

        self.comboBoxHistType.clear()
        self.comboBoxHistType.addItems(self._histogram_type_options)
        self.comboBoxHistType.setCurrentText(self._histogram_type_options[0])
        self.dock.ui.app_data.hist_plot_style = self._histogram_type_options[0]
        self.comboBoxHistType.activated.connect(lambda _: self.update_hist_plot_style())

        self.toolButtonHistogramReset.clicked.connect(self.dock.ui.app_data.histogram_reset_bins)

        self.comboBoxHistType.activated.connect(self.dock.ui.schedule_update)

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.dock.ui.app_data.add_observer("hist_bin_width", self.update_hist_bin_width)
        self.dock.ui.app_data.add_observer("hist_num_bins", self.update_hist_num_bins)
        self.dock.ui.app_data.add_observer("hist_plot_style", self.update_hist_plot_style)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.doubleSpinBoxBinWidth.valueChanged.connect(lambda: log(f"doubleSpinBoxBinWidth value=[{self.doubleSpinBoxBinWidth.value()}]", prefix="UI"))
        self.spinBoxNBins.valueChanged.connect(lambda: log(f"spinBoxNBins value=[{self.spinBoxNBins.value()}]", prefix="UI"))
        self.toolButtonHistogramReset.clicked.connect(lambda: log("toolButtonHistogramReset", prefix="UI"))

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
            self.dock.ui.app_data.hist_bin_width = self.doubleSpinBoxBinWidth.value()
        else:
            # update doubleSpinBoxBinWidth with new value
            if self.doubleSpinBoxBinWidth.value() == value:
                return
            # block signals to prevent infinite loop
            self.doubleSpinBoxBinWidth.blockSignals(True)
            self.doubleSpinBoxBinWidth.setValue(value)
            self.doubleSpinBoxBinWidth.blockSignals(False)

        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "histogram":
            self.dock.ui.schedule_update()

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
            self.dock.ui.app_data.hist_num_bins = self.spinBoxNBins.value()
        else:
            # if value is 0, set to default number of bins
            if value == 0:
                self.dock.ui.app_data.reset_hist_num_bins()

            # update spinBoxNBins with new value
            if self.spinBoxNBins.value() == value:
                return

            # block signals to prevent infinite loop
            self.spinBoxNBins.blockSignals(True)
            self.spinBoxNBins.setValue(value)
            self.spinBoxNBins.blockSignals(False)

        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "histogram":
            self.dock.ui.schedule_update()

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
            self.dock.ui.app_data.hist_plot_style = self.comboBoxHistType.currentText()
        else:
            # update combobox with new plot style
            if self.comboBoxHistType.currentText() == new_plot_style:
                return
            # block signals to prevent infinite loop
            self.comboBoxHistType.blockSignals(True)
            self.comboBoxHistType.setCurrentText(new_plot_style)
            self.comboBoxHistType.blockSignals(False)

        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "histogram":
            self.dock.ui.schedule_update()

@auto_log_methods(logger_key="Plot")
class CorrelationUI(QGroupBox):
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
    def __init__(self, dock):
        super().__init__(dock)

        self.dock = dock
        self.logger_key = "Plot"

        self.setupUI()

        self._correlation_method_options = ['Pearson','Spearman','Kendall']
        
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self, parent=None):

        self.setTitle("Correlation")
        self.setObjectName("groupBoxCorrelation")

        box_layout = QHBoxLayout(self)
        box_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(box_layout)

        label_method = QLabel(parent=self)
        label_method.setText("Method")
        label_method.setAlignment(Qt.AlignmentFlag.AlignRight)
        box_layout.addWidget(label_method)

        self.comboBoxCorrelationMethod = QComboBox(parent=self)
        self.comboBoxCorrelationMethod.setObjectName("comboBoxCorrelationMethod")
        box_layout.addWidget(self.comboBoxCorrelationMethod)

        self.checkBoxCorrelationSquared = QCheckBox(parent=self)
        self.checkBoxCorrelationSquared.setText("C²")
        self.checkBoxCorrelationSquared.setObjectName("checkBoxCorrelationSquared")
        box_layout.addWidget(self.checkBoxCorrelationSquared)


    def connect_widgets(self):
        """Connects correlation widgets to methods."""
        self.comboBoxCorrelationMethod.clear()
        self.comboBoxCorrelationMethod.addItems(self._correlation_method_options)
        self.comboBoxCorrelationMethod.setCurrentText(self._correlation_method_options[0])
        self.dock.ui.app_data.corr_method = self._correlation_method_options[0]
        self.comboBoxCorrelationMethod.activated.connect(lambda _: self.update_corr_method())

        self.checkBoxCorrelationSquared.stateChanged.connect(lambda _: self.update_corr_squared())

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.dock.ui.app_data.add_observer("corr_method", self.update_corr_method)
        self.dock.ui.app_data.add_observer("corr_squared", self.update_corr_squared)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxCorrelationMethod.activated.connect(lambda: log(f"comboBoxCorrelationMethod value=[{self.comboBoxCorrelationMethod.currentText()}]", prefix="UI"))
        self.checkBoxCorrelationSquared.checkStateChanged.connect(lambda: log(f"checkBoxCorrelationSquared value=[{self.checkBoxCorrelationSquared.isChecked()}]", prefix="UI"))


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
            self.dock.ui.app_data.corr_method = self.comboBoxCorrelationMethod.currentText()
        else:
            # update combobox with new method
            if self.comboBoxCorrelationMethod.currentText() == new_method:
                return
            # block signals to prevent infinite loop
            self.comboBoxCorrelationMethod.blockSignals(True)
            self.comboBoxCorrelationMethod.setCurrentText(new_method)
            self.comboBoxCorrelationMethod.blockSignals(False)

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
            self.dock.ui.app_data.corr_squared = self.checkBoxCorrelationSquared.isChecked()
        else:
            if self.checkBoxCorrelationSquared.isChecked() == new_state:
                return
            # block signals to prevent infinite loop
            self.checkBoxCorrelationSquared.blockSignals(True)
            self.checkBoxCorrelationSquared.setChecked(new_state)
            self.checkBoxCorrelationSquared.blockSignals(False)

        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "correlation":
            self.dock.ui.schedule_update()

        # update the color limits and colormap based on whether the correlation is squared or not
        self.correlation_squared_callback()

    def correlation_method_callback(self):
        """
        Updates colorbar label for correlation plots.
        
        Checks the current correlation method and updates the colorbar label accordingly.
        If the method has changed, it updates the color limits and colormap based on whether the correlation is squared or not.
        Also ensures that the plot type is set to 'correlation'.
        """
        method = self.dock.ui.app_data.corr_method
        if self.dock.ui.style_data.clabel == method:
            return

        if self.dock.ui.app_data.corr_squared:
            power = '^2'
        else:
            power = ''

        # update colorbar label for change in method
        match method:
            case 'Pearson':
                self.dock.ui.style_data.clabel = method + "'s $r" + power + "$"
            case 'Spearman':
                self.dock.ui.style_data.clabel = method + "'s $\\rho" + power + "$"
            case 'Kendall':
                self.dock.ui.style_data.clabel = method + "'s $\\tau" + power + "$"

        if self.dock.ui.style_data.plot_type != 'correlation':
            self.dock.ui.style_data.plot_type = 'correlation'

        # trigger update to plot
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "correlation":
            self.dock.ui.schedule_update()

    def correlation_squared_callback(self):
        """
        Produces a plot of the squared correlation.
        
        Updates the color limits and colormap based on whether the correlation is squared or not.
        Also updates the colorbar label based on the current correlation method.
        """
        # update color limits and colorbar
        if self.dock.ui.app_data.corr_squared:
            self.dock.ui.style_data.clim = [0,1]
            self.dock.ui.style_data.cmap = 'cmc.oslo'
        else:
            self.dock.ui.style_data.clim = [-1,1]
            self.dock.ui.style_data.cmap = 'RdBu'

        # update label
        self.correlation_method_callback()

        # trigger update to plot
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['sample'] and self.dock.ui.style_data.plot_type == "correlation":
            self.dock.ui.schedule_update()
    
@auto_log_methods(logger_key="Plot")
class ScatterUI(CustomPage):
    def __init__(self, dock):
        super().__init__(obj_name="ScatterPage", parent=dock)
        self.logger_key = "Plot"
        self.dock = dock

        self._heatmap_options = ['counts','median','median, MAD','MAD','mean','mean, std','std']
        self.setupUI()

        self.comboBoxScatterPreset.clear()
        self.comboBoxScatterPreset.addItems(list(self.dock.ui.app_data.scatter_preset_dict.keys()))
        self.comboBoxScatterPreset.setPlaceholderText("Select predefined plot...")

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()


    def setupUI(self):

        # scatter group map
        scatter_group_box = QGroupBox(self)
        scatter_group_box.setObjectName("groupBoxScatter")
        scatter_group_box.setTitle("Biplot and Ternary")

        scatter_form_layout = QFormLayout(scatter_group_box)
        scatter_form_layout.setContentsMargins(6, 6, 6, 6)

        preset_layout = QHBoxLayout(scatter_group_box)

        self.comboBoxScatterPreset = QComboBox(parent=scatter_group_box)
        self.comboBoxScatterPreset.setObjectName("comboBoxScatterPreset")

        self.toolButtonScatterSavePreset = CustomToolButton(
            text="Save Preset",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=scatter_group_box
        )
        self.toolButtonScatterSavePreset.setObjectName("toolButtonScatterSaveFields")

        preset_layout.addWidget(self.comboBoxScatterPreset)
        preset_layout.addWidget(self.toolButtonScatterSavePreset)
        scatter_form_layout.addRow("Preset", preset_layout)

        self.comboBoxHeatmaps = QComboBox(parent=scatter_group_box)
        self.comboBoxHeatmaps.setObjectName("comboBoxHeatmaps")
        scatter_form_layout.addRow("Heatmaps", self.comboBoxHeatmaps)

        self.addWidget(scatter_group_box)

        # ternary map group
        ternary_map_group_box = QGroupBox(self)
        ternary_map_group_box.setObjectName("ternary_map_group_box")
        ternary_map_group_box.setTitle("Ternary Map")

        ternary_map_form_layout = QFormLayout(ternary_map_group_box)
        ternary_map_form_layout.setContentsMargins(6, 6, 6, 6)

        self.comboBoxTernaryColormap = QComboBox(parent=ternary_map_group_box)
        self.comboBoxTernaryColormap.setObjectName("comboBoxTernaryColormap")
        ternary_map_form_layout.addRow("Colormap", self.comboBoxTernaryColormap)

        ternary_swatches_layout = QHBoxLayout(ternary_map_group_box)
        ternary_swatches_layout.setContentsMargins(0, 0, 0, 0)
        ternary_swatches_layout.setSpacing(2)

        self.colorButtonTCmapXColor = ColorButton(
            permanent_text="X",
            parent=ternary_map_group_box,
            ui = self,
        )
        #self.colorButtonTCmapXColor.setMaximumSize(QSize(18, 18))
        self.colorButtonTCmapXColor.setObjectName("colorButtonTCmapXColor")

        self.colorButtonTCmapYColor = ColorButton(
            permanent_text="Y",
            parent=ternary_map_group_box,
            ui = self,
        )
        #self.colorButtonTCmapYColor.setMaximumSize(QSize(18, 18))
        self.colorButtonTCmapYColor.setObjectName("colorButtonTCmapYColor")

        self.colorButtonTCmapZColor = ColorButton(
            permanent_text="Z",
            parent=ternary_map_group_box,
            ui = self,
        )
        #self.colorButtonTCmapZColor.setMaximumSize(QSize(18, 18))
        self.colorButtonTCmapZColor.setObjectName("colorButtonTCmapZColor")

        self.colorButtonTCmapMColor = ColorButton(
            permanent_text="M",
            parent=ternary_map_group_box,
            ui = self,
        )
        #self.colorButtonTCmapMColor.setMaximumSize(QSize(18, 18))
        self.colorButtonTCmapMColor.setObjectName("colorButtonTCmapMColor")

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolButtonSaveTernaryColormap = CustomToolButton(
            text="Save",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=ternary_map_group_box,
        )
        self.toolButtonSaveTernaryColormap.setObjectName("toolButtonSaveTernaryColormap")
        self.toolButtonSaveTernaryColormap.setToolTip("Save colors to create a custom ternary colormap")

        self.toolButtonTernaryMap = CustomToolButton(
            text="Create Map",
            light_icon_unchecked="icon-illuminati-64.svg",
            parent=ternary_map_group_box,
        )
        self.toolButtonTernaryMap.setObjectName("toolButtonTernaryMap")
        self.toolButtonTernaryMap.setToolTip("Create map from ternary coordinates")

        ternary_swatches_layout.addWidget(self.colorButtonTCmapXColor)
        ternary_swatches_layout.addWidget(self.colorButtonTCmapYColor)
        ternary_swatches_layout.addWidget(self.colorButtonTCmapZColor)
        ternary_swatches_layout.addWidget(self.colorButtonTCmapMColor)
        ternary_swatches_layout.addItem(spacer)
        ternary_swatches_layout.addWidget(self.toolButtonSaveTernaryColormap)


        ternary_map_form_layout.addRow("Colors", ternary_swatches_layout)
        ternary_map_form_layout.addRow("Ternary map", self.toolButtonTernaryMap)

        self.addWidget(ternary_map_group_box)
        scatter_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.addItem(scatter_spacer)

        # add the page to the toolbox
        scatter_icon = QIcon(str(ICONPATH / "icon-ternary-64.svg"))
        page_name = "Scatter and Heatmaps" 

        self.dock.toolbox.addItem(self, scatter_icon, page_name)

        self.dock.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-ternary-64.svg",
            dark_icon = ICONPATH / "icon-ternary-dark-64.svg"
        )

    def connect_widgets(self):
        """Connects scatter and heatmap widgets to methods."""
        self.comboBoxHeatmaps.clear()
        self.comboBoxHeatmaps.addItems(self._heatmap_options)
        self.comboBoxHeatmaps.activated.connect(self.update_heatmap_style_combobox)

        self.toolButtonScatterSavePreset.clicked.connect(self.save_scatter_preset)

        self.comboBoxTernaryColormap.clear()
        self.comboBoxTernaryColormap.addItems(self.dock.ui.app_data.color_schemes)
        self.comboBoxTernaryColormap.addItem('user defined')
        self.comboBoxTernaryColormap.setCurrentIndex(0)

        # dialog for adding and saving new colormaps
        self.toolButtonSaveTernaryColormap.clicked.connect(self.input_ternary_name_dlg)

        self.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())

        self.ternary_colormap_changed()


    def connect_observer(self):
        """Connects properties to observer functions."""
        self.dock.ui.app_data.add_observer("scatter_preset", self.update_scatter_preset_combobox)
        self.dock.ui.app_data.add_observer("heatmap_style", self.update_heatmap_style_combobox)

        # ternary maps
        self.dock.ui.app_data.add_observer("ternary_colormap", self.update_ternary_colormap)
        self.dock.ui.app_data.add_observer("ternary_color_x", self.update_ternary_color_x)
        self.dock.ui.app_data.add_observer("ternary_color_y", self.update_ternary_color_y)
        self.dock.ui.app_data.add_observer("ternary_color_z", self.update_ternary_color_z)
        self.dock.ui.app_data.add_observer("ternary_color_m", self.update_ternary_color_m)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxScatterPreset.activated.connect(lambda: log(f"comboBoxScatterPreset value=[{self.comboBoxScatterPreset.currentText()}]", prefix="UI"))
        self.toolButtonScatterSavePreset.clicked.connect(lambda: log("toolButtonScatterSavePreset", prefix="UI"))

        # ternary colormap
        self.comboBoxTernaryColormap.activated.connect(lambda: log(f"comboBoxTernaryColormap value=[{self.comboBoxTernaryColormap.currentText()}]", prefix="UI"))
        self.colorButtonTCmapXColor.clicked.connect(lambda: log("colorButtonTCmapXColor", prefix="UI"))
        self.colorButtonTCmapYColor.clicked.connect(lambda: log("colorButtonTCmapYColor", prefix="UI"))
        self.colorButtonTCmapZColor.clicked.connect(lambda: log("colorButtonTCmapZColor", prefix="UI"))
        self.colorButtonTCmapMColor.clicked.connect(lambda: log("colorButtonTCmapMColor", prefix="UI"))
        self.toolButtonSaveTernaryColormap.clicked.connect(lambda: log("toolButtonSaveTernaryColormap", prefix="UI"))
        self.toolButtonTernaryMap.clicked.connect(lambda: log("toolButtonTernaryMap", prefix="UI"))

        self.comboBoxHeatmaps.activated.connect(lambda: log(f"comboBoxHeatmaps value=[{self.comboBoxHeatmaps.currentText()}]", prefix="UI"))

    def save_scatter_preset(self):
        """
        Saves the current scatter fields to a file.

        This method prompts the user for a name for the new list, saves the current NDim list to the
        application's data dictionary, and exports the dictionary to a CSV file.

        If the user cancels the input dialog or an error occurs during saving, a warning message is displayed.
        """
        # get the list name from the user
        name, ok = QInputDialog.getText(self.dock.ui, 'Save custom scatter preset', 'Enter name for new plot:')
        if ok:
            try:
                self.dock.ui.app_data.scatter_preset_dict[name] = [
                    self.dock.toolbox.comboBoxFieldX.currentText(),
                    self.dock.toolbox.comboBoxFieldY.currentText(),
                    self.dock.toolbox.comboBoxFieldZ.currentText(),
                    self.dock.toolbox.comboBoxFieldC.currentText(),
                ]

                # export the csv
                csvdict.export_dict_to_csv(self.dock.ui.app_data.scatter_preset_dict, self.dock.ui.app_data.scatter_list_filename)
            except:
                QMessageBox.warning(self.dock.ui,'Error','could not save scatter presets to file.')
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.dock.ui,'Error','could not save scatter preset fields.')

            return

    def update_scatter_preset_combobox(self, new_scatter_preset):
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()

    def update_heatmap_style_combobox(self, new_heatmap_style):
        self.comboBoxHeatmaps.setCurrentText(new_heatmap_style)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()

    def input_ternary_name_dlg(self):
        """Opens a dialog to save new colormap

        Executes on ``MainWindow.toolButtonSaveTernaryColormap`` is clicked.  Saves the current
        colors of `MainWindow.colorButtonTCmap*Color` into
        `resources/styles/ternary_colormaps_new.csv`.
        """
        name, ok = QInputDialog.getText(self.dock.ui, 'Custom ternary colormap', 'Enter new colormap name:')
        if ok:
            # update colormap structure
            self.dock.ui.app_data.ternary_colormaps.append({'scheme': name,
                    'top': get_hex_color(self.colorButtonTCmapXColor.palette().button().color()),
                    'left': get_hex_color(self.colorButtonTCmapYColor.palette().button().color()),
                    'right': get_hex_color(self.colorButtonTCmapZColor.palette().button().color()),
                    'center': get_hex_color(self.colorButtonTCmapMColor.palette().button().color())})
            # update comboBox
            self.comboBoxTernaryColormap.addItem(name)
            self.comboBoxTernaryColormap.setCurrentText(name)
            # add new row to file
            df = pd.DataFrame.from_dict(self.dock.ui.app_data.ternary_colormaps)
            try:
                df.to_csv('resources/styles/ternary_colormaps_new.csv', index=False)
            except Exception as e:
                QMessageBox.warning(self.dock.ui,'Error',f"Could not save style theme.\nError: {e}")

        else:
            QMessageBox.warning(self.dock.ui,'Warning',f"Style theme not saved.\n")
            return


    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        for cmap in self.dock.ui.app_data.ternary_colormaps:
            if cmap['scheme'] == self.comboBoxTernaryColormap.currentText():
                self.colorButtonTCmapXColor.setStyleSheet("background-color: %s;" % cmap['top'])
                self.colorButtonTCmapYColor.setStyleSheet("background-color: %s;" % cmap['left'])
                self.colorButtonTCmapZColor.setStyleSheet("background-color: %s;" % cmap['right'])
                self.colorButtonTCmapMColor.setStyleSheet("background-color: %s;" % cmap['center'])

    def update_ternary_colormap(self, new_colormap=None):
        """Updates ternary colormap used to make ternary maps.

        Updates the colors for the vertices and centroid of a ternary colormap
        that is used to produce a map-style image colored by pixel locations
        within a ternary diagram.

        Parameters
        ----------
        new_colormap : str, optional
            New color map name, by default None
        """
        if new_colormap is None:
             # use current value of widget
             self.ternary_colormap = self.comboBoxTernaryColormap.currentText()
        else:
             # update combobox with new value
             if self.comboBoxTernaryColormap.currentText() == new_colormap:
                 return
             # block signals to prevent infinite loop
             self.comboBoxTernaryColormap.blockSignals(True)
             self.comboBoxTernaryColormap.setCurrentText(new_colormap)
             self.comboBoxTernaryColormap.blockSignals(False)
        
        # update plot if required
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter'] and self.dock.ui.style_data.plot_type == 'ternary map':
            self.dock.ui.schedule_update()

    def update_ternary_color_x(self, new_color):
        self.colorButtonTCmapXColor.setStyleSheet("background-color: %s;" % new_color)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()

    def update_ternary_color_y(self, new_color):
        self.colorButtonTCmapYColor.setStyleSheet("background-color: %s;" % new_color)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()

    def update_ternary_color_z(self, new_color):
        self.colorButtonTCmapZColor.setStyleSheet("background-color: %s;" % new_color)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()

    def update_ternary_color_m(self, new_color):
        self.colorButtonTCmapMColor.setStyleSheet("background-color: %s;" % new_color)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['scatter']:
            self.dock.ui.schedule_update()



@auto_log_methods(logger_key="Plot")
class NDimUI(CustomPage):
    def __init__(self, dock):
        super().__init__("NDimPage", parent=dock)
        self.dock = dock
        self.logger_key = "Plot"

        self.table_fcn = TableFcn(self)

        self.setupUI()

        # setup comboBoxNDIM
        self.comboBoxNDimAnalyteSet.clear()
        self.comboBoxNDimAnalyteSet.addItems(list(self.dock.ui.app_data.ndim_list_dict.keys()))
        self.comboBoxNDimAnalyteSet.setPlaceholderText("Select preset list...")

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self):

        group_box = QGroupBox(parent=self)
        group_box.setTitle("")
        group_box.setObjectName("groupBoxNDim")

        group_box_layout = QVBoxLayout(group_box)
        group_box_layout.setContentsMargins(6, 6, 6, 6)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(2)

        horizontal_analyte_layout = QHBoxLayout()
        horizontal_analyte_layout.setContentsMargins(0, 0, 0, 0)

        self.comboBoxNDimAnalyte = CustomComboBox(parent=group_box)
        self.comboBoxNDimAnalyte.setObjectName("comboBoxNDimAnalyte")

        self.toolButtonNDimAnalyteAdd = CustomToolButton(
            text="Add",
            light_icon_unchecked="icon-accept-64.svg",
            parent=group_box,
        )
        self.toolButtonNDimAnalyteAdd.setObjectName("toolButtonNDimAnalyteAdd")
        self.toolButtonNDimAnalyteAdd.setToolTip("Add analyte to plot")

        analyte_spacer = QSpacerItem(60, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        horizontal_analyte_layout.addWidget(self.comboBoxNDimAnalyte)
        horizontal_analyte_layout.addItem(analyte_spacer)
        horizontal_analyte_layout.addWidget(self.toolButtonNDimAnalyteAdd)
        form_layout.addRow("Analyte", horizontal_analyte_layout)

        horizontal_list_layout = QHBoxLayout()

        self.comboBoxNDimAnalyteSet = QComboBox(parent=group_box)
        self.comboBoxNDimAnalyteSet.setObjectName("comboBoxNDimAnalyteSet")

        self.toolButtonNDimAnalyteSetAdd = CustomToolButton(
            text="Add List",
            light_icon_unchecked="icon-add-list-64.svg",
            dark_icon_unchecked="icon-add-list-dark-64.svg",
            parent=group_box,
        )
        self.toolButtonNDimAnalyteSetAdd.setObjectName("toolButtonNDimAnalyteSetAdd")
        self.toolButtonNDimAnalyteSetAdd.setToolTip("Add set of analytes to plot")

        predefined_spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        horizontal_list_layout.addWidget(self.comboBoxNDimAnalyteSet)
        horizontal_list_layout.addItem(predefined_spacer)
        horizontal_list_layout.addWidget(self.toolButtonNDimAnalyteSetAdd)
        form_layout.addRow("Predefined", horizontal_list_layout)

        self.comboBoxNDimQuantiles = QComboBox(parent=group_box)
        self.comboBoxNDimQuantiles.setObjectName("comboBoxNDimQuantiles")
        form_layout.addRow("Quantiles", self.comboBoxNDimQuantiles)

        group_box_layout.addLayout(form_layout)

        table_layout = QHBoxLayout()
        self.tableWidgetNDim = CustomTableWidget()
        self.tableWidgetNDim.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetNDim.setObjectName("tableWidgetNDim")
        self.tableWidgetNDim.setColumnCount(2)
        self.tableWidgetNDim.setRowCount(0)
        item = QTableWidgetItem()
        self.tableWidgetNDim.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self.tableWidgetNDim.setHorizontalHeaderItem(1, item)
        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        if header:
            header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)

        table_tools_layout = QVBoxLayout()

        self.toolButtonNDimSelectAll = CustomToolButton(
            text="Select All",
            light_icon_unchecked="icon-select-all-64.svg",
            dark_icon_unchecked="icon-select-all-dark-64.svg",
            parent=group_box
        )
        self.toolButtonNDimSelectAll.setObjectName("toolButtonNDimSelectAll")
        self.toolButtonNDimSelectAll.setToolTip("Select all fields in table")

        self.toolButtonNDimUp = CustomToolButton(
            text="Up",
            light_icon_unchecked="icon-up-arrow-64.svg",
            dark_icon_unchecked="icon-up-arrow-dark-64.svg",
            parent=group_box
        )
        self.toolButtonNDimUp.setObjectName("toolButtonNDimUp")
        self.toolButtonNDimUp.setToolTip("Move selected field up")

        self.toolButtonNDimDown = CustomToolButton(
            text="Down",
            light_icon_unchecked="icon-down-arrow-64.svg",
            dark_icon_unchecked="icon-down-arrow-dark-64.svg",
            parent=group_box
        )
        self.toolButtonNDimDown.setObjectName("toolButtonNDimDown")
        self.toolButtonNDimDown.setToolTip("Move selected field down")

        self.toolButtonNDimSaveList = CustomToolButton(
            text="Save List",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=group_box
        )
        self.toolButtonNDimSaveList.setObjectName("toolButtonNDimSaveList")
        self.toolButtonNDimSaveList.setToolTip("Save List")

        self.toolButtonNDimRemove = CustomToolButton(
            text="Remove",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=group_box
        )
        self.toolButtonNDimRemove.setObjectName("toolButtonNDimRemove")
        self.toolButtonNDimRemove.setToolTip("Remove selected fields")

        table_tools_layout.addWidget(self.toolButtonNDimSelectAll)
        table_tools_layout.addWidget(self.toolButtonNDimUp)
        table_tools_layout.addWidget(self.toolButtonNDimDown)
        table_tools_layout.addWidget(self.toolButtonNDimSaveList)
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        table_tools_layout.addItem(spacer)
        table_tools_layout.addWidget(self.toolButtonNDimRemove)

        table_layout.addWidget(self.tableWidgetNDim)
        table_layout.addLayout(table_tools_layout)

        group_box_layout.addLayout(table_layout)
        self.addWidget(group_box)

        spacer_end = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.addItem(spacer_end)
        

        # add the page to the toolbox
        ndim_icon = QIcon(str(ICONPATH / "icon-TEC-64.svg"))
        page_name = "n-Dimensional" 

        self.dock.toolbox.addItem(self, ndim_icon, page_name)

        self.dock.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-TEC-64.svg",
            dark_icon = ICONPATH / "icon-TEC-dark-64.svg"
        )

    def connect_widgets(self):
        """Connects n-dimensional widgets to methods."""
        self.comboBoxNDimQuantiles.setCurrentIndex(self.dock.ui.app_data.ndim_quantile_index)
        self.comboBoxNDimQuantiles.activated.connect(lambda _: self.update_ndim_quantile_index())
        
        self.toolButtonNDimAnalyteAdd.clicked.connect(lambda _: self.update_ndim_table('analyteAdd'))
        self.toolButtonNDimAnalyteAdd.clicked.connect(self.dock.ui.schedule_update)

        self.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda _ : self.update_ndim_table('analyteSetAdd'))
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(self.dock.ui.schedule_update)

        self.toolButtonNDimUp.clicked.connect(lambda _: self.table_fcn.move_row_up(self.tableWidgetNDim))
        self.toolButtonNDimUp.clicked.connect(self.dock.ui.schedule_update)

        self.toolButtonNDimDown.clicked.connect(lambda _: self.table_fcn.move_row_down(self.tableWidgetNDim))
        self.toolButtonNDimDown.clicked.connect(self.dock.ui.schedule_update)

        self.toolButtonNDimRemove.clicked.connect(lambda _: self.table_fcn.delete_row(self.tableWidgetNDim))
        self.toolButtonNDimRemove.clicked.connect(self.dock.ui.schedule_update)

        self.toolButtonNDimSelectAll.clicked.connect(lambda _: self.tableWidgetNDim.selectAll())
        self.toolButtonNDimSaveList.clicked.connect(lambda _: self.save_ndim_list())

        

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.dock.ui.app_data.add_observer("ndim_analyte_set", self.update_ndim_analyte_set)
        self.dock.ui.app_data.add_observer("ndim_quantile_index", self.update_ndim_quantile_index)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxNDimAnalyte.activated.connect(lambda: log(f"comboBoxNDimAnalyte value=[{self.comboBoxNDimAnalyte.currentText()}]", prefix="UI"))
        self.toolButtonNDimAnalyteAdd.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.comboBoxNDimAnalyteSet.activated.connect(lambda: log(f"comboBoxNDimAnalyteSet value=[{self.comboBoxNDimAnalyteSet.currentText()}]", prefix="UI"))
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.comboBoxNDimQuantiles.activated.connect(lambda: log(f"comboBoxNDimQuantiles value=[{self.comboBoxNDimQuantiles.currentText()}]", prefix="UI"))
        self.toolButtonNDimSelectAll.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.toolButtonNDimUp.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.toolButtonNDimDown.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.toolButtonNDimSaveList.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.toolButtonNDimRemove.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))

    def update_ndim_analyte_set(self, new_ndim_analyte_set):

        self.comboBoxNDimAnalyteSet.setCurrentText(new_ndim_analyte_set)
        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['ndim']:
            self.dock.ui.schedule_update()

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
            self.dock.ui.app_data.current_data.filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.comboBoxNDimAnalyte.currentText().lower()]
            self.comboBoxNDimAnalyteSet.setCurrentText('user defined')
        elif calling_widget == 'analyteSetAdd':
            el_list = self.dock.ui.app_data.ndim_list_dict[self.comboBoxNDimAnalyteSet.currentText()]

        analytes_list = self.dock.ui.app_data.current_data.processed_data.match_attribute('data_type','Analyte')

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.dock.ui.app_data.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.CheckState.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            self.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetNDim.setItem(row, 1, QTableWidgetItem(analyte))
    
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
            self.dock.ui.app_data.ndim_quantile_index = self.comboBoxNDimQuantiles.currentIndex()
        else:
            self.comboBoxNDimQuantiles.blockSignals(True)
            self.comboBoxNDimQuantiles.setCurrentIndex(new_index)
            self.comboBoxNDimQuantiles.blockSignals(False)

        if self.dock.toolbox.currentIndex() == self.dock.tab_dict['ndim']:
            self.dock.ui.schedule_update()

    def save_ndim_list(self):
        """
        Saves the current NDim list to a file.

        This method prompts the user for a name for the new list, saves the current NDim list to the
        application's data dictionary, and exports the dictionary to a CSV file.

        If the user cancels the input dialog or an error occurs during saving, a warning message is displayed.
        """
        # get the list name from the user
        name, ok = QInputDialog.getText(self.dock.ui, 'Save custom TEC list', 'Enter name for new list:')
        if ok:
            try:
                self.dock.ui.app_data.ndim_list_dict[name] = self.tableWidgetNDim.column_to_list('Analyte')

                # export the csv
                csvdict.export_dict_to_csv(self.dock.ui.app_data.ndim_list_dict, self.dock.ui.app_data.ndim_list_filename)
            except:
                QMessageBox.warning(self.dock.ui,'Error','could not save TEC file.')
                
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.dock.ui,'Error','could not save TEC list.')

            return