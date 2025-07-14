import os, darkdetect
from PyQt6.QtCore import ( Qt, QSize )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout, QMessageBox,
    QHeaderView, QMenu, QDialog, QWidget, QCheckBox, QHeaderView, QSizePolicy,
    QLineEdit, QLabel, QToolBar
)
from PyQt6.QtGui import ( QIcon, QAction, QFont )
from src.common.CustomWidgets import CustomActionMenu
from src.app.config import BASEDIR, ICONPATH 

import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

import src.common.CustomMplCanvas as mplc
from src.common.LamePlot import plot_small_histogram
import src.common.csvdict as csvdict
from src.common.TableFunctions import TableFcn as TableFcn
import src.app.CustomTableWidget as TW
from src.common.SortAnalytes import sort_analytes
from src.app.UITheme import default_font
from src.common.Logger import auto_log_methods, log, no_log

@auto_log_methods(logger_key='Canvas')
class CanvasWidget():
    def __init__(self, parent):
        self.ui = parent
        self.logger_key = "Canvas"

        self.duplicate_plot_info = None
        self.lasermaps = {}

        self.QV_analyte_list = {}
        try:
            self.QV_analyte_list = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/styles/qv_lists.csv'))
        except:
            self.QV_analyte_list = {'default':['Si29','Ti47','Al27','Cr52','Fe56','Mn55','Mg24','Ca43','K39','Na23','P31',
                'Ba137','Th232','U238','La139','Ce140','Pb206','Pr141','Sr88','Zr90','Hf178','Nd146','Eu153',
                'Gd157','Tb159','Dy163','Ho165','Y89','Er166','Tm169','Yb172','Lu175']}

        self.ui.toolButtonNewList.clicked.connect(lambda: QuickView(self))
        self.ui.comboBoxQVList.activated.connect(lambda _: self.display_QV())

        self.ui.canvasWindow.currentChanged.connect(lambda _: self.canvas_changed())
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

        self.ui.toolButtonNewList.clicked.connect(lambda: QuickView(self))
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

            self.display_QV()

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
            canvas = mplc.MplCanvas(parent=self.ui)

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
            if self.ui.widgetQuickView.layout() is None:
                layout_quick_view = QGridLayout()
                layout_quick_view.setSpacing(0)
                layout_quick_view.setContentsMargins(0, 0, 0, 0)
                self.ui.widgetQuickView.setLayout(layout_quick_view)
            layout = self.ui.widgetQuickView.layout()

            # add canvas to layout
            layout.addWidget(canvas,row,col)

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
                    item = self.ui.widgetMultiView.layout().itemAt(index)
                    if item is not None:
                        widget = item.widget()
                        if widget is not None:
                            self.move_widget_between_layouts(self.ui.widgetMultiView.layout(), self.ui.widgetSingleView.layout(), widget)
                            self.duplicate_plot_info = plot_info
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
            if src_row is not None and src_col is not None:
                source_layout.addWidget(placeholder, src_row, src_col)
            # else: skip adding placeholder if position is invalid
        else:
            placeholder = QWidget()  # Create an empty placeholder widget for non-grid layouts
            placeholder.setFixedSize(widget.size())

            source_layout.insertWidget(0, placeholder)
        
        if isinstance(target_layout, QGridLayout):
            # Add widget to the target grid layout
            if row is not None and col is not None:
                target_layout.addWidget(widget, row, col)
        else:
            # Add widget to the target layout
            target_layout.addWidget(widget)
        widget.show()  # Ensure the widget is visible in the new layout

# QuickViewDialog gui
# -------------------------------
@auto_log_methods(logger_key='Canvas')
class QuickView(QDialog):
    """Creates a dialog for the user to select and order analytes for Quick View.

    This dialog allows the user to select analytes from a list, reorder them, and save the
    selection for quick access in the Quick View tab.

    Parameters
    ----------
    parent : None
        Parent UI
    """
    def __init__(self, parent):
        if hasattr(parent, 'ui'):
            self.ui = parent.ui
        else:
            self.ui = parent
        super().__init__(self.ui)
        self.parent = parent

        # Set up list of fields for the table
        self.analyte_list = self.ui.app_data.get_field_list("Analyte")

        # Initialize the dialog
        self.setupUi()

    def setupUi(self):
        font = default_font()

        self.setObjectName("QuickViewDialog")
        self.resize(300, 640)
        self.setWindowTitle("Quick View List Editor")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt
            .WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        self.setFont(font)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setObjectName("dialog_layout")
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)
        self.setLayout(dialog_layout)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out
        dialog_layout.addWidget(toolbar)

        sort_icon = ":resources/icons/icon-sort-64.svg"
        sortmenu_items = [
            ("alphabetical", lambda: self.apply_sort("alphabetical")),
            ("atomic number", lambda: self.apply_sort("atomic number")),
            ("mass", lambda: self.apply_sort("mass")),
            ("compatibility", lambda: self.apply_sort("compatibility")),
            ("radius", lambda: self.apply_sort("radius")),
        ]

        self.sort_action_menu = CustomActionMenu(
            icon=sort_icon,
            text="Sort fields for Quick View",
            menu_items=sortmenu_items,
            parent=self
        )

        self.label = QLabel()
        self.label.setText("Enter name:")

        self.lineEditQVName = QLineEdit(toolbar)
        self.lineEditQVName.setFont(font)
        self.lineEditQVName.setText("")
        self.lineEditQVName.setObjectName("lineEditViewName")

        self.save_action = QAction(toolbar)
        self.save_action.setObjectName("actionSave")
        self.save_action.setToolTip("Save current analyte list")
        self.save_action.triggered.connect(lambda: self.apply_selected_analytes(save=True))

        self.apply_action = QAction(toolbar)
        self.apply_action.setObjectName("actionApply")
        self.apply_action.setToolTip("Apply current analyte list to Quick View")
        self.apply_action.triggered.connect(lambda: self.apply_selected_analytes(save=False))

        # Setup sort menu and associated toolButton
        if darkdetect.isDark():
            self.sort_action_menu.setIcon(QIcon(":resources/icons/icon-sort-dark-64.svg"))
            self.save_action.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
            self.apply_action.setIcon(QIcon(":resources/icons/icon-add-list-dark-64.svg"))
        else:
            self.sort_action_menu.setIcon(QIcon(":resources/icons/icon-sort-64.svg"))
            self.save_action.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
            self.apply_action.setIcon(QIcon(":resources/icons/icon-add-list-64.svg"))

        toolbar.addAction(self.sort_action_menu)
        toolbar.addSeparator()
        toolbar.addWidget(self.label)
        toolbar.addWidget(self.lineEditQVName)
        toolbar.addSeparator()
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.apply_action)

        # Assuming TableWidgetDragRows is defined elsewhere
        self.tableWidget = TW.TableWidgetDragRows()  
        dialog_layout.addWidget(self.tableWidget)

        self.setup_table()

        self.show()

    def setup_table(self):
        """
        Sets up analyte selection table in dialog.
        
        This method initializes the table widget with the analyte list, sets the number of rows
        and columns, and configures the header labels. It also sets the resize modes for the
        columns to ensure proper display of the analyte names and checkboxes.
        """
        self.tableWidget.setRowCount(len(self.analyte_list))
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Show', 'Analyte'])

        header = self.tableWidget.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.populate_table()

    def populate_table(self):
        """
        Populates dialog table with analytes.
        
        This method fills the table with analytes from the `self.analyte_list` and adds checkboxes
        for each analyte to allow the user to select which analytes to include in the Quick
        View. It also restores the state of checkboxes based on previous selections.
        If the table is empty, it will be populated with the default analyte list.
        """
        # Before repopulating, save the current state of checkboxes
        checkbox_states = {}
        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 0)
            item = self.tableWidget.item(row, 1)
            if checkbox is not None and isinstance(checkbox, QCheckBox) and item is not None:
                analyte = item.text()
                checkbox_states[analyte] = checkbox.isChecked()

        # Clear the table and repopulate
        self.tableWidget.setRowCount(len(self.analyte_list))
        for row, analyte in enumerate(self.analyte_list):
            checkbox = QCheckBox()
            checkbox.setChecked(checkbox_states.get(analyte, True))
            self.tableWidget.setCellWidget(row, 0, checkbox)

            item = QTableWidgetItem(analyte)
            self.tableWidget.setItem(row, 1, item)


    def apply_sort(self, method):
        """
        Sorts analyte table in dialog.

        Sorts the analyte list based on the specified method and repopulates the table.

        Parameters
        ----------
        method : str
            The sorting method to apply. Options include 'alphabetical', 'atomic number',
            'mass', 'compatibility', and 'radius'.
        """        
        self.analyte_list = sort_analytes(method, self.analyte_list)
        self.populate_table()  # Refresh table with sorted data

    def apply_selected_analytes(self, save=False):
        """Gets list of analytes and group name when Save button is clicked.

        Retrieves the user-defined name from ``quickView.lineEditViewName`` and list of analytes
        using ``quickView.column_to_list()``, and adds them to a dictionary item with the name
        defined as the key.

        Parameters
        ----------
        save : bool, optional
            If True, the list is saved to a CSV file. Defaults to False.

        Raises
        ------
        ValueError
            If the view name is empty or if no analytes are selected.
        QMessageBox.warning
            If the view name is invalid or if no analytes are selected.
        QMessageBox.information
            If the analyte list is saved successfully.
        ValueError
            If the view name is not valid or if no analytes are selected.
        """        
        self.view_name = self.lineEditQVName.text().strip() if self.lineEditQVName is not None else ''
        if not self.view_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid view name.")
            return

        # Collect selected analytes from the table
        selected_analytes = []
        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 1)
            checkbox = self.tableWidget.cellWidget(row, 0)
            if item is not None and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_analytes.append(item.text())

        if not selected_analytes:
            QMessageBox.warning(self, "No Analytes Selected", "Please select at least one analyte.")
            return

        # Update the main QV_analyte_list dict in the parent
        self.parent.QV_analyte_list[self.view_name] = selected_analytes

        # update self.main_window.comboBoxQVList combo box with view_name if not already present
        if self.ui.comboBoxQVList.findText(self.view_name) == -1:
            self.ui.comboBoxQVList.addItem(self.view_name)
        
        # Save to CSV
        if save == True:
            self.save_to_csv()

    def save_to_csv(self):
        """Opens a message box, prompting user to in put a file to save the table list.

        Saves the current analyte list to a CSV file in the resources/styles directory.
        If the directory does not exist, it is created. The file is named 'qv_lists.csv' and
        contains the analyte lists for quick access in the Quick View tab.
        If the parent has a QV_analyte_list attribute, it exports the list to the CSV file.
        If the save is successful, a message box informs the user of the success.
        If the save fails, a warning message box is displayed.

        Raises
        ------
        OSError
            If there is an issue creating the directory or writing to the file.
        QMessageBox.warning
            If the save operation fails or if the QV_analyte_list is not available.
        QMessageBox.information
            If the save operation is successful.
        """
        file_path = os.path.join(BASEDIR,'resources', 'styles', 'qv_lists.csv')
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # append dictionary to file of saved qv_lists
        if hasattr(self.parent, 'QV_analyte_list'):
            csvdict.export_dict_to_csv(self.ui.QV_analyte_list, file_path)
            QMessageBox.information(self, "Save Successful", f"Analytes view saved under '{self.view_name}' successfully.")
        else:
            QMessageBox.warning(self, "Error", "Could not save analyte list.")