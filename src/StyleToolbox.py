import os, re, copy, pickle
from PyQt5.QtWidgets import (
    QColorDialog, QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QPushButton, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView, QProgressBar,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
)
from PyQt5.QtGui import (
    QIntValidator, QDoubleValidator, QColor, QImage, QPainter, QPixmap, QFont, QPen, QPalette,
    QCursor, QBrush, QStandardItemModel, QStandardItem, QTextCursor, QDropEvent, QFontDatabase, QIcon, QWindow
)
from pyqtgraph import colormap
import src.format as fmt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import src.csvdict as csvdict
from src.colorfunc import get_hex_color, get_rgb_color
from src.LameIO import BASEDIR

class Styling():
    def __init__(self, parent):
        #super().__init__(parent)

        self.parent = parent
        self.reset_default_styles()

        # set style theme
        parent.comboBoxStyleTheme.activated.connect(self.read_theme)

        # comboBox with plot type
        # overlay and annotation properties
        parent.toolButtonOverlayColor.clicked.connect(self.overlay_color_callback)
        parent.toolButtonMarkerColor.clicked.connect(self.marker_color_callback)
        parent.toolButtonLineColor.clicked.connect(self.line_color_callback)
        parent.toolButtonClusterColor.clicked.connect(self.cluster_color_callback)
        parent.toolButtonXAxisReset.clicked.connect(lambda: self.axis_reset_callback('x'))
        parent.toolButtonYAxisReset.clicked.connect(lambda: self.axis_reset_callback('y'))
        parent.toolButtonCAxisReset.clicked.connect(lambda: self.axis_reset_callback('c'))
        parent.toolButtonClusterColorReset.clicked.connect(self.set_default_cluster_colors)
        #self.toolButtonOverlayColor.setStyleSheet("background-color: white;")

        setattr(parent.comboBoxMarker, "allItems", lambda: [parent.comboBoxMarker.itemText(i) for i in range(parent.comboBoxMarker.count())])
        setattr(parent.comboBoxLineWidth, "allItems", lambda: [parent.comboBoxLineWidth.itemText(i) for i in range(parent.comboBoxLineWidth.count())])
        setattr(parent.comboBoxColorByField, "allItems", lambda: [parent.comboBoxColorByField.itemText(i) for i in range(parent.comboBoxColorByField.count())])
        setattr(parent.comboBoxColorField, "allItems", lambda: [parent.comboBoxColorField.itemText(i) for i in range(parent.comboBoxColorField.count())])
        setattr(parent.comboBoxFieldColormap, "allItems", lambda: [parent.comboBoxFieldColormap.itemText(i) for i in range(parent.comboBoxFieldColormap.count())])

        # colormaps
        # matplotlib colormaps
        self.mpl_colormaps = colormap.listMaps('matplotlib')
        for i in range(len(self.mpl_colormaps) - 1, -1, -1):
            if self.mpl_colormaps[i].endswith('_r'):
                # If the item ends with '_r', remove it from the list
                del self.mpl_colormaps[i]

        # custom colormaps
        self.custom_color_dict = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/app_data/custom_colormaps.csv'))
        for key in self.custom_color_dict:
            self.custom_color_dict[key] = [h for h in self.custom_color_dict[key] if h]

        # add list of colormaps to comboBoxFieldColormap and set callbacks
        parent.comboBoxFieldColormap.clear()
        parent.comboBoxFieldColormap.addItems(list(self.custom_color_dict.keys())+self.mpl_colormaps)
        parent.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        parent.checkBoxReverseColormap.stateChanged.connect(self.colormap_direction_callback)

        # callback functions
        parent.comboBoxPlotType.currentIndexChanged.connect(lambda: self.plot_type_callback(update=True))
        parent.toolButtonUpdatePlot.clicked.connect(parent.update_SV)
        parent.toolButtonSaveTheme.clicked.connect(self.input_theme_name_dlg)
        # axes
        parent.lineEditXLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('x',parent.lineEditXLabel.text()))
        parent.lineEditYLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('y',parent.lineEditYLabel.text()))
        parent.lineEditZLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('z',parent.lineEditZLabel.text()))
        parent.lineEditCbarLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('c',parent.lineEditCbarLabel.text()))

        parent.comboBoxXScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxXScale,'x'))
        parent.comboBoxYScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxYScale,'y'))
        parent.comboBoxColorScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxColorScale,'c'))

        parent.lineEditXLB.setValidator(QDoubleValidator())
        parent.lineEditXLB.precision = 3
        parent.lineEditXLB.toward = 0
        parent.lineEditXUB.setValidator(QDoubleValidator())
        parent.lineEditXUB.precision = 3
        parent.lineEditXUB.toward = 1
        parent.lineEditYLB.setValidator(QDoubleValidator())
        parent.lineEditYLB.precision = 3
        parent.lineEditYLB.toward = 0
        parent.lineEditYUB.setValidator(QDoubleValidator())
        parent.lineEditYUB.precision = 3
        parent.lineEditYUB.toward = 1
        parent.lineEditColorLB.setValidator(QDoubleValidator())
        parent.lineEditColorLB.precision = 3
        parent.lineEditColorLB.toward = 0
        parent.lineEditColorUB.setValidator(QDoubleValidator())
        parent.lineEditColorUB.precision = 3
        parent.lineEditColorUB.toward = 1
        parent.lineEditAspectRatio.setValidator(QDoubleValidator())

        parent.lineEditXLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 0, float(parent.lineEditXLB.text())))
        parent.lineEditXUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 1, float(parent.lineEditXUB.text())))
        parent.lineEditYLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 0, float(parent.lineEditYLB.text())))
        parent.lineEditYUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 1, float(parent.lineEditYUB.text())))
        parent.lineEditColorLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 0, float(parent.lineEditColorLB.text())))
        parent.lineEditColorUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 1, float(parent.lineEditColorUB.text())))

        parent.lineEditAspectRatio.editingFinished.connect(self.aspect_ratio_callback)
        parent.comboBoxTickDirection.activated.connect(self.tickdir_callback)
        # annotations
        parent.fontComboBox.activated.connect(self.font_callback)
        parent.doubleSpinBoxFontSize.valueChanged.connect(self.font_size_callback)
        # ---------
        # These are tools are for future use, when individual annotations can be added
        parent.tableWidgetAnnotation.setVisible(False)
        parent.toolButtonAnnotationDelete.setVisible(False)
        parent.toolButtonAnnotationSelectAll.setVisible(False)
        # ---------

        # scales
        parent.lineEditScaleLength.setValidator(QDoubleValidator())
        parent.comboBoxScaleDirection.activated.connect(self.scale_direction_callback)
        parent.comboBoxScaleLocation.activated.connect(self.scale_location_callback)
        parent.lineEditScaleLength.editingFinished.connect(self.scale_length_callback)
        #overlay color
        parent.comboBoxMarker.activated.connect(self.marker_symbol_callback)
        parent.doubleSpinBoxMarkerSize.valueChanged.connect(self.marker_size_callback)
        parent.horizontalSliderMarkerAlpha.sliderReleased.connect(self.slider_alpha_changed)
        # lines
        parent.comboBoxLineWidth.activated.connect(self.line_width_callback)
        parent.lineEditLengthMultiplier.editingFinished.connect(self.length_multiplier_callback)
        # colors
        # marker color
        parent.comboBoxColorByField.activated.connect(self.color_by_field_callback)
        parent.comboBoxColorField.activated.connect(self.color_field_callback)
        parent.spinBoxColorField.valueChanged.connect(self.color_field_update)
        parent.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        parent.comboBoxCbarDirection.activated.connect(self.cbar_direction_callback)
        # resolution
        parent.spinBoxHeatmapResolution.valueChanged.connect(lambda: self.resolution_callback(update_plot=True))
        # clusters
        parent.spinBoxClusterGroup.valueChanged.connect(self.select_cluster_group_callback)

        # ternary colormaps
        # create ternary colors dictionary
        df = pd.read_csv(os.path.join(BASEDIR,'resources/styles/ternary_colormaps.csv'))
        self.ternary_colormaps = df.to_dict(orient='records')
        parent.comboBoxTernaryColormap.clear()
        schemes = []
        for cmap in self.ternary_colormaps:
            schemes.append(cmap['scheme'])
        parent.comboBoxTernaryColormap.addItems(schemes)
        parent.comboBoxTernaryColormap.addItem('user defined')

        # dialog for adding and saving new colormaps
        parent.toolButtonSaveTernaryColormap.clicked.connect(parent.input_ternary_name_dlg)

        # select new ternary colors
        parent.toolButtonTCmapXColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapXColor))
        parent.toolButtonTCmapYColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapYColor))
        parent.toolButtonTCmapZColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapZColor))
        parent.toolButtonTCmapMColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapMColor))
        parent.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())
        self.ternary_colormap_changed()


    # -------------------------------------
    # Style related fuctions/callbacks
    # -------------------------------------
    def reset_default_styles(self):
        """Resets ``MainWindow.styles`` dictionary to default values."""

        parent = self.parent
        styles = {}

        default_plot_style = {'Axes': {'XLim': [0,1], 'XScale': 'linear', 'XLabel': '', 'YLim': [0,1], 'YScale': 'linear', 'YLabel': '', 'ZLabel': '', 'AspectRatio': '1.0', 'TickDir': 'out'},
                               'Text': {'Font': '', 'FontSize': 11.0},
                               'Scale': {'Direction': 'none', 'Location': 'northeast', 'Length': None, 'OverlayColor': '#ffffff'},
                               'Markers': {'Symbol': 'circle', 'Size': 6, 'Alpha': 30},
                               'Lines': {'LineWidth': 1.5, 'Multiplier': 1, 'Color': '#1c75bc'},
                               'Colors': {'Color': '#1c75bc', 'ColorByField': 'None', 'Field': '', 'Colormap': 'viridis', 'Reverse': False, 'CLim':[0,1], 'CScale':'linear', 'Direction': 'vertical', 'CLabel': '', 'Resolution': 10}
                               }

        # try to load one of the preferred fonts
        default_font = ['Avenir','Candara','Myriad Pro','Myriad','Aptos','Calibri','Helvetica','Arial','Verdana']
        names = QFontDatabase().families()
        for font in default_font:
            if font in names:
                parent.fontComboBox.setCurrentFont(QFont(font, 11))
                default_plot_style['Text']['Font'] = parent.fontComboBox.currentFont().family()
                break
            # try:
            #     self.fontComboBox.setCurrentFont(QFont(font, 11))
            #     default_plot_style['Text']['Font'] = self.fontComboBox.currentFont().family()
            # except:
            #     print(f'Could not find {font} font')


        styles = {'analyte map': copy.deepcopy(default_plot_style),
                'correlation': copy.deepcopy(default_plot_style),
                'histogram': copy.deepcopy(default_plot_style),
                'gradient map': copy.deepcopy(default_plot_style),
                'scatter': copy.deepcopy(default_plot_style),
                'heatmap': copy.deepcopy(default_plot_style),
                'ternary map': copy.deepcopy(default_plot_style),
                'TEC': copy.deepcopy(default_plot_style),
                'Radar': copy.deepcopy(default_plot_style),
                'variance': copy.deepcopy(default_plot_style),
                'vectors': copy.deepcopy(default_plot_style),
                'PCA scatter': copy.deepcopy(default_plot_style),
                'PCA heatmap': copy.deepcopy(default_plot_style),
                'PCA score': copy.deepcopy(default_plot_style),
                'cluster': copy.deepcopy(default_plot_style),
                'cluster score': copy.deepcopy(default_plot_style),
                'cluster performance': copy.deepcopy(default_plot_style),
                'profile': copy.deepcopy(default_plot_style)}

        # update default styles
        for k in styles.keys():
            styles[k]['Text']['Font'] = parent.fontComboBox.currentFont().family()

        styles['analyte map']['Colors']['Colormap'] = 'plasma'
        styles['analyte map']['Colors']['ColorByField'] = 'Analyte'

        styles['correlation']['Axes']['AspectRatio'] = 1.0
        styles['correlation']['Text']['FontSize'] = 8
        styles['correlation']['Colors']['Colormap'] = 'RdBu'
        styles['correlation']['Colors']['Direction'] = 'vertical'
        styles['correlation']['Colors']['CLim'] = [-1,1]

        styles['vectors']['Axes']['AspectRatio'] = 1.0
        styles['vectors']['Colors']['Colormap'] = 'RdBu'

        styles['gradient map']['Colors']['Colormap'] = 'RdYlBu'

        styles['cluster score']['Colors']['Colormap'] = 'plasma'
        styles['cluster score']['Colors']['Direction'] = 'vertical'
        styles['cluster score']['Colors']['ColorByField'] = 'cluster score'
        styles['cluster score']['Colors']['ColorField'] = 'cluster0'
        styles['cluster score']['Colors']['CScale'] = 'linear'

        styles['cluster']['Colors']['CScale'] = 'discrete'
        styles['cluster']['Markers']['Alpha'] = 100

        styles['cluster performance']['Axes']['AspectRatio'] = 0.62

        styles['PCA score']['Colors']['CScale'] = 'linear'
        styles['PCA score']['Colors']['ColorByField'] = 'PCA score'
        styles['PCA score']['Colors']['ColorField'] = 'PC1'

        styles['scatter']['Axes']['AspectRatio'] = 1

        styles['heatmap']['Axes']['AspectRatio'] = 1
        styles['heatmap']['Colors']['CLim'] = [1,1000]
        styles['heatmap']['Colors']['CScale'] = 'log'
        styles['TEC']['Axes']['AspectRatio'] = 0.62
        styles['variance']['Axes']['AspectRatio'] = 0.62
        styles['PCA scatter']['Lines']['Color'] = '#4d4d4d'
        styles['PCA scatter']['Lines']['LineWidth'] = 0.5
        styles['PCA scatter']['Axes']['AspectRatio'] = 1
        styles['PCA heatmap']['Axes']['AspectRatio'] = 1
        styles['PCA heatmap']['Lines']['Color'] = '#ffffff'

        styles['variance']['Text']['FontSize'] = 8

        styles['histogram']['Axes']['AspectRatio'] = 0.62
        styles['histogram']['Lines']['LineWidth'] = 0

        styles['profile']['Axes']['AspectRatio'] = 0.62
        styles['profile']['Lines']['LineWidth'] = 1.0
        styles['profile']['Markers']['Size'] = 12
        styles['profile']['Colors']['Color'] = '#d3d3d3'
        styles['profile']['Lines']['Color'] = '#d3d3d3'

        self.parent.styles = styles

    # Themes
    # -------------------------------------
    def load_theme_names(self):
        """Loads theme names and adds them to the theme comboBox
        
        Looks for saved style themes (*.sty) in ``resources/styles/`` directory and adds them to
        ``MainWindow.comboBoxStyleTheme``.  After setting list, the comboBox is set to default style.
        """
        parent = self.parent

        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/styles/'))
        style_list = [file.replace('.sty','') for file in file_list if file.endswith('.sty')]

        # add default to list
        style_list.insert(0,'default')

        # update theme comboBox
        parent.comboBoxStyleTheme.clear()
        parent.comboBoxStyleTheme.addItems(style_list)
        parent.comboBoxStyleTheme.setCurrentIndex(0)

        self.reset_default_styles()

    def read_theme(self):
        """Reads a style theme
        
        Executes when the user changes the ``MainWindow.comboBoxStyleTheme.currentIndex()``.
        """
        parent = self.parent

        name = parent.comboBoxStyleTheme.currentText()

        if name == 'default':
            self.reset_default_styles()
            return

        with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'rb') as file:
            parent.styles = pickle.load(file)

    def input_theme_name_dlg(self):
        """Opens a dialog to save style theme

        Executes on ``MainWindow.toolButtonSaveTheme`` is clicked.  The theme is added to
        ``MainWindow.comboBoxStyleTheme`` and the style widget settings for each plot type (``MainWindow.styles``) are saved as a
        dictionary into the theme name with a ``.sty`` extension.
        """
        parent = self.parent

        name, ok = QInputDialog.getText(parent, 'Save custom theme', 'Enter theme name:')
        if ok:
            # update comboBox
            parent.comboBoxStyleTheme.addItem(name)
            parent.comboBoxStyleTheme.setCurrentText(name)

            # append theme to file of saved themes
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'wb') as file:
                pickle.dump(parent.styles, file, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(parent,'Error','could not save theme.')

            return

    # general style functions
    # -------------------------------------
    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        parent = self.parent

        #print('toggle_style_widgets')
        plot_type = parent.comboBoxPlotType.currentText().lower()

        # annotation properties
        parent.fontComboBox.setEnabled(True)
        parent.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'analyte map' | 'gradient map':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(False)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.comboBoxYScale.setEnabled(False)
                parent.lineEditXLabel.setEnabled(False)
                parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(False)
                parent.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(parent.spotdata) != 0:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)

                    parent.toolButtonMarkerColor.setEnabled(True)
                else:
                    parent.comboBoxMarker.setEnabled(False)
                    parent.doubleSpinBoxMarkerSize.setEnabled(False)
                    parent.horizontalSliderMarkerAlpha.setEnabled(False)
                    parent.labelMarkerAlpha.setEnabled(False)

                    parent.toolButtonMarkerColor.setEnabled(False)

                # line properties
                #if len(parent.polygon.polygons) > 0:
                #    parent.comboBoxLineWidth.setEnabled(True)
                #else:
                #    parent.comboBoxLineWidth.setEnabled(False)
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                parent.comboBoxColorField.setEnabled(True)
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxColorScale.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(True)

                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'correlation' | 'vectors':
                # axes properties
                parent.lineEditXLB.setEnabled(False)
                parent.lineEditXUB.setEnabled(False)
                parent.comboBoxXScale.setEnabled(False)
                parent.lineEditYLB.setEnabled(False)
                parent.lineEditYUB.setEnabled(False)
                parent.comboBoxYScale.setEnabled(False)
                parent.lineEditXLabel.setEnabled(False)
                parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.comboBoxXScale.setEnabled(False)
                parent.comboBoxYScale.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(False)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(False)
                parent.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(False)
                parent.doubleSpinBoxMarkerSize.setEnabled(False)
                parent.horizontalSliderMarkerAlpha.setEnabled(False)
                parent.labelMarkerAlpha.setEnabled(False)

                # line properties
                parent.comboBoxLineWidth.setEnabled(False)
                parent.lineEditLengthMultiplier.setEnabled(False)
                parent.toolButtonLineColor.setEnabled(False)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(False)
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.comboBoxColorScale.setEnabled(False)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(False)
                if plot_type.lower() == 'correlation':
                    parent.comboBoxColorByField.setEnabled(True)
                    if parent.comboBoxColorByField.currentText() == 'cluster':
                        parent.comboBoxColorField.setEnabled(True)
                    else:
                        parent.comboBoxColorField.setEnabled(False)

                else:
                    parent.comboBoxColorByField.setEnabled(False)
                    parent.comboBoxColorField.setEnabled(False)

                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'histogram':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(True)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.comboBoxYScale.setEnabled(False)
                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(False)
                parent.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(False)
                parent.doubleSpinBoxMarkerSize.setEnabled(False)
                parent.horizontalSliderMarkerAlpha.setEnabled(True)
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                parent.comboBoxColorScale.setEnabled(False)
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)
                    parent.comboBoxColorField.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(False)
                else:
                    parent.toolButtonMarkerColor.setEnabled(False)
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)

                parent.comboBoxFieldColormap.setEnabled(False)
                parent.lineEditColorLB.setEnabled(False)
                parent.lineEditColorUB.setEnabled(False)
                parent.lineEditCbarLabel.setEnabled(False)

                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'scatter' | 'PCA scatter':
                # axes properties
                if (parent.toolBox.currentIndex() != parent.left_tab['scatter']) or (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditXLB.setEnabled(True)
                    parent.lineEditXUB.setEnabled(True)
                    parent.comboBoxXScale.setEnabled(True)
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.comboBoxYScale.setEnabled(True)
                else:
                    parent.lineEditXLB.setEnabled(False)
                    parent.lineEditXUB.setEnabled(False)
                    parent.comboBoxXScale.setEnabled(False)
                    parent.lineEditYLB.setEnabled(False)
                    parent.lineEditYUB.setEnabled(False)
                    parent.comboBoxYScale.setEnabled(False)

                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                if parent.comboBoxFieldZ.currentText() == '':
                    parent.lineEditZLabel.setEnabled(False)
                else:
                    parent.lineEditZLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(False)
                parent.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)
                parent.horizontalSliderMarkerAlpha.setEnabled(True)
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                if parent.comboBoxFieldZ.currentText() == '':
                    parent.comboBoxLineWidth.setEnabled(True)
                    parent.toolButtonLineColor.setEnabled(True)
                else:
                    parent.comboBoxLineWidth.setEnabled(False)
                    parent.toolButtonLineColor.setEnabled(False)

                if plot_type == 'PCA scatter':
                    parent.lineEditLengthMultiplier.setEnabled(True)
                else:
                    parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)

                    parent.comboBoxColorField.setEnabled(False)
                    parent.comboBoxFieldColormap.setEnabled(False)
                    parent.lineEditColorLB.setEnabled(False)
                    parent.lineEditColorUB.setEnabled(False)
                    parent.comboBoxColorScale.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(False)
                    parent.lineEditCbarLabel.setEnabled(False)
                elif parent.comboBoxColorByField.currentText() == 'cluster':
                    parent.toolButtonMarkerColor.setEnabled(False)

                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(False)
                    parent.lineEditColorLB.setEnabled(False)
                    parent.lineEditColorUB.setEnabled(False)
                    parent.comboBoxColorScale.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(True)
                    parent.lineEditCbarLabel.setEnabled(False)
                else:
                    parent.toolButtonMarkerColor.setEnabled(False)

                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(True)
                    parent.lineEditColorLB.setEnabled(True)
                    parent.lineEditColorUB.setEnabled(True)
                    parent.comboBoxColorScale.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)
                    parent.lineEditCbarLabel.setEnabled(True)

                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'heatmap' | 'PCA heatmap':
                # axes properties
                if (parent.toolBox.currentIndex() != parent.left_tab['scatter']) or (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditXLB.setEnabled(True)
                    parent.lineEditXUB.setEnabled(True)
                    parent.comboBoxXScale.setEnabled(True)
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.comboBoxYScale.setEnabled(True)
                else:
                    parent.lineEditXLB.setEnabled(False)
                    parent.lineEditXUB.setEnabled(False)
                    parent.comboBoxXScale.setEnabled(False)
                    parent.lineEditYLB.setEnabled(False)
                    parent.lineEditYUB.setEnabled(False)
                    parent.comboBoxYScale.setEnabled(False)

                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                if (parent.toolBox.currentIndex() != parent.left_tab['scatter']) or (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditZLabel.setEnabled(False)
                else:
                    parent.lineEditZLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.toolButtonOverlayColor.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(False)
                parent.doubleSpinBoxMarkerSize.setEnabled(False)
                parent.horizontalSliderMarkerAlpha.setEnabled(False)
                parent.labelMarkerAlpha.setEnabled(False)

                # line properties
                if parent.comboBoxFieldZ.currentText() == '':
                    parent.comboBoxLineWidth.setEnabled(True)
                    parent.toolButtonLineColor.setEnabled(True)
                else:
                    parent.comboBoxLineWidth.setEnabled(False)
                    parent.toolButtonLineColor.setEnabled(False)

                if plot_type == 'PCA heatmap':
                    parent.lineEditLengthMultiplier.setEnabled(True)
                else:
                    parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(False)
                parent.comboBoxColorByField.setEnabled(False)
                parent.comboBoxColorField.setEnabled(False)
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxColorScale.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(True)

                parent.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(False)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(False)
                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                parent.lineEditZLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(False)
                parent.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if not parent.spotdata.empty:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)

                    parent.toolButtonMarkerColor.setEnabled(True)
                else:
                    parent.comboBoxMarker.setEnabled(False)
                    parent.doubleSpinBoxMarkerSize.setEnabled(False)
                    parent.horizontalSliderMarkerAlpha.setEnabled(False)
                    parent.labelMarkerAlpha.setEnabled(False)

                    parent.toolButtonMarkerColor.setEnabled(False)

                # line properties
                parent.comboBoxLineWidth.setEnabled(False)
                parent.lineEditLengthMultiplier.setEnabled(False)
                parent.toolButtonLineColor.setEnabled(False)

                # color properties
                parent.comboBoxColorByField.setEnabled(False)
                parent.comboBoxColorField.setEnabled(False)
                parent.comboBoxFieldColormap.setEnabled(False)
                parent.comboBoxColorScale.setEnabled(False)
                parent.lineEditColorLB.setEnabled(False)
                parent.lineEditColorUB.setEnabled(False)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(False)

                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'tec' | 'radar':
                # axes properties
                parent.lineEditXLB.setEnabled(False)
                parent.lineEditXUB.setEnabled(False)
                parent.lineEditXLabel.setEnabled(False)
                if plot_type == 'tec':
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.lineEditYLabel.setEnabled(True)
                else:
                    parent.lineEditYLB.setEnabled(False)
                    parent.lineEditYUB.setEnabled(False)
                    parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(False)
                parent.doubleSpinBoxMarkerSize.setEnabled(False)
                parent.horizontalSliderMarkerAlpha.setEnabled(False)
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)
                    parent.comboBoxColorField.setEnabled(False)
                    parent.comboBoxFieldColormap.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(False)
                elif parent.comboBoxColorByField.currentText().lower() == 'cluster':
                    parent.toolButtonMarkerColor.setEnabled(False)
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(True)

                parent.comboBoxColorScale.setEnabled(False)
                parent.lineEditColorLB.setEnabled(False)
                parent.lineEditColorUB.setEnabled(False)
                parent.lineEditCbarLabel.setEnabled(False)
                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'variance' | 'cluster performance':
                # axes properties
                parent.lineEditXLB.setEnabled(False)
                parent.lineEditXUB.setEnabled(False)
                parent.lineEditXLabel.setEnabled(False)
                parent.lineEditYLB.setEnabled(False)
                parent.lineEditYUB.setEnabled(False)
                parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)
                parent.horizontalSliderMarkerAlpha.setEnabled(False)
                parent.labelMarkerAlpha.setEnabled(False)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(True)
                parent.comboBoxColorByField.setEnabled(False)
                parent.comboBoxFieldColormap.setEnabled(False)
                parent.lineEditColorLB.setEnabled(False)
                parent.lineEditColorUB.setEnabled(False)
                parent.comboBoxColorScale.setEnabled(False)
                parent.comboBoxCbarDirection.setEnabled(False)
                parent.lineEditCbarLabel.setEnabled(False)
                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'pca score' | 'cluster score' | 'cluster':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.lineEditXLabel.setEnabled(False)
                parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(False)
                parent.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(parent.spotdata) != 0:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)

                    parent.toolButtonMarkerColor.setEnabled(True)
                else:
                    parent.comboBoxMarker.setEnabled(False)
                    parent.doubleSpinBoxMarkerSize.setEnabled(False)
                    parent.horizontalSliderMarkerAlpha.setEnabled(False)
                    parent.labelMarkerAlpha.setEnabled(False)

                    parent.toolButtonMarkerColor.setEnabled(False)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                if plot_type == 'clusters':
                    parent.comboBoxColorByField.setEnabled(False)
                    parent.comboBoxColorField.setEnabled(False)
                    parent.comboBoxFieldColormap.setEnabled(False)
                    parent.lineEditColorLB.setEnabled(False)
                    parent.lineEditColorUB.setEnabled(False)
                    parent.comboBoxColorScale.setEnabled(False)
                    parent.comboBoxCbarDirection.setEnabled(False)
                    parent.lineEditCbarLabel.setEnabled(False)
                else:
                    parent.comboBoxColorByField.setEnabled(True)
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(True)
                    parent.lineEditColorLB.setEnabled(True)
                    parent.lineEditColorUB.setEnabled(True)
                    parent.comboBoxColorScale.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)
                    parent.lineEditCbarLabel.setEnabled(True)
                parent.spinBoxHeatmapResolution.setEnabled(False)
            case 'profile':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLB.setEnabled(False)
                parent.lineEditYUB.setEnabled(False)
                parent.lineEditYLabel.setEnabled(False)
                parent.lineEditZLabel.setEnabled(False)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(False)
                parent.comboBoxScaleLocation.setEnabled(False)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)
                parent.horizontalSliderMarkerAlpha.setEnabled(False)
                parent.labelMarkerAlpha.setEnabled(False)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)
                parent.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(True)
                parent.comboBoxColorByField.setEnabled(False)
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(False)
                parent.lineEditColorUB.setEnabled(False)
                parent.comboBoxColorScale.setEnabled(False)
                parent.comboBoxCbarDirection.setEnabled(False)
                parent.lineEditCbarLabel.setEnabled(False)
                parent.spinBoxHeatmapResolution.setEnabled(False)

        # enable/disable labels
        # axes properties
        parent.labelXLim.setEnabled(parent.lineEditXLB.isEnabled())
        parent.toolButtonXAxisReset.setEnabled(parent.labelXLim.isEnabled())
        parent.labelXScale.setEnabled(parent.comboBoxXScale.isEnabled())
        parent.labelYLim.setEnabled(parent.lineEditYLB.isEnabled())
        parent.toolButtonYAxisReset.setEnabled(parent.labelYLim.isEnabled())
        parent.labelYScale.setEnabled(parent.comboBoxYScale.isEnabled())
        parent.labelXLabel.setEnabled(parent.lineEditXLabel.isEnabled())
        parent.labelYLabel.setEnabled(parent.lineEditYLabel.isEnabled())
        parent.labelZLabel.setEnabled(parent.lineEditZLabel.isEnabled())
        parent.labelAspectRatio.setEnabled(parent.lineEditAspectRatio.isEnabled())
        parent.labelTickDirection.setEnabled(parent.comboBoxTickDirection.isEnabled())

        # scalebar properties
        parent.labelScaleLocation.setEnabled(parent.comboBoxScaleLocation.isEnabled())
        parent.labelScaleDirection.setEnabled(parent.comboBoxScaleDirection.isEnabled())
        if parent.toolButtonOverlayColor.isEnabled():
            parent.labelOverlayColor.setEnabled(True)
        else:
            parent.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            parent.labelOverlayColor.setEnabled(False)
        parent.labelScaleLength.setEnabled(parent.lineEditScaleLength.isEnabled())

        # marker properties
        parent.labelMarker.setEnabled(parent.comboBoxMarker.isEnabled())
        parent.labelMarkerSize.setEnabled(parent.doubleSpinBoxMarkerSize.isEnabled())
        parent.labelTransparency.setEnabled(parent.horizontalSliderMarkerAlpha.isEnabled())

        # line properties
        parent.labelLineWidth.setEnabled(parent.comboBoxLineWidth.isEnabled())
        parent.labelLineColor.setEnabled(parent.toolButtonLineColor.isEnabled())
        parent.labelLengthMultiplier.setEnabled(parent.lineEditLengthMultiplier.isEnabled())

        # color properties
        if parent.toolButtonMarkerColor.isEnabled():
            parent.labelMarkerColor.setEnabled(True)
        else:
            parent.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            parent.labelMarkerColor.setEnabled(False)
        parent.labelColorByField.setEnabled(parent.comboBoxColorByField.isEnabled())
        parent.labelColorField.setEnabled(parent.comboBoxColorField.isEnabled())
        parent.checkBoxReverseColormap.setEnabled(parent.comboBoxFieldColormap.isEnabled())
        parent.labelReverseColormap.setEnabled(parent.checkBoxReverseColormap.isEnabled())
        parent.labelFieldColormap.setEnabled(parent.comboBoxFieldColormap.isEnabled())
        parent.labelColorScale.setEnabled(parent.comboBoxColorScale.isEnabled())
        parent.labelColorBounds.setEnabled(parent.lineEditColorLB.isEnabled())
        parent.toolButtonCAxisReset.setEnabled(parent.labelColorBounds.isEnabled())
        parent.labelCbarDirection.setEnabled(parent.comboBoxCbarDirection.isEnabled())
        parent.labelCbarLabel.setEnabled(parent.lineEditCbarLabel.isEnabled())
        parent.labelHeatmapResolution.setEnabled(parent.spinBoxHeatmapResolution.isEnabled())

    def set_style_widgets(self, plot_type=None, style=None):
        """Sets values in right toolbox style page

        :param plot_type: dictionary key into ``MainWindow.style``
        :type plot_type: str, optional
        """
        #print('set_style_widgets')
        parent = self.parent
        data = parent.data[parent.sample_id]

        tab_id = parent.toolBox.currentIndex()

        if plot_type is None:
            plot_type = parent.plot_types[tab_id][parent.plot_types[tab_id][0]+1]
            parent.comboBoxPlotType.blockSignals(True)
            parent.comboBoxPlotType.clear()
            parent.comboBoxPlotType.addItems(parent.plot_types[tab_id][1:])
            parent.comboBoxPlotType.setCurrentText(plot_type)
            parent.comboBoxPlotType.blockSignals(False)
        elif plot_type == '':
            return

        # toggle actionSwapAxes
        match plot_type:
            case 'analyte map':
                parent.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                parent.actionSwapAxes.setEnabled(True)
            case _:
                parent.actionSwapAxes.setEnabled(False)

        if style is None:
            style = parent.styles[plot_type]

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if plot_type.lower() in parent.map_plot_types:
            if ('X' not in list(parent.data[parent.sample_id].axis_dict.keys())) or ('Y' not in list(parent.data[parent.sample_id].axis_dict.keys())):
                # initialize 'X' and 'Y' axes
                # all plot types use the same map dimensions so just use Analyte for the field_type
                self.initialize_axis_values('Analyte','X')
                self.initialize_axis_values('Analyte','Y')
            xmin,xmax,xscale,xlabel = self.get_axis_values('Analyte','X')
            ymin,ymax,yscale,ylabel = self.get_axis_values('Analyte','Y')

            # set style dictionary values for X and Y
            style['Axes']['XLim'] = [xmin, xmax]
            style['Axes']['XScale'] = xscale
            style['Axes']['XLabel'] = 'X'
            style['Axes']['YLim'] = [ymin, ymax]
            style['Axes']['YScale'] = yscale
            style['Axes']['YLabel'] = 'Y'
            style['Axes']['AspectRatio'] = parent.data[parent.sample_id].aspect_ratio

            # do not round axes limits for maps
            parent.lineEditXLB.precision = None
            parent.lineEditXUB.precision = None
            parent.lineEditXLB.value = style['Axes']['XLim'][0]
            parent.lineEditXUB.value = style['Axes']['XLim'][1]

            parent.lineEditYLB.value = style['Axes']['YLim'][0]
            parent.lineEditYUB.value = style['Axes']['YLim'][1]
        else:
            # round axes limits for everything that isn't a map
            parent.lineEditXLB.value = style['Axes']['XLim'][0]
            parent.lineEditXUB.value = style['Axes']['XLim'][1]

            parent.lineEditYLB.value = style['Axes']['YLim'][0]
            parent.lineEditYUB.value = style['Axes']['YLim'][1]

        parent.comboBoxXScale.setCurrentText(style['Axes']['XScale'])
        parent.lineEditXLabel.setText(style['Axes']['XLabel'])

        parent.comboBoxYScale.setCurrentText(style['Axes']['YScale'])
        parent.lineEditYLabel.setText(style['Axes']['YLabel'])

        parent.lineEditZLabel.setText(style['Axes']['ZLabel'])
        parent.lineEditAspectRatio.setText(str(style['Axes']['AspectRatio']))

        # annotation properties
        #parent.fontComboBox.setCurrentFont(style['Text']['Font'])
        parent.doubleSpinBoxFontSize.blockSignals(True)
        parent.doubleSpinBoxFontSize.setValue(style['Text']['FontSize'])
        parent.doubleSpinBoxFontSize.blockSignals(False)

        # scalebar properties
        parent.comboBoxScaleLocation.setCurrentText(style['Scale']['Location'])
        parent.comboBoxScaleDirection.setCurrentText(style['Scale']['Direction'])
        if (style['Scale']['Length'] is None) and (plot_type in parent.map_plot_types):
            style['Scale']['Length'] = parent.default_scale_length()

            parent.lineEditScaleLength.value = style['Scale']['Length']
        else:
            parent.lineEditScaleLength.value = None
            
        parent.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % style['Scale']['OverlayColor'])

        # marker properties
        parent.comboBoxMarker.setCurrentText(style['Markers']['Symbol'])

        parent.doubleSpinBoxMarkerSize.blockSignals(True)
        parent.doubleSpinBoxMarkerSize.setValue(style['Markers']['Size'])
        parent.doubleSpinBoxMarkerSize.blockSignals(False)

        parent.horizontalSliderMarkerAlpha.setValue(int(style['Markers']['Alpha']))
        parent.labelMarkerAlpha.setText(str(parent.horizontalSliderMarkerAlpha.value()))

        # line properties
        parent.comboBoxLineWidth.setCurrentText(str(style['Lines']['LineWidth']))
        parent.lineEditLengthMultiplier.value = style['Lines']['Multiplier']
        parent.toolButtonLineColor.setStyleSheet("background-color: %s;" % style['Lines']['Color'])

        # color properties
        parent.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % style['Colors']['Color'])
        parent.update_field_type_combobox(parent.comboBoxColorByField,addNone=True,plot_type=plot_type)
        parent.comboBoxColorByField.setCurrentText(style['Colors']['ColorByField'])

        if style['Colors']['ColorByField'] == '':
            parent.comboBoxColorField.clear()
        else:
            parent.update_field_combobox(parent.comboBoxColorByField, parent.comboBoxColorField)
            parent.spinBoxColorField.setMinimum(0)
            parent.spinBoxColorField.setMaximum(parent.comboBoxColorField.count() - 1)

        if style['Colors']['Field'] in parent.comboBoxColorField.allItems():
            parent.comboBoxColorField.setCurrentText(style['Colors']['Field'])
            parent.update_color_field_spinbox()
        else:
            style['Colors']['Field'] = parent.comboBoxColorField.currentText()

        parent.comboBoxFieldColormap.setCurrentText(style['Colors']['Colormap'])
        parent.checkBoxReverseColormap.blockSignals(True)
        parent.checkBoxReverseColormap.setChecked(style['Colors']['Reverse'])
        parent.checkBoxReverseColormap.blockSignals(False)
        if style['Colors']['Field'] in list(data.axis_dict.keys()):
            style['Colors']['CLim'] = [data.axis_dict[style['Colors']['Field']]['min'], data.axis_dict[style['Colors']['Field']]['max']]
            style['Colors']['CLabel'] = data.axis_dict[style['Colors']['Field']]['label']
        parent.lineEditColorLB.value = style['Colors']['CLim'][0]
        parent.lineEditColorUB.value = style['Colors']['CLim'][1]
        if style['Colors']['ColorByField'] == 'cluster':
            # set ColorField to active cluster method
            parent.comboBoxColorField.setCurrentText(parent.cluster_dict['active method'])

            # set color scale to discrete
            parent.comboBoxColorScale.clear()
            parent.comboBoxColorScale.addItem('discrete')
            parent.comboBoxColorScale.setCurrentText('discrete')

            parent.styles[plot_type]['Colors']['CScale'] = 'discrete'
        else:
            # set color scale options to linear/log
            parent.comboBoxColorScale.clear()
            parent.comboBoxColorScale.addItems(['linear','log'])
            parent.styles[plot_type]['Colors']['CScale'] = 'linear'
            parent.comboBoxColorScale.setCurrentText(parent.styles[plot_type]['Colors']['CScale'])
            
        parent.comboBoxColorScale.setCurrentText(style['Colors']['CScale'])
        parent.comboBoxCbarDirection.setCurrentText(style['Colors']['Direction'])
        parent.lineEditCbarLabel.setText(style['Colors']['CLabel'])

        parent.spinBoxHeatmapResolution.blockSignals(True)
        parent.spinBoxHeatmapResolution.setValue(style['Colors']['Resolution'])
        parent.spinBoxHeatmapResolution.blockSignals(False)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        # update plot (is this line needed)
        # self.update_SV()

    def get_style_dict(self):
        """Get style properties"""        
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        parent.plot_types[parent.toolBox.currentIndex()][0] = parent.comboBoxPlotType.currentIndex()

        # update axes properties
        parent.styles[plot_type]['Axes'] = {'XLim': [float(parent.lineEditXLB.text()), float(parent.lineEditXUB.text())],
                    'XLabel': parent.lineEditXLabel.text(),
                    'YLim': [float(parent.lineEditYLB.text()), float(parent.lineEditYUB.text())],
                    'YLabel': parent.lineEditYLabel.text(),
                    'ZLabel': parent.lineEditZLabel.text(),
                    'AspectRatio': float(parent.lineEditAspectRatio.text()),
                    'TickDir': parent.comboBoxTickDirection.text()}

        # update annotation properties
        parent.styles[plot_type]['Text'] = {'Font': parent.fontComboBox.currentFont(),
                    'FontSize': parent.doubleSpinBoxFontSize.value()}

        # update scale properties
        parent.styles[plot_type]['Scale'] = {'Location': parent.comboBoxScaleLocation.currentText(),
                    'Direction': parent.comboBoxScaleDirection.currentText(),
                    'OverlayColor': get_hex_color(parent.toolButtonOverlayColor.palette().button().color())}

        # update marker properties
        parent.styles[plot_type]['Markers'] = {'Symbol': parent.comboBoxMarker.currentText(),
                    'Size': parent.doubleSpinBoxMarkerSize.value(),
                    'Alpha': float(parent.horizontalSliderMarkerAlpha.value())}

        # update line properties
        parent.styles[plot_type]['Lines'] = {'LineWidth': float(parent.comboBoxLineWidth.currentText()),
                    'Multiplier': float(parent.lineEditLengthMultiplier.text()),
                    'Color': get_hex_color(parent.toolButtonMarkerColor.palette().button().color())}

        # update color properties
        parent.styles[plot_type]['Colors'] = {'Color': get_hex_color(parent.toolButtonMarkerColor.palette().button().color()),
                    'ColorByField': parent.comboBoxColorByField.currentText(),
                    'Field': parent.comboBoxColorField.currentText(),
                    'Colormap': parent.comboBoxFieldColormap.currentText(),
                    'Reverse': parent.checkBoxReverseColormap.isChecked(),
                    'CLim': [float(parent.lineEditColorLB.text()), float(parent.lineEditColorUB.text())],
                    'CScale': parent.comboBoxColorScale.currentText(),
                    'Direction': parent.comboBoxCbarDirection.currentText(),
                    'CLabel': parent.lineEditCbarLabel.text(),
                    'Resolution': parent.spinBoxHeatmapResolution.value()}

    # style widget callbacks
    # -------------------------------------
    def plot_type_callback(self, update=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        #print('plot_type_callback')
        # set plot flag to false
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        parent.plot_types[parent.toolBox.currentIndex()][0] = parent.comboBoxPlotType.currentIndex()
        match plot_type:
            case 'analyte map':
                parent.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                parent.actionSwapAxes.setEnabled(True)
            case 'correlation':
                parent.actionSwapAxes.setEnabled(False)
                if parent.comboBoxCorrelationMethod.currentText() == 'None':
                    parent.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance':
                parent.labelClusterMax.show()
                parent.spinBoxClusterMax.show()
                parent.labelNClusters.hide()
                parent.spinBoxNClusters.hide()
            case 'cluster' | 'cluster score':
                parent.labelClusterMax.hide()
                parent.spinBoxClusterMax.hide()
                parent.labelNClusters.show()
                parent.spinBoxNClusters.show()
            case _:
                parent.actionSwapAxes.setEnabled(False)

        self.set_style_widgets(plot_type=plot_type)
        #self.check_analysis_type()

        if update:
            parent.update_SV()

    # axes
    # -------------------------------------
    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.
        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if ax == 'c':
            return parent.comboBoxColorField.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return parent.comboBoxHistField.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return parent.comboBoxFieldX.currentText()
                    case 'y':
                        return parent.comboBoxFieldY.currentText()
                    case 'z':
                        return parent.comboBoxFieldZ.currentText()
            case 'PCA scatter' | 'PCA heatmap':
                match ax:
                    case 'x':
                        return f'PC{parent.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{parent.spinBoxPCY.value()}'
            case 'analyte map' | 'ternary map' | 'PCA score' | 'cluster' | 'cluster score':
                return ax.upper()

    def axis_label_edit_callback(self, ax, new_label):
        """Updates axis label in dictionaries from widget

        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        :param new_label: new label set by user
        :type new_label: str
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()

        old_label = parent.styles[plot_type]['Axes'][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        parent.data[parent.sample_id].axis_dict[field]['label'] = new_label
        parent.styles[plot_type]['Axes'][ax.upper()+'Label'] = new_label

        # update plot
        parent.update_SV()

    def axis_limit_edit_callback(self, ax, bound, new_value):
        """Updates axis limit in dictionaries from widget

        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        :param bound: ``0`` for lower and ``1`` for upper
        :type bound: int
        :param new_value: new value set by user
        :type new_value: float
        """
        parent = self.parent
        axis_dict = parent.data[parent.sample_id].axis_dict
        plot_type = parent.comboBoxPlotType.currentText()

        if ax == 'c':
            old_value = parent.styles[plot_type]['Colors']['CLim'][bound]
        else:
            old_value = parent.styles[plot_type]['Axes'][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ax == 'c' and plot_type in ['heatmap', 'correlation']:
            parent.update_SV()
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                axis_dict[field]['pmax'] = new_value
                axis_dict[field]['pstatus'] = 'custom'
            else:
                axis_dict[field]['max'] = new_value
                axis_dict[field]['status'] = 'custom'
        else:
            if plot_type == 'histogram' and ax == 'y':
                axis_dict[field]['pmin'] = new_value
                axis_dict[field]['pstatus'] = 'custom'
            else:
                axis_dict[field]['min'] = new_value
                axis_dict[field]['status'] = 'custom'

        if ax == 'c':
            parent.styles[plot_type]['Colors'][f'{ax.upper()}Lim'][bound] = new_value
        else:
            parent.styles[plot_type]['Axes'][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        parent.update_SV()

    def axis_scale_callback(self, comboBox, ax):
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        styles = parent.styles[plot_type]

        new_value = comboBox.currentText()
        if ax == 'c':
            if styles['Colors']['CLim'] == new_value:
                return
        elif styles['Axes'][ax.upper()+'Scale'] == new_value:
            return

        field = self.get_axis_field(ax)

        if plot_type != 'heatmap':
            parent.data[parent.sample_id].axis_dict[field]['scale'] = new_value

        if ax == 'c':
            styles['Colors']['CScale'] = new_value
        else:
            styles['Axes'][ax.upper()+'Scale'] = new_value

        # update plot
        parent.update_SV()

    def set_color_axis_widgets(self):
        """Sets the color axis widgets

        Sets color axis limits and label
        """
        #print('set_color_axis_widgets')
        parent = self.parent

        axis_dict = parent.data[parent.sample_id].axis_dict

        field = parent.comboBoxColorField.currentText()
        if field == '':
            return
        parent.lineEditColorLB.value = axis_dict[field]['min']
        parent.lineEditColorUB.value = axis_dict[field]['max']
        parent.comboBoxColorScale.setCurrentText(axis_dict[field]['scale'])

    def set_axis_widgets(self, ax, field):
        """Sets axis widgets in the style toolbox

        Updates axes limits and labels.

        Parameters
        ----------
        ax : str
            Axis 'x', 'y', or 'z'
        field : str
            Field plotted on axis, used as key to ``MainWindow.axis_dict``
        """
        #print('set_axis_widgets')
        parent = self.parent

        match ax:
            case 'x':
                if field == 'X':
                    parent.lineEditXLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                    parent.lineEditXUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                else:
                    parent.lineEditXLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                    parent.lineEditXUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                parent.lineEditXLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])
                parent.comboBoxXScale.setCurrentText(parent.data[parent.sample_id].axis_dict[field]['scale'])
            case 'y':
                if parent.comboBoxPlotType.currentText() == 'histogram':
                    parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['pmin']
                    parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['pmax']
                    parent.lineEditYLabel.setText(parent.comboBoxHistType.currentText())
                    parent.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'X':
                        parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                        parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                    else:
                        parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                        parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                    parent.lineEditYLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])
                    parent.comboBoxYScale.setCurrentText(parent.data[parent.sample_id].axis_dict[field]['scale'])
            case 'z':
                parent.lineEditZLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])

    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Axes parameters with ``MainWindow.axis_dict['status']`` can be ``auto`` or ``custom``, where ``custom``
        is set by the user in the appropriate *lineEdit* widgets.  The ``auto`` status is set by the full range
        of values of a data column.        

        Parameters
        ----------
        ax : str
            axis to reset values, can be ``x``, ``y``, and ``c``

        .. seealso::
            :ref: `initialize_axis_values` for initializing the axis dictionary
        """
        #print('axis_reset_callback')
        parent = self.parent

        if ax == 'c':
            if parent.comboBoxPlotType.currentText() == 'vectors':
                parent.styles['vectors']['Colors']['CLim'] = [np.amin(parent.pca_results.components_), np.amax(parent.pca_results.components_)]
                self.set_color_axis_widgets()
            elif not (parent.comboBoxColorByField.currentText() in ['None','cluster']):
                field_type = parent.comboBoxColorByField.currentText()
                field = parent.comboBoxColorField.currentText()
                if field == '':
                    return
                self.initialize_axis_values(field_type, field)
                self.set_color_axis_widgets()
        else:
            match parent.comboBoxPlotType.currentText().lower():
                case 'analyte map' | 'cluster' | 'cluster score' | 'pca score':
                    field = ax.upper()
                    self.initialize_axis_values('Analyte', field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = parent.comboBoxHistField.currentText()
                    if ax == 'x':
                        field_type = parent.comboBoxHistFieldType.currentText()
                        self.initialize_axis_values(field_type, field)
                        self.set_axis_widgets(ax, field)
                    else:
                        parent.data[parent.sample_id].axis_dict[field].update({'pstatus':'auto', 'pmin':None, 'pmax':None})

                case 'scatter' | 'heatmap':
                    if ax == 'x':
                        field_type = parent.comboBoxFieldTypeX.currentText()
                        field = parent.comboBoxFieldX.currentText()
                    else:
                        field_type = parent.comboBoxFieldTypeY.currentText()
                        field = parent.comboBoxFieldY.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case 'PCA scatter' | 'PCA heatmap':
                    field_type = 'PCA score'
                    if ax == 'x':
                        field = parent.spinBoxPCX.currentText()
                    else:
                        field = parent.spinBoxPCY.currentText()
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.set_style_widgets()
        parent.update_SV()

    def get_axis_values(self, field_type, field, ax=None):
        """Gets axis values

        Returns the axis parameters *field_type* \> *field* for plotting, including the minimum and maximum vales,
        the scale (``linear`` or ``log``) and the axis label.  For x, y and color axes associated with the plot,
        no axis needs to be supplied.  For a probability axis associated with histogram PDF plots, ``ax=p``.

        Parameters
        ----------
        field_type : str
            Field type of axis data
        field : str
            Field name of axis data
        ax : str, optional
            stored axis: ``p`` for probability axis, otherwise all are same, by default None

        Returns
        -------
        float, float, str, float
            Axis parameters: minimum, maximum, scale (``linear`` or ``log``), axis label
        """ 
        #print('get_axis_values')
        axis_dict = self.parent.data[self.parent.sample_id].axis_dict

        if field not in axis_dict.keys():
            self.initialize_axis_values(field_type, field)

        # get axis values from axis_dict
        amin = axis_dict[field]['min']
        amax = axis_dict[field]['max']
        scale = axis_dict[field]['scale']
        label = axis_dict[field]['label']

        # if probability axis associated with histogram
        if ax == 'p':
            pmin = axis_dict[field]['pmin']
            pmax = axis_dict[field]['pmax']
            return amin, amax, scale, label, pmin, pmax

        return amin, amax, scale, label

    def initialize_axis_values(self, field_type, field):
        #print('initialize_axis_values')
        data = self.parent.data[self.parent.sample_id]

        # initialize variables
        if field not in data.axis_dict.keys():
            #print('initialize data.axis_dict["field"]')
            data.axis_dict.update({field:{'status':'auto', 'label':field, 'min':None, 'max':None}})

        #current_plot_df = pd.DataFrame()
        if field not in ['X','Y']:
            df = data.get_map_data(field, field_type)
            array = df['array'][data.mask].values if not df.empty else []
        else:
            # field 'X' and 'Y' require separate extraction
            array = data.processed_data[field].values

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                if field in ['X','Y']:
                    scale = 'linear'
                else:
                    symbol, mass = self.parse_field(field)
                    if field_type == 'Analyte':
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol} ({self.parent.preferences['Units']['Concentration']})"
                    else:
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol}$_N$ ({self.parent.preferences['Units']['Concentration']})"

                    scale = data.processed_data.get_attribute(field, 'norm')

                amin = np.nanmin(array)
                amax = np.nanmax(array)
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                symbol_1, mass_1 = self.parse_field(field_1)
                symbol_2, mass_2 = self.parse_field(field_2)
                if field_type == 'Ratio':
                    data.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1} / $^{{{mass_2}}}${symbol_2}"
                else:
                    data.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1}$_N$ / $^{{{mass_2}}}${symbol_2}$_N$"

                amin = np.nanmin(array)
                amax = np.nanmax(array)
                scale = data.processed_data.get_attribute(field, 'norm')
            case _:
                scale = 'linear'

                amin = np.nanmin(array)
                amax = np.nanmax(array)

        # do not round 'X' and 'Y' so full extent of map is viewable
        if field not in ['X','Y']:
            amin = fmt.oround(amin, order=2, toward=0)
            amax = fmt.oround(amax, order=2, toward=1)

        d = {'status':'auto', 'min':amin, 'max':amax, 'scale':scale}

        data.axis_dict[field].update(d)
        #print(data.axis_dict[field])

    def parse_field(self,field):

        match = re.match(r"([A-Za-z]+)(\d*)", field)
        symbol = match.group(1) if match else field
        mass = int(match.group(2)) if match.group(2) else None

        return symbol, mass

    def aspect_ratio_callback(self):
        """Update aspect ratio

        Updates ``MainWindow.style`` dictionary after user change
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Axes']['AspectRatio'] == parent.lineEditAspectRatio.text():
            return

        parent.styles[plot_type]['Axes']['AspectRatio'] = parent.lineEditAspectRatio.text()
        parent.update_SV()

    def tickdir_callback(self):
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Axes']['TickDir'] == parent.comboBoxTickDirection.currentText():
            return

        parent.styles[plot_type]['Axes']['TickDir'] = parent.comboBoxTickDirection.currentText()
        parent.update_SV()

    # text and annotations
    # -------------------------------------
    def font_callback(self):
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Text']['Font'] == parent.fontComboBox.currentFont().family():
            return

        parent.styles[plot_type]['Text']['Font'] = parent.fontComboBox.currentFont().family()
        parent.update_SV()

    def font_size_callback(self):
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Text']['FontSize'] == parent.doubleSpinBoxFontSize.value():
            return

        parent.styles[plot_type]['Text']['FontSize'] = parent.doubleSpinBoxFontSize.value()
        parent.update_SV()

    def update_figure_font(self, canvas, font_name):
        if font_name == '':
            return

        # Update font of all text elements in the figure
        try:
            for text_obj in canvas.fig.findobj(match=plt.Text):
                text_obj.set_fontname(font_name)
        except:
            print('Unable to update figure font.')

    def toggle_mass(self, labels):
        """Removes mass from labels

        Removes mass if ``MainWindow.checkBoxShowMass.isChecked()`` is False

        Parameters
        ----------
        labels : str
            Input labels

        Returns
        -------
        list
            Output labels with or without mass
        """
        if not self.parent.checkBoxShowMass.isChecked():
            labels = [re.sub(r'\d', '', col) for col in labels]

        return labels

    # scales
    # -------------------------------------
    def scale_direction_callback(self):
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        direction = parent.comboBoxScaleDirection.currentText()
        if parent.styles[plot_type]['Scale']['Direction'] == direction:
            return

        parent.styles[plot_type]['Scale']['Direction'] = direction
        if direction == 'none':
            parent.labelScaleLocation.setEnabled(False)
            parent.comboBoxScaleLocation.setEnabled(False)
            parent.labelScaleLength.setEnabled(False)
            parent.lineEditScaleLength.setEnabled(False)
            parent.lineEditScaleLength.value = None
        else:
            parent.labelScaleLocation.setEnabled(True)
            parent.comboBoxScaleLocation.setEnabled(True)
            parent.labelScaleLength.setEnabled(True)
            parent.lineEditScaleLength.setEnabled(True)
            # set scalebar length if plot is a map type
            if plot_type in parent.map_plot_types:
                if parent.styles[plot_type]['Scale']['Length'] is None:
                    scale_length = parent.default_scale_length()
                elif ((direction == 'horizontal') and (parent.styles[plot_type]['Scale']['Length'] > parent.data[parent.sample_id].x_range)) or ((direction == 'vertical') and (parent.styles[plot_type]['Scale']['Length'] > parent.data[parent.sample_id].y_range)):
                    scale_length = parent.default_scale_length()
                else:
                    scale_length = parent.styles[plot_type]['Scale']['Length']
                parent.styles[plot_type]['Scale']['Length'] = scale_length
                parent.lineEditScaleLength.value = scale_length
            else:
                parent.lineEditScaleLength.value = None

        parent.update_SV()

    def scale_location_callback(self):
        """Sets scalebar location on map from ``MainWindow.comboBoxScaleLocation``"""        
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()

        if parent.styles[plot_type]['Scale']['Location'] == parent.comboBoxScaleLocation.currentText():
            return

        parent.styles[plot_type]['Scale']['Location'] = parent.comboBoxScaleLocation.currentText()
        parent.update_SV()

    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """ 
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()

        # if length is changed to None
        if parent.lineEditScaleLength.text() == '':
            if parent.styles[plot_type]['Scale']['Length'] is None:
                return
            else:
                parent.styles[plot_type]['Scale']['Length'] = None
                parent.update_SV()
                return

        scale_length = float(parent.lineEditScaleLength.text())
        if plot_type in parent.map_plot_types:
            # make sure user input is within bounds, do not change
            if ((parent.comboBoxScaleDirection.currentText() == 'horizontal') and (scale_length > parent.data[parent.sample_id].x_range)) or (scale_length <= 0):
                scale_length = parent.styles[plot_type]['Scale']['Length']
                parent.lineEditScaleLength.value = scale_length
                return
            elif ((parent.comboBoxScaleDirection.currentText() == 'vertical') and (scale_length > parent.data[parent.sample_id].y_range)) or (scale_length <= 0):
                scale_length = parent.styles[plot_type]['Scale']['Length']
                parent.lineEditScaleLength.value = scale_length
                return
        else:
            parent.lineEditScaleLength.value = None
            return

        # update style dictionary
        if scale_length == parent.styles[plot_type]['Scale']['Length']:
            return
        parent.styles[plot_type]['Scale']['Length'] = scale_length

        # update plot
        parent.update_SV()

    def overlay_color_callback(self):
        """Updates color of overlay markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonOverlayColor`` color.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonOverlayColor)

        color = get_hex_color(parent.toolButtonOverlayColor.palette().button().color())
        # update style
        if parent.styles[plot_type]['Scale']['OverlayColor'] == color:
            return

        parent.styles[plot_type]['Scale']['OverlayColor'] = color
        # update plot
        parent.update_SV()

    # markers
    # -------------------------------------
    def marker_symbol_callback(self):
        """Updates marker symbol

        Updates marker symbols on current plot on change of ``MainWindow.comboBoxMarker.currentText()``.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Markers']['Symbol'] == parent.comboBoxMarker.currentText():
            return
        parent.styles[plot_type]['Markers']['Symbol'] = parent.comboBoxMarker.currentText()

        parent.update_SV()

    def marker_size_callback(self):
        """Updates marker size

        Updates marker size on current plot on change of ``MainWindow.doubleSpinBoxMarkerSize.value()``.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Markers']['Size'] == parent.doubleSpinBoxMarkerSize.value():
            return
        parent.styles[plot_type]['Markers']['Size'] = parent.doubleSpinBoxMarkerSize.value()

        parent.update_SV()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.

        Executes on change of ``MainWindow.horizontalSliderMarkerAlpha.value()``.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        parent.labelMarkerAlpha.setText(str(parent.horizontalSliderMarkerAlpha.value()))

        if parent.horizontalSliderMarkerAlpha.isEnabled():
            parent.styles[plot_type]['Markers']['Alpha'] = float(parent.horizontalSliderMarkerAlpha.value())
            parent.update_SV()

    # lines
    # -------------------------------------
    def line_width_callback(self):
        """Updates line width

        Updates line width on current plot on change of ``MainWindow.comboBoxLineWidth.currentText().
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Lines']['LineWidth'] == float(parent.comboBoxLineWidth.currentText()):
            return

        parent.styles[plot_type]['Lines']['LineWidth'] = float(parent.comboBoxLineWidth.currentText())
        parent.update_SV()

    def length_multiplier_callback(self):
        """Updates line length multiplier

        Used when plotting vector components in multidimensional plots.  Values entered by the user must be (0,10]
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if not float(parent.lineEditLengthMultiplier.text()):
            parent.lineEditLengthMultiplier.values = parent.styles[plot_type]['Lines']['Multiplier']

        value = float(parent.lineEditLengthMultiplier.text())
        if parent.styles[plot_type]['Lines']['Multiplier'] == value:
            return
        elif (value < 0) or (value >= 100):
            parent.lineEditLengthMultiplier.values = parent.styles[plot_type]['Lines']['Multiplier']
            return

        parent.styles[plot_type]['Lines']['Multiplier'] = value
        parent.update_SV()

    def line_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonLineColor`` color.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonLineColor)
        color = get_hex_color(parent.toolButtonLineColor.palette().button().color())
        if parent.styles[plot_type]['Lines']['Color'] == color:
            return

        # update style
        parent.styles[plot_type]['Lines']['Color'] = color

        # update plot
        parent.update_SV()

    # colors
    # -------------------------------------
    def marker_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonMarkerColor`` color.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonMarkerColor)
        color = get_hex_color(parent.toolButtonMarkerColor.palette().button().color())
        if parent.styles[plot_type]['Colors']['Color'] == color:
            return

        # update style
        parent.styles[plot_type]['Colors']['Color'] = color

        # update plot
        parent.update_SV()

    def resolution_callback(self, update_plot=False):
        """Updates heatmap resolution

        Updates the resolution of heatmaps when ``MainWindow.spinBoxHeatmapResolution`` is changed.

        Parameters
        ----------
        update_plot : bool, optional
            Sets the resolution of a heatmap for either Cartesian or ternary plots and both *heatmap* and *pca heatmap*, by default ``False``
        """
        parent = self.parent

        style = parent.styles[parent.comboBoxPlotType.currentText()]

        style['Colors']['Resolution'] = parent.spinBoxHeatmapResolution.value()

        if update_plot:
            parent.update_SV()

    # updates scatter styles when ColorByField comboBox is changed
    def color_by_field_callback(self):
        """Executes on change to *ColorByField* combobox
        
        Updates style associated with ``MainWindow.comboBoxColorByField``.  Also updates
        ``MainWindow.comboBoxColorField`` and ``MainWindow.comboBoxColorScale``."""
        #print('color_by_field_callback')
        parent = self.parent

        # need this line to update field comboboxes when colorby field is updated
        parent.update_field_combobox(parent.comboBoxColorByField, parent.comboBoxColorField)
        parent.update_color_field_spinbox()
        plot_type = parent.comboBoxPlotType.currentText()
        if plot_type == '':
            return

        style = parent.styles[plot_type]
        if style['Colors']['ColorByField'] == parent.comboBoxColorByField.currentText():
            return

        style['Colors']['ColorByField'] = parent.comboBoxColorByField.currentText()
        if parent.comboBoxColorByField.currentText() != '':
            self.set_style_widgets(plot_type)

        if parent.comboBoxPlotType.isEnabled() == False | parent.comboBoxColorByField.isEnabled() == False:
            return

        # only run update current plot if color field is selected or the color by field is clusters
        if parent.comboBoxColorByField.currentText() != 'None' or parent.comboBoxColorField.currentText() != '' or parent.comboBoxColorByField.currentText() in ['cluster']:
            parent.update_SV()

    def color_field_callback(self, plot=True):
        """Updates color field and plot

        Executes on change of ``MainWindow.comboBoxColorField``
        """
        parent = self.parent

        #print('color_field_callback')
        data = parent.data[parent.sample_id]

        plot_type = parent.comboBoxPlotType.currentText()
        field = parent.comboBoxColorField.currentText()
        parent.update_color_field_spinbox()
        
        if parent.styles[plot_type]['Colors']['Field'] == field:
            return

        parent.styles[plot_type]['Colors']['Field'] = field

        if field != '' and field is not None:
            if field not in data.axis_dict.keys():
                self.initialize_axis_values(parent.comboBoxColorByField.currentText(), field)

            self.set_color_axis_widgets()
            if plot_type not in ['correlation']:
                parent.styles[plot_type]['Colors']['CLim'] = [data.axis_dict[field]['min'], data.axis_dict[field]['max']]
                parent.styles[plot_type]['Colors']['CLabel'] = data.axis_dict[field]['label']
        else:
            parent.lineEditCbarLabel.setText('')

        # update plot
        if plot:
            parent.update_SV()

    def color_field_update(self):
        """Updates ``MainWindow.comboBoxColorField``"""        
        parent = self.parent

        parent.spinBoxColorField.blockSignals(True)
        parent.comboBoxColorField.setCurrentIndex(parent.spinBoxColorField.value())
        self.color_field_callback(plot=True)
        parent.spinBoxColorField.blockSignals(False)

    def field_colormap_callback(self):
        """Sets the color map

        Sets the colormap in ``MainWindow.styles`` for the current plot type, set from ``MainWindow.comboBoxFieldColormap``.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Colors']['Colormap'] == parent.comboBoxFieldColormap.currentText():
            return

        self.toggle_style_widgets()
        parent.styles[parent.comboBoxPlotType.currentText()]['Colors']['Colormap'] = parent.comboBoxFieldColormap.currentText()

        parent.update_SV()

    def colormap_direction_callback(self):
        """Set colormap direction (normal/reverse)

        Reverses colormap if ``MainWindow.checkBoxReverseColormap.isChecked()`` is ``True``."""
        parent = self.parent

        plot_type = self.parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Colors']['Reverse'] == parent.checkBoxReverseColormap.isChecked():
            return

        parent.styles[plot_type]['Colors']['Reverse'] = parent.checkBoxReverseColormap.isChecked()

        parent.update_SV()

    def get_cluster_colormap(self, cluster_dict, alpha=100):
        """Converts hex colors to a colormap

        Creates a discrete colormap given a list of hex color strings.  The colors in cluster_dict are set/changed in the ``MainWindow.tableWidgetViewGroups``.

        Parameters
        ----------
        cluster_dict : dict
            Dictionary with cluster information    
        alpha : int, optional
            Transparency to be added to color, by default 100

        Returns
        -------
        matplotlib.colormap
            A discrete (colors.ListedColormap) colormap
        """
        n = cluster_dict['n_clusters']
        cluster_color = [None]*n
        cluster_label = [None]*n
        
        # convert colors from hex to rgb and add to cluster_color list
        for i in range(n):
            color = get_rgb_color(cluster_dict[i]['color'])
            cluster_color[i] = tuple(float(c)/255 for c in color) + (float(alpha)/100,)
            cluster_label[i] = cluster_dict[i]['name']

        # mask
        if 99 in list(cluster_dict.keys()):
            color = get_rgb_color(cluster_dict[99]['color'])
            cluster_color.append(tuple(float(c)/255 for c in color) + (float(alpha)/100,))
            cluster_label.append(cluster_dict[99]['name'])
            cmap = colors.ListedColormap(cluster_color, N=n+1)
        else:
            cmap = colors.ListedColormap(cluster_color, N=n)

        return cluster_color, cluster_label, cmap

    def get_colormap(self, N=None):
        """Gets the color map

        Gets the colormap from ``MainWindow.styles`` for the current plot type and reverses or sets as discrete in needed.

        Parameters
        ----------
        N : int, optional
            Creates a discrete color map, if not supplied, the colormap is continuous, Defaults to None.

        Returns
        -------
        matplotlib.colormap.ListedColormap : colormap
        """
        parent = self.parent

        if parent.canvasWindow.currentIndex() == parent.canvas_tab['qv']:
            plot_type = 'analyte map'
        else:
            plot_type = self.parent.comboBoxPlotType.currentText()

        name = parent.styles[plot_type]['Colors']['Colormap']
        if name in self.mpl_colormaps:
            if N is not None:
                cmap = plt.get_cmap(name, N)
            else:
                cmap = plt.get_cmap(name)
        else:
            cmap = self.create_custom_colormap(name, N)

        if parent.styles[plot_type]['Colors']['Reverse']:
            cmap = cmap.reversed()

        return cmap

    def create_custom_colormap(self, name, N=None):
        """Creates custom colormaps

        Custom colormaps as found in ``resources/appdata/custom_colormaps.xlsx``.

        Parameters
        ----------
        name : str
            Name of colormap
        N : int, optional
            Number of colors to compute using colormap, by default None

        Returns
        -------
        matplotlib.LinearSegmentedColormap
            Colormap
        """
        if N is None:
            N = 256

        color_list = get_rgb_color(self.parent.custom_color_dict[name])

        cmap = colors.LinearSegmentedColormap.from_list(name, color_list, N=N)

        return cmap

    def clim_callback(self):
        """Sets the color limits

        Sets the color limits in ``MainWindow.styles`` for the current plot type.
        """
        parent = self.parent

        plot_type = self.parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Colors']['CLim'][0] == float(parent.lineEditColorLB.text()) and parent.styles[plot_type]['Colors']['CLim'][1] == float(parent.lineEditColorUB.text()):
            return

        parent.styles[plot_type]['Colors']['CLim'] = [float(parent.lineEditColorLB.text()), float(parent.lineEditColorUB.text())]

        parent.update_SV()

    def cbar_direction_callback(self):
        """Sets the colorbar direction

        Sets the colorbar direction in ``MainWindow.styles`` for the current plot type.
        """
        parent = self.parent

        plot_type = self.parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Colors']['Direction'] == parent.comboBoxCbarDirection.currentText():
            return
        parent.styles[plot_type]['Colors']['Direction'] = parent.comboBoxCbarDirection.currentText()

        parent.update_SV()

    def cbar_label_callback(self):
        """Sets color label

        Sets the color label in ``MainWindow.styles`` for the current plot type.
        """
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if parent.styles[plot_type]['Colors']['CLabel'] == parent.lineEditCbarLabel.text():
            return
        parent.styles[plot_type]['Colors']['CLabel'] = parent.lineEditCbarLabel.text()

        if parent.comboBoxCbarLabel.isEnabled():
            parent.update_SV()

    # cluster styles
    # -------------------------------------
    def cluster_color_callback(self):
        """Updates color of a cluster

        Uses ``QColorDialog`` to select new cluster color and then updates plot on change of
        backround ``MainWindow.toolButtonClusterColor`` color.  Also updates ``MainWindow.tableWidgetViewGroups``
        color associated with selected cluster.  The selected cluster is determined by ``MainWindow.spinBoxClusterGroup.value()``
        """
        parent = self.parent
        #print('cluster_color_callback')
        if parent.tableWidgetViewGroups.rowCount() == 0:
            return

        selected_cluster = parent.spinBoxClusterGroup.value()-1

        # change color
        self.button_color_select(parent.toolButtonClusterColor)
        color = get_hex_color(parent.toolButtonClusterColor.palette().button().color())
        parent.cluster_dict[parent.cluster_dict['active method']][selected_cluster]['color'] = color
        if parent.tableWidgetViewGroups.item(selected_cluster,2).text() == color:
            return

        # update_table
        parent.tableWidgetViewGroups.setItem(selected_cluster,2,QTableWidgetItem(color))

        # update plot
        if parent.comboBoxColorByField.currentText() == 'cluster':
            parent.update_SV()

    def set_default_cluster_colors(self, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``MainWindow.tableWidgetViewGroups`` to the default colormap in
        ``MainWindow.styles['cluster']['Colors']['Colormap'].  Change the default colormap
        by changing ``MainWindow.comboBoxColormap``, when ``MainWindow.comboBoxColorByField.currentText()`` is ``Cluster``.

        Returns
        -------
            str : hexcolor
        """
        #print('set_default_cluster_colors')
        parent = self.parent

        # cluster colormap
        cmap = self.get_colormap(N=self.parent.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(parent.tableWidgetViewGroups.rowCount()):
            hexcolor.append(get_hex_color(colors[i]))
            parent.tableWidgetViewGroups.blockSignals(True)
            parent.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            parent.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(parent.styles['cluster']['Scale']['OverlayColor'])

        parent.toolButtonClusterColor.setStyleSheet("background-color: %s;" % parent.tableWidgetViewGroups.item(parent.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor

    def select_cluster_group_callback(self):
        """Set cluster color button background after change of selected cluster group

        Sets ``MainWindow.toolButtonClusterColor`` background on change of ``MainWindow.spinBoxClusterGroup``
        """
        parent = self.parent
        if parent.tableWidgetViewGroups.rowCount() == 0:
            return
        parent.toolButtonClusterColor.setStyleSheet("background-color: %s;" % parent.tableWidgetViewGroups.item(parent.spinBoxClusterGroup.value()-1,2).text())

    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        parent = self.parent
        for cmap in self.ternary_colormaps:
            if cmap['scheme'] == parent.comboBoxTernaryColormap.currentText():
                parent.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % cmap['top'])
                parent.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % cmap['left'])
                parent.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % cmap['right'])
                parent.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % cmap['center'])
    
    def button_color_select(self, button):
        """Select background color of button

        :param button: button clicked
        :type button: QPushbutton | QToolButton
        """
        old_color = button.palette().color(button.backgroundRole())
        color_dlg = QColorDialog(self.parent)
        color_dlg.setCurrentColor(old_color)
        color_dlg.setCustomColor(int(1),old_color)

        color = color_dlg.getColor()

        if color.isValid():
            button.setStyleSheet("background-color: %s;" % color.name())
            QColorDialog.setCustomColor(int(1),color)
            if button.accessibleName().startswith('Ternary'):
                button.setCurrentText('user defined')