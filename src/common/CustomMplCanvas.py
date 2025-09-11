import copy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import (
    Qt, pyqtSignal, QSize
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
from src.app.config import ICONPATH

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

        self.ui = parent

    def closeEvent(self, event):
        """Properly cleanup matplotlib resources for SimpleMplCanvas."""
        try:
            # Clear matplotlib objects
            if hasattr(self, 'axes') and self.axes is not None:
                self.axes.clear()
            
            if hasattr(self, 'fig') and self.fig is not None:
                self.fig.clear()
                
        except (RuntimeError, AttributeError):
            # Objects might already be deleted, which is fine
            pass
        
        # Call parent closeEvent if it exists
        try:
            super().closeEvent(event)
        except AttributeError:
            # FigureCanvas might not have closeEvent
            pass


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
    locationChanged = pyqtSignal()  # x, y 
    valueChanged = pyqtSignal()  # value 
    distanceChanged = pyqtSignal()  # distance
    annotationsUpdated = pyqtSignal(list)  # list of annotations

    def __init__(self, fig=None, sub=111, parent=None, width=5, height=4, proj=None, ui=None, map_flag=False, plot_id=None, sample_obj=None):
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

        if parent is None:
            return
        self.ui = parent
        
        # Registry integration (for persistence across canvas recreation)
        self.plot_id = plot_id
        self.sample_obj = sample_obj

        # indicates whether the data are map form (x, y, value) or simply (x, y)
        self.map_flag = map_flag
        
        # Hold the data of the canvas as a pandas DataFrame
        self._data = None
        self._plot_name = None
        # for placing text annotations
        # --------------------
        self.setCursorPosition()

        # restoring initial axes
        # ----------------------
        self.initial_extent = None

        self.active_tool = None

        # data for estimating self.distance and self.value
        # these come from the data and should be provided when the plot is added
        # to the canvas.
        self.array = None
        self.dx = None
        self.dy = None
        self.color_units = ''
        self.distance_units = ''

        # distance measurement
        # --------------------
        # Variables to store points and line
        self._xpos = None
        self._ypos = None
        self._value = None
        self._distance = None

        self.first_point = None
        self.line = None
        self.dtext = None
        self.saved_line = []
        self.saved_dtext = []
        
        # Keep existing annotations list for backward compatibility
        self.annotations = []
        
        self.interaction_mode = None
        self.distance_cid_press = None
        self.distance_cid_move = None

        self.mpl_connect('motion_notify_event', self.mouseLocation)
        
        self.mpl_toolbar = NavigationToolbar(self)
        
        # Load existing annotations from registry if available
        if self.sample_obj and self.plot_id:
            self._load_annotations_from_registry()

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

    @property
    def xpos(self):
        """str : x position of mouse pointer on canvas"""
        return self._xpos

    @xpos.setter
    def xpos(self, value):
        if self._xpos == value:
            return
        self._xpos = value
        self.locationChanged.emit()

    @property
    def ypos(self):
        """str : y position of mouse pointer on canvas"""
        return self._ypos

    @ypos.setter
    def ypos(self, value):
        if self._ypos == value:
            return
        self._ypos = value
        self.locationChanged.emit()

    @property
    def value(self):
        """str : volue at mouse pointer location"""
        return self._value

    @value.setter
    def value(self, value):
        if self._value == value:
            return
        self._value = value
        self.valueChanged.emit()

    @property
    def distance(self):
        """str : when distance tool is active, the distance of the line"""
        return self._distance

    @distance.setter
    def distance(self, value):
        if self._distance == value:
            return
        self._distance = value
        self.distanceChanged.emit()

    def toggle_tool(self, tool, enable=None):
        if tool == 'home':
            self.restore_view()
            return

        # If the tool is already active and being disabled
        if self.active_tool == tool and not enable:
            self.disable_tool(tool)
            self.active_tool = None
            return

        # If switching to a new tool
        if self.active_tool and self.active_tool != tool:
            self.disable_tool(self.active_tool)

        # Enable the new tool
        if enable:
            self.active_tool = tool
            self.enable_tool(tool)
        else:
            self.active_tool = None

    def enable_tool(self, tool):
        match tool:
            case 'pan':
                # Toggle pan mode in Matplotlib
                self.mpl_toolbar.pan()
            case 'zoom':
                # Toggle zoom mode in Matplotlib
                self.mpl_toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            case 'annotate':
                self.setCursorPosition()
                self.setCursor(Qt.CursorShape.CrossCursor)
            case 'distance':
                # Only enable distance mode for map-type plots
                if self.map_flag:
                    self.enable_distance_mode()
                else:
                    # Disable the distance button if it's not a map
                    if hasattr(self.ui, 'canvas_widget') and hasattr(self.ui.canvas_widget, 'toolbar'):
                        self.ui.canvas_widget.toolbar.sv.toolButtonDistance.setChecked(False)
            case 'preference':
                self.mpl_toolbar.edit_parameters()
            case 'axes':
                self.mpl_toolbar.configure_subplots()
    
    def disable_tool(self, tool):
        match tool:
            case 'pan':
                self.mpl_toolbar.pan()  # toggles off
            case 'zoom':
                self.mpl_toolbar.zoom()  # toggles off
            case 'annotate':
                # Disconnect annotation event handler
                if hasattr(self, 'cid') and self.cid is not None:
                    self.mpl_disconnect(self.cid)
                    self.cid = None
                self.unsetCursor()
            case 'distance':
                # Disconnect mouse events or clear state
                self.disable_distance_mode()
            case 'polygon' | 'profile':
                pass
                
    def enable_distance_mode(self):
        if self.active_tool == 'distance':
            # Connect the button and canvas events for distance measurement
            self.distance_cid_press = self.mpl_connect('button_press_event', self.distanceOnClick)
            self.distance_cid_move = self.mpl_connect('motion_notify_event', self.distanceOnMove)

    def disable_distance_mode(self):
        self.mpl_disconnect(self.distance_cid_press)
        self.mpl_disconnect(self.distance_cid_move)
        self.distance_cid_press = None
        self.distance_cid_move = None

    def enterEvent(self, event):
        # Set cursor to cross when the mouse enters the window and a tool is active
        if self.active_tool in ['annotate', 'distance']:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        # Reset cursor to default when the mouse leaves the window
        if self.active_tool in ['annotate', 'distance']:
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
            self.xpos = None
            self.ypos = None
            self.value = None
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
            
            #x = x_i*self.ui.dx
            #y = y_i*self.ui.dy
            # if self.ui.app_data.sample_id in self.ui.app_data.data:
            #     x = x_i*self.ui.app_data.data[self.ui.app_data.sample_id].dx
            #     y = y_i*self.ui.app_data.data[self.ui.app_data.sample_id].dy
            # else:
            #     return
            x = x_i*self.dx
            y = y_i*self.dy
    
        else:
            x = event.xdata
            y = event.ydata

            if self.array is not None:
                x_i = round(x)
                y_i = round(y)

                #label = ''

        if self.array is not None:
            self._value = self.array[y_i][x_i]
            #txt = f"V: {value:.4g}{label}"

        self.xpos = x
        self.ypos = y

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

        Restores the initial extent when ``home`` signal is received.

        :seealso: toggle_tool
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
        if self.active_tool != 'annotate':
            return

        x, y = event.xdata, event.ydata
        # get text
        txt, ok = QInputDialog.getText(self, 'Figure', 'Enter text:')
        if not ok:
            # Restore cursor after dialog cancellation
            if self.active_tool == 'annotate':
                self.setCursor(Qt.CursorShape.CrossCursor)
            return

        # Restore cursor after dialog completion
        if self.active_tool == 'annotate':
            self.setCursor(Qt.CursorShape.CrossCursor)
            
        overlay_color = self.ui.style_data.overlay_color
        font_size = self.ui.style_data.font_size
        annotation_obj = self.axes.text(x, y, txt, color=overlay_color, fontsize=font_size, visible=True)
        self.draw()

        new = {
            'Type': 'Text',
            'X1': x,
            'Y1': y,
            'Text': txt,
            'Color': overlay_color,
            'Size': font_size,
            'Visible': True,
            'object': annotation_obj
        }
        self.annotations.append(new)
        # Store in registry for persistence
        self._store_annotation_in_registry(new)
        self.annotationsUpdated.emit(copy.deepcopy(self.annotations))

    def redraw_annotations(self):
        for ann in self.annotations:
            if not ann.get('Visible', True):
                continue

            if ann['Type'] == "text":
                self.axes.text(ann['X1'], ann['Y1'], ann['Text'],
                            color=ann['Color'], fontsize=ann['Size'])
            elif ann['Type'] == 'line':
                # Ensure line width is valid
                line_width = ann.get('Line Width', 1.0)
                if line_width is None or line_width <= 0:
                    line_width = 1.0
                    
                self.axes.plot([ann['X1'], ann['X2']], [ann['Y1'], ann['Y2']],
                            color=ann['Color'], linewidth=line_width)
                txt = ann['Text']
                self.axes.text(txt['X1'], txt['Y1'], txt['Text'], ha=txt['HAlign'], va=txt['VAlign'], fontdict=txt['FontDict'], c=ann['Color'])

        self.draw_idle()

    def calculate_distance(self,p1,p2):
        """Calculuates distance on a figure

        Parameters
        ----------
        p1 : [float]
            First endpoint
        p2 : [float]
            Second endpoint

        Returns
        -------
        float
            Distance between two given points.
        """
        # Check if points are valid
        if p1 is None or p2 is None or p1[0] is None or p1[1] is None or p2[0] is None or p2[1] is None:
            return 0.0
            
        if self.map_flag and self.dx is not None and self.dy is not None:
            #dx = self.ui.app_data.data[self.ui.app_data.sample_id].dx
            #dy = self.ui.app_data.data[self.ui.app_data.sample_id].dy
            dx = self.dx
            dy = self.dy
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
        #plot_type = self.ui.app_data.plot_info['plot_type']
        overlay_color = self.ui.style_data.overlay_color
        line_width = self.ui.style_data.line_width
        
        # Ensure line width is valid (not None, not 0, not negative)
        if line_width is None or line_width <= 0:
            line_width = 1.0

        # plot line (keep only first returned handle)
        p = self.axes.plot(
            [p1[0], p2[0]],
            [p1[1], p2[1]],
            ':',
            c=overlay_color,
            lw=line_width
        )[0]

        return p
 
    def plot_text(self, p1, p2):
        """Adds distance to plot and updates distance label

        Updates distance in ``MainWindow.labelInfoDistance`` and adds distance
        at the end of the measuring line.

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.

        Returns
        -------
        matplotlib.text
            Handle to text.

        text_dict : dict
            Dictionary needed to reconstruct distance label
        """        
        # Validate coordinates
        if (p1 is None or p2 is None or 
            p1[0] is None or p1[1] is None or 
            p2[0] is None or p2[1] is None):
            return None, {}
            
        style = self.ui.style_data

        # compute distance
        self.distance = self.calculate_distance(p1, p2)

        units = self.distance_units or ''

        # Update distance label in widget 
        distance_text = f"{self.distance:.4g} {units}"

        # Update distance label on map
        if self.map_flag:
            xrange = self.ui.app_data.data[self.ui.app_data.sample_id].x.nunique()*self.ui.app_data.data[self.ui.app_data.sample_id].aspect_ratio
            yrange = self.ui.app_data.data[self.ui.app_data.sample_id].y.nunique()

            xl = self.axes.get_xlim()
            xrange = xl[1] - xl[0]
            yl = self.axes.get_ylim()
            yrange = yl[1] - yl[0]  # Fixed: was using xrange instead of yrange
        else:
            # For non-map plots, use axis limits
            xl = self.axes.get_xlim()
            yl = self.axes.get_ylim()
            xrange = xl[1] - xl[0]
            yrange = yl[1] - yl[0]

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

        text_dict = {'Text': distance_text,
            'X1': p2[0]+dx,
            'Y1': p2[1]+dy,
            'HAlign': halign,
            'VAlign': valign,
            'FontDict': font,
        } 

        return t, text_dict

    def on_click(self, event):
        """Handle left/right clicks for distance calculation, polygons and profiles."""
        if event.inaxes != self.axes:
            return
        if self.active_tool == 'distance':
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
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            if self.first_point is None:
                # First click
                self.first_point = (event.xdata, event.ydata)
                self.distance = 0
            else:
                # Second click
                second_point = (event.xdata, event.ydata)

                # Plot permanent line and text
                line_obj = self.plot_line(self.first_point, second_point)
                text_obj, text_dict = self.plot_text(self.first_point, second_point)

                # Save to your existing lists if needed
                if line_obj is not None:
                    self.saved_line.append(line_obj)
                if text_obj is not None:
                    self.saved_dtext.append(text_obj)

                new = {
                    "Type": "line",
                    'X1': self.first_point[0],
                    'Y1': self.first_point[1],
                    'X2': second_point[0],
                    'Y2': second_point[1],
                    'Text': text_dict,
                    'Label': text_obj.get_text(),
                    'Color': self.ui.style_data.line_color,
                    'Size': self.ui.style.font_size,
                    'Width': self.ui.style_data.line_width,
                    'Visible': True,
                    'object': line_obj,
                    'text_object': text_obj
                }
                self.annotations.append(new)
                # Store in registry for persistence
                self._store_annotation_in_registry(new)
                self.notify_observers("annotations", copy.deepcopy(self.annotations))

                # Reset first_point so next click starts a new line
                self.first_point = None
                if self.line:
                    try:
                        self.line.remove()
                    except ValueError:
                        pass
                    self.line = None
                if self.dtext:
                    try:
                        self.dtext.remove()
                    except ValueError:
                        pass
                    self.dtext = None
                self.distance = None

        self.draw()

    def on_mouse_move(self, event):
        """Optional: handle dynamic feedback (e.g., while moving a polygon vertex)."""
        if event.inaxes != self.axes:
            return
        if (self.active_tool == 'distance') and (self.first_point is not None) and event.inaxes:
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
            try:
                self.line.remove()
            except ValueError:
                # Line not in list, that's ok
                pass
        if self.dtext:
            try:
                self.dtext.remove()
            except ValueError:
                # Text not in list, that's ok
                pass

        second_point = (event.xdata,event.ydata)
        if self.first_point and event.xdata is not None and event.ydata is not None:
            self.line = self.plot_line(self.first_point, second_point)
            dtext, _ = self.plot_text(self.first_point, second_point)
            if dtext is not None:
                self.dtext = dtext

            self.draw()

    def distance_reset(self):
        """Resets distance variables and clears plot

        Sets ``MplCanvas.first_point`` to ``None``, ``MplCanvas.line`` and ``MplCanvas.dtext``.
        If ``MainWindow.toolButtonDistance`` is not checked, then ``MainWindow.labelInfoDistance`` is 
        also reset.
        """        
        self.first_point = None
        if self.line:
            try:
                self.line.remove()
            except ValueError:
                pass
            self.line = None
        if self.dtext:
            try:
                self.dtext.remove()
            except ValueError:
                pass
            self.dtext = None
        self.draw()
        if self.active_tool != 'distance':
            self.distance = None

    # ==========================================
    # REGISTRY INTEGRATION METHODS (HYBRID APPROACH)
    # ==========================================
    
    def _load_annotations_from_registry(self):
        """Load annotations from registry and recreate them in the annotations list."""
        if not self.sample_obj or not self.plot_id:
            return
            
        try:
            registry_annotations = self.sample_obj.get_annotations(self.plot_id)
            
            for reg_ann in registry_annotations:
                # Convert registry format to canvas format
                canvas_ann = self._registry_to_canvas_format(reg_ann)
                if canvas_ann:
                    # Recreate matplotlib object
                    mpl_obj = self._recreate_matplotlib_object(canvas_ann)
                    canvas_ann['object'] = mpl_obj
                    self.annotations.append(canvas_ann)
                    
        except Exception as e:
            print(f"Error loading annotations from registry: {e}")
    
    def _registry_to_canvas_format(self, registry_ann):
        """Convert registry annotation format to canvas annotation format."""
        try:
            if registry_ann['type'] == 'text':
                return {
                    'Type': 'text',
                    'X1': registry_ann['position'][0],
                    'Y1': registry_ann['position'][1],
                    'Text': registry_ann['text'],
                    'Color': registry_ann['style']['color'],
                    'Size': registry_ann['style'].get('font_size', 12),
                    'Visible': registry_ann.get('visible', True),
                    'registry_id': registry_ann['id']  # Keep reference to registry
                }
            elif registry_ann['type'] == 'line':
                positions = registry_ann['position']
                return {
                    'Type': 'line',
                    'X1': positions[0][0],
                    'Y1': positions[0][1], 
                    'X2': positions[-1][0],
                    'Y2': positions[-1][1],
                    'Text': registry_ann.get('text', ''),
                    'Color': registry_ann['style']['color'],
                    'Width': registry_ann['style'].get('line_width', 2),
                    'Visible': registry_ann.get('visible', True),
                    'registry_id': registry_ann['id'],
                    'positions': positions  # Store all positions for multi-point lines
                }
        except KeyError as e:
            print(f"Missing key in registry annotation: {e}")
            return None
    
    def _recreate_matplotlib_object(self, canvas_ann):
        """Recreate matplotlib object from canvas annotation."""
        try:
            if canvas_ann['Type'] == 'text':
                return self.axes.text(
                    canvas_ann['X1'], canvas_ann['Y1'], canvas_ann['Text'],
                    color=canvas_ann['Color'],
                    fontsize=canvas_ann['Size'],
                    visible=canvas_ann['Visible']
                )
            elif canvas_ann['Type'] == 'line':
                if 'positions' in canvas_ann:
                    # Multi-point line
                    positions = canvas_ann['positions']
                    x_coords, y_coords = zip(*positions)
                else:
                    # Simple two-point line
                    x_coords = [canvas_ann['X1'], canvas_ann['X2']]
                    y_coords = [canvas_ann['Y1'], canvas_ann['Y2']]
                
                line_obj = self.axes.plot(
                    x_coords, y_coords,
                    color=canvas_ann['Color'],
                    linewidth=canvas_ann.get('Width', 2),
                    visible=canvas_ann['Visible']
                )[0]
                
                # Add text if present
                if canvas_ann.get('Text'):
                    mid_x = sum(x_coords) / len(x_coords)
                    mid_y = sum(y_coords) / len(y_coords)
                    text_obj = self.axes.text(
                        mid_x, mid_y, canvas_ann['Text'],
                        color=canvas_ann['Color'],
                        fontsize=canvas_ann.get('Size', 12),
                        ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                        visible=canvas_ann['Visible']
                    )
                    return [line_obj, text_obj]  # Return both objects
                
                return line_obj
                
        except Exception as e:
            print(f"Error recreating matplotlib object: {e}")
            return None
    
    def _store_annotation_in_registry(self, canvas_annotation):
        """Store a canvas annotation in the registry for persistence."""
        if not self.sample_obj or not self.plot_id:
            return
            
        try:
            # Convert canvas format to registry format
            registry_ann = self._canvas_to_registry_format(canvas_annotation)
            if registry_ann:
                self.sample_obj.add_annotation(self.plot_id, registry_ann)
                # Store registry ID back in canvas annotation for updates
                canvas_annotation['registry_id'] = registry_ann.get('id')
                
        except Exception as e:
            print(f"Error storing annotation in registry: {e}")
    
    def _canvas_to_registry_format(self, canvas_ann):
        """Convert canvas annotation format to registry format."""
        try:
            if canvas_ann['Type'].lower() == 'text':
                return {
                    'type': 'text',
                    'text': canvas_ann['Text'],
                    'position': (canvas_ann['X1'], canvas_ann['Y1']),
                    'style': {
                        'color': canvas_ann['Color'],
                        'font_size': canvas_ann.get('Size', 12),
                        'font_family': 'Arial'  # Default
                    },
                    'visible': canvas_ann.get('Visible', True)
                }
            elif canvas_ann['Type'].lower() == 'line':
                if 'positions' in canvas_ann:
                    positions = canvas_ann['positions']
                else:
                    positions = [(canvas_ann['X1'], canvas_ann['Y1']), 
                               (canvas_ann['X2'], canvas_ann['Y2'])]
                
                return {
                    'type': 'line',
                    'text': canvas_ann.get('Text', ''),
                    'position': positions,
                    'style': {
                        'color': canvas_ann['Color'],
                        'line_width': canvas_ann.get('Width', 2)
                    },
                    'visible': canvas_ann.get('Visible', True)
                }
        except KeyError as e:
            print(f"Missing key in canvas annotation: {e}")
            return None

    def closeEvent(self, event):
        """Properly cleanup matplotlib resources to avoid 'wrapped C/C++ object deleted' errors."""
        try:
            # Disconnect any matplotlib event connections
            if hasattr(self, 'distance_cid_press') and self.distance_cid_press is not None:
                self.mpl_disconnect(self.distance_cid_press)
                self.distance_cid_press = None
                
            if hasattr(self, 'distance_cid_move') and self.distance_cid_move is not None:
                self.mpl_disconnect(self.distance_cid_move)
                self.distance_cid_move = None
            
            # Clean up toolbar
            if hasattr(self, 'mpl_toolbar') and self.mpl_toolbar is not None:
                try:
                    self.mpl_toolbar.close()
                    self.mpl_toolbar.deleteLater()
                    self.mpl_toolbar = None
                except RuntimeError:
                    pass  # Already deleted
            
            # Clear annotations to prevent issues
            if hasattr(self, 'annotations'):
                self.annotations.clear()
            
            # Clear matplotlib objects
            if hasattr(self, 'axes') and self.axes is not None:
                self.axes.clear()
            
            if hasattr(self, 'fig') and self.fig is not None:
                self.fig.clear()
                
        except (RuntimeError, AttributeError) as e:
            # Objects might already be deleted, which is fine
            pass
        
        # Call parent closeEvent if it exists
        try:
            super().closeEvent(event)
        except AttributeError:
            # FigureCanvas might not have closeEvent
            pass


