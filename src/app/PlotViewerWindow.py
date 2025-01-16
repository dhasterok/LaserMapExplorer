from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QEvent)
from PyQt5.QtWidgets import (QWidget,QVBoxLayout, QGridLayout, QSizePolicy, QDialog, QTableWidgetItem, QLabel, QComboBox, QHeaderView, QFileDialog, QMessageBox)
from PyQt5.QtGui import (QImage, QColor, QFont, QPixmap, QPainter, QBrush)
from src.ui.PlotViewer import Ui_widgetPlotViewer
from src.common.rotated import RotatedHeaderView
from src.app.config import BASEDIR
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import os
# Analyte GUI
# -------------------------------
class PlotViewer(QWidget, Ui_widgetPlotViewer):
    """Creates an widget to display plots

    plot can be viewed in Singleview, Multiview and Quickview

    Parameters
    ----------
    QWidget : 
        _description_
    Ui_Dialog : 
        _description_

    Returns
    -------
    _type_
        _description_
    """    
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.duplicate_plot_info = None

        # Plot Layouts
        #-------------------------
        # Central widget plot view layouts
        # single view
        layout_single_view = QVBoxLayout()
        layout_single_view.setSpacing(0)
        layout_single_view.setContentsMargins(0, 0, 0, 0)
        self.widgetSingleView.setLayout(layout_single_view)
        self.widgetSingleView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mpl_toolbar = None
        
        
        self.canvas_tab = {}
        for tid in range(self.plot_viewer.canvasWindow.count()):
            match self.plot_viewer.canvasWindow.tabText(tid).lower():
                case 'single view':
                    self.canvas_tab.update({'sv': tid})
                case 'multi view':
                    self.canvas_tab.update({'mv': tid})
                case 'quick view':
                    self.canvas_tab.update({'qv': tid})
        

    def add_plotwidget_to_plot_viewer(self, plot_info, position=None):
        """Adds plot to selected view

        Parameters
        ----------
        plot_info : dict
            A dictionary with details about the plot
        current_plot_df : dict, optional
            Defaults to None
        """
        #print('add_plotwidget_to_canvas')
        if self.widgetSingleView:
            self.sv_widget = plot_info['figure']
            self.update_canvas(self.sv_widget)
            self.sv_widget.show()


    def clear_layout(self, layout):
        """Clears a widget that contains plots

        Parameters
        ----------
        layout : QLayout
            A layout associated with a ``canvasWindow`` tab.
        """
        #remove current plot
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()   # Get the widget from the item
                if widget is not None:
                    widget.hide()
                    # layout.removeWidget(widget)  # Remove the widget from the layout
                    # widget.setParent(None)      # Set the widget's parent to None

        if self.canvasWindow.currentIndex() == self.parent.canvas_tab['mv']:
            list = self.comboBoxMVPlots.allItems()
            if not list:
                return

            for i, _ in enumerate(list):
                # get data from comboBoxMVPlots
                data = self.comboBoxMVPlots.itemData(i, role=Qt.UserRole)

                # # get plot_info from tree location and
                # # reset view to False and position to none
                # plot_info = self.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                # #print(plot_info)
                # plot_info['view'][1] = False
                # plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.comboBoxMVPlots.clear()


    def update_canvas(self, new_canvas):
        # Clear the existing layout
        self.clear_layout(self.widgetSingleView.layout())
        
        
        # Add the new canvas to the layout
        self.widgetSingleView.layout().addWidget(new_canvas)
        
        try:
            # Recreate the NavigationToolbar with the new canvas
            self.mpl_toolbar = NavigationToolbar(new_canvas, self.widgetSingleView)
            #hide the toolbar
            self.mpl_toolbar.hide()
            self.widgetSingleView.layout().addWidget(self.mpl_toolbar)
        except:
            # canvas is not a mplc.MplCanvas  
            pass
