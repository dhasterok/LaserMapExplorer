from PyQt5 import QtWidgets, QtCore, QtGui
from src.ui.MainWindow import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.default_styles = {'Axes': {'XLimAuto': True, 'XLim': [0,0], 'XLabel': '', 'YLimCustom': True, 'YLim': [0,0], 'YLabel': '', 'ZLabel': '', 'AspectRatio': '1.0', 'TickDir': 'out'},
                               'Text': {'Font': self.fontComboBox.currentFont(), 'FontSize': 11.0},
                               'Scales': {'Location': 'northeast', 'Direction': 'none', 'OverlayColor': '#ffffff'},
                               'Markers': {'Symbol': 'circle', 'Size': 6, 'Alpha': 30},
                               'Lines': {'LineWidth': 1.5},
                               'Colors': {'Color': '#1c75bc', 'ColorByField': 'None', 'Field': None, 'Colormap': 'viridis', 'CLimAuto': True, 'CLim':[0,0], 'Direction': 'none', 'CLabel': None, 'Resolution': 10}
                               }

        self.plot_types = {self.sample_tab_id: ['analyte map','correlation'],
                           self.process_tab_id: ['analyte map','histogram','gradient map'],
                           self.filter_tab_id: ['analyte map'],
                           self.scatter_tab_id: ['scatter', 'heatmap', 'ternary map'],
                           self.ndim_tab_id: ['TEC', 'radar'],
                           self.pca_tab_id: ['variance','vectors','PCx vs. PCy scatter','PCx vs. PCy heatmap','pca score'],
                           self.cluster_tab_id: ['cluster', 'cluster score'],
                           self.profile_tab_id: ['profile']}

        self.styles = {'analyte map': self.default_styles,
                        'correlation': self.default_styles,
                        'histogram': self.default_styles,
                        'gradient map': self.default_styles, 
                        'scatter': self.default_styles, 
                        'heatmap': self.default_styles, 
                        'ternary map': self.default_styles, 
                        'TEC': self.default_styles, 
                        'radar': self.default_styles, 
                        'variance': self.default_styles, 
                        'vectors': self.default_styles, 
                        'PCx vs. PCy scatter': self.default_styles, 
                        'PCx vs. PCy heatmap': self.default_styles, 
                        'PCA score': self.default_styles,
                        'cluster': self.default_styles,
                        'cluster score': self.default_styles,
                        'profile': self.default_styles}

    def toggle_style_widgets(self):
        plot_type = self.comboBoxStylePlotType.currentText().lower()

        # annotation properties
        self.fontComboBox.setEnabled(True)
        self.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type:
            case 'analyte map' | 'gradient map':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(True)
                self.doubleSpinBoxYUB.setEnabled(True)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)

                # marker properties
                if len(self.spotdata.spots[self.sample_id]) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                self.comboBoxColorField.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                self.doubleSpinBoxColorLB.setEnabled(True)
                self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'correlation' | 'vectors':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                if plot_type == 'vectors':
                    self.lineEditXLabel.setEnabled(True)
                    self.lineEditYLabel.setEnabled(True)
                else:
                    self.lineEditXLabel.setEnabled(False)
                    self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.doubleSpinBoxColorLB.setEnabled(True)
                self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'histogram':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                self.comboBoxColorField.setEnabled(False)
                if self.comboBoxColorByField.currentText() == 'Clusters':
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxFieldColormap.setEnabled(True)
                    self.doubleSpinBoxColorLB.setEnabled(True)
                    self.doubleSpinBoxColorUB.setEnabled(True)
                    self.comboBoxColorbarDirection.setEnabled(True)
                else:
                    self.toolButtonMarkerColor.setEnabled(True)

                    self.comboBoxFieldColormap.setEnabled(False)
                    self.doubleSpinBoxColorLB.setEnabled(False)
                    self.doubleSpinBoxColorUB.setEnabled(False)
                    self.comboBoxColorbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'scatter' | 'pcx vs. pcy scatter':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(True)
                self.doubleSpinBoxYLB.setEnabled(True)
                self.doubleSpinBoxYUB.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if self.comboBoxScatterAnalyteZ.currentText() == '':
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if self.comboBoxColorByField.currentText() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)

                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.doubleSpinBoxColorLB.setEnabled(False)
                    self.doubleSpinBoxColorUB.setEnabled(False)
                    self.comboBoxColorbarDirection.setEnabled(False)
                    self.lineEditCbarLabel.setEnabled(False)
                else:
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    self.doubleSpinBoxColorLB.setEnabled(True)
                    self.doubleSpinBoxColorUB.setEnabled(True)
                    self.comboBoxColorbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'heatmap' | 'pcx vs. pcy heatmap':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(True)
                self.doubleSpinBoxYLB.setEnabled(True)
                self.doubleSpinBoxYUB.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if self.comboBoxScatterAnalyteZ.currentText() == '':
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.doubleSpinBoxColorLB.setEnabled(True)
                self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                if len(self.spotdata.spots[self.sample_id]) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.doubleSpinBoxColorLB.setEnabled(False)
                self.doubleSpinBoxColorUB.setEnabled(False)
                self.comboBoxColorbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'tec' | 'radar':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                if plot_type == 'tec':
                    self.lineEditYLabel.setEnabled(True)
                else:
                    self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.doubleSpinBoxColorLB.setEnabled(False)
                self.doubleSpinBoxColorUB.setEnabled(False)
                self.comboBoxColorbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'variance':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.doubleSpinBoxColorLB.setEnabled(False)
                self.doubleSpinBoxColorUB.setEnabled(False)
                self.comboBoxColorbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'pca score' | 'cluster score' | 'clusters':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(True)
                self.doubleSpinBoxYUB.setEnabled(True)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)

                # marker properties
                if len(self.spotdata.spots[self.sample_id]) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                if plot_type == 'cluster map':
                    self.doubleSpinBoxColorLB.setEnabled(False)
                    self.doubleSpinBoxColorUB.setEnabled(False)
                else:
                    self.doubleSpinBoxColorLB.setEnabled(True)
                    self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'profile':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(True)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                self.doubleSpinBoxColorLB.setEnabled(True)
                self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)
                self.spinBoxHeatmapResolution.setEnabled(False)

    def set_style_widgets(self, plot_type=None):

        tab_id = self.toolBox.currentIndex()

        if plot_type is None:
            self.comboBoxStylePlotType.clear()
            self.comboBoxStylePlotType.addItems(self.plot_types[tab_id])

            plot_type = self.plot_types[tab_id][0]

        # axes properties
        self.doubleSpinBoxXLB.setValue(self.styles[plot_type]['Axes']['XLim'][0])
        self.doubleSpinBoxXUB.setValue(self.styles[plot_type]['Axes']['XLim'][1])
        self.lineEditXLabel.setText(self.styles[plot_type]['Axes']['XLabel'])
        self.doubleSpinBoxYLB.setValue(self.styles[plot_type]['Axes']['YLim'][0])
        self.doubleSpinBoxYUB.setValue(self.styles[plot_type]['Axes']['YLim'][1])
        self.lineEditYLabel.setText(self.styles[plot_type]['Axes']['YLabel'])
        self.lineEditZLabel.setText(self.styles[plot_type]['Axes']['ZLabel'])
        self.lineEditAspectRatio.setText(str(self.styles[plot_type]['Axes']['AspectRatio']))

        # annotation properties
        self.fontComboBox.setFont(self.styles[plot_type]['Text']['Font'])
        self.doubleSpinBoxFontSize.setValue(self.styles[plot_type]['Text']['FontSize'])

        # scalebar properties
        self.comboBoxScaleLocation.setCurrentText(self.styles[plot_type]['Scales']['Location'])
        self.comboBoxScaleDirection.setCurrentText(self.styles[plot_type]['Scales']['Direction'])
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % self.styles[plot_type]['Scales']['OverlayColor'])

        # marker properties
        self.comboBoxMarker.setCurrentText(self.styles[plot_type]['Markers']['Symbol'])
        self.doubleSpinBoxMarkerSize.setValue(self.styles[plot_type]['Markers']['Size'])
        self.horizontalSliderMarkerAlpha.setValue(int(self.styles[plot_type]['Markers']['Alpha']))
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))

        # line properties
        self.comboBoxLineWidth.setCurrentText(str(self.styles[plot_type]['Lines']['LineWidth']))

        # color properties
        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.styles[plot_type]['Colors']['Color'])
        self.comboBoxColorByField.setCurrentText(self.styles[plot_type]['Colors']['ColorByField'])
        self.comboBoxColorField.setCurrentText(self.styles[plot_type]['Colors']['Field'])
        self.comboBoxFieldColormap.setCurrentText(self.styles[plot_type]['Colors']['Colormap'])
        self.doubleSpinBoxColorLB.setValue(self.styles[plot_type]['Colors']['CLim'][0])
        self.doubleSpinBoxColorUB.setValue(self.styles[plot_type]['Colors']['CLim'][1])
        self.comboBoxColorbarDirection.setCurrentText(self.styles[plot_type]['Colors']['Direction'])
        self.lineEditCbarLabel.setText(self.styles[plot_type]['Colors']['CLabel'])
        self.spinBoxHeatmapResolution.setValue(self.styles[plot_type]['Colors']['Resolution'])

        # turn properties on/off based on plot type and style settings
        self.toggle_style()

        # update plot
        #self.update_plot()

    def get_style_dict(self):
        plot_type = self.comboBoxStylePlotType.currentText()

        # update axes properties
        self.styles[plot_type]['Axes'] = {'XLim': [self.doubleSpinBoxXLB.value(), self.doubleSpinBoxXUB.value()],
                    'XLabel': self.lineEditXLabel.currentText(),
                    'YLim': [self.doubleSpinBoxYLB.value(), self.doubleSpinBoxYUB.value()],
                    'YLabel': self.lineEditYLabel.currentText(),
                    'ZLabel': self.lineEditZLabel.currentText(),
                    'AspectRatio': float(self.lineEditAspectRatio.currentText()),
                    'TickDir': self.comboBoxTickDirection.currentText()}

        # update annotation properties
        self.styles[plot_type]['Text'] = {'Font': self.fontComboBox.currentFont(),
                    'FontSize': self.doubleSpinBoxFontSize.value()}

        # update scale properties
        self.styles[plot_type]['Scales'] = {'Location': self.comboBoxScaleLocation.currentText(),
                    'Direction': self.comboBoxScaleDirection.currentText(),
                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())}

        # update marker properties
        self.styles[plot_type]['Markers'] = {'Symbol': self.comboBoxMarker.currentText(),
                    'Size': self.doubleSpinBoxMarkerSize.value(),
                    'Alpha': float(self.horizontalSliderMarkerAlpha.value())}

        # update line properties
        self.styles[plot_type]['Lines']['LineWidth'] = float(self.comboBoxLineWidth.currentText())

        # update color properties
        self.styles[plot_type]['Colors'] = {'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color()),
                    'ColorByField': self.comboBoxColorByField.currentText(),
                    'Field': self.comboBoxColorField.currentText(),
                    'Colormap': self.comboBoxFieldColormap.currentText(),
                    'CLim': [self.doubleSpinBoxColorLB.value(), self.doubleSpinBoxColorUB.value()],
                    'Direction': self.comboBoxColorbarDirection.currentText(),
                    'CLabel': self.lineEditCbarLabel.currentText(),
                    'Resolution': self.spinBoxHeatmapResolution.value()}