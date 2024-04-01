from PyQt5 import QtWidgets, QtCore, QtGui
from src.ui.MainWindow import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.default_styles = {'Axes': {'XLimAuto': True, 'XLim':[0,0], 'XLabel':'', 'YLimCustom': True, 'YLim': [0,0], 'YLabel':'', 'AspectRatio': '1.0', 'TickDir': 'out'},
                               'Annotations': {'Font': self.fontComboBox.currentFont(), 'FontSize': 11.0},
                               'Scales': {'Location': 'northeast', 'Direction': 'none', 'OverlayColor': '#ffffff'},
                               'Markers': {'Symbol': 'circle', 'Size': 6, 'Alpha': 30},
                               'Lines': {'LineWidth': 1.5},
                               'Colors': {'Color': '#1c75bc', 'ColorByField': 'None', 'Field': None, 'Colormap': 'viridis', 'CLim':[0,0], 'Direction': 'none', 'CLabel': None, 'Resolution': 10}
                               }

        self.plot_types = {self.sample_tab_id: ['analyte map','correlation'],
                           self.process_tab_id: ['analyte map','histogram','gradient map'],
                           self.filter_tab_id: ['analyte map'],
                           self.scatter_tab_id: ['scatter', 'heatmap', 'ternary map'],
                           self.ndim_tab_id: ['TEC/radar'],
                           self.pca_tab_id: ['variance','vectors','x vs. y scatter','x vs. y heatmap','pca score map'],
                           self.cluster_tab_id: ['cluster map', 'cluster score map'],
                           self.profile_tab_id: ['profile']}

        self.styles = {'analyte map': self.default_styles,
                        'correlation': self.default_styles,
                        'histogram': self.default_styles,
                        'gradient map': self.default_styles, 
                        'scatter': self.default_styles, 
                        'heatmap': self.default_styles, 
                        'ternary map': self.default_styles, 
                        'TEC/radar': self.default_styles, 
                        'variance': self.default_styles, 
                        'vectors': self.default_styles, 
                        'x vs. y scatter': self.default_styles, 
                        'x vs. y heatmap': self.default_styles, 
                        'pca score map': self.default_styles,
                        'cluster map': self.default_styles,
                        'cluster score map': self.default_styles,
                        'profile': self.default_styles}

    def toggle_style(self):
        plot_type = self.comboBoxStylePlotType.currentText()

        match plot_type:
            case 'analyte map' | 'gradient map':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(True)
                self.doubleSpinBoxXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(True)
                self.doubleSpinBoxYUB.setEnabled(True)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # annotation properties
                self.fontComboBox.setEnabled(True)
                self.doubleSpinBoxFontSize.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)
                if self.comboBoxScaleLocation.currentValue().lower() != 'none':
                    self.comboBoxScaleLocation.setEnabled(True)
                else:
                    self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                if len(self.spotdata.spots[self.sample_id]) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                if len(self.polygon.polygons) != 0:
                    self.comboBoxLineWidth.setEnabled(True)
                else:
                    self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                self.comboBoxColorField.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                self.doubleSpinBoxColorLB.setEnabled(True)
                self.doubleSpinBoxColorUB.setEnabled(True)
                self.comboBoxColorbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'correlation':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # annotation properties
                self.fontComboBox.setEnabled(False)
                self.doubleSpinBoxFontSize.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.self.doubleSpinBoxMarkerSize.setEnabled(False)
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
                self.lineEditXLabel.setEnabled(False)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)

                # annotation properties
                self.fontComboBox.setEnabled(False)
                self.doubleSpinBoxFontSize.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
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
            case 'scatter':
            case 'heatmap':
            case 'ternary map':
            case 'TEC/radar':
                # axes properties
                self.doubleSpinBoxXLB.setEnabled(False)
                self.doubleSpinBoxXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.doubleSpinBoxYLB.setEnabled(False)
                self.doubleSpinBoxYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)

                # annotation properties
                self.fontComboBox.setEnabled(False)
                self.doubleSpinBoxFontSize.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.self.doubleSpinBoxMarkerSize.setEnabled(False)
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
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'variance':
            case 'vectors':
            case 'x vs. y scatter':
            case 'x vs. y heatmap':
            case 'pca score map':
            case 'cluster map':
            case 'cluster score map':
            case 'profile':

    def set_style(self, plot_type=None):

        tab_id = self.toolBox.currentIndex()

        if plot_type is None:
            self.comboBoxStylePlotType.clear()
            self.comboBoxStylePlotType.addItems(self.plot_types[tab_id])

            plot_type = self.plot_types[tab_id](0)

        # axes properties
        self.doubleSpinBoxXLB.setValue(self.styles[plot_type]['Axes']['XLim'](0))
        self.doubleSpinBoxXUB.setValue(self.styles[plot_type]['Axes']['XLim'](1))
        self.lineEditXLabel.setText(self.styles[plot_type]['Axes']['XLabel'])
        self.doubleSpinBoxYLB.setValue(self.styles[plot_type]['Axes']['YLim'](0))
        self.doubleSpinBoxYUB.setValue(self.styles[plot_type]['Axes']['YLim'](1))
        self.lineEditYLabel.setText(self.styles[plot_type]['Axes']['YLabel'])
        self.lineEditAspectRatio.setText(str(self.styles[plot_type]['Axes']['AspectRatio']))

        # annotation properties
        self.fontComboBox.setFont(self.styles[plot_type]['Annotations']['Font'])
        self.doubleSpinBoxFontSize.setValue(self.styles[plot_type]['Annotations']['FontSize'])

        # scalebar properties
        self.comboBoxScaleLocation.setCurrentText(self.styles[plot_type]['Scales']['Location'])
        self.comboBoxScaleDirection.setCurrentText(self.styles[plot_type]['Scales']['Direction'])
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % self.styles[plot_type]['Scales']['OverlayColor'])

        # marker properties
        self.comboBoxMarker.setCurrentText(self.styles[plot_type]['Markers']['Symbol'])
        self.self.doubleSpinBoxMarkerSize.setValue(self.styles[plot_type]['Markers']['Size'])
        self.horizontalSliderMarkerAlpha.setValue(int(self.styles[plot_type]['Markers']['Alpha']))
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))

        # line properties
        self.comboBoxLineWidth.setCurrentText(str(self.styles[plot_type]['Lines']['LineWidth']))

        # color properties
        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.styles[plot_type]['Colors']['Color'])
        self.comboBoxColorByField.setCurrentText(self.styles[plot_type]['Colors']['ColorByField'])
        self.comboBoxColorField.setCurrentText(self.styles[plot_type]['Colors']['Field'])
        self.comboBoxFieldColormap.setCurrentText(self.styles[plot_type]['Colors']['Colormap'])
        self.doubleSpinBoxColorLB.setValue(self.styles[plot_type]['Colors']['CLim'](0))
        self.doubleSpinBoxColorUB.setValue(self.styles[plot_type]['Colors']['CLim'](1))
        self.comboBoxColorbarDirection.setCurrentText(self.styles[plot_type]['Colors']['Direction'])
        self.lineEditCbarLabel.setCurrentText(self.styles[plot_type]['Colors']['CLabel'])
        self.spinBoxHeatmapResolution.setValue(self.styles[plot_type]['Colors']['Resolution'])

        # turn properties on/off based on plot type and style settings
        self.toggle_style()

        # update plot
        self.update_plot()

    def get_style(self):
        plot_type = self.comboBoxStylePlotType.currentText()

        # update axes properties
        self.styles[plot_type]['Axes'] = {'XLim': [self.doubleSpinBoxXLB.value(), self.doubleSpinBoxXUB.value()],
                    'XLabel': self.lineEditXLabel.currentText(),
                    'YLim': [self.doubleSpinBoxYLB.value(), self.doubleSpinBoxYUB.value()],
                    'YLabel': self.lineEditYLabel.currentText(),
                    'AspectRatio': double(self.lineEditAspectRatio.currentText()),
                    'TickDir': self.comboBoxTickDirection.currentText()}

        # update annotation properties
        self.styles[plot_type]['Annotations'] = {'Font': self.fontComboBox.currentFont(),
                    'FontSize': self.doubleSpinBoxFontSize.value()}

        # update scale properties
        self.styles[plot_type]['Scales'] = {'Location': self.comboBoxScaleLocation.currentText(),
                    'Direction': self.comboBoxScaleDirection.currentText(),
                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())}

        # update marker properties
        self.styles[plot_type]['Markers'] = {'Symbol': self.comboBoxMarker.currentText(),
                    'Size': self.self.doubleSpinBoxMarkerSize.value(),
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
