
import sys, os, re, copy, random, darkdetect
from PyQt6.QtCore import ( Qt, QTimer, QUrl, QSize, QRectF )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
)
from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon )
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from src.common.LamePlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot
import src.common.csvdict as csvdict
from src.common.TableFunctions import TableFcn as TableFcn
import src.common.CustomMplCanvas as mplc
import src.app.QuickView as QV
from src.app.config import BASEDIR, ICONPATH, SSPATH, load_stylesheet
from src.common.Logger import auto_log_methods, log, no_log

@auto_log_methods(logger_key='Canvas')
class CanvasWidget():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Canvas"

        self.duplicate_plot_info = None
        self.lasermaps = {}

        self.ui.canvasWindow.currentChanged.connect(lambda: self.canvas_changed())
        self.ui.canvasWindow.setCurrentIndex(self.ui.canvas_tab['sv'])
        self.canvas_changed()

    def init_canvas_widget(self):
        """Initializes the central canvas tabs"""
        # Plot Layouts
        #-------------------------
        # Central widget plot view layouts
        # single view
        layout_single_view = QVBoxLayout()
        layout_single_view.setSpacing(0)
        layout_single_view.setContentsMargins(0, 0, 0, 0)
        self.ui.widgetSingleView.setLayout(layout_single_view)
        self.ui.widgetSingleView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mpl_toolbar = None
        #self.mpl_toolbar = NavigationToolbar(mplc.MplCanvas())
        # for button show hide
        #self.toolButtonPopFigure.setVisible(False)
        #self.toolButtonPopFigure.raise_()
        #self.toolButtonPopFigure.enterEvent = self.mouseEnter
        #self.toolButtonPopFigure.leaveEvent = self.mouseLeave

        layout_histogram_view = QVBoxLayout()
        layout_histogram_view.setSpacing(0)
        layout_histogram_view.setContentsMargins(0, 0, 0, 0)
        self.ui.widgetHistView.setLayout(layout_histogram_view)

        # multi-view
        self.multi_view_index = []
        self.multiview_info_label = {}
        layout_multi_view = QGridLayout()
        layout_multi_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_multi_view.setContentsMargins(0, 0, 0, 0)
        self.ui.widgetMultiView.setLayout(layout_multi_view)
        self.ui.widgetMultiView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ui.toolButtonRemoveMVPlot.clicked.connect(lambda: self.remove_multi_plot(self.ui.comboBoxMVPlots.currentText()))
        self.ui.toolButtonRemoveAllMVPlots.clicked.connect(lambda: self.clear_layout(self.ui.widgetMultiView.layout()))

        # quick view
        layout_quick_view = QGridLayout()
        layout_quick_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_quick_view.setContentsMargins(0, 0, 0, 0)
        self.ui.widgetQuickView.setLayout(layout_quick_view)
        self.ui.widgetQuickView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        try:
            self.QV_analyte_list = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/styles/qv_lists.csv'))
        except:
            self.QV_analyte_list = {'default':['Si29','Ti47','Al27','Cr52','Fe56','Mn55','Mg24','Ca43','K39','Na23','P31',
                'Ba137','Th232','U238','La139','Ce140','Pb206','Pr141','Sr88','Zr90','Hf178','Nd146','Eu153',
                'Gd157','Tb159','Dy163','Ho165','Y89','Er166','Tm169','Yb172','Lu175']}

        self.ui.toolButtonNewList.clicked.connect(lambda: QV.QuickView(self))
        self.ui.comboBoxQVList.activated.connect(lambda: self.display_QV())

    def canvas_changed(self):
        """Sets visibility of canvas tools and updates canvas plots"""        
        ui = self.ui

        if ui.app_data.sample_id == '':
            ui.toolButtonHome.setVisible(False)
            ui.toolButtonPan.setVisible(False)
            ui.toolButtonZoom.setVisible(False)
            ui.toolButtonAnnotate.setVisible(False)
            ui.toolButtonDistance.setVisible(False)
            ui.toolButtonPopFigure.setVisible(False)
            ui.toolButtonSave.setVisible(False)
            ui.widgetPlotInfoSV.hide()
            ui.labelMaxRows.setVisible(False)
            ui.spinBoxMaxRows.setVisible(False)
            ui.labelMaxCols.setVisible(False)
            ui.spinBoxMaxCols.setVisible(False)
            ui.comboBoxMVPlots.setVisible(False)
            ui.toolButtonRemoveMVPlot.setVisible(False)
            ui.toolButtonRemoveAllMVPlots.setVisible(False)
            ui.widgetPlotInfoMV.hide()
            ui.comboBoxQVList.setVisible(False)
            ui.toolButtonNewList.setVisible(False)

            ui.actionUpdatePlot.setEnabled(False)
            ui.actionSavePlotToTree.setEnabled(False)
            return

        if ui.canvasWindow.currentIndex() == ui.canvas_tab['sv']:
            # plot toolbar items
            ui.toolButtonHome.setVisible(True)
            ui.toolButtonPan.setVisible(True)
            ui.toolButtonZoom.setVisible(True)
            ui.toolButtonAnnotate.setVisible(True)
            ui.toolButtonDistance.setVisible(True)
            ui.toolButtonPopFigure.setVisible(True)
            ui.toolButtonSave.setVisible(True)
            ui.widgetPlotInfoSV.show()
            ui.labelMaxRows.setVisible(False)
            ui.spinBoxMaxRows.setVisible(False)
            ui.labelMaxCols.setVisible(False)
            ui.spinBoxMaxCols.setVisible(False)
            ui.comboBoxMVPlots.setVisible(False)
            ui.toolButtonRemoveMVPlot.setVisible(False)
            ui.toolButtonRemoveAllMVPlots.setVisible(False)
            ui.widgetPlotInfoMV.hide()
            ui.comboBoxQVList.setVisible(False)
            ui.toolButtonNewList.setVisible(False)

            ui.SelectAnalytePage.setEnabled(True)
            ui.PreprocessPage.setEnabled(True)
            ui.ScatterPage.setEnabled(True)
            ui.NDIMPage.setEnabled(True)
            ui.MultidimensionalPage.setEnabled(True)
            ui.ClusteringPage.setEnabled(True)
            if hasattr(ui, "spot_tools"):
                ui.spot_tools.setEnabled(True)
            if hasattr(ui, "special_tools"):
                ui.special_tools.setEnabled(True)
            if hasattr(ui, "mask_dock"):
                ui.mask_dock.setEnabled(True)

            ui.toolBoxStyle.setEnabled(True)
            ui.comboBoxPlotType.setEnabled(True)
            ui.comboBoxStyleTheme.setEnabled(True)
            ui.actionUpdatePlot.setEnabled(True)
            ui.actionSavePlotToTree.setEnabled(True)
            ui.toolButtonSaveTheme.setEnabled(True)

            ui.dockWidgetStyling.setEnabled(True)

            if self.duplicate_plot_info:
                ui.add_plotwidget_to_canvas(self.duplicate_plot_info)
        elif ui.canvasWindow.currentIndex() == ui.canvas_tab['mv']:
            # plot toolbar items
            ui.toolButtonHome.setVisible(False)
            ui.toolButtonPan.setVisible(False)
            ui.toolButtonZoom.setVisible(False)
            ui.toolButtonAnnotate.setVisible(False)
            ui.toolButtonDistance.setVisible(False)
            ui.toolButtonPopFigure.setVisible(False)
            ui.toolButtonSave.setVisible(True)
            ui.widgetPlotInfoSV.hide()
            ui.labelMaxRows.setVisible(True)
            ui.spinBoxMaxRows.setVisible(True)
            ui.labelMaxCols.setVisible(True)
            ui.spinBoxMaxCols.setVisible(True)
            ui.comboBoxMVPlots.setVisible(True)
            ui.toolButtonRemoveMVPlot.setVisible(True)
            ui.toolButtonRemoveAllMVPlots.setVisible(True)
            ui.widgetPlotInfoMV.show()
            ui.comboBoxQVList.setVisible(False)
            ui.toolButtonNewList.setVisible(False)

            ui.SelectAnalytePage.setEnabled(False)
            ui.PreprocessPage.setEnabled(False)
            ui.ScatterPage.setEnabled(False)
            ui.NDIMPage.setEnabled(False)
            ui.MultidimensionalPage.setEnabled(False)
            ui.ClusteringPage.setEnabled(False)
            if hasattr(ui, "spot_tools"):
                ui.spot_tools.setEnabled(False)
            if hasattr(ui, "special_tools"):
                ui.special_tools.setEnabled(False)
            if hasattr(ui, "mask_dock"):
                ui.mask_dock.setEnabled(False)

            ui.actionUpdatePlot.setEnabled(False)
            ui.actionSavePlotToTree.setEnabled(False)

            ui.dockWidgetStyling.setEnabled(False)
            if self.duplicate_plot_info:
                ui.add_plotwidget_to_canvas(self.duplicate_plot_info)
        else:
            # plot toolbar items
            ui.toolButtonHome.setVisible(False)
            ui.toolButtonPan.setVisible(False)
            ui.toolButtonZoom.setVisible(False)
            ui.toolButtonAnnotate.setVisible(False)
            ui.toolButtonDistance.setVisible(False)
            ui.toolButtonPopFigure.setVisible(False)
            ui.toolButtonSave.setVisible(True)
            ui.widgetPlotInfoSV.hide()
            ui.labelMaxRows.setVisible(False)
            ui.spinBoxMaxRows.setVisible(False)
            ui.labelMaxCols.setVisible(False)
            ui.spinBoxMaxCols.setVisible(False)
            ui.comboBoxMVPlots.setVisible(False)
            ui.toolButtonRemoveMVPlot.setVisible(False)
            ui.toolButtonRemoveAllMVPlots.setVisible(False)
            ui.widgetPlotInfoMV.hide()
            ui.comboBoxQVList.setVisible(True)
            ui.toolButtonNewList.setVisible(True)

            ui.SelectAnalytePage.setEnabled(False)
            ui.PreprocessPage.setEnabled(False)
            ui.ScatterPage.setEnabled(False)
            ui.NDIMPage.setEnabled(False)
            ui.MultidimensionalPage.setEnabled(False)
            ui.ClusteringPage.setEnabled(False)
            if hasattr(ui, "spot_tools"):
                ui.spot_tools.setEnabled(False)
            if hasattr(ui, "special_tools"):
                ui.special_tools.setEnabled(False)
            if hasattr(ui, "mask_dock"):
                ui.mask_dock.setEnabled(False)

            ui.dockWidgetStyling.setEnabled(False)
            ui.actionUpdatePlot.setEnabled(False)
            ui.actionSavePlotToTree.setEnabled(False)

            ui.display_QV()

    def remove_multi_plot(self, selected_plot_name):
        """Removes selected plot from MulitView

        Parameters
        ----------
        selected_plot_name : str
            Plot selected in ``MainWindow.treeWidget``
        """
        widget_index = self.multi_view_index.index(selected_plot_name)
        layout = self.ui.widgetMultiView.layout()
        item = layout.itemAt(widget_index)  # Get the item at the specified index
        if item is not None:
            widget = item.widget()   # Get the widget from the item
            if widget is not None:
                layout.removeWidget(widget)  # Remove the widget from the layout
                widget.setParent(None)      # Set the widget's parent to None
        # if widget is not None:
        #     index = self.canvasWindow.addTab( widget, selected_plot_name)
        self.multi_view_index.pop(widget_index)
        for widget in self.multiview_info_label[selected_plot_name+'1']:
            widget.setParent(None)
            widget.deleteLater()
        del self.multiview_info_label[selected_plot_name+'1']
        del self.lasermaps[selected_plot_name+'1']
        #self.axis_widget_dict[selected_plot_name] = widget
        #self.add_remove(selected_plot_name)
        self.ui.comboBoxMVPlots.clear()
        self.ui.comboBoxMVPlots.addItems(self.multi_view_index)

    def update_canvas(self, new_canvas):
        # Clear the existing layout
        self.clear_layout(self.ui.widgetSingleView.layout())
        
        # Add the new canvas to the layout
        if not self.ui.widgetSingleView.layout():
            self.ui.widgetSingleView.setLayout(QVBoxLayout())

        self.ui.widgetSingleView.layout().addWidget(new_canvas)
        
        try:
            # Recreate the NavigationToolbar with the new canvas
            self.mpl_toolbar = NavigationToolbar(new_canvas, self.ui.widgetSingleView)
            #hide the toolbar
            self.mpl_toolbar.hide()
            self.ui.widgetSingleView.layout().addWidget(self.mpl_toolbar)
        except:
            # canvas is not a mplc.MplCanvas  
            pass

    def display_QV(self):
        """Plots selected maps to the Quick View tab

        Adds plots of predefined analytes to the Quick View tab in a grid layout."""
        self.ui.canvasWindow.setCurrentIndex(self.ui.canvas_tab['qv'])
        if self.ui.app_data.sample_id == '':
            return

        key = self.ui.comboBoxQVList.currentText()

        # establish number of rows and columns
        ratio = 1.8 # aspect ratio of gridlayout
        # ratio = ncol / nrow, nplots = ncol * nrow
        ncol = int(np.sqrt(len(self.QV_analyte_list[key])*ratio))

        # fields in current sample
        fields = self.ui.app_data.field_dict['Analyte']

        # clear the quickView layout
        self.clear_layout(self.ui.widgetQuickView.layout())
        for i, analyte in enumerate(self.QV_analyte_list[key]):
            # if analyte is in list of measured fields
            if analyte not in fields:
                continue

            # create plot canvas
            canvas = mplc.MplCanvas()

            # determine location of plot
            col = i % ncol
            row = i // ncol

            # get data for current analyte
            current_plot_df = self.ui.data[self.ui.app_data.sample_id].get_map_data(analyte, 'Analyte')
            reshaped_array = np.reshape(current_plot_df['array'].values, self.ui.data[self.ui.app_data.sample_id].array_size, order=self.ui.data[self.ui.app_data.sample_id].order)

            # add image to canvas
            cmap = self.ui.plot_style.get_colormap()
            cax = canvas.axes.imshow(reshaped_array, cmap=cmap,  aspect=self.ui.data[self.ui.app_data.sample_id].aspect_ratio, interpolation='none')
            font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
            canvas.axes.text( 0.025*self.ui.data[self.ui.app_data.sample_id].array_size[0],
                    0.1*self.ui.data[self.ui.app_data.sample_id].array_size[1],
                    analyte,
                    fontdict=font,
                    color=self.ui.plot_style.overlay_color,
                    ha='left', va='top' )
            canvas.axes.set_axis_off()
            canvas.fig.tight_layout()

            # add canvas to quickView grid layout
            self.ui.widgetQuickView.layout().addWidget(canvas,row,col)

    def clear_layout(self, layout):
        """Clears a widget that contains plots.

        This function removes all widgets from the specified layout, effectively clearing it.

        Parameters
        ----------
        layout : QLayout
            A layout associated with a ``canvasWindow`` tab.
        """
        if layout is None:
            return

        #remove current plot
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()   # Get the widget from the item
                if widget is not None:
                    widget.hide()
                    # layout.removeWidget(widget)  # Remove the widget from the layout
                    # widget.setParent(None)      # Set the widget's parent to None

        if self.ui.canvasWindow.currentIndex() == self.ui.canvas_tab['mv']:
            list = self.ui.comboBoxMVPlots.allItems()
            if not list:
                return

            for i, _ in enumerate(list):
                # get data from comboBoxMVPlots
                data = self.ui.comboBoxMVPlots.itemData(i, role=Qt.ItemDataRole.UserRole)

                # get plot_info from tree location and
                # reset view to False and position to none
                plot_info = self.ui.plot_tree.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                #print(plot_info)
                plot_info['view'][1] = False
                plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.ui.comboBoxMVPlots.clear()        

    def add_plotwidget_to_canvas(self, plot_info, position=None):
        """Adds plot to selected view.

        If plot is already in MultiView, it will be moved to SingleView.

        Parameters
        ----------
        plot_info : dict
            A dictionary with details about the plot
        current_plot_df : dict, optional
            Defaults to None
        """
        sample_id = plot_info['sample_id']
        tree = plot_info['plot_type']
        # widget_dict = self.axis_widget_dict[tree][sample_id][plot_name]

        # if on QuickView canvas, then set to SingleView canvas
        if self.ui.canvasWindow.currentIndex() == self.ui.canvas_tab['qv']:
            self.ui.canvasWindow.setCurrentIndex(self.ui.canvas_tab['sv'])

        # add figure to SingleView canvas
        if self.ui.canvasWindow.currentIndex() == self.ui.canvas_tab['sv']:
            #print('add_plotwidget_to_canvas: SV')
            self.clear_layout(self.ui.widgetSingleView.layout())
            self.sv_widget = plot_info['figure']
            
            
            plot_info['view'][0] = True
            
            self.SV_plot_name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            #self.labelPlotInfo.

            for index in range(self.ui.comboBoxMVPlots.count()):
                if self.ui.comboBoxMVPlots.itemText(index) == self.SV_plot_name:
                    #plot exists in MVself.pyqtgraph_widget
                    self.move_widget_between_layouts(self.ui.widgetMultiView.layout(), self.ui.widgetSingleView.layout(),widget)
                    self.duplicate_plot_info = plot_info
                    self.hide()
                    self.show()
                    return
            
            if self.duplicate_plot_info: #if duplicate exists and new plot has been plotted on SV
                #return duplicate back to MV
                row, col = self.duplicate_plot_info['position']
                #print(f'd{row,col}')
                dup_widget =self.duplicate_plot_info['figure']
                self.ui.widgetMultiView.layout().addWidget( dup_widget, row, col )
                dup_widget.show()
                self.duplicate_plot_info = None #reset to avoid plotting previous duplicates
            else:
                #update toolbar and SV canvas
                self.update_canvas(self.sv_widget)
            self.sv_widget.show()

            if (self.ui.plot_style.plot_type == 'field map') and (self.ui.toolBox.currentIndex() == self.ui.left_tab['sample']):
                current_map_df = self.ui.data[self.ui.app_data.sample_id].get_map_data(plot_info['plot_name'], plot_info['field_type'], norm=self.ui.plot_style.cscale)
                plot_small_histogram(self.ui, self.ui.data[self.ui.app_data.sample_id], self.ui.app_data, self.ui.plot_style, current_map_df)
        # add figure to MultiView canvas
        elif self.ui.canvasWindow.currentIndex() == self.ui.canvas_tab['mv']:
            #print('add_plotwidget_to_canvas: MV')
            name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            layout = self.ui.widgetMultiView.layout()

            list = self.ui.comboBoxMVPlots.allItems()
            
            # if list:
            #     for i, item in enumerate(list):
            #         mv_plot_data = self.comboBoxMVPlots.itemData(i)
            #         if mv_plot_data[2] == tree and mv_plot_data[3] == sample_id and mv_plot_data[4] == plot_name:
            #             self.statusBar().showMessage('Plot already displayed on canvas.')
            #             return
            plot_exists = False # to check if plot is already in comboBoxMVPlots
            for index in range(self.ui.comboBoxMVPlots.count()):
                if self.ui.comboBoxMVPlots.itemText(index) == name:
                    plot_exists = True
                
            if plot_exists and name != self.SV_plot_name:
                #plot exists in MV and is doesnt exist in SV
                self.ui.statusBar().showMessage('Plot already displayed on canvas.')
                return
            
            # if position is given, use it
            if position:
                row = position[0]
                col = position[1]
                
                # remove widget that is currently in this place
                widget = layout.itemAtPosition(row,col)
                if widget is not None and name != self.SV_plot_name:
                    # layout.removeWidget(widget)
                    # widget.setParent(None)
                    widget.hide()

            # if no position, find first empty space
            else:
                keepgoing = True
                for row in range(self.ui.spinBoxMaxRows.value()):
                    for col in range(self.ui.spinBoxMaxCols.value()):
                        if layout.itemAtPosition(row,col):
                            #print(f'row: {row}   col : {col}')
                            continue
                        else:
                            keepgoing = False
                            break

                    if not keepgoing:
                        #print(f'row: {row}   col : {col}')
                        break

            # check if canvas is full
            if row == self.ui.spinBoxMaxRows.value()-1 and col == self.ui.spinBoxMaxCols.value()-1 and layout.itemAtPosition(row,col):
                QMessageBox.warning(self.ui, "Add plot to canvas warning", "Canvas is full, to add more plots, increase row or column max.")
                return

            
            widget = plot_info['figure']
            plot_info['view'][1] = True
            plot_info['position'] = [row,col]
            
            
            if name == self.SV_plot_name and plot_exists: #if plot already exists in MV and SV
                self.move_widget_between_layouts(self.ui.widgetSingleView.layout(),self.ui.widgetMultiView.layout(),widget, row,col)
                self.duplicate_plot_info = plot_info
            elif name == self.SV_plot_name and not plot_exists: #if plot doesnt exist in MV but exists in SV
                # save plot info to replot when tab changes to single view and add plot to comboBox
                self.duplicate_plot_info = plot_info
                data = [row, col, tree, sample_id, name]
                self.move_widget_between_layouts(self.ui.widgetSingleView.layout(),self.ui.widgetMultiView.layout(),widget, row,col)
                self.ui.comboBoxMVPlots.addItem(name, userData=data)
            else: #new plot which doesnt exist in single view
                # add figure to canvas
                layout.addWidget(widget,row,col)    
                
                data = [row, col, tree, sample_id, name]
                self.ui.comboBoxMVPlots.addItem(name, userData=data)

        # self.hide()
        # self.show()

        # put plot_info back into table
        #print(plot_info)
        self.ui.plot_tree.add_tree_item(plot_info)

    def move_widget_between_layouts(self,source_layout, target_layout, widget, row=None, col=None):
        """
        Move a widget from source_layout to a specific position in target layout,  (row, col) if target layout is a QGridLayout.
        This function also inserts a placeholder in the original position to maintain layout integrity.
        """
        # Remove widget from source layout
        index = source_layout.indexOf(widget)

        source_layout.removeWidget(widget)
        # widget.hide()
        # If the source layout is a grid, handle placeholders differently
        if isinstance(source_layout, QGridLayout):
            placeholder = QWidget()
            placeholder.setFixedSize(widget.size())
            src_row, src_col, _, _ = source_layout.getItemPosition(index)
            source_layout.addWidget(placeholder, src_row, src_col)
        else:
            placeholder = QWidget()  # Create an empty placeholder widget for non-grid layouts
            placeholder.setFixedSize(widget.size())

            source_layout.insertWidget(0, placeholder)
            
        if isinstance(target_layout, QGridLayout):
            # Add widget to the target grid layout
            target_layout.addWidget(widget, row, col)
        else:
            # Add widget to the target layout
            target_layout.addWidget(widget)
        widget.show()  # Ensure the widget is visible in the new layout
