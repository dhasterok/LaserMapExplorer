from PyQt6 import QtGui
from PyQt6.QtCore import (
    Qt, QSize
)
from PyQt6.QtWidgets import (
    QVBoxLayout, QDialog, QInputDialog, QDialogButtonBox, QMenu
)
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import FigureManagerQT
from matplotlib.figure import Figure
import pandas as pd
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import matplotlib as mpl
from src.app.config import BASEDIR

# set the directory where figures are saved
save_dir = BASEDIR / "saved" / "figure"
save_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
mpl.rcParams['savefig.directory'] = str(save_dir)
# Matplotlib Canvas object
# -------------------------------
class SimpleMplCanvas(FigureCanvas):
    """Matplotlib canvas object for non-interactive plots

    Parameters
    ----------
    sub : int, optional
        Subplot location, by default 111
    parent : object, optional
        Parent calling MplCanvas, by default None
    width : int, optional
        Width in inches, by default 5
    height : int, optional
        Height in inches, by default 4
    proj : str, optional
        Projection, by default None
    """    
    def __init__(self, sub=111, parent=None, width=5, height=4, proj=None):
        self.fig = Figure(figsize=(width, height))
        if proj is not None:
            self.axes = self.fig.add_subplot(sub, projection='radar')
        else:
            self.axes = self.fig.add_subplot(sub)
        super(SimpleMplCanvas, self).__init__(self.fig)

        self.parent = parent


class MplCanvas(FigureCanvas):
    """Matplotlib canvas object for interactive plots

    Parameters
    ----------
    sub : int, optional
        Subplot location, by default 111
    parent : object, optional
        Parent calling MplCanvas, by default None
    width : int, optional
        Width in inches, by default 5
    height : int, optional
        Height in inches, by default 4
    proj : str, optional
        Projection, by default None
    """    
    def __init__(self,fig=None, sub=111, parent=None, width=5, height=4, proj=None, ui= None):
        #create MPLCanvas with existing figure (required when loading saved projects)
        if fig:
            self.fig = fig
        else:
            self.fig = Figure(figsize=(width, height))
        if proj is not None:
            self.axes = self.fig.add_subplot(sub, projection='radar')
        else:
            self.axes = self.fig.add_subplot(sub)
        super(MplCanvas, self).__init__(self.fig)

        # Create a FigureManagerQT for your canvas
        self.manager = FigureManagerQT(self, num=1)
        if parent is None:
            return
        self.parent = parent
        
        # if ui components does are not part of parent initialise them seperately
        if ui:
            self.ui = ui
        else:
            self.ui = parent
        
        # Hold the data of the canvas as a pandas DataFrame
        self._data = None
        self._plot_name = None
        # for placing text annotations
        # --------------------
        self.setCursorPosition()

        # restoring initial axes
        # --------------------
        self.initial_extent = None

        # distance measurement
        # --------------------
        # Variables to store points and line
        self.first_point = None
        self.line = None
        self.dtext = None
        self.saved_line = []
        self.saved_dtext = []
        self.array = None
        self.annotations = {}
        
        self.interaction_mode = None
        self.distance_cid_press = None
        self.distance_cid_move = None


        if self.parent is not None and self.parent.app_data.sample_id in self.parent.app_data.data:
            if self.parent.plot_style.plot_type in self.parent.plot_style.map_plot_types:
                self.map_flag = True
            else:
                self.map_flag = False
            
            self.mpl_connect('motion_notify_event', self.mouseLocation)
        
        self.mpl_toolbar = NavigationToolbar(self)

        # enable distance mode by default
        self.ui.toolButtonDistance.clicked.connect( self.enable_distance_mode)
        self.ui.toolButtonHome.clicked.connect( self.enable_distance_mode)
        self.ui.toolButtonPan.clicked.connect(lambda: self.toolbar_plotting('pan', 'SV', self.ui.toolButtonPan.isChecked()))
        self.ui.toolButtonZoom.clicked.connect(lambda: self.toolbar_plotting('zoom', 'SV', self.ui.toolButtonZoom.isChecked()))   
        self.ui.toolButtonAnnotate.clicked.connect(lambda: self.toolbar_plotting('annotate', 'SV'))
        
        SaveMenu_items = ['Figure', 'Data']
        SaveMenu = QMenu()
        SaveMenu.triggered.connect(self.save_plot)
        self.ui.toolButtonSave.setMenu(SaveMenu)
        for item in SaveMenu_items:
            SaveMenu.addAction(item)


        if hasattr(self.ui, 'toolButtonPopFigure'):
            self.ui.toolButtonPopFigure.clicked.connect(lambda: self.toolbar_plotting('pop', 'SV'))

    @property
    def plot_name(self):
        """Return the stored pandas DataFrame."""
        return self._plot_name

    @plot_name.setter
    def plot_name(self, value):
        """Set the plot_name only if it is a str."""
        if value is None or isinstance(value, str):
            self._plot_name = value
        else:
            raise TypeError("plot_name must be a str or None")
    
    @property
    def data(self):
        """Return the stored pandas DataFrame."""
        return self._data

    @data.setter
    def data(self, value):
        """Set the data only if it is a pandas DataFrame."""
        if value is None or isinstance(value, pd.DataFrame):
            self._data = value
        else:
            raise TypeError("data must be a pandas DataFrame or None")
    
    
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
            self.ui.toolButtonPan.setChecked(False)
            self.ui.toolButtonZoom.setChecked(False)
            self.ui.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,MplCanvas):
                canvas.restore_view()

            # elif isinstance(canvas,GraphicsLayoutWidget):
            #     canvas.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.ui.toolButtonZoom.setChecked(False)
            self.ui.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,MplCanvas):
                # Toggle pan mode in Matplotlib
                self.mpl_toolbar.pan()
                print(self.mpl_toolbar)
                #canvas.figure.canvas.toolbar.pan()

            # elif isinstance(canvas,GraphicsLayoutWidget):
            #     # Enable or disable panning
            #     canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode if enable else ViewBox.RectMode)

        if function == 'zoom':
            self.ui.toolButtonPan.setChecked(False)
            self.ui.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,MplCanvas):
                # Toggle zoom mode in Matplotlib
                self.mpl_toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            # elif isinstance(canvas,GraphicsLayoutWidget):
            #     # Assuming pyqtgraph_widget is a GraphicsLayoutWidget or similar
            #     if enable:

            #         canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.RectMode)
            #     else:
            #         canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode)

        if function == 'annotate':
            self.ui.toolButtonPan.setChecked(False)
            self.ui.toolButtonZoom.setChecked(False)
        
        if function == 'distance':
            self.ui.toolButtonPan.setChecked(False)
            self.ui.toolButtonZoom.setChecked(False)


        if function == 'preference':
            if isinstance(canvas,MplCanvas):
                self.mpl_toolbar.edit_parameters()

            # elif isinstance(canvas,GraphicsLayoutWidget):
            #     # Assuming it's about showing/hiding axes
            #     if enable:
            #         canvas.showAxis('left', True)
            #         canvas.showAxis('bottom', True)
            #     else:
            #         canvas.showAxis('left', False)
            #         canvas.showAxis('bottom', False)

        if function == 'axes':
            if isinstance(canvas,MplCanvas):
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
            self.ui.toolButtonPan.setChecked(False)
            self.ui.toolButtonZoom.setChecked(False)
            self.ui.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,MplCanvas):
                self.pop_figure = MplDialog(self,canvas,self.plot_info['plot_name'])
                self.pop_figure.show()

            # since the canvas is moved to the dialog, the figure needs to be recreated in the main window
            # trigger update to plot        
            self.plot_style.schedule_update()

        if function == 'save':
            if isinstance(canvas,MplCanvas):
                self.mpl_toolbar.save_figure()
        #     elif isinstance(canvas,GraphicsLayoutWidget):
        #         # Save functionality for pyqtgraph
        #         export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
        #         export.show(canvas.getItem(0, 0).getViewBox())
        #         export.exec()
                
    def save_plot(self, action):
        """Sorts analyte table in dialog"""        
        # get save method (Figure/Data)
        method = action.text()
        if method == 'Figure':
            self.mpl_toolbar.save_figure()

            # elif isinstance(canvas,GraphicsLayoutWidget):
            #     # Save functionality for pyqtgraph
            #     export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
            #     export.show(canvas.getItem(0, 0).getViewBox())

        elif method == 'Data':
            if isinstance(self.data, pd.DataFrame):
                self.parent.io.save_data(self.data, self.plot_name)
                    


    def enable_distance_mode(self):
        if self.ui.toolButtonDistance.isChecked():
            # Connect the button and canvas events for distance measurement
            self.distance_cid_press = self.mpl_connect('button_press_event', self.distanceOnClick)
            self.distance_cid_move = self.mpl_connect('motion_notify_event', self.distanceOnMove)

    def disable_distance_mode(self):
        self.mpl_disconnect(self.distance_cid_press)
        self.mpl_disconnect(self.distance_cid_move)
        self.distance_cid_press = None
        self.distance_cid_move = None


    def enterEvent(self, event):
        # Set cursor to cross when the mouse enters the window
        self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        # Reset cursor to default when the mouse leaves the window
        self.unsetCursor()

    def mouseLocation(self,event):
        """Get mouse location on axes for display

        Displays the location and value of a map in ``MainWindow.widgetPlotInfoSV``.

        Parameters
        ----------
        event : event data
            Includes the location of mouse pointer.
        """   
        x = 0
        y = 0     
        if (not event.inaxes) or (event.xdata is None) or (event.ydata is None):
            return

        if event.inaxes.get_label() == '<colorbar>':
            return

        if self.map_flag:
            if self.array is None:
                return
            # pixel location on current MplCanvas
            x_i = round(event.xdata)
            if x_i < 0:
                x_i = 0
            elif x_i > self.array.shape[1]-1:
                x_i = self.array.shape[1]-1
            
            y_i = round(event.ydata)
            if y_i < 0:
                y_i = 0
            elif y_i > self.array.shape[0]-1:
                y_i = self.array.shape[0]-1
            
            #x = x_i*self.parent.dx
            #y = y_i*self.parent.dy
            if self.parent.app_data.sample_id in self.parent.app_data.data:
                x = x_i*self.parent.app_data.data[self.parent.app_data.sample_id].dx
                y = y_i*self.parent.app_data.data[self.parent.app_data.sample_id].dy
            else:
                return

            label =  f" {self.parent.app_data.preferences['Units']['Concentration']}"
        else:
            x = event.xdata
            y = event.ydata
            self.ui.labelSVInfoValue.setText(f"V: N/A")

            if self.array is not None:
                x_i = round(x)
                y_i = round(y)

                label = ''
        

        if self.array is not None:
            value = self.array[y_i][x_i]
            txt = f"V: {value:.4g}{label}"
            self.ui.labelSVInfoValue.setText(txt)

        txt = f'X: {x:.4g}'
        self.ui.labelSVInfoX.setText(txt)
        txt = f'Y: {y:.4g}'
        self.ui.labelSVInfoY.setText(txt)

    def set_initial_extent(self):
        """Initial extent of the plot

        Sets the initital extent of the plot.
        """
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        self.initial_extent = (xlim[0], xlim[1], ylim[0], ylim[1])
        #print(f"Initial extent set to: {self.initial_extent}")

    def restore_view(self):
        """Restores the initial extent

        Restores the initial extent when ``MainWindow.toolButtonHome`` is clicked.
        """
        if self.initial_extent:
            self.axes.set_xlim(self.initial_extent[:2])
            self.axes.set_ylim(self.initial_extent[2:])
        else:
            self.axes.set_xlim(auto=True)
            self.axes.set_ylim(auto=True)
        self.draw()

    def load_figure(self, fig):
        """Load existing figure
        
        Parameters
        ----------
        fig : matplotlib.Figure
            Matplotlib figure.
        """
        self.fig = fig
        self.axes = self.fig.gca()  # Get current axes
        self.draw()  # Redraw the canvas with the loaded figure

    def setCursorPosition(self):
        """Gets the cursor position on an MplCanvas

        Mouse listener
        """        
        self.cid = self.mpl_connect('button_press_event', self.textOnClick)

    def textOnClick(self, event):
        """Adds text to plot at clicked position

        Only adds a text to a plot when the Annotate button is checked.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """ 

        if hasattr(self.ui,'canvas_tab') and hasattr(self.ui,'canvasWindow'):
            if (self.ui.canvasWindow.currentIndex() != self.ui.canvas_tab['sv']) or (not self.ui.toolButtonAnnotate.isChecked()):
                return
        else:
            if (not self.ui.toolButtonAnnotate.isChecked()):
                return

        x,y = event.xdata, event.ydata
        # get text
        txt, ok = QInputDialog.getText(self, 'Figure', 'Enter text:')
        if not ok:
            return

        overlay_color = self.parent.plot_style.overlay_color
        font_size = self.parent.plot_style.font_size
        annotation = self.axes.text(x,y,txt, color=overlay_color, fontsize=font_size)
        self.draw()

        self.annotations[annotation] = {"Type":"Text", "Value":txt, "Visible":True}

    def calculate_distance(self,p1,p2):
        """Calculuates distance on a figure

        Parameters
        ----------
        p1 : _type_
            _description_
        p2 : _type_
            _description_

        Returns
        -------
        float
            Distance between two given points.
        """
        if self.map_flag:
            dx = self.parent.app_data.data[self.parent.app_data.sample_id].dx
            dy = self.parent.app_data.data[self.parent.app_data.sample_id].dy
        else:
            dx = 1
            dy = 1

        return np.sqrt(((p2[0] - p1[0])*dx)**2 + ((p2[1] - p1[1])*dy)**2)

    def plot_line(self, p1, p2):
        """Plots line from distance calculation

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.

        Returns
        -------
        matplotlib.plot
            Handle to line
        """        
        #plot_type = self.parent.app_data.plot_info['plot_type']
        overlay_color = self.parent.plot_style.overlay_color
        line_width = self.parent.plot_style.line_width

        # plot line (keep only first returned handle)
        p = self.axes.plot([p1[0], p2[0]], [p1[1], p2[1]],
                ':', c=overlay_color, lw=line_width
            )[0]

        return p
 
    def plot_text(self, p1,p2):
        """Adds distance to plot and updates distance label

        Updates distance in ``MainWindow.labelSVInfoDistance`` and adds distance
        at the end of the measuring line.

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.

        Returns
        -------
        matplotlib.text
            Handle to text.
        """        
        # plot_type = self.parent.app_data.plot_info['plot_type']
        style = self.parent.plot_style

        # compute distance
        distance = self.calculate_distance(p1, p2)

        # Update distance label in widget 
        distance_text = f"{distance:.4g} {self.parent.app_data.preferences['Units']['Distance']}"
        self.ui.labelSVInfoDistance.setText(f"D: {distance_text}")

        # Update distance label on map
        if self.map_flag:
            xrange = self.parent.app_data.data[self.parent.app_data.sample_id].x.nunique()*self.parent.app_data.data[self.parent.app_data.sample_id].aspect_ratio
            yrange = self.parent.app_data.data[self.parent.app_data.sample_id].y.nunique()

            xl = self.axes.get_xlim()
            xrange = xl[1] - xl[0]
            yl = self.axes.get_ylim()
            xrange = yl[1] - yl[0]

        # x-shift for text
        dx = 0.03*xrange
        if p2[0] > p1[0]:
            halign = 'left'
        else:
            dx = -dx
            halign = 'right'

        # y-shift for text
        dy = 0.03*yrange
        if p2[1] > p1[1]:
            valign = 'bottom'
        else:
            dy = -dy
            valign = 'top'

        # text on plot
        font = {'family':style.font, 'size':style.font_size-2}
        t = self.axes.text(p2[0]+dx, p2[1]+dy, distance_text, ha=halign, va=valign, fontdict=font, c=style.overlay_color)

        return t

    def on_click(self, event):
        """Handle left/right clicks for distance calculation, polygons and profiles."""
        if event.inaxes != self.axes:
            return
        self.setCursor(Qt.CursorShape.CrossCursor)
        if self.ui.toolButtonDistance.isChecked():
            self.distanceOnClick(event)
            return
        
        # Polygon creation or moving
        if self.is_creating_polygon or self.is_moving_polygon:
            self.polygon_manager.handle_polygon_click(self,event, self.axes)
            self.draw()  # refresh the plot
            return 
        
        # Profile creation or moving
        if self.is_creating_profile or self.is_moving_profile:
            self.profiling.handle_profile_click(self, event, self.axes)
            self.draw()
            return


    def distanceOnClick(self, event):
        """Updates static endpoints of distance measuring line.

        Updates the endpoint of the distance measuring line and calls methods that 
        update the line and text.  Updates ``MplCanvas.first_point`` if it is the start of the line
        and ``MplCanvas.line_saved`` and ``MplCanvas.dtext_saved`` if it is the end of the line.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """        
        
        if event.inaxes:
            if self.first_point is None:
                # First click
                self.first_point = (event.xdata, event.ydata)
                self.ui.labelSVInfoDistance.setText(f"D: 0 {self.parent.app_data.preferences['Units']['Distance']}")
            else:
                # Second click
                second_point = (event.xdata, event.ydata)

                self.saved_line.append(self.plot_line(self.first_point, second_point))
                self.saved_dtext.append(self.plot_text(self.first_point, second_point))
                
                self.distance_reset()

        self.draw()

    def on_mouse_move(self, event):
        """Optional: handle dynamic feedback (e.g., while moving a polygon vertex)."""
        if event.inaxes != self.axes:
            return

        self.setCursor(Qt.CursorShape.CrossCursor)
        if (self.ui.toolButtonDistance.isChecked()) and (self.first_point is not None) and event.inaxes:
            self.distanceOnMove(event)
            return
        
        # If in polygon creation mode, we can show dynamic lines
        if (hasattr(self.ui, "mask_dock")):
            if self.ui.mask_dock.polygon_tab.polygon_toggle.isChecked(): #check if polygon toggle is on
                self.polygon_manager.handle_polygon_mouse_move(event, self.axes)
                self.draw()
                return

        # If in profile creation mode, we can show dynamic lines or interpolation
        if (hasattr(self.ui, "profile_dock")):
            if self.ui.profile_dock.profile_toggle.isChecked():
                self.profiling.handle_profile_mouse_move(event, self.axes)
                self.draw()
                return

    def distanceOnMove(self, event):
        """Updates dynamic second point of distance measuring line.

        Updates the second endpoint of the distance measuring line and calls methods that 
        update the line and text.  Updates ``MplCanvas.line`` and ``MplCanvas.dtext``.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """        
        
        if self.line:
            self.line.remove()
        if self.dtext:
            self.dtext.remove()

        second_point = (event.xdata,event.ydata)
        if self.first_point:
            self.line = self.plot_line(self.first_point, second_point)
            self.dtext = self.plot_text(self.first_point, second_point)

            self.draw()

    def distance_reset(self):
        """Resets distance variables and clears plot

        Sets ``MplCanvas.first_point`` to ``None``, ``MplCanvas.line`` and ``MplCanvas.dtext``.
        If ``MainWindow.toolButtonDistance`` is not checked, then ``MainWindow.labelSVInfoDistance`` is 
        also reset.
        """        
        self.first_point = None
        if self.line:
            self.line.remove()
            self.line = None
        if self.dtext:
            self.dtext.remove()
            self.dtext = None
        self.draw()
        if not self.ui.toolButtonDistance.isChecked():
            self.ui.labelSVInfoDistance.setText("D: N/A")


class MplDialog(QDialog):
    def __init__(self, parent, canvas, title=''):
        """A plot dialog

        This dialog is used to plot a matplotlib figure.  In general the dialog is used when a figure popped out from ``MainWindow.canvasWindow`` using ``MainWindow.toolButtonPopFigure``.

        Parameters
        ----------
        parent : MainWindow
            Calling class.
        canvas : MplCanvas
            Matplotlib plot canvas.
        title : str, optional
            Dialog title, by default ''
        """        
        super(MplDialog, self).__init__(parent)

        self.parent = parent

        self.setWindowTitle(title)

        # Create a QVBoxLayout to hold the canvas and toolbar
        layout = QVBoxLayout(self)

        # Create a NavigationToolbar and add it to the layout
        self.toolbar = NavigationToolbar(canvas, self)

        # use custom buttons
        unwanted_buttons = ["Back", "Forward", "Customize", "Subplots"]

        icons_buttons = {
            "Home": QtGui.QIcon("resources/icons/icon-home-64.svg"),
            "Pan": QtGui.QIcon("resources/icons/icon-move-64.svg"),
            "Zoom": QtGui.QIcon("resources/icons/icon-zoom-64.svg"),
            "Save": QtGui.QIcon("resources/icons/icon-save-file-64.svg")
        }
        for action in self.toolbar.actions():
            if action.text() in unwanted_buttons:
                self.toolbar.removeAction(action)
            if action.text() in icons_buttons:
                action.setIcon(icons_buttons.get(action.text(), QtGui.QIcon()))

        self.toolbar.setMaximumHeight(int(32))
        self.toolbar.setIconSize(QSize(24,24))

        # Add toolbar to self.layout
        layout.addWidget(self.toolbar,0)

        # Add a matplotlib canvas to self.layout
        layout.addWidget(canvas,1)

        # Create a button box for OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box,2)

        self.parent.clear_layout(self.parent.widgetSingleView.layout())


