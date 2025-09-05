from PyQt6.QtCore import ( Qt, QSize, QTimer )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGridLayout, QMessageBox,
    QHeaderView, QDialog, QWidget, QCheckBox, QHeaderView, QSizePolicy, QToolButton,
    QLineEdit, QLabel, QToolBar, QTabWidget, QGroupBox, QSpacerItem, QSpinBox, QComboBox,
    QButtonGroup, QDialogButtonBox, QMenu
)
from PyQt6.QtGui import QFont, QIcon, QCursor
from src.common.CustomWidgets import CustomActionMenu, CustomAction, CustomToolButton, CustomComboBox, VisibilityWidget
from src.app.config import APPDATA_PATH, ICONPATH, get_top_parent

import gc
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

from src.common.CustomMplCanvas import MplCanvas
from src.common.LamePlot import plot_small_histogram
import src.common.csvdict as csvdict
from src.common.TableFunctions import TableFcn as TableFcn
import src.app.CustomTableWidget as TW
from src.common.SortAnalytes import sort_analytes
from src.app.UITheme import default_font
from src.common.Logger import auto_log_methods, log, no_log

@auto_log_methods(logger_key='Canvas')
class CanvasWidget(QWidget):
    def __init__(self, ui, parent=None):
        super().__init__(parent=parent)
        self.ui = ui
        self.logger_key = "Canvas"

        self.duplicate_plot_info = None
        self.lasermaps = {}

        self.QV_analyte_list = {}
        try:
            self.QV_analyte_list = csvdict.import_csv_to_dict(APPDATA_PATH / 'qv_lists.csv')
        except:
            self.QV_analyte_list = {'default':['Si29','Ti47','Al27','Cr52','Fe56','Mn55','Mg24','Ca43','K39','Na23','P31',
                'Ba137','Th232','U238','La139','Ce140','Pb206','Pr141','Sr88','Zr90','Hf178','Nd146','Eu153',
                'Gd157','Tb159','Dy163','Ho165','Y89','Er166','Tm169','Yb172','Lu175']}

        self.setupUI()
        self.connect_widgets()
        self.reindex_tab_dict()

        self.toolbar.qv.comboBoxQVList.addItems(list(self.QV_analyte_list.keys()))

        self.canvasWindow.currentChanged.connect(lambda _: self.tab_changed())
        self.canvasWindow.setCurrentIndex(self.tab_dict['sv'])

        self.tab_changed()

    def setupUI(self):
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())

        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(0, 450))
        self.setObjectName("centralwidget")

        canvas_widget_layout = QVBoxLayout(self)

        self.canvasWindow = QTabWidget(parent=self)

        self.single_view = SingleViewTab(self.canvasWindow)
        self.multi_view = MultiViewTab(self.canvasWindow)
        self.quick_view = QuickViewTab(self.canvasWindow)

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.canvasWindow.sizePolicy().hasHeightForWidth())

        self.canvasWindow.setSizePolicy(sizePolicy)
        self.canvasWindow.setMinimumSize(QSize(0, 0))
        self.canvasWindow.setAccessibleName("")
        self.canvasWindow.setDocumentMode(False)
        self.canvasWindow.setTabsClosable(False)
        self.canvasWindow.setTabBarAutoHide(False)
        self.canvasWindow.setObjectName("canvasWindow")

        self.toolbar = CanvasToolBar(self)

        canvas_widget_layout.addWidget(self.canvasWindow)
        canvas_widget_layout.addWidget(self.toolbar)

    def connect_widgets(self):
        """Connects widgets to their respective functions"""
        self.multi_view_index = []
        self.multiview_info_label = {}
        self.toolbar.mv.toolButtonRemovePlot.clicked.connect(lambda: self.remove_multi_plot(self.toolbar.mv.comboBoxMVPlots.currentText()))
        self.toolbar.mv.toolButtonRemoveAllPlots.clicked.connect(lambda: self.clear_layout(self.multi_view.layout()))

    @property
    def current_canvas(self):
        """MplCanvas : Returns the current canvas based on the selected tab."""
        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
            layout = self.single_view.layout()
            if layout is not None:
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, MplCanvas):
                        return widget
            return None
        elif self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            return self.multi_view.layout()
        elif self.canvasWindow.currentIndex() == self.tab_dict['qv']:
            return self.quick_view.layout()
        else:
            return None

    @current_canvas.setter
    def current_canvas(self, canvas: MplCanvas):
        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
            self.update_canvas(canvas)
        elif self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            layout = self.multi_view.layout() 
            if layout is not None:
                layout.addWidget(canvas)
                #QTimer.singleShot(0, lambda: layout.addWidget(canvas))
        elif self.canvasWindow.currentIndex() == self.tab_dict['qv']:
            layout = self.quick_view.layout()
            if layout is not None:
                layout.addWidget(canvas)
                #QTimer.singleShot(0, lambda: layout.addWidget(canvas))
        else:
            raise ValueError("Invalid tab index.")

    def reindex_tab_dict(self):
        """Reindexes the tab_dict to match the current tabs in canvasWindow.

        This function updates the tab_dict to ensure it reflects the current state of the canvasWindow tabs.
        """
        self.tab_dict = {}
        for tid in range(self.canvasWindow.count()):
            match self.canvasWindow.tabText(tid).lower():
                case 'single view':
                    self.tab_dict.update({'sv': tid})
                case 'multi view':
                    self.tab_dict.update({'mv': tid})
                case 'quick view':
                    self.tab_dict.update({'qv': tid})

    def tab_changed(self):
        """Sets visibility of canvas tools and updates canvas plots.

        If the current tab is SingleView, MultiView, or QuickView, it shows the corresponding toolbar.
        """        

        if self.ui.app_data.sample_id == '':
            self.toolbar.sv.hide()
            self.toolbar.mv.hide()
            self.toolbar.qv.hide()
            self.toolbar.toolButtonSave.setVisible(False)

            return

        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
            # plot toolbar items
            
            self.toolbar.sv.show()
            self.toolbar.mv.hide()
            self.toolbar.qv.hide()
            self.toolbar.toolButtonSave.setVisible(True)

            if self.duplicate_plot_info:
                self.ui.add_canvas_to_window(self.duplicate_plot_info)
        elif self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            # plot toolbar items
            self.toolbar.sv.hide()
            self.toolbar.mv.show()
            self.toolbar.qv.hide()
            self.toolbar.toolButtonSave.setVisible(True)

            if self.duplicate_plot_info:
                self.ui.add_canvas_to_window(self.duplicate_plot_info)
        else:
            # plot toolbar items
            self.toolbar.sv.hide()
            self.toolbar.mv.hide()
            self.toolbar.qv.show()
            self.toolbar.toolButtonSave.setVisible(True)

            self.display_QV()

    def remove_multi_plot(self, selected_plot_name):
        """Removes selected plot from MulitView

        Parameters
        ----------
        selected_plot_name : str
            Plot selected in ``MainWindow.treeWidget``
        """
        widget_index = self.multi_view_index.index(selected_plot_name)
        layout = self.multi_view.layout()
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
            gc.collect()
        del self.multiview_info_label[selected_plot_name+'1']
        del self.lasermaps[selected_plot_name+'1']
        #self.axis_widget_dict[selected_plot_name] = widget
        #self.add_remove(selected_plot_name)
        self.toolbar.mv.comboBoxMVPlots.clear()
        self.toolbar.mv.comboBoxMVPlots.addItems(self.multi_view_index)

    def update_canvas(self, new_canvas):
        """Updates the current canvas with a new canvas.
        Clears the existing layout and adds the new canvas to the SingleView tab.

        Parameters
        ----------
        new_canvas : MplCanvas
            The new canvas to be added to the SingleView tab.
        """
        # Clean up existing matplotlib toolbar first
        if hasattr(self, 'mpl_toolbar') and self.mpl_toolbar is not None:
            try:
                self.mpl_toolbar.setParent(None)
                self.mpl_toolbar.close()
                del self.mpl_toolbar
            except:
                pass
            finally:
                self.mpl_toolbar = None

        # Clear the existing layout
        self.clear_layout(self.single_view.layout())
        
        # Add the new canvas to the layout
        if not self.single_view.layout():
            self.single_view.setLayout(QVBoxLayout())
        
        layout = self.single_view.layout()
        if layout is not None:
            layout.addWidget(new_canvas)
            #QTimer.singleShot(0, lambda: layout.addWidget(new_canvas))
        
        new_canvas.show()
        
        # Add observers safely
        try:
            new_canvas.locationChanged.connect(lambda: self.toolbar.update_sv_info())
            new_canvas.valueChanged.connect(lambda: self.toolbar.update_sv_info())
            new_canvas.distanceChanged.connect(lambda: self.toolbar.update_sv_info())
        except AttributeError:
            # Canvas doesn't support observers, that's ok
            pass
            
        # Update tool availability based on canvas type
        self.toolbar.sv.update_tool_availability(new_canvas)
        
        try:
            # Recreate the NavigationToolbar with the new canvas
            self.mpl_toolbar = NavigationToolbar(new_canvas, self.single_view)
            # hide the toolbar
            self.mpl_toolbar.hide()
            if layout is not None:
                layout.addWidget(self.mpl_toolbar)
        except Exception as e:
            # Canvas is not a MplCanvas or other error
            print(f"Could not create navigation toolbar: {e}")
            self.mpl_toolbar = None

        self.single_view.show()

    def display_QV(self):
        """Plots selected maps to the Quick View tab

        Adds plots of predefined analytes to the Quick View tab in a grid layout."""
        self.canvasWindow.setCurrentIndex(self.tab_dict['qv'])
        if self.ui.app_data.sample_id == '':
            return

        key = self.toolbar.qv.comboBoxQVList.currentText()

        # establish number of rows and columns
        ratio = 1.8 # aspect ratio of gridlayout
        # ratio = ncol / nrow, nplots = ncol * nrow
        ncol = int(np.sqrt(len(self.QV_analyte_list[key])*ratio))

        # fields in current sample
        fields = self.ui.app_data.field_dict['Analyte']

        # clear the quickView layout
        self.clear_layout(self.quick_view.layout())
        for i, analyte in enumerate(self.QV_analyte_list[key]):
            # if analyte is in list of measured fields
            if analyte not in fields:
                continue

            # create plot canvas
            canvas = MplCanvas(parent=self.ui)

            # determine location of plot
            col = i % ncol
            row = i // ncol

            # get data for current analyte
            current_plot_df = self.ui.data[self.ui.app_data.sample_id].get_map_data(analyte, 'Analyte')
            reshaped_array = np.reshape(current_plot_df['array'].values, self.ui.data[self.ui.app_data.sample_id].array_size, order=self.ui.data[self.ui.app_data.sample_id].order)

            # add image to canvas
            cmap = self.ui.style_data.get_colormap()
            cax = canvas.axes.imshow(reshaped_array, cmap=cmap,  aspect=self.ui.data[self.ui.app_data.sample_id].aspect_ratio, interpolation='none')
            font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
            canvas.axes.text( 0.025*self.ui.data[self.ui.app_data.sample_id].array_size[0],
                    0.1*self.ui.data[self.ui.app_data.sample_id].array_size[1],
                    analyte,
                    fontdict=font,
                    color=self.ui.style_data.overlay_color,
                    ha='left', va='top' )
            canvas.axes.set_axis_off()
            canvas.fig.tight_layout()

            # add canvas to quickView grid layout
            if self.quick_view.layout() is None:
                layout_quick_view = QGridLayout()
                layout_quick_view.setSpacing(0)
                layout_quick_view.setContentsMargins(0, 0, 0, 0)
                self.quick_view.setLayout(layout_quick_view)

            # add canvas to layout
            layout = self.quick_view.layout()
            if layout is not None:
                layout.addWidget(canvas,row,col)

    def clear_layout(self, layout):
        """Clears a widget that contains plots.

        Removes widgets from the specified layout. If a widget is referenced in the PlotTree, it is only hidden and removed from the layout. If not, it is deleted.
        """
        if layout is None:
            return

        # Get the top parent (MainWindow or Workflow)
        top_parent = get_top_parent(self)
        plot_tree = getattr(top_parent, 'plot_tree', None) if top_parent and hasattr(top_parent, 'plot_tree') else None

        # Collect widgets to remove first
        widgets_to_remove = []
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widgets_to_remove.append((widget, item))

        # Now process each widget
        for widget, item in widgets_to_remove:
            # Check if widget is referenced in PlotTree
            keep_widget = False
            if plot_tree is not None:
                # Try to find a plot_info referencing this widget
                # Search all trees and branches for a matching figure
                for tree_name, tree_items in plot_tree.tree.items():
                    for branch_idx in range(tree_items.rowCount()):
                        branch_item = tree_items.child(branch_idx)
                        for leaf_idx in range(branch_item.rowCount()):
                            leaf_item = branch_item.child(leaf_idx)
                            plot_info = leaf_item.data(role=Qt.ItemDataRole.UserRole)
                            if plot_info and isinstance(plot_info, dict) and plot_info.get('figure') is widget:
                                keep_widget = True
                                break
                        if keep_widget:
                            break
                    if keep_widget:
                        break
            
            # Remove from layout first
            layout.removeWidget(widget)
            
            if keep_widget:
                # Just hide, don't delete
                widget.hide()
                # Ensure widget has a valid parent to prevent garbage collection
                if widget.parent() is None:
                    widget.setParent(self)
            else:
                # Proper cleanup before deletion
                try:
                    # Disconnect all signals to prevent callbacks on deleted widget
                    widget.blockSignals(True)
                    
                    # If it's a matplotlib canvas, clean it up properly
                    if hasattr(widget, 'figure'):
                        if hasattr(widget.figure, 'clear'):
                            widget.figure.clear()
                        if hasattr(widget.figure, 'canvas'):
                            widget.figure.canvas = None

                    if hasattr(self, 'mpl_toolbar') and self.mpl_toolbar is not None:
                        self.mpl_toolbar.setParent(None)  # remove from the Qt layout

                    if hasattr(self, 'mpl_toolbar') and self.mpl_toolbar is not None:
                        self.mpl_toolbar.canvas = None
                    
                    # Clean up any observers if present
                    if hasattr(widget, 'observers'):
                        widget.observers.clear()
                    
                    # Set parent to None and delete immediately
                    widget.setParent(None)
                    widget.close()
                    #del widget  # Immediate deletion instead of deleteLater()
                    widget.blockSignals(True)
                    try:
                        widget.disconnect()
                    except Exception:
                        pass
                    widget.deleteLater()
                    # gc.collect()
                    
                except Exception as e:
                    print(f"Error during widget cleanup: {e}")
                    # Fallback to original method
                    widget.setParent(None)
                    try:
                        widget.disconnect()
                    except Exception:
                        pass
                    widget.deleteLater()
                    # gc.collect()

        # Clear the rest of the multiview specific cleanup
        if self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            list_items = self.toolbar.mv.comboBoxMVPlots.allItems()
            if list_items:
                for i, _ in enumerate(list_items):
                    # get data from comboBoxMVPlots
                    data = self.toolbar.mv.comboBoxMVPlots.itemData(i, role=Qt.ItemDataRole.UserRole)
                    if data:
                        # get plot_info from tree location and reset view to False and position to none
                        plot_info = self.ui.plot_tree.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                        if plot_info:
                            plot_info['view'][1] = False
                            plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.toolbar.mv.comboBoxMVPlots.clear()       

    def add_canvas_to_window(self, plot_info, position=None):
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
        if self.canvasWindow.currentIndex() == self.tab_dict['qv']:
            self.canvasWindow.setCurrentIndex(self.tab_dict['sv'])

        # add figure to SingleView canvas
        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
            #print('add_canvas_to_window: SV')
            self.clear_layout(self.single_view.layout())
            self.sv_widget = plot_info['figure']
            
            
            plot_info['view'][0] = True
            
            self.SV_plot_name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            #self.labelPlotInfo.

            for index in range(self.toolbar.mv.comboBoxMVPlots.count()):
                if self.toolbar.mv.comboBoxMVPlots.itemText(index) == self.SV_plot_name:
                    item = None
                    layout =  self.multi_view.layout()
                    if layout is not None:
                        item = layout.itemAt(index)

                    if item is not None:
                        widget = item.widget()
                        if widget is not None:
                            self.move_widget_between_layouts(self.multi_view.layout(), self.single_view.layout(), widget)
                            self.duplicate_plot_info = plot_info
                    return
            
            if self.duplicate_plot_info: #if duplicate exists and new plot has been plotted on SV
                #return duplicate back to MV
                row, col = self.duplicate_plot_info['position']
                #print(f'd{row,col}')
                dup_widget =self.duplicate_plot_info['figure']
                layout = self.multi_view.layout()
                if layout is not None:
                    layout.addWidget( dup_widget, row, col )
                dup_widget.show()
                self.duplicate_plot_info = None #reset to avoid plotting previous duplicates
            else:
                #update toolbar and SV canvas
                self.current_canvas = self.sv_widget
            self.sv_widget.show()
            
            if hasattr(self.ui, 'control_dock') and (self.ui.style_data.plot_type == 'field map') and (self.ui.control_dock.toolbox.currentIndex() == self.ui.control_dock.tab_dict['sample']):
                current_map_df = self.ui.app_data.current_data.get_map_data(plot_info['plot_name'], plot_info['field_type'], norm=self.ui.style_data.cscale)
                plot_small_histogram(self.ui, self.ui.app_data.current_data, self.ui.app_data, self.ui.style_data, current_map_df)
        # add figure to MultiView canvas
        elif self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            #print('add_canvas_to_window: MV')
            name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            layout = self.multi_view.layout()

            list = self.toolbar.mv.comboBoxMVPlots.allItems()
            
            # if list:
            #     for i, item in enumerate(list):
            #         mv_style_data = self.comboBoxMVPlots.itemData(i)
            #         if mv_style_data[2] == tree and mv_style_data[3] == sample_id and mv_style_data[4] == plot_name:
            #             self.statusBar().showMessage('Plot already displayed on canvas.')
            #             return
            plot_exists = False # to check if plot is already in comboBoxMVPlots
            for index in range(self.toolbar.mv.comboBoxMVPlots.count()):
                if self.toolbar.mv.comboBoxMVPlots.itemText(index) == name:
                    plot_exists = True
                
            if plot_exists and name != self.SV_plot_name:
                #plot exists in MV and is doesnt exist in SV
                self.ui.statusbar().showMessage('Plot already displayed on canvas.')
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
                for row in range(self.toolbar.mv.spinBoxMaxRows.value()):
                    for col in range(self.toolbar.mv.spinBoxMaxCols.value()):
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
            if row == self.toolbar.mv.spinBoxMaxRows.value()-1 and col == self.toolbar.mv.spinBoxMaxCols.value()-1 and layout.itemAtPosition(row,col):
                QMessageBox.warning(self.ui, "Add plot to canvas warning", "Canvas is full, to add more plots, increase row or column max.")
                return

            
            widget = plot_info['figure']
            plot_info['view'][1] = True
            plot_info['position'] = [row,col]
            
            
            if name == self.SV_plot_name and plot_exists: #if plot already exists in MV and SV
                self.move_widget_between_layouts(self.single_view.layout(),self.multi_view.layout(),widget, row,col)
                self.duplicate_plot_info = plot_info
            elif name == self.SV_plot_name and not plot_exists: #if plot doesnt exist in MV but exists in SV
                # save plot info to replot when tab changes to single view and add plot to comboBox
                self.duplicate_plot_info = plot_info
                data = [row, col, tree, sample_id, name]
                self.move_widget_between_layouts(self.single_view.layout(),self.multi_view.layout(),widget, row,col)
                self.toolbar.mv.comboBoxMVPlots.addItem(name, userData=data)
            else: #new plot which doesnt exist in single view
                # add figure to canvas
                if layout is not None:
                    layout.addWidget(widget,row,col)    
                
                data = [row, col, tree, sample_id, name]
                self.toolbar.mv.comboBoxMVPlots.addItem(name, userData=data)

        # put plot_info back into table
        #print(plot_info)
        if hasattr(self.ui, "plot_tree"):
            self.ui.plot_tree.add_tree_item(plot_info)

    def save_current_plot_to_tree(self):
        """Save the current plot displayed on canvas to the plot tree and registry."""
        try:
            current_plot_info = None
            
            # Try to get current plot info from SingleView
            if (self.canvasWindow.currentIndex() == self.tab_dict['sv'] and 
                hasattr(self, 'sv_widget') and self.sv_widget):
                
                # Check if sv_widget has the plot information we need
                if hasattr(self.sv_widget, 'plot_name') and hasattr(self.sv_widget, 'sample_obj'):
                    sample_obj = self.sv_widget.sample_obj
                    if sample_obj and hasattr(sample_obj, 'sample_id'):
                        # Build plot_info from canvas properties
                        current_plot_info = {
                            'sample_id': sample_obj.sample_id,
                            'plot_name': getattr(self.sv_widget, 'plot_name', 'Saved Plot'),
                            'figure': self.sv_widget,
                            'view': [True, False],
                            'position': None,
                        }
                        
                        # Try to get plot type from style data
                        if hasattr(self.ui, 'style_data') and hasattr(self.ui.style_data, 'plot_type'):
                            current_plot_info['plot_type'] = self.ui.style_data.plot_type
                        else:
                            current_plot_info['plot_type'] = 'field map'  # default
                        
                        # Try to get field info from UI
                        if hasattr(self.ui, 'control_dock'):
                            if hasattr(self.ui.control_dock, 'comboBoxColorByField'):
                                field_type = self.ui.control_dock.comboBoxColorByField.currentText()
                                if field_type:
                                    current_plot_info['field_type'] = field_type
                                    
                            if hasattr(self.ui.control_dock, 'comboBoxColorField'):
                                field = self.ui.control_dock.comboBoxColorField.currentText()
                                if field:
                                    current_plot_info['field'] = field
            
            # If we couldn't get from SingleView, try to get from UI plot_info
            if not current_plot_info and hasattr(self.ui, 'plot_info') and self.ui.plot_info:
                current_plot_info = self.ui.plot_info.copy()
                # Ensure it has required fields
                if 'view' not in current_plot_info:
                    current_plot_info['view'] = [True, False]
                if 'position' not in current_plot_info:
                    current_plot_info['position'] = None
            
            if not current_plot_info:
                log("No current plot available to save", "WARNING")
                return False
                
            # Validate required fields
            required_fields = ['sample_id', 'plot_type']
            for field in required_fields:
                if field not in current_plot_info:
                    log(f"Plot info missing required field: {field}", "WARNING")
                    return False
            
            # Register plot in registry if registry is available
            if hasattr(self.ui, 'plot_registry') and self.ui.plot_registry:
                plot_id = self.ui.plot_registry.register_plot(current_plot_info)
                log(f"Registered plot in registry: {plot_id}", "INFO")
            
            # Add to plot tree
            if hasattr(self.ui, 'plot_tree') and self.ui.plot_tree:
                self.ui.plot_tree.add_tree_item(current_plot_info)
                plot_name = current_plot_info.get('plot_name', 'Saved Plot')
                log(f"Added plot to tree: {plot_name}", "INFO")
                return True
            else:
                log("Plot tree not available", "WARNING")
                return False
                
        except Exception as e:
            log(f"Error saving plot to tree: {e}", "ERROR")
            return False

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

    def get_SV_widget(self, index):
        layout = self.single_view.layout()
        if layout is not None:
            item = layout.itemAt(index)
            if item is not None:
                return item.widget()
        return None

    def toggle_distance_tool(self):
        canvas = self.get_SV_widget(1)
        if not isinstance(canvas, MplCanvas):
            return

        if not self.toolbar.sv.toolButtonDistance.isChecked():
            canvas.distance_reset()
            for line, dtext in zip(reversed(canvas.saved_line), reversed(canvas.saved_dtext)):
                line.remove()
                dtext.remove()
            canvas.saved_line = []
            canvas.saved_dtext = []
            canvas.draw()

class SingleViewTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setObjectName("singleViewTab")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        tab_layout = QVBoxLayout(self)
        tab_layout.setSpacing(0)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(tab_layout)

        parent.addTab(self, "Single View")

class MultiViewTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setObjectName("multiViewTab")
        self.setMinimumSize(QSize(0, 0))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        tab_layout = QGridLayout()
        tab_layout.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        tab_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(tab_layout)

        parent.addTab(self, "Multi View")

class QuickViewTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setObjectName("quickViewTab")
        self.setMinimumSize(QSize(0, 0))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        tab_layout = QGridLayout()
        tab_layout.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        tab_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(tab_layout)

        parent.addTab(self, "Quick View")

class NavigationWidgetsSV(VisibilityWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        navigation_layout = QHBoxLayout()
        navigation_layout.setContentsMargins(3, 3, 3, 3)
        navigation_layout.setSpacing(2)
        self.setLayout(navigation_layout)

        self.toolButtonHome = CustomToolButton(
            text="Reset Axes",
            light_icon_unchecked="icon-home-64.svg",
            dark_icon_unchecked="icon-home-dark-64.svg",
            parent=self
        )
        self.toolButtonHome.setObjectName("toolButtonHome")

        self.toolButtonPan = CustomToolButton(
            text = "Pan",
            light_icon_unchecked="icon-move-64.svg",
            dark_icon_unchecked="icon-move-dark-64.svg",
            parent=self
        )
        self.toolButtonPan.setObjectName("toolButtonPan")
        self.toolButtonPan.setCheckable(True)
        self.toolButtonPan.setChecked(False)

        self.toolButtonZoom = CustomToolButton(
            text="",
            light_icon_unchecked="icon-zoom-64.svg",
            dark_icon_unchecked="icon-zoom-64.svg",
            parent=self,
        )
        self.toolButtonZoom.setCheckable(True)
        self.toolButtonZoom.setObjectName("toolButtonZoom")
        self.toolButtonZoom.setCheckable(True)
        self.toolButtonZoom.setChecked(False)

        self.toolButtonAnnotate = CustomToolButton(
            text="Annotate",
            light_icon_unchecked="icon-annotate-64.svg",
            dark_icon_unchecked="icon-annotate-dark-64.svg",
            parent=self,
        )
        self.toolButtonAnnotate.setCheckable(True)
        self.toolButtonAnnotate.setObjectName("toolButtonAnnotate")
        self.toolButtonAnnotate.setCheckable(True)
        self.toolButtonAnnotate.setChecked(False)

        self.toolButtonDistance = CustomToolButton(
            text="Calculate\nDistance",
            light_icon_unchecked="icon-distance-64.svg",
            dark_icon_unchecked="icon-distance-dark-64.svg",
            parent=self,
        )
        self.toolButtonDistance.setCheckable(True)
        self.toolButtonDistance.setObjectName("toolButtonDistance")
        self.toolButtonDistance.setCheckable(True)
        self.toolButtonDistance.setChecked(False)

        self.toolButtonPopFigure = CustomToolButton(
            text="Pop Figure",
            light_icon_unchecked="icon-popout-64.svg",
            dark_icon_unchecked="icon-popout-dark-64.svg",
            parent=self,
        )
        self.toolButtonPopFigure.setObjectName("toolButtonPopFigure")
        self.toolButtonPopFigure.setToolTip("Pop the figure out into a separate window")

        navigation_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.widgetPlotInfo = QWidget(parent=self)
        self.widgetPlotInfo.setObjectName("widgetPlotInfo")

        plot_info_layout = QHBoxLayout(self.widgetPlotInfo)
        plot_info_layout.setContentsMargins(0, 0, 0, 0)

        label_stats = QLabel(self.widgetPlotInfo)
        label_stats.setText("Stats:")

        self.labelInfoY = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoY.setMinimumSize(QSize(60, 0))
        self.labelInfoY.setMaximumSize(QSize(60, 16777215))
        self.labelInfoY.setObjectName("labelInfoY")
        self.labelInfoY.setText("Y: 0")

        self.labelInfoX = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoX.setMinimumSize(QSize(60, 0))
        self.labelInfoX.setMaximumSize(QSize(60, 16777215))
        self.labelInfoX.setObjectName("labelInfoX")
        self.labelInfoX.setText("X: 0")

        self.labelInfoValue = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoValue.setMinimumSize(QSize(80, 0))
        self.labelInfoValue.setMaximumSize(QSize(80, 16777215))
        self.labelInfoValue.setObjectName("labelInfoValue")
        self.labelInfoValue.setText("V: 0")
        self.labelInfoValue.setToolTip("Value at mouse pointer")

        self.labelInfoDistance = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoDistance.setMinimumSize(QSize(80, 0))
        self.labelInfoDistance.setMaximumSize(QSize(80, 16777215))
        self.labelInfoDistance.setObjectName("labelInfoDistance")
        self.labelInfoDistance.setText("D: 0")
        self.labelInfoDistance.setToolTip("Distance from anchor point to mouse pointer")

        coordinate_layout = QVBoxLayout()
        coordinate_layout.addWidget(self.labelInfoY)
        coordinate_layout.addWidget(self.labelInfoX)

        stats_layout = QVBoxLayout()
        stats_layout.addWidget(self.labelInfoValue)
        stats_layout.addWidget(self.labelInfoDistance)

        plot_info_layout.addWidget(label_stats)
        plot_info_layout.addLayout(coordinate_layout)
        plot_info_layout.addLayout(stats_layout)

        navigation_layout.addWidget(self.toolButtonHome)
        navigation_layout.addWidget(self.toolButtonPan)
        navigation_layout.addWidget(self.toolButtonZoom)
        navigation_layout.addWidget(self.toolButtonAnnotate)
        navigation_layout.addWidget(self.toolButtonDistance)
        navigation_layout.addWidget(self.toolButtonPopFigure)
        navigation_layout.addItem(navigation_spacer)
        navigation_layout.addWidget(self.widgetPlotInfo)

        # button_group = QButtonGroup(self)
        # button_group.addButton(self.toolButtonPan)
        # button_group.addButton(self.toolButtonZoom)
        # button_group.addButton(self.toolButtonAnnotate)
        # button_group.addButton(self.toolButtonDistance)
        # button_group.setExclusive(True)

    def connect_widgets(self):
        self.visibilityChanged.connect(lambda _: self.reset_buttons)
        self.toolButtonPopFigure.clicked.connect(lambda _: self.all_buttons_off)
        self.toolButtonPan.clicked.connect(lambda _: self.update_button_state(button=self.toolButtonPan))
        self.toolButtonZoom.clicked.connect(lambda _: self.update_button_state(button=self.toolButtonZoom))
        self.toolButtonAnnotate.clicked.connect(lambda _: self.update_button_state(button=self.toolButtonAnnotate))
        self.toolButtonDistance.clicked.connect(lambda _: self.update_button_state(button=self.toolButtonDistance))

    def update_tool_availability(self, canvas=None):
        """Update tool availability based on current canvas/plot type."""
        if canvas is None or not hasattr(canvas, 'map_flag'):
            return
            
        # Enable/disable distance tool based on whether this is a map
        is_map = canvas.map_flag
        self.toolButtonDistance.setEnabled(is_map)
        
        if not is_map and self.toolButtonDistance.isChecked():
            self.toolButtonDistance.setChecked(False)

    def reset_buttons(self):
        if not self.isVisible():
            return
        self.all_buttons_off()

    def all_buttons_off(self):
        self.toolButtonZoom.setChecked(False)
        self.toolButtonPan.setChecked(False)
        self.toolButtonAnnotate.setChecked(False)
        self.toolButtonDistance.setChecked(False)

    def update_button_state(self, button):
        if not button.isChecked():
            return

        for btn in [self.toolButtonPan, self.toolButtonZoom, self.toolButtonAnnotate, self.toolButtonDistance]:
            if btn == button:
                continue
            else:
                btn.setChecked(False)


class NavigationWidgetsMV(VisibilityWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        navigation_layout = QHBoxLayout()
        navigation_layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(navigation_layout)


        self.labelMaxRows = QLabel(parent=self)
        self.labelMaxRows.setObjectName("labelMaxRows")
        self.labelMaxRows.setText("Max rows:")

        self.spinBoxMaxRows = QSpinBox(parent=self)
        self.spinBoxMaxRows.setMinimum(1)
        self.spinBoxMaxRows.setMaximum(6)
        self.spinBoxMaxRows.setProperty("value", 2)
        self.spinBoxMaxRows.setObjectName("spinBoxMaxRows")

        self.labelMaxCols = QLabel(parent=self)
        self.labelMaxCols.setObjectName("labelMaxCols")
        self.labelMaxCols.setText("Max cols:")

        self.spinBoxMaxCols = QSpinBox(parent=self)
        self.spinBoxMaxCols.setMinimum(1)
        self.spinBoxMaxCols.setMaximum(8)
        self.spinBoxMaxCols.setProperty("value", 3)
        self.spinBoxMaxCols.setObjectName("spinBoxMaxCols")

        spinbox_width = 40

        for sb in [self.spinBoxMaxRows, self.spinBoxMaxCols]:
            sb.setMinimumWidth(spinbox_width)
            sb.setMaximumWidth(spinbox_width)
            sb.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.comboBoxMVPlots = CustomComboBox(parent=self)
        self.comboBoxMVPlots.setObjectName("comboBoxMVPlots")

        self.toolButtonRemoveAllPlots = CustomToolButton(
            text="Remove All",
            light_icon_unchecked="icon-delete-all-64.svg",
            dark_icon_unchecked="icon-delete-all-dark-64.svg",
            parent=self,
        )
        self.toolButtonRemoveAllPlots.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.toolButtonRemoveAllPlots.setObjectName("toolButtonRemoveAllPlots")
        self.toolButtonRemoveAllPlots.setToolTip("Remove all plots from the multiview canvas")

        self.toolButtonRemovePlot = CustomToolButton(
            text="Remove Selected",
            light_icon_unchecked="icon-eraser-64.svg",
            parent=self,
        )
        self.toolButtonRemovePlot.setObjectName("toolButtonRemovePlot")

        navigation_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.widgetPlotInfo = QWidget(parent=self)
        self.widgetPlotInfo.setObjectName("widgetPlotInfoMV")

        plot_info_layout = QHBoxLayout(self.widgetPlotInfo)
        plot_info_layout.setContentsMargins(0, 0, 0, 0)

        self.labelInfoLabel = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoLabel.setMaximumSize(QSize(35, 16777215))
        self.labelInfoLabel.setObjectName("labelInfoLabel")

        self.labelInfoX = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoX.setMinimumSize(QSize(60, 0))
        self.labelInfoX.setMaximumSize(QSize(60, 16777215))
        self.labelInfoX.setObjectName("labelInfoX")

        self.labelInfoY = QLabel(parent=self.widgetPlotInfo)
        self.labelInfoY.setMinimumSize(QSize(60, 0))
        self.labelInfoY.setMaximumSize(QSize(60, 16777215))
        self.labelInfoY.setObjectName("labelInfoY")

        coordinate_layout = QVBoxLayout()
        coordinate_layout.addWidget(self.labelInfoY)
        coordinate_layout.addWidget(self.labelInfoX)

        plot_info_layout.addWidget(self.labelInfoLabel)
        plot_info_layout.addLayout(coordinate_layout)

        navigation_layout.addWidget(self.labelMaxRows)
        navigation_layout.addWidget(self.spinBoxMaxRows)
        navigation_layout.addWidget(self.labelMaxCols)
        navigation_layout.addWidget(self.spinBoxMaxCols)
        navigation_layout.addWidget(self.comboBoxMVPlots)
        navigation_layout.addWidget(self.toolButtonRemovePlot)
        navigation_layout.addWidget(self.toolButtonRemoveAllPlots)
        navigation_layout.addItem(navigation_spacer)
        navigation_layout.addWidget(self.widgetPlotInfo)

class NavigationWidgetsQV(VisibilityWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        navigation_layout = QHBoxLayout()
        navigation_layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(navigation_layout)

        list_label = QLabel()
        list_label.setText("QV List:")

        self.comboBoxQVList = QComboBox(parent=self)
        self.comboBoxQVList.setObjectName("comboBoxQVList")

        self.toolButtonNewList = CustomToolButton(
            text="Add list",
            light_icon_unchecked="icon-add-list-64.svg",
            dark_icon_unchecked="icon-add-list-dark-64.svg",
            parent=self,
        )
        self.toolButtonNewList.setObjectName("toolButtonNewList")

        navigation_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        navigation_layout.addWidget(list_label)
        navigation_layout.addWidget(self.comboBoxQVList)
        navigation_layout.addWidget(self.toolButtonNewList)
        navigation_layout.addItem(navigation_spacer)


class CanvasToolBar(QGroupBox):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.parent = parent

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        self.setMinimumSize(QSize(200, 50))
        self.setMaximumSize(QSize(16777215, 50))
        self.setTitle("")
        self.setObjectName("groupBoxPlotToolBar")

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(toolbar_layout)

        # single view nav widgets
        self.sv = NavigationWidgetsSV()
        self.sv.hide()
        # multi view nav widgets
        self.mv = NavigationWidgetsMV()
        self.mv.hide()
        # quick view nav widgets
        self.qv = NavigationWidgetsQV()
        self.qv.hide()

        toolbar_layout.addWidget(self.sv)
        toolbar_layout.addWidget(self.mv)
        toolbar_layout.addWidget(self.qv)

        # widgets common to all
        self.toolButtonSave = CustomToolButton(
            text="Save Figure",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=self,
        )
        self.toolButtonSave.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.toolButtonSave.setObjectName("toolButtonSave")
        self.toolButtonSave.setShortcut("Ctrl+P")
        
        #SaveMenu_items = ['Figure', 'Data', 'Both']
        #SaveMenu = QMenu(self)
        #SaveMenu.triggered.connect(lambda action: self.parent.ui.io.save_plot(canvas=self.parent.current_canvas, method=action.text()))

        #self.toolButtonSave.setMenu(SaveMenu)
        #for item in SaveMenu_items:
        #    SaveMenu.addAction(item)

        toolbar_layout.addWidget(self.toolButtonSave)

    def connect_widgets(self):
        self.sv.toolButtonHome.clicked.connect(lambda _: self.parent.current_canvas.toggle_tool('home'))
        self.sv.toolButtonPan.clicked.connect(lambda state: self.parent.current_canvas.toggle_tool('pan', state))
        self.sv.toolButtonZoom.clicked.connect(lambda state: self.parent.current_canvas.toggle_tool('zoom', state))
        self.sv.toolButtonAnnotate.clicked.connect(lambda state: self.parent.current_canvas.toggle_tool('annotate', state))
        self.sv.toolButtonDistance.clicked.connect(lambda state: self.parent.current_canvas.toggle_tool('distance', state))
        self.sv.toolButtonPopFigure.clicked.connect(lambda _: self.move_canvas_to_window())
        self.toolButtonSave.clicked.connect(lambda _: self.parent.ui.io.save_plot(canvas=self.parent.current_canvas, parent=self.parent))

        # quick view
        self.qv.toolButtonNewList.clicked.connect(lambda: QuickView(parent=self.parent))
        self.qv.comboBoxQVList.activated.connect(lambda: self.parent.display_QV())

    def move_canvas_to_window(self):
        self.parent.current_canvas.toggle_tool('pop_figure',True)
        self.parent.current_canvas.redraw_annotations()
        self.pop_figure = PlotWindow(self.parent.ui, self.parent.current_canvas)
        self.pop_figure.show()

        # since the canvas is moved to the dialog, the figure needs to be recreated in the
        # main window trigger update to plot        
        self.parent.ui.schedule_update()

    def update_sv_info(self, *args, **kwargs):
        """Updates the information labels in the SingleView tab."""
        if not self.isVisible():
            return

        canvas = self.parent.current_canvas
        if not isinstance(canvas, MplCanvas):
            return

        xpos = canvas.xpos
        ypos = canvas.ypos

        if xpos is None or ypos is None:
            self.sv.labelInfoX.setText("X: N/A")
            self.sv.labelInfoY.setText(f"Y: N/A")
        else:
            self.sv.labelInfoX.setText(f"X: {xpos:.4g}")
            self.sv.labelInfoY.setText(f"Y: {ypos:.4g}")
        if canvas.array is not None:
            val = canvas.value
            units = canvas.color_units or ''
            if val:
                self.sv.labelInfoValue.setText(f"V: {val:.2f} {units}")
        else:
            self.sv.labelInfoValue.setText("V: N/A")
        if self.sv.toolButtonDistance.isChecked():
            distance = canvas.distance
            units = canvas.distance_units or ''
            if distance:
                self.sv.labelInfoDistance.setText(f"D: {distance:.2f} {units}")


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
            text="Sort fields for Quick View",
            menu_items=sortmenu_items,
            light_icon_unchecked="icon-sort-64.svg",
            dark_icon_unchecked="icon-sort-64.svg",
            parent=toolbar,
        )

        self.label = QLabel()
        self.label.setText("Enter name:")

        self.lineEditQVName = QLineEdit(toolbar)
        self.lineEditQVName.setFont(font)
        self.lineEditQVName.setText("")
        self.lineEditQVName.setObjectName("lineEditViewName")

        self.save_action = CustomAction(
            text="Save Figure",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=toolbar,
        )
        self.save_action.setObjectName("actionSaveFigure")
        self.save_action.setToolTip("Save current analyte list")

        self.apply_action = CustomAction(
            text="Apply",
            light_icon_unchecked="icon-add-list-64.svg",
            dark_icon_unchecked="icon-add-list-dark-64.svg",
            parent=toolbar
        )
        self.apply_action.setObjectName("actionApply")
        self.apply_action.setToolTip("Apply current analyte list to Quick View")

        self.save_action.triggered.connect(lambda: self.apply_selected_analytes(save=True))
        self.apply_action.triggered.connect(lambda: self.apply_selected_analytes(save=False))

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
        if self.ui.canvas_widget.toolbar.qv.comboBoxQVList.findText(self.view_name) == -1:
            self.ui.canvas_widget.toolbar.qv.omboBoxQVList.addItem(self.view_name)
        
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
        file_path = APPDATA_PATH / 'qv_lists.csv'

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # append dictionary to file of saved qv_lists
        if hasattr(self.parent, 'QV_analyte_list'):
            csvdict.export_dict_to_csv(self.parent.QV_analyte_list, file_path)
            QMessageBox.information(self, "Save Successful", f"Analytes view saved under '{self.view_name}' successfully.")
        else:
            QMessageBox.warning(self, "Error", "Could not save analyte list.")


class PlotWindow(QDialog):
    def __init__(self, parent, canvas):
        """A plot dialog

        This dialog is used to plot a matplotlib figure.  In general the dialog is used when a figure popped out
        from ``MainWindow.canvasWindow`` using ``CanvasWindow.toolbar.sv.toolButtonPopFigure``.

        Parameters
        ----------
        parent : MainWindow
            Calling class.
        canvas : MplCanvas
            Matplotlib plot canvas.
        title : str, optional
            Dialog title, by default ''
        """        
        super().__init__(parent)

        self.parent = parent

        self.setWindowTitle(canvas.plot_name)

        # Create a QVBoxLayout to hold the canvas and toolbar
        layout = QVBoxLayout(self)

        # Create a NavigationToolbar and add it to the layout
        self.toolbar = NavigationToolbar(canvas, self)

        # use custom buttons
        unwanted_buttons = ["Back", "Forward", "Customize", "Subplots"]

        icons_buttons = {
            "Home": QIcon(str(ICONPATH / "icon-home-64.svg")),
            "Pan": QIcon(str(ICONPATH / "icon-move-64.svg")),
            "Zoom": QIcon(str(ICONPATH / "icon-zoom-64.svg")),
            "Save": QIcon(str(ICONPATH / "icon-save-file-64.svg"))
        }
        for action in self.toolbar.actions():
            if action.text() in unwanted_buttons:
                self.toolbar.removeAction(action)
            if action.text() in icons_buttons:
                action.setIcon(icons_buttons.get(action.text(), QIcon()))

        self.toolbar.setMaximumHeight(int(32))
        self.toolbar.setIconSize(QSize(24,24))

        # Add toolbar to self.layout
        layout.addWidget(self.toolbar,0)

        # Add a matplotlib canvas to self.layout
        layout.addWidget(canvas,1)

        # Create a button box for OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box,2)

        #self.parent.clear_layout(self.parent.layout())


class CanvasDialog(QDialog):
    """
    A non-modal top-level window that hosts a full CanvasWidget instance.
    Use this from BlocklyModules so it appears as a separate window.
    """
    def __init__(self, ui, parent=None):
        # parent: keep it the top-level main window if available
        super().__init__(parent)
        self.setObjectName("CanvasDialog")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowTitle("Canvas")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Host a fresh CanvasWidget inside this dialog (independent from MainWindow’s central widget)
        self.canvas_widget = CanvasWidget(ui=ui, parent=self)
        layout.addWidget(self.canvas_widget)
    
    def closeEvent(self, event):
        """Hide instead of destroying; keeps C++ object alive."""
        event.ignore()
        self.hide()

    def get_canvas(self) -> "CanvasWidget":
        return self.canvas_widget