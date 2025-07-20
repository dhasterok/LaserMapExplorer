from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSizePolicy, QMenu, QFileDialog
)
from pyqtgraph import (
    ViewBox, 
    GraphicsLayoutWidget,
)
from pyqtgraph.GraphicsScene import exportDialog
from src.ui.PlotViewer import Ui_widgetPlotViewer
from src.app.config import BASEDIR
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import src.common.CustomMplCanvas as mplc
from src.common.Logger import auto_log_methods

# Analyte GUI
# -------------------------------
@auto_log_methods(logger_key="Plot")
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
        self.logger_key = "Plot"
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
        self.widgetSingleView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mpl_toolbar = None
        
                # Plot toolbars
        #-------------------------

        # single view tools
        self.toolButtonHome.clicked.connect(lambda: self.toolbar_plotting('home', 'SV'))
        self.toolButtonPan.clicked.connect(lambda: self.toolbar_plotting('pan', 'SV', self.toolButtonPan.isChecked()))
        self.toolButtonZoom.clicked.connect(lambda: self.toolbar_plotting('zoom', 'SV', self.toolButtonZoom.isChecked()))
        self.toolButtonAnnotate.clicked.connect(lambda: self.toolbar_plotting('annotate', 'SV'))
        self.toolButtonDistance.toggled.connect(self.toggle_distance_tool)
        self.toolButtonDistance.clicked.connect(lambda: self.toolbar_plotting('distance', 'SV'))
        self.toolButtonPopFigure.clicked.connect(lambda: self.toolbar_plotting('pop', 'SV'))
        # self.toolButtonSave.clicked.connect(lambda: self.toolbar_plotting('save', 'SV', self.toolButtonSave.isChecked()))
        SaveMenu_items = ['Figure', 'Data']
        SaveMenu = QMenu()
        SaveMenu.triggered.connect(self.save_plot)
        self.toolButtonSave.setMenu(SaveMenu)
        for item in SaveMenu_items:
            SaveMenu.addAction(item)
        

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
            A layout associated with widgetSingleView.
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

    def toolbar_plotting(self,function,view,enable=None):
        """Controls functionality of the toolbar

        Controls the viewing behavior, home view, pan, zoom, pop out, and saving.

        Parameters
        ----------
        function : str
            Button fuction
        view : _type_
            _description_
        enable : _type_
            _description_
        """
        
        match view:
            case 'SV':
                canvas = self.sv_widget
            case 'MV':
                pass
            case 'QV':
                pass

        if function == 'home':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                canvas.restore_view()

            elif isinstance(canvas,GraphicsLayoutWidget):
                canvas.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                # Toggle pan mode in Matplotlib
                self.mpl_toolbar.pan()
                print(self.mpl_toolbar)
                #canvas.figure.canvas.toolbar.pan()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Enable or disable panning
                canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode if enable else ViewBox.RectMode)

        if function == 'zoom':
            self.toolButtonPan.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                # Toggle zoom mode in Matplotlib
                self.mpl_toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming pyqtgraph_widget is a GraphicsLayoutWidget or similar
                if enable:

                    canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.RectMode)
                else:
                    canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode)

        if function == 'annotate':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
        
        if function == 'distance':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)


        if function == 'preference':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.edit_parameters()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming it's about showing/hiding axes
                if enable:
                    canvas.showAxis('left', True)
                    canvas.showAxis('bottom', True)
                else:
                    canvas.showAxis('left', False)
                    canvas.showAxis('bottom', False)

        if function == 'axes':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.configure_subplots()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming it's about showing/hiding axes
                if enable:
                    canvas.showAxis('left', True)
                    canvas.showAxis('bottom', True)
                else:
                    canvas.showAxis('left', False)
                    canvas.showAxis('bottom', False)
        
        if function == 'pop':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                self.pop_figure = mplc.MplDialog(self,canvas,self.parent.plot_info['plot_name'])
                self.pop_figure.show()

            # since the canvas is moved to the dialog, the figure needs to be recreated in the main window
            # trigger update to plot        
            self.plot_style.scheduler.schedule_update()

        if function == 'save':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.save_figure()
            elif isinstance(canvas,GraphicsLayoutWidget):
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
                export.show(canvas.getItem(0, 0).getViewBox())
                export.exec()
                
    def save_plot(self, action):
        """Sorts analyte table in dialog"""        
        # get save method (Figure/Data)
        canvas = self.sv_widget #get the widget in SV layout
        method = action.text()
        if method == 'Figure':
            if isinstance(canvas, mplc.MplCanvas):
                self.mpl_toolbar.save_figure()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
                export.show(canvas.getItem(0, 0).getViewBox())

        elif method == 'Data':
            if self.plot_info:
                sample_id = self.plot_info['sample_id']
                plot_type = self.plot_info['plot_type']
                
                match plot_type:
                    case 'field map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.data[self.sample_id].get_map_data(field, field_type)
                    case 'gradient map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.data[self.sample_id].get_map_data(field, field_type)
                        filtered_image = self.noise_red_array
                    case 'cluster':
                        save_data= self.data[self.sample_id].processed_data[field]
                    case _:
                        save_data = self.plot_info['data']
                    
            #open dialog to get name of file
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_name:
                with open(file_name, 'wb') as file:
                    # self.save_data holds data used for current plot 
                    save_data.to_csv(file,index = False)
                
                self.statusBar.showMessage("Plot Data saved successfully")

    def toggle_distance_tool(self):
        canvas = self.get_SV_widget(1)
        if not isinstance(canvas, mplc.MplCanvas):
            return
