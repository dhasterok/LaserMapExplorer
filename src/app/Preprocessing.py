import numpy as np
from PyQt6.QtCore import ( Qt, QRect, QSize )
from PyQt6.QtWidgets import ( 
    QCheckBox, QTableWidgetItem, QMessageBox, QInputDialog, QGroupBox, QFormLayout, QVBoxLayout,
    QHBoxLayout, QAbstractSpinBox, QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QWidget, QScrollArea,
    QFrame, QToolButton, QSpacerItem, QSizePolicy, QAbstractItemView, QHeaderView
)
from PyQt6.QtGui import ( QIcon )
from src.common.Logger import log, auto_log_methods
from src.common.CustomWidgets import CustomPage, CustomLineEdit, CustomToolButton
from src.app.config import ICONPATH

@auto_log_methods(logger_key="Data")
class PreprocessingUI(CustomPage):
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
    def __init__(self, dock):
        super().__init__(obj_name="PreprocessPage", parent=dock)

        self.dock = dock 
        
        self.setupUI()
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self):
        # Coordinate group box
        self.groupBoxCoordinates = QGroupBox(parent=self)
        self.groupBoxCoordinates.setTitle("Sample dimensions")
        self.groupBoxCoordinates.setObjectName("groupBoxSampleOptions")

        form_layout_coordinates = QFormLayout(self.groupBoxCoordinates)
        form_layout_coordinates.setContentsMargins(3, 3, 3, 3)

        widget_resolution_label = QWidget(parent=self.groupBoxCoordinates)
        layout_resolution_label = QHBoxLayout()
        layout_resolution_label.setContentsMargins(3, 3, 3, 3)
        widget_resolution_label.setLayout(layout_resolution_label)

        self.labelSampleResolution = QLabel(parent=self.groupBoxCoordinates)
        self.labelSampleResolution.setObjectName("labelSampleResolution")
        self.labelSampleResolution.setText("Resolution")

        self.toolButtonResolutionReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self.groupBoxCoordinates)
        self.toolButtonResolutionReset.setEnabled(False)
        self.toolButtonResolutionReset.setObjectName("toolButtonResolutionReset")
        self.toolButtonResolutionReset.setText("Reset")
        self.toolButtonResolutionReset.setToolTip("Reset map resolution, to reset to original cropped resolution, use full map instead")

        layout_resolution_label.addWidget(self.labelSampleResolution)
        layout_resolution_label.addWidget(self.toolButtonResolutionReset)

        widget_resolution = QWidget(self.groupBoxCoordinates)
        layout_resolution = QHBoxLayout(widget_resolution)
        layout_resolution.setContentsMargins(3, 3, 3, 3)
        widget_resolution.setLayout(layout_resolution)

        self.labelResolutionNx = QLabel(parent=self.groupBoxCoordinates)
        self.labelResolutionNx.setObjectName("labelResolutionNx")
        self.labelResolutionNx.setText("Nx:")

        self.lineEditResolutionNx = CustomLineEdit(parent=self.groupBoxCoordinates)
        self.lineEditResolutionNx.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditResolutionNx.setReadOnly(True)
        self.lineEditResolutionNx.setObjectName("lineEditResolutionNx")
        self.lineEditResolutionNx.setToolTip("Number of pixels in X-direction")

        self.labelResolutionNy = QLabel(parent=self.groupBoxCoordinates)
        self.labelResolutionNy.setObjectName("labelResolutionNy")
        self.labelResolutionNy.setText("Ny:")

        self.lineEditResolutionNy = CustomLineEdit(parent=self.groupBoxCoordinates)
        self.lineEditResolutionNy.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditResolutionNy.setReadOnly(True)
        self.lineEditResolutionNy.setObjectName("lineEditResolutionNy")
        self.lineEditResolutionNx.setToolTip("Number of pixels in Y-direction")

        layout_resolution.addWidget(self.labelResolutionNx)
        layout_resolution.addWidget(self.lineEditResolutionNx)
        layout_resolution.addWidget(self.labelResolutionNy)
        layout_resolution.addWidget(self.lineEditResolutionNy)

        form_layout_coordinates.addRow(widget_resolution_label, widget_resolution)

        widget_dimension_label = QWidget(parent=self.groupBoxCoordinates)
        layout_dimension_label = QHBoxLayout()
        layout_dimension_label.setContentsMargins(3, 3, 3, 3)
        widget_dimension_label.setLayout(layout_dimension_label)

        self.labelPixelResolution = QLabel(parent=self.groupBoxCoordinates)
        self.labelPixelResolution.setText("Dimensions")
        self.labelPixelResolution.setObjectName("labelPixelResolution")

        self.toolButtonPixelResolutionReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self.groupBoxCoordinates
        )
        self.toolButtonPixelResolutionReset.setObjectName("toolButtonPixelResolutionReset")
        self.toolButtonPixelResolutionReset.setToolTip("Reset pixel dimensions")
        
        layout_dimension_label.addWidget(self.labelPixelResolution)
        layout_dimension_label.addWidget(self.toolButtonPixelResolutionReset)

        widget_dimension = QWidget(self.groupBoxCoordinates)
        layout_dimension = QHBoxLayout()
        layout_dimension.setContentsMargins(3, 3, 3, 3)
        widget_dimension.setLayout(layout_dimension)

        self.labelDX = QLabel(parent=self.groupBoxCoordinates)
        self.labelDX.setText("dX:")

        self.lineEditDX = CustomLineEdit(parent=self.groupBoxCoordinates)
        self.lineEditDX.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDX.setObjectName("lineEditDX")
        self.lineEditDX.setToolTip("Pixel width")

        self.toolButtonSwapResolution = CustomToolButton(
            text="Swap",
            light_icon_unchecked="icon-swap-resolution-64.svg",
            dark_icon_unchecked="icon-swap-resolution-dark-64.svg",
            parent=self.groupBoxCoordinates
        )
        self.toolButtonSwapResolution.setObjectName("toolButtonSwapResolution")
        self.toolButtonSwapResolution.setToolTip("Swap X and Y resolution")
        
        self.labelDY = QLabel(parent=self.groupBoxCoordinates)
        self.labelDY.setText("dY:")

        self.lineEditDY = CustomLineEdit(parent=self.groupBoxCoordinates)
        self.lineEditDY.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDY.setObjectName("lineEditDY")
        self.lineEditDY.setToolTip("Pixel height")

        layout_dimension.addWidget(self.labelDX)
        layout_dimension.addWidget(self.lineEditDX)
        layout_dimension.addWidget(self.toolButtonSwapResolution)
        layout_dimension.addWidget(self.labelDY)
        layout_dimension.addWidget(self.lineEditDY)

        form_layout_coordinates.addRow(widget_dimension_label, widget_dimension)

        # Small histogram widget
        self.widgetHistView = QWidget(parent=self)
        self.widgetHistView.setMinimumSize(QSize(0, 150))
        self.widgetHistView.setAutoFillBackground(False)
        self.widgetHistView.setObjectName("widgetHistView")

        layout_histogram_view = QVBoxLayout()
        layout_histogram_view.setSpacing(0)
        layout_histogram_view.setContentsMargins(0, 0, 0, 0)
        self.widgetHistView.setLayout(layout_histogram_view)

        self.checkBoxShowHistCmap = QCheckBox(parent=self)
        self.checkBoxShowHistCmap.setText("Show with colormap")
        self.checkBoxShowHistCmap.setChecked(True)
        self.checkBoxShowHistCmap.setObjectName("checkBoxShowHistCmap")


        # Autoscale group box
        self.groupBoxAutoscale = QGroupBox(parent=self)
        self.groupBoxAutoscale.setObjectName("groupBoxAutoscale")
        self.groupBoxAutoscale.setTitle("Outliers and negatives")

        layout_autoscale = QVBoxLayout(self.groupBoxAutoscale)
        layout_autoscale.setContentsMargins(6, 6, 6, 6)

        layout_buttons = QHBoxLayout()
        layout_buttons.setObjectName("horizontalLayout_61")
        
        self.toolButtonAutoScale = CustomToolButton(
            text="Autoscale",
            light_icon_unchecked="icon-autoscale-64.svg",
            parent=self.groupBoxAutoscale
        )
        self.toolButtonAutoScale.setCheckable(True)
        self.toolButtonAutoScale.setChecked(True)
        self.toolButtonAutoScale.setObjectName("toolButtonAutoScale")
        self.toolButtonAutoScale.setToolTip("Autoscale data")

        self.toolButtonScaleEqualize = CustomToolButton(
            text="Equalize Scale",
            light_icon_unchecked="icon-histeq-64.svg",
            dark_icon_unchecked="icon-histeq-dark-64.svg",
            parent=self.groupBoxAutoscale,
        )
        self.toolButtonScaleEqualize.setCheckable(True)
        self.toolButtonScaleEqualize.setObjectName("toolButtonScaleEqualize")
        self.toolButtonScaleEqualize.setToolTip("Equalize colormap to histogram")

        button_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.checkBoxApplyAll = QCheckBox(parent=self.groupBoxAutoscale)
        self.checkBoxApplyAll.setText("Apply All")
        self.checkBoxApplyAll.setObjectName("checkBoxApplyAll")

        self.toolButtonOutlierReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self.groupBoxAutoscale,
        )
        self.toolButtonOutlierReset.setObjectName("toolButtonOutlierReset")
        self.toolButtonOutlierReset.setToolTip("Reset autoscaling and outlier handling")

        layout_buttons.addWidget(self.toolButtonAutoScale)
        layout_buttons.addWidget(self.toolButtonScaleEqualize)
        layout_buttons.addItem(button_spacer)
        layout_buttons.addWidget(self.checkBoxApplyAll)
        layout_buttons.addWidget(self.toolButtonOutlierReset)

        layout_autoscale.addLayout(layout_buttons)

        form_layout_autoscale = QFormLayout()

        self.comboBoxOutlierMethod = QComboBox(parent=self.groupBoxAutoscale)
        self.comboBoxOutlierMethod.setObjectName("comboBoxOutlierMethod")
        self.comboBoxOutlierMethod.setToolTip("Select method for removing outliers from analyte and ratio data")
        self.comboBoxOutlierMethod.setMaximumWidth(150)
        form_layout_autoscale.addRow("Outlier Method", self.comboBoxOutlierMethod)

        self.comboBoxNegativeMethod = QComboBox(parent=self.groupBoxAutoscale)
        self.comboBoxNegativeMethod.setObjectName("comboBoxNegativeMethod")
        self.comboBoxNegativeMethod.setToolTip("Select method to handle negative values")
        self.comboBoxNegativeMethod.setMaximumWidth(150)
        form_layout_autoscale.addRow("Negative handling", self.comboBoxNegativeMethod)

        layout_quantiles = QHBoxLayout()

        self.lineEditLowerQuantile = CustomLineEdit(parent=self.groupBoxAutoscale)
        self.lineEditLowerQuantile.setMaximumSize(QSize(75, 16777215))
        self.lineEditLowerQuantile.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditLowerQuantile.setObjectName("lineEditLowerQuantile")

        self.lineEditUpperQuantile = CustomLineEdit(parent=self.groupBoxAutoscale)
        self.lineEditUpperQuantile.setMaximumSize(QSize(75, 16777215))
        self.lineEditUpperQuantile.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditUpperQuantile.setObjectName("lineEditUpperQuantile")

        layout_quantiles.addWidget(self.lineEditLowerQuantile)
        layout_quantiles.addWidget(self.lineEditUpperQuantile)

        form_layout_autoscale.addRow("Quantile bounds", layout_quantiles)

        layout_quantiles_diff = QHBoxLayout()

        self.lineEditDifferenceLowerQuantile = CustomLineEdit(parent=self.groupBoxAutoscale)
        self.lineEditDifferenceLowerQuantile.setMaximumSize(QSize(75, 16777215))
        self.lineEditDifferenceLowerQuantile.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDifferenceLowerQuantile.setObjectName("lineEditDifferenceLowerQuantile")

        self.lineEditDifferenceUpperQuantile = CustomLineEdit(parent=self.groupBoxAutoscale)
        self.lineEditDifferenceUpperQuantile.setMaximumSize(QSize(75, 16777215))
        self.lineEditDifferenceUpperQuantile.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDifferenceUpperQuantile.setObjectName("lineEditDifferenceUpperQuantile")

        layout_quantiles_diff.addWidget(self.lineEditDifferenceLowerQuantile)
        layout_quantiles_diff.addWidget(self.lineEditDifferenceUpperQuantile)

        form_layout_autoscale.addRow("Difference bound", layout_quantiles_diff)

        layout_autoscale.addLayout(form_layout_autoscale)

        preprocess_spacer = QSpacerItem(285, 132, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.addWidget(self.groupBoxCoordinates)
        self.addWidget(self.widgetHistView)
        self.addWidget(self.checkBoxShowHistCmap)
        self.addWidget(self.groupBoxAutoscale)
        self.addItem(preprocess_spacer)
        
        icon_preprocess = QIcon(str(ICONPATH / "icon-histogram-64.svg"))
        page_name = "Preprocess"
        self.dock.toolbox.addItem(self, icon_preprocess, page_name)

        self.dock.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-histogram-64.svg",
            dark_icon = ICONPATH / "icon-histogram-dark-64.svg"
        )

    def connect_widgets(self):
        self.lineEditDX.editingFinished.connect(lambda _: self.update_dimension('x'))
        self.lineEditDY.editingFinished.connect(lambda _: self.update_dimension('y'))
        self.lineEditResolutionNx.editingFinished.connect(lambda _: self.update_resolution('x'))
        self.lineEditResolutionNx.editingFinished.connect(lambda _: self.update_resolution('y'))

        self.toolButtonSwapResolution.clicked.connect(self.update_swap_resolution)
        self.toolButtonPixelResolutionReset.clicked.connect(self.reset_pixel_resolution)

        self.comboBoxOutlierMethod.addItems(self.dock.ui.app_data.outlier_methods)
        self.comboBoxOutlierMethod.setMaximumWidth(150)
        if 'Chauvenet criterion' in self.dock.ui.app_data.outlier_methods:
            self.comboBoxOutlierMethod.setCurrentText('Chauvenet criterion')
        self.comboBoxOutlierMethod.activated.connect(
            lambda: self.update_outlier_removal(self.comboBoxOutlierMethod.currentText())
        )

        self.comboBoxNegativeMethod.addItems(self.dock.ui.app_data.negative_methods)
        self.comboBoxNegativeMethod.activated.connect(
            lambda: self.update_neg_handling(self.comboBoxNegativeMethod.currentText())
        )

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.dock.ui.app_data.applyAutoscaleChanged.connect(lambda flag: self.update_autoscale_checkbox(flag))

    def connect_logger(self):
        """Connects widgets to logger."""
        self.lineEditResolutionNx.editingFinished.connect(lambda: log(f"lineEditResolutionNx value=[{self.lineEditResolutionNx.value}]", prefix="UI"))
        self.lineEditResolutionNy.editingFinished.connect(lambda: log(f"lineEditResolutionNy value=[{self.lineEditResolutionNy.value}]", prefix="UI"))
        self.toolButtonPixelResolutionReset.clicked.connect(lambda: log("toolButtonSwapResolution",prefix="UI"))
        self.lineEditDX.editingFinished.connect(lambda: log(f"lineEditDX, value=[{self.lineEditDX.value}]",prefix="UI"))
        self.lineEditDY.editingFinished.connect(lambda: log(f"lineEditDY, value=[{self.lineEditDY.value}]",prefix="UI"))
        self.toolButtonResolutionReset.clicked.connect(lambda: log("toolButtonsRolutionReset",prefix="UI"))
        self.toolButtonSwapResolution.clicked.connect(lambda: log("toolButtonSwapResolution",prefix="UI"))
        self.toolButtonAutoScale.clicked.connect(lambda: log(f"toolButtonAutoScale value=[{self.toolButtonAutoScale.isChecked()}]", prefix="UI"))
        self.toolButtonScaleEqualize.clicked.connect(lambda: log(f"toolButtonScaleEqualize value=[{self.toolButtonScaleEqualize.isChecked()}]", prefix="UI"))
        self.checkBoxShowHistCmap.checkStateChanged.connect(lambda: log(f"checkBoxShowHistCmap value=[{self.checkBoxShowHistCmap.isChecked()}]", prefix="UI"))
        self.checkBoxApplyAll.checkStateChanged.connect(lambda: log(f"checkBoxApplyAll value=[{self.checkBoxApplyAll.isChecked()}]", prefix="UI"))
        self.toolButtonOutlierReset.clicked.connect(lambda: log("toolButtonOutlierReset", prefix="UI"))
        self.comboBoxOutlierMethod.activated.connect(lambda: log(f"comboBoxOutlierMethod value=[{self.comboBoxOutlierMethod.currentText()}]", prefix="UI"))
        self.comboBoxNegativeMethod.activated.connect(lambda: log(f"comboBoxNegativeMethod value=[{self.comboBoxNegativeMethod.currentText()}]", prefix="UI"))
        self.lineEditLowerQuantile.editingFinished.connect(lambda: log(f"lineEditLowerQuantile value=[{self.lineEditLowerQuantile.value}]", prefix="UI"))
        self.lineEditUpperQuantile.editingFinished.connect(lambda: log(f"lineEditUpperQuantile value=[{self.lineEditUpperQuantile.value}]", prefix="UI"))
        self.lineEditDifferenceLowerQuantile.editingFinished.connect(lambda: log(f"lineEditDifferenceLowerQuantile value=[{self.lineEditDifferenceLowerQuantile.value}]", prefix="UI"))
        self.lineEditDifferenceUpperQuantile.editingFinished.connect(lambda: log(f"lineEditDifferenceUpperQuantile value=[{self.lineEditDifferenceUpperQuantile.value}]", prefix="UI"))

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
        data.pixelDimensionChanged.connect(lambda ax, value: self.update_dimension(ax, value))
        data.imageResolutionChanged.connect(lambda ax, value: self.update_resolution(ax, value))
        data.dataQuantileChanged.connect(lambda bound, value: self.update_data_quantile(bound, value))
        data.dataDiffQuantileChanged.connect(lambda bound, value: self.update_data_diff_quantile(bound, value))
        self.dock.ui.app_data.equalizeColorScaleChanged.connect(self.update_equalize_color_scale_toolbutton)
        data.autoscaleStateChanged.connect(lambda state: self.toggle_autoscale(state))
        data.applyOutlierAllChanged.connect(lambda state: self.update_apply_outlier_to_all(state))
        data.outlierMethodChanged.connect(lambda method: self.update_outlier_method(method))
        data.negativeMethodChanged.connect(lambda method: self.update_negative_handling_method(method))

    def update_equalize_color_scale_toolbutton(self, value):
        self.toolButtonScaleEqualize.setChecked(value)

        if self.dock.ui.style_data.plot_type == 'field map':
            # this needs to equalize the colorscale
            # right now it doesn't do anything
            pass
            self.dock.ui.schedule_update()

    def update_resolution(self, ax, value):
        """Updates ``lineEditResolutionNx`` and ``lineEditResolutionNy`` values

        Called as an update to ``app_data.n_x``.  Updates Nx and  Schedules a plot update.

        Parameters
        ----------
        ax : str
            Axis to update ('x' or 'y').
        value : str
            x dimension.
        """
        line_edit = getattr(self, f"lineEditResolutionN{ax}")
        setattr(line_edit, "value", value)
        if self.dock.ui.control_dock.toolbox.currentIndex() == self.dock.ui.control_dock.tab_dict['process']:
            self.dock.ui.schedule_update()

    def update_dimension(self, ax, value):
        """Updates ``lineEditDX`` and ``lineEditDY`` values

        Called as an update to ``app_data.dx``.  Updates dx and schedules a plot update.

        Parameters
        ----------
        ax : str
            Axis to update ('x' or 'y').
        value : str
            x dimension.
        """
        line_edit = getattr(self, f"lineEditD{ax.upper()}")
        setattr(line_edit, "value", value)
        if self.dock.toolbox.currentIndex() == self.dock.ui.control_dock.tab_dict['process']:
            self.dock.ui.schedule_update()
            field = f"{ax.upper()}c"
            if isinstance(self.dock.ui.plot_info, dict) \
                and 'field_type' in self.dock.ui.plot_info \
                and 'field' in self.dock.ui.plot_info:
                # update x axis limits in style_dict 
                self.dock.ui.style_data.initialize_axis_values(self.dock.ui.data, self.dock.ui.plot_info['field_type'], self.dock.ui.plot_info['field'])
                # update limits in styling tabs
                self.dock.ui.style_data.set_axis_attributes("x",field)

    def update_data_quantile(self, bound, value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 

        Parameters
        ----------
        bound : str
            'min' or 'max' to indicate which quantile to update.
        value : float
            Lower quantile value.
        """
        if bound == 'min':
            line_edit = getattr(self, f"lineEditLowerQuantile")
        else:
            line_edit = getattr(self, f"lineEditUpperQuantile")
        setattr(line_edit, "value", value)

        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.dock.ui.mask_dock.filter_tab.update_filter_values()
        if self.dock.toolbox.currentIndex() == self.dock.ui.control_dock.tab_dict['process']:
            self.dock.ui.scheduler.schedule_update()

    def update_data_diff_quantile(self, bound, value):
        """
        Updates ``MainWindow.lineEditDifferenceLowerQuantile.value``

        Called when the lower difference quantile threshold changes.

        Parameters
        ----------
        bound : str
            'min' or 'max' to indicate which quantile to update.
        value : float
            Lower difference quantile value.
        """
        if bound == 'min':
            line_edit = getattr(self, f"lineEditDifferenceLowerQuantile")
        else:
            line_edit = getattr(self, f"lineEditDifferenceUpperQuantile")
        setattr(line_edit, "value", value)

        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.dock.ui.mask_dock.filter_tab.update_filter_values()
        if self.dock.toolbox.currentIndex() == self.dock.ui.control_dock.tab_dict['process']:
            self.dock.ui.schedule_update()

    def toggle_autoscale(self, flag):
        """Updates ``toolButtonAutoScale`` checked state 

        Parameters
        ----------
        flag : bool
            Whether autoscaling is enabled.
        """
        self.toolButtonAutoScale.setChecked(flag)
        if flag:
            self.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.lineEditDifferenceUpperQuantile.setEnabled(True)
        else:
            self.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.lineEditDifferenceUpperQuantile.setEnabled(False)
        if hasattr(self,"mask_dock"):
            self.dock.ui.mask_dock.filter_tab.update_filter_values()
        if self.dock.toolbox.currentIndex() == self.dock.ui.control_dock.tab_dict['process']:
            self.dock.ui.schedule_update()

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
        self.checkBoxApplyAll.setChecked(value)
        ratio = ('/' in self.dock.ui.app_data.plot_info['field'])
        if value and not ratio: 
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.dock.ui.plot_tree.clear_tree_data(tree)
        elif value and not ratio:
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in [ 'Ratio', 'Ratio (normalized)']:
                self.dock.ui.plot_tree.clear_tree_data(tree) 
        
    def update_outlier_method(self,method):
        """Updates ``MainWindow.comboBoxOutlierMethod.currentText()``

        Called as an update to ``DataHandling.outlier_method``.  Resets data bound widgets visibility upon change.

        Parameters
        ----------
        method : str
             Method used to remove outliers.
        """
        if self.dock.ui.data[self.dock.ui.app_data.sample_id].outlier_method == method:
            return

        self.dock.ui.data[self.dock.ui.app_data.sample_id].outlier_method = method

        match method.lower():
            case 'none':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)

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
        data = self.dock.ui.data[self.dock.ui.app_data.sample_id]

        if self.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed.match_attribute('data_type', 'Analyte') + data.processed.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.dock.ui.plot_tree.clear_tree_data(tree)
            data.prep_data('all')
        else:
            data.negative_method = method
            data.prep_data(self.dock.ui.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.dock.ui.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.dock.ui.schedule_update()

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
            self.checkBoxApplyAll.setChecked(True)
        else:
            self.checkBoxApplyAll.setChecked(False)

        self.dock.ui.schedule_update()

    def update_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.dock.ui.data[self.dock.ui.app_data.sample_id].processed

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.dock.ui.statusbar.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")


    def update_invalid_data_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.dock.ui.data[self.dock.ui.app_data.sample_id].processed

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.dock.ui.statusbar.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")

    def update_outlier_removal(self, method):
        """Removes outliers from one or all analytes.
        
        Parameters
        ----------
        method : str
            Method used to remove outliers.
        """        
        data = self.dock.ui.data[self.dock.ui.app_data.sample_id]

        if data.outlier_method == method:
            return

        data.outlier_method = method

        match method.lower():
            case 'none':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)

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
        data = self.dock.ui.data[self.dock.ui.app_data.sample_id]

        if self.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed.match_attribute('data_type', 'Analyte') + data.processed.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.dock.ui.plot_tree.clear_tree_data(tree)
            data.prep_data('all')
        else:
            data.negative_method = method

            assert self.dock.ui.app_data.c_field == self.dock.ui.comboBoxFieldC.currentText(), f"AppData.c_field {self.dock.ui.app_data.c_field} and MainWindow.comboBoxFieldC.currentText() {self.dock.ui.comboBoxFieldC.currentText()} do not match"
            data.prep_data(self.dock.ui.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.dock.ui.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.dock.ui.schedule_update()

    def update_dx(self):
        """Updates the x-resolution (`dx`) of the current sample and triggers a plot update."""
        self.dock.ui.data[self.dock.ui.app_data.sample_id].update_resolution('x', self.lineEditDX.value)
        self.dock.ui.schedule_update()

    def update_dy(self):
        """Updates the y-resolution (`dy`) of the current sample and triggers a plot update."""
        self.dock.ui.data[self.dock.ui.app_data.sample_id].update_resolution('y', self.lineEditDY.value)
        self.dock.ui.schedule_update()

    def reset_crop(self):
        """Resets the cropping of the current sample and triggers a plot update."""
        self.dock.ui.data[self.dock.ui.app_data.sample_id].reset_crop
        self.dock.ui.schedule_update()

    def update_swap_resolution(self):
        """Resets the pixel resolution of the current sample to original values and triggers a plot update."""
        if not self.dock.ui.data or self.dock.ui.app_data.sample_id != '':
            return

        self.dock.ui.data[self.dock.ui.app_data.sample_id].swap_resolution 
        self.dock.ui.schedule_update()

    def reset_pixel_resolution(self):
        """
        Swaps the x and y resolutions in the current dataset and schedules a plot update.

        Does nothing if no data is loaded or the sample ID is empty.
        """
        self.dock.ui.data[self.dock.ui.app_data.sample_id].reset_resolution
        self.dock.ui.schedule_update()