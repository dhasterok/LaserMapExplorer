class StyleToolbox():
    def __init__(self, parent=None):
        super().__init__(parent)

    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        #print('toggle_style_widgets')
        plot_type = self.comboBoxPlotType.currentText().lower()

        # annotation properties
        self.fontComboBox.setEnabled(True)
        self.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'analyte map' | 'gradient map':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata) != 0:
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
                #if len(self.polygon.polygons) > 0:
                #    self.comboBoxLineWidth.setEnabled(True)
                #else:
                #    self.comboBoxLineWidth.setEnabled(False)
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                self.comboBoxColorField.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxColorScale.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'correlation' | 'vectors':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.comboBoxXScale.setEnabled(False)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)
                self.lineEditLengthMultiplier.setEnabled(False)
                self.toolButtonLineColor.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(False)
                if plot_type.lower() == 'correlation':
                    self.comboBoxColorByField.setEnabled(True)
                    if self.comboBoxColorByField.currentText() == 'Cluster':
                        self.comboBoxColorField.setEnabled(True)
                    else:
                        self.comboBoxColorField.setEnabled(False)

                else:
                    self.comboBoxColorByField.setEnabled(False)
                    self.comboBoxColorField.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'histogram':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(True)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                self.comboBoxColorScale.setEnabled(False)
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                else:
                    self.toolButtonMarkerColor.setEnabled(False)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)

                self.comboBoxFieldColormap.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'scatter' | 'pca scatter':
                # axes properties
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditXLB.setEnabled(True)
                    self.lineEditXUB.setEnabled(True)
                    self.comboBoxXScale.setEnabled(True)
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.comboBoxYScale.setEnabled(True)
                else:
                    self.lineEditXLB.setEnabled(False)
                    self.lineEditXUB.setEnabled(False)
                    self.comboBoxXScale.setEnabled(False)
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.comboBoxYScale.setEnabled(False)

                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if self.comboBoxFieldZ.currentText() == '':
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                if self.comboBoxFieldZ.currentText() == '':
                    self.comboBoxLineWidth.setEnabled(True)
                    self.toolButtonLineColor.setEnabled(True)
                else:
                    self.comboBoxLineWidth.setEnabled(False)
                    self.toolButtonLineColor.setEnabled(False)

                if plot_type == 'pca scatter':
                    self.lineEditLengthMultiplier.setEnabled(True)
                else:
                    self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)

                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                    self.lineEditCbarLabel.setEnabled(False)
                elif self.comboBoxColorByField.currentText() == 'Cluster':
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(False)
                else:
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    self.lineEditColorLB.setEnabled(True)
                    self.lineEditColorUB.setEnabled(True)
                    self.comboBoxColorScale.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'heatmap' | 'pca heatmap':
                # axes properties
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditXLB.setEnabled(True)
                    self.lineEditXUB.setEnabled(True)
                    self.comboBoxXScale.setEnabled(True)
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.comboBoxYScale.setEnabled(True)
                else:
                    self.lineEditXLB.setEnabled(False)
                    self.lineEditXUB.setEnabled(False)
                    self.comboBoxXScale.setEnabled(False)
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.comboBoxYScale.setEnabled(False)

                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                if self.comboBoxFieldZ.currentText() == '':
                    self.comboBoxLineWidth.setEnabled(True)
                    self.toolButtonLineColor.setEnabled(True)
                else:
                    self.comboBoxLineWidth.setEnabled(False)
                    self.toolButtonLineColor.setEnabled(False)

                if plot_type == 'pca heatmap':
                    self.lineEditLengthMultiplier.setEnabled(True)
                else:
                    self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxColorScale.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata.spots) != 0:
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
                self.lineEditLengthMultiplier.setEnabled(False)
                self.toolButtonLineColor.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'tec' | 'radar':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                if plot_type == 'tec':
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.lineEditYLabel.setEnabled(True)
                else:
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                elif self.comboBoxColorByField.currentText().lower() == 'cluster':
                    self.toolButtonMarkerColor.setEnabled(False)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(True)

                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'variance':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'pca score' | 'cluster score' | 'cluster':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata) != 0:
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
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                if plot_type == 'clusters':
                    self.comboBoxColorByField.setEnabled(False)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                    self.lineEditCbarLabel.setEnabled(False)
                else:
                    self.comboBoxColorByField.setEnabled(True)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    self.lineEditColorLB.setEnabled(True)
                    self.lineEditColorUB.setEnabled(True)
                    self.comboBoxColorScale.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(True)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'profile':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)

        # enable/disable labels
        # axes properties
        self.labelXLim.setEnabled(self.lineEditXLB.isEnabled())
        self.toolButtonXAxisReset.setEnabled(self.labelXLim.isEnabled())
        self.labelXScale.setEnabled(self.comboBoxXScale.isEnabled())
        self.labelYLim.setEnabled(self.lineEditYLB.isEnabled())
        self.toolButtonYAxisReset.setEnabled(self.labelYLim.isEnabled())
        self.labelYScale.setEnabled(self.comboBoxYScale.isEnabled())
        self.labelXLabel.setEnabled(self.lineEditXLabel.isEnabled())
        self.labelYLabel.setEnabled(self.lineEditYLabel.isEnabled())
        self.labelZLabel.setEnabled(self.lineEditZLabel.isEnabled())
        self.labelAspectRatio.setEnabled(self.lineEditAspectRatio.isEnabled())
        self.labelTickDirection.setEnabled(self.comboBoxTickDirection.isEnabled())

        # scalebar properties
        self.labelScaleLocation.setEnabled(self.comboBoxScaleLocation.isEnabled())
        self.labelScaleDirection.setEnabled(self.comboBoxScaleDirection.isEnabled())
        if self.toolButtonOverlayColor.isEnabled():
            self.labelOverlayColor.setEnabled(True)
        else:
            self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            self.labelOverlayColor.setEnabled(False)
        self.labelScaleLength.setEnabled(self.lineEditScaleLength.isEnabled())

        # marker properties
        self.labelMarker.setEnabled(self.comboBoxMarker.isEnabled())
        self.labelMarkerSize.setEnabled(self.doubleSpinBoxMarkerSize.isEnabled())
        self.labelTransparency.setEnabled(self.horizontalSliderMarkerAlpha.isEnabled())

        # line properties
        self.labelLineWidth.setEnabled(self.comboBoxLineWidth.isEnabled())
        self.labelLineColor.setEnabled(self.toolButtonLineColor.isEnabled())
        self.labelLengthMultiplier.setEnabled(self.lineEditLengthMultiplier.isEnabled())

        # color properties
        if self.toolButtonMarkerColor.isEnabled():
            self.labelMarkerColor.setEnabled(True)
        else:
            self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            self.labelMarkerColor.setEnabled(False)
        self.labelColorByField.setEnabled(self.comboBoxColorByField.isEnabled())
        self.labelColorField.setEnabled(self.comboBoxColorField.isEnabled())
        self.checkBoxReverseColormap.setEnabled(self.comboBoxFieldColormap.isEnabled())
        self.labelReverseColormap.setEnabled(self.checkBoxReverseColormap.isEnabled())
        self.labelFieldColormap.setEnabled(self.comboBoxFieldColormap.isEnabled())
        self.labelColorScale.setEnabled(self.comboBoxColorScale.isEnabled())
        self.labelColorBounds.setEnabled(self.lineEditColorLB.isEnabled())
        self.toolButtonCAxisReset.setEnabled(self.labelColorBounds.isEnabled())
        self.labelCbarDirection.setEnabled(self.comboBoxCbarDirection.isEnabled())
        self.labelCbarLabel.setEnabled(self.lineEditCbarLabel.isEnabled())
        self.labelHeatmapResolution.setEnabled(self.spinBoxHeatmapResolution.isEnabled())

    def set_style_widgets(self, plot_type=None, style=None):
        """Sets values in right toolbox style page

        Parameters
        ----------
        plot_type : str, optional
            dictionary key into ``MainWindow.style``
        style : dict, optional
            style dictionary
        """
        print('set_style_widgets')
        tab_id = self.toolBox.currentIndex()

        if plot_type is None:
            plot_type = self.plot_types[tab_id][self.plot_types[tab_id][0]+1]
            self.comboBoxPlotType.blockSignals(True)
            self.comboBoxPlotType.clear()
            self.comboBoxPlotType.addItems(self.plot_types[tab_id][1:])
            self.comboBoxPlotType.setCurrentText(plot_type)
            self.comboBoxPlotType.blockSignals(False)
        elif plot_type == '':
            return

        # toggle actionSwapAxes
        match plot_type:
            case 'analyte map':
                self.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.actionSwapAxes.setEnabled(True)
            case _:
                self.actionSwapAxes.setEnabled(False)

        if style is None:
            style = self.styles[plot_type]

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if plot_type.lower() in self.map_plot_types:
            if ('X' not in list(self.axis_dict.keys())) or ('Y' not in list(self.axis_dict.keys())):
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
            style['Axes']['AspectRatio'] = self.aspect_ratio

            # do not round axes limits for maps
            self.lineEditXLB.precision = None
            self.lineEditXUB.precision = None
            self.lineEditXLB.value = style['Axes']['XLim'][0]
            self.lineEditXUB.value = style['Axes']['XLim'][1]

            self.lineEditYLB.value = style['Axes']['YLim'][0]
            self.lineEditYUB.value = style['Axes']['YLim'][1]
        else:
            # round axes limits for everything that isn't a map
            self.lineEditXLB.setText(fmt.dynamic_format(style['Axes']['XLim'][0],order=3,toward=0))
            self.lineEditXUB.setText(fmt.dynamic_format(style['Axes']['XLim'][1],order=3,toward=1))

            self.lineEditYLB.setText(fmt.dynamic_format(style['Axes']['YLim'][0],order=3,toward=0))
            self.lineEditYUB.setText(fmt.dynamic_format(style['Axes']['YLim'][1],order=3,toward=1))

        self.comboBoxXScale.setCurrentText(style['Axes']['XScale'])
        self.lineEditXLabel.setText(style['Axes']['XLabel'])

        self.comboBoxYScale.setCurrentText(style['Axes']['YScale'])
        self.lineEditYLabel.setText(style['Axes']['YLabel'])

        self.lineEditZLabel.setText(style['Axes']['ZLabel'])
        self.lineEditAspectRatio.setText(str(style['Axes']['AspectRatio']))

        # annotation properties
        #self.fontComboBox.setCurrentFont(style['Text']['Font'])
        self.doubleSpinBoxFontSize.blockSignals(True)
        self.doubleSpinBoxFontSize.setValue(style['Text']['FontSize'])
        self.doubleSpinBoxFontSize.blockSignals(False)

        # scalebar properties
        self.comboBoxScaleLocation.setCurrentText(style['Scale']['Location'])
        self.comboBoxScaleDirection.setCurrentText(style['Scale']['Direction'])
        if (style['Scale']['Length'] is None) and (plot_type in self.map_plot_types):
            style['Scale']['Length'] = self.default_scale_length()

            self.lineEditScaleLength.value = style['Scale']['Length']
        else:
            self.lineEditScaleLength.value = None
            
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % style['Scale']['OverlayColor'])

        # marker properties
        self.comboBoxMarker.setCurrentText(style['Markers']['Symbol'])

        self.doubleSpinBoxMarkerSize.blockSignals(True)
        self.doubleSpinBoxMarkerSize.setValue(style['Markers']['Size'])
        self.doubleSpinBoxMarkerSize.blockSignals(False)

        self.horizontalSliderMarkerAlpha.setValue(int(style['Markers']['Alpha']))
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))

        # line properties
        self.comboBoxLineWidth.setCurrentText(str(style['Lines']['LineWidth']))
        self.lineEditLengthMultiplier.value = style['Lines']['Multiplier']
        self.toolButtonLineColor.setStyleSheet("background-color: %s;" % style['Lines']['Color'])

        # color properties
        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % style['Colors']['Color'])
        self.update_field_type_combobox(self.comboBoxColorByField,addNone=True,plot_type=plot_type)
        self.comboBoxColorByField.setCurrentText(style['Colors']['ColorByField'])

        if style['Colors']['ColorByField'] == '':
            self.comboBoxColorField.clear()
        else:
            self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)

        if style['Colors']['Field'] in self.comboBoxColorField.allItems():
            self.comboBoxColorField.setCurrentText(style['Colors']['Field'])
        else:
            style['Colors']['Field'] = self.comboBoxColorField.currentText()

        self.comboBoxFieldColormap.setCurrentText(style['Colors']['Colormap'])
        self.checkBoxReverseColormap.blockSignals(True)
        self.checkBoxReverseColormap.setChecked(style['Colors']['Reverse'])
        self.checkBoxReverseColormap.blockSignals(False)
        if style['Colors']['Field'] in list(self.axis_dict.keys()):
            style['Colors']['CLim'] = [self.axis_dict[style['Colors']['Field']]['min'], self.axis_dict[style['Colors']['Field']]['max']]
            style['Colors']['CLabel'] = self.axis_dict[style['Colors']['Field']]['label']
        self.lineEditColorLB.setText(fmt.dynamic_format(style['Colors']['CLim'][0],order=3,toward=0))
        self.lineEditColorUB.setText(fmt.dynamic_format(style['Colors']['CLim'][1],order=3,toward=1))
        if style['Colors']['ColorByField'] == 'Cluster':
            # set ColorField to active cluster method
            self.comboBoxColorField.setCurrentText(self.cluster_dict['active method'])

            # set color scale to discrete
            self.comboBoxColorScale.clear()
            self.comboBoxColorScale.addItem('discrete')
            self.comboBoxColorScale.setCurrentText('discrete')

            self.styles[plot_type]['Colors']['CScale'] = 'discrete'
        else:
            # set color scale options to linear/log
            self.comboBoxColorScale.clear()
            self.comboBoxColorScale.addItems(['linear','log'])
            self.comboBoxColorScale.setCurrentText(self.styles[plot_type]['Colors']['CScale'])
        self.comboBoxColorScale.setCurrentText(style['Colors']['CScale'])
        self.comboBoxCbarDirection.setCurrentText(style['Colors']['Direction'])
        self.lineEditCbarLabel.setText(style['Colors']['CLabel'])

        self.spinBoxHeatmapResolution.blockSignals(True)
        self.spinBoxHeatmapResolution.setValue(style['Colors']['Resolution'])
        self.spinBoxHeatmapResolution.blockSignals(False)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        # update plot (is this line needed)
        # self.update_SV()

    def get_style_dict(self):
        """Get style properties"""        
        plot_type = self.comboBoxPlotType.currentText()
        self.plot_types[self.toolBox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()

        # update axes properties
        self.styles[plot_type]['Axes'] = {'XLim': [float(self.lineEditXLB.text()), float(self.lineEditXUB.text())],
                    'XLabel': self.lineEditXLabel.text(),
                    'YLim': [float(self.lineEditYLB.text()), float(self.lineEditYUB.text())],
                    'YLabel': self.lineEditYLabel.text(),
                    'ZLabel': self.lineEditZLabel.text(),
                    'AspectRatio': float(self.lineEditAspectRatio.text()),
                    'TickDir': self.comboBoxTickDirection.text()}

        # update annotation properties
        self.styles[plot_type]['Text'] = {'Font': self.fontComboBox.currentFont(),
                    'FontSize': self.doubleSpinBoxFontSize.value()}

        # update scale properties
        self.styles[plot_type]['Scale'] = {'Location': self.comboBoxScaleLocation.currentText(),
                    'Direction': self.comboBoxScaleDirection.currentText(),
                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())}

        # update marker properties
        self.styles[plot_type]['Markers'] = {'Symbol': self.comboBoxMarker.currentText(),
                    'Size': self.doubleSpinBoxMarkerSize.value(),
                    'Alpha': float(self.horizontalSliderMarkerAlpha.value())}

        # update line properties
        self.styles[plot_type]['Lines'] = {'LineWidth': float(self.comboBoxLineWidth.currentText()),
                    'Multiplier': float(self.lineEditLengthMultiplier.text()),
                    'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color())}

        # update color properties
        self.styles[plot_type]['Colors'] = {'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color()),
                    'ColorByField': self.comboBoxColorByField.currentText(),
                    'Field': self.comboBoxColorField.currentText(),
                    'Colormap': self.comboBoxFieldColormap.currentText(),
                    'Reverse': self.checkBoxReverseColormap.isChecked(),
                    'CLim': [float(self.lineEditColorLB.text()), float(self.lineEditColorUB.text())],
                    'CScale': self.comboBoxColorScale.currentText(),
                    'Direction': self.comboBoxCbarDirection.currentText(),
                    'CLabel': self.lineEditCbarLabel.text(),
                    'Resolution': self.spinBoxHeatmapResolution.value()}

    # style widget callbacks
    # -------------------------------------
    def plot_type_callback(self, update=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        print('plot_type_callback')
        # set plot flag to false
        plot_type = self.comboBoxPlotType.currentText()
        self.plot_types[self.toolBox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()
        match plot_type:
            case 'analyte map':
                self.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.actionSwapAxes.setEnabled(True)
            case 'correlation':
                self.actionSwapAxes.setEnabled(False)
                if self.comboBoxCorrelationMethod.currentText() == 'None':
                    self.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case _:
                self.actionSwapAxes.setEnabled(False)

        self.set_style_widgets(plot_type=plot_type)
        self.check_analysis_type()

        if update:
            self.update_SV()

    # axes
    # -------------------------------------
    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.

        Parameters
        ----------
        ax : str
            axis, options include ``x``, ``y``, ``z``, and ``c``
        """
        plot_type = self.comboBoxPlotType.currentText()
        if ax == 'c':
            return self.comboBoxColorField.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return self.comboBoxHistField.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return self.comboBoxFieldX.currentText()
                    case 'y':
                        return self.comboBoxFieldY.currentText()
                    case 'z':
                        return self.comboBoxFieldZ.currentText()
            case 'pca scatter' | 'pca heatmap':
                match ax:
                    case 'x':
                        return f'PC{self.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{self.spinBoxPCY.value()}'
            case 'analyte map' | 'ternary map' | 'PCA Score' | 'Cluster' | 'Cluster Score':
                return ax.upper()


    def axis_label_edit_callback(self, ax, new_label):
        """Updates axis label in dictionaries from widget

        Parameters
        ----------
        ax : str
            axis, options include ``x``, ``y``, ``z``, and ``c``
        new_label : str
            new label set by user
        """
        plot_type = self.comboBoxPlotType.currentText()

        old_label = self.styles[plot_type]['Axes'][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        self.axis_dict[field]['label'] = new_label
        self.styles[plot_type]['Axes'][ax.upper()+'Label'] = new_label

        # update plot
        self.update_SV()

    def axis_limit_edit_callback(self, ax, bound, new_value):
        """Updates axis limit in dictionaries from widget

        Parameters
        ----------
        ax : str
            axis, options include ``x``, ``y``, ``z``, and ``c``
        bound : int
            ``0`` for lower and ``1`` for upper
        new_value : float
            new value set by user
        """
        plot_type = self.comboBoxPlotType.currentText()

        if ax == 'c':
            old_value = self.styles[plot_type]['Colors']['CLim'][bound]
        else:
            old_value = self.styles[plot_type]['Axes'][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ax == 'c' and plot_type in ['heatmap', 'correlation']:
            self.update_SV()
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                self.axis_dict[field]['pmax'] = new_value
                self.axis_dict[field]['pstatus'] = 'custom'
            else:
                self.axis_dict[field]['max'] = new_value
                self.axis_dict[field]['status'] = 'custom'
        else:
            if plot_type == 'histogram' and ax == 'y':
                self.axis_dict[field]['pmin'] = new_value
                self.axis_dict[field]['pstatus'] = 'custom'
            else:
                self.axis_dict[field]['min'] = new_value
                self.axis_dict[field]['status'] = 'custom'

        if ax == 'c':
            self.styles[plot_type]['Colors'][f'{ax.upper()}Lim'][bound] = new_value
        else:
            self.styles[plot_type]['Axes'][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        self.update_SV()

    def axis_scale_callback(self, comboBox, ax):
        """_summary_

        _extended_summary_

        Parameters
        ----------
        comboBox : QComboBox
            Field comboBox 
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        """        
        plot_type = self.comboBoxPlotType.currentText()

        new_value = comboBox.currentText()
        if ax == 'c':
            if self.styles[plot_type]['Colors']['CLim'] == new_value:
                return
        elif self.styles[plot_type]['Axes'][ax.upper()+'Scale'] == new_value:
            return

        field = self.get_axis_field(ax)
        self.axis_dict[field]['scale'] = new_value

        if ax == 'c':
            self.styles[plot_type]['Colors']['CScale'] = new_value
        else:
            self.styles[plot_type]['Axes'][ax.upper()+'Scale'] = new_value

        # update plot
        self.update_SV()

    def set_color_axis_widgets(self):
        """Sets the color axis widgets

        Sets color axis limits and label
        """
        #print('set_color_axis_widgets')
        field = self.comboBoxColorField.currentText()
        if field == '':
            return
        self.lineEditColorLB.setText(fmt.dynamic_format(self.axis_dict[field]['min'], order=3,toward=0))
        self.lineEditColorUB.setText(fmt.dynamic_format(self.axis_dict[field]['max'], order=3,toward=1))
        self.comboBoxColorScale.setCurrentText(self.axis_dict[field]['scale'])

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
        match ax:
            case 'x':
                if field == 'X':
                    self.lineEditXLB.value = self.axis_dict[field]['min']
                    self.lineEditXUB.value = self.axis_dict[field]['max']
                else:
                    self.lineEditXLB.setText(fmt.dynamic_format(self.axis_dict[field]['min'],order=3,toward=0))
                    self.lineEditXUB.setText(fmt.dynamic_format(self.axis_dict[field]['max'],order=3,toward=1))
                self.lineEditXLabel.setText(self.axis_dict[field]['label'])
                self.comboBoxXScale.setCurrentText(self.axis_dict[field]['scale'])
            case 'y':
                if self.comboBoxPlotType.currentText() == 'histogram':
                    self.lineEditYLB.setText(fmt.dynamic_format(self.axis_dict[field]['pmin'],order=3,toward=0))
                    self.lineEditYUB.setText(fmt.dynamic_format(self.axis_dict[field]['pmax'],order=3,toward=1))
                    self.lineEditYLabel.setText(self.comboBoxHistType.currentText())
                    self.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'X':
                        self.lineEditYLB.value = self.axis_dict[field]['min']
                        self.lineEditYUB.value = self.axis_dict[field]['max']
                    else:
                        self.lineEditYLB.setText(fmt.dynamic_format(self.axis_dict[field]['min'],order=3,toward=0))
                        self.lineEditYUB.setText(fmt.dynamic_format(self.axis_dict[field]['max'],order=3,toward=1))
                    self.lineEditYLabel.setText(self.axis_dict[field]['label'])
                    self.comboBoxYScale.setCurrentText(self.axis_dict[field]['scale'])
            case 'z':
                self.lineEditZLabel.setText(self.axis_dict[field]['label'])

    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Axes parameters with ``MainWindow.axis_dict['status']`` can be ``auto`` or ``custom``, where ``custom``
        is set by the user in the appropriate *lineEdit* widgets.  The ``auto`` status is set by the full range
        of values of a data column.        

        Parameters
        ----------
        ax : str
            Axis to reset values, can be ``x``, ``y``, and ``c``

        .. seealso::
            :ref: `initialize_axis_values` for initializing the axis dictionary
        """
        #print('axis_reset_callback')
        if ax == 'c':
            if self.comboBoxPlotType.currentText() == 'vectors':
                self.styles['vectors']['Colors']['CLim'] = [np.amin(self.pca_results.components_), np.amax(self.pca_results.components_)]
                self.set_color_axis_widgets()
            elif not (self.comboBoxColorByField.currentText() in ['None','Cluster']):
                field_type = self.comboBoxColorByField.currentText()
                field = self.comboBoxColorField.currentText()
                if field == '':
                    return
                self.initialize_axis_values(field_type, field)
                self.set_color_axis_widgets()
        else:
            match self.comboBoxPlotType.currentText().lower():
                case 'analyte map' | 'cluster' | 'cluster score' | 'pca score':
                    field = ax.upper()
                    self.initialize_axis_values('Analyte', field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = self.comboBoxHistField.currentText()
                    if ax == 'x':
                        field_type = self.comboBoxHistFieldType.currentText()
                        self.initialize_axis_values(field_type, field)
                        self.set_axis_widgets(ax, field)
                    else:
                        self.axis_dict[field].update({'pstatus':'auto', 'pmin':None, 'pmax':None})

                case 'scatter' | 'heatmap':
                    if ax == 'x':
                        field_type = self.comboBoxFieldTypeX.currentText()
                        field = self.comboBoxFieldX.currentText()
                    else:
                        field_type = self.comboBoxFieldTypeY.currentText()
                        field = self.comboBoxFieldY.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case 'pca scatter' | 'pca heatmap':
                    field_type = 'PCA Score'
                    if ax == 'x':
                        field = self.spinBoxPCX.currentText()
                    else:
                        field = self.spinBoxPCY.currentText()
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.update_SV()

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
            Stored axis: ``p`` for probability axis, otherwise all are same, by default None

        Returns
        -------
        float, float, str, float
            Axis parameters: minimum, maximum, scale (``linear`` or ``log``), axis label
        """        
        #print('get_axis_values')
        if field not in self.axis_dict.keys():
            self.initialize_axis_values(field_type, field)

        # get axis values from self.axis_dict
        amin = self.axis_dict[field]['min']
        amax = self.axis_dict[field]['max']
        scale = self.axis_dict[field]['scale']
        label = self.axis_dict[field]['label']

        # if probability axis associated with histogram
        if ax == 'p':
            pmin = self.axis_dict[field]['pmin']
            pmax = self.axis_dict[field]['pmax']
            return amin, amax, scale, label, pmin, pmax

        return amin, amax, scale, label

    def initialize_axis_values(self, field_type, field):
        """Initializes dictionary ``axis_dict`` values 

        Parameters
        ----------
        field_type : str
            Field type set by a comboBox associated with data type on an axis
        field : str
            Field set by a comboBox assocaiated with data on an axis
        """        
        #print('initialize_axis_values')
        # initialize variables
        if field not in self.axis_dict.keys():
            #print('initialize self.axis_dict["field"]')
            self.axis_dict.update({field:{'status':'auto', 'label':field, 'min':None, 'max':None}})

        #current_plot_df = pd.DataFrame()
        if field not in ['X','Y']:
            df = self.get_map_data(self.sample_id, field, field_type)
            array = df['array'][self.data[self.sample_id]['mask']].values if not df.empty else []
        else:
            # field 'X' and 'Y' require separate extraction
            array = self.data[self.sample_id]['raw_data'].loc[:,field].values

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                if field in ['X','Y']:
                    scale = 'linear'
                else:
                    #current_plot_df = self.data[self.sample_id]['processed_data'].loc[:,field].values
                    symbol, mass = self.parse_field(field)
                    if field_type == 'Analyte':
                        self.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol} ({self.preferences['Units']['Concentration']})"
                    else:
                        self.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol}$_N$ ({self.preferences['Units']['Concentration']})"

                    #amin = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'v_min'].values[0]
                    #amax = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'v_max'].values[0]
                    scale = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'norm'].values[0]

                amin = array.min()
                amax = array.max()
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                symbol_1, mass_1 = self.parse_field(field_1)
                symbol_2, mass_2 = self.parse_field(field_2)
                if field_type == 'Ratio':
                    self.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1} / $^{{{mass_2}}}${symbol_2}"
                else:
                    self.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1}$_N$ / $^{{{mass_2}}}${symbol_2}$_N$"

                amin = array.min()
                amax = array.max()
                scale = self.data[self.sample_id]['ratio_info'].loc[
                    (self.data[self.sample_id]['ratio_info']['analyte_1']==field_1) & (self.data[self.sample_id]['ratio_info']['analyte_2']==field_2),
                    'norm'].values[0]
            case _:
                #current_plot_df = self.data[self.sample_id]['computed_data'][field_type].loc[:,field].values
                scale = 'linear'

                amin = array.min()
                amax = array.max()

        # do not round 'X' and 'Y' so full extent of map is viewable
        if field not in ['X','Y']:
            amin = fmt.oround(amin, order=2, toward=0)
            amax = fmt.oround(amax, order=2, toward=1)

        d = {'status':'auto', 'min':amin, 'max':amax, 'scale':scale}

        self.axis_dict[field].update(d)
        #print(self.axis_dict[field])