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
from matplotlib.backends.backend_qt import NavigationToolbar2QT as _NavigationToolbar2QT
from matplotlib.backend_bases import MouseButton
import matplotlib as mpl
from lame_core.config import ICONPATH
from src.control.Logger import log


class NavigationToolbar(_NavigationToolbar2QT):
    """``NavigationToolbar2QT`` with one addition: holding Control while
    clicking the zoom tool acts like a right-click (zoom OUT) instead of a
    left-click (zoom IN) -- convenient wherever a right-click gesture isn't
    always at hand (e.g. a one-button mouse/trackpad on macOS).

    Matplotlib's Qt backend already compensates for macOS's Control/Command
    modifier swap at the ``SPECIAL_KEYS`` level (see
    ``matplotlib.backends.backend_qt``), so ``event.modifiers`` reporting
    ``"ctrl"`` here always means the physical Control key, on every
    platform including macOS -- no platform-specific branching needed.
    If a platform/trackpad configuration already delivers Ctrl+click as an
    actual right-click (``event.button`` is already ``MouseButton.RIGHT``),
    this is a no-op -- it only steps in for the common case of Ctrl+click
    arriving as a left click with the Control modifier held.
    """

    def press_zoom(self, event):
        super().press_zoom(event)
        if (self._zoom_info is not None and self._zoom_info.button == MouseButton.LEFT
                and "ctrl" in event.modifiers):
            self._zoom_info = self._zoom_info._replace(button=MouseButton.RIGHT)


def make_compact_nav_toolbar(canvas, parent=None) -> NavigationToolbar:
    """Compact matplotlib navigation toolbar (home/pan/zoom/save only),
    re-iconed with LaME's icon set.

    Shared by ``CanvasWidget.PlotWindow`` and any other lightweight canvas
    that wants the same minimal toolbar without ``CanvasWidget``'s app-level
    coupling (``current_canvas``, ``ui.io.save_plot``, etc.) -- just a plain
    ``NavigationToolbar2QT`` bound to whatever ``canvas`` is passed in.

    Parameters
    ----------
    canvas : FigureCanvasQTAgg
        Any matplotlib Qt canvas (``SimpleMplCanvas``, ``MplCanvas``, or a
        bare ``FigureCanvasQTAgg``).
    parent : QWidget, optional
        Toolbar's Qt parent.

    Returns
    -------
    NavigationToolbar2QT
    """
    toolbar = NavigationToolbar(canvas, parent)

    unwanted_actions = {"Back", "Forward", "Customize", "Subplots"}
    icons_by_action = {
        "Home": QIcon(str(ICONPATH / "icon-home-64.svg")),
        "Pan": QIcon(str(ICONPATH / "icon-move-64.svg")),
        "Zoom": QIcon(str(ICONPATH / "icon-zoom-64.svg")),
        "Save": QIcon(str(ICONPATH / "icon-save-file-64.svg")),
    }
    for action in toolbar.actions():
        if action.text() in unwanted_actions:
            toolbar.removeAction(action)
        elif action.text() in icons_by_action:
            action.setIcon(icons_by_action[action.text()])

    toolbar.setMaximumHeight(32)
    toolbar.setIconSize(QSize(24, 24))
    return toolbar


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

    def __init__(self, fig=None, sub=111, parent=None, width=5, height=4, proj=None, ui=None, map_flag=False, sample_obj=None, plot_key=None):
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

        # An embedded FigureCanvasQTAgg defaults to Qt.FocusPolicy.NoFocus
        # (only pyplot's own FigureManagerQT sets this), so matplotlib
        # 'key_press_event's never fire and every keyboard shortcut bound to
        # the canvas is dead -- e.g. the polygon tool's z/Escape/Delete.
        # StrongFocus gives the canvas focus on click, which is when those
        # shortcuts are meant to apply.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if parent is None:
            return
        self.ui = parent
        
        # Registry integration (for persistence across canvas recreation)
        # A canvas drawn in the sample's stage coordinates is given the
        # sample, and that is what makes it carry the map-annotation layer
        # (see `_load_annotations`). Plots with their own axes --
        # scatter, histogram, ternary diagram -- are not given one, because
        # an annotation placed at a concentration pair means nothing on a
        # map and vice versa.
        # A canvas drawn in stage coordinates is given `sample_obj` alone
        # and carries the shared map layer. A plot with its own axes is
        # given `sample_obj` *and* a `plot_key`, and keeps its annotations
        # in that plot's own list -- they cannot be shared, since a point
        # placed at a pair of concentrations has no position anywhere else.
        self.sample_obj = sample_obj
        self.plot_key = plot_key
        self._annotation_slot = None
        #: Fingerprint of the records last drawn, so a change elsewhere in
        #: the sample does not make this canvas redraw for nothing.
        self._drawn_annotations = None

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
        
        if self.sample_obj is not None:
            self._load_annotations()
            # Redraw when the layer changes anywhere else -- another canvas,
            # or the annotations table in the Info dock.
            self._annotation_slot = self._on_map_annotations_changed
            self.sample_obj.mapAnnotationsChanged.connect(self._annotation_slot)

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
        # A half-finished measurement does not survive the tool being
        # switched off -- otherwise the next click after switching back on
        # is read as the *second* click of the abandoned one, and measures
        # from wherever the user happened to start before. Finished
        # measurements (saved_line/saved_dtext) are kept.
        self._clear_pending_measurement()
        self.draw()

    def _clear_pending_measurement(self):
        """Forget a measurement in progress: its start point and rubber band.

        Leaves completed measurements alone. Does not redraw -- callers that
        need the canvas repainted do it themselves, so a click that goes
        straight on to draw a permanent line does not paint twice.
        """
        self.first_point = None
        for artist in ('line', 'dtext'):
            obj = getattr(self, artist, None)
            if obj is not None:
                try:
                    obj.remove()
                except ValueError:
                    pass
                setattr(self, artist, None)

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
            # lower case, matching the stored records and the checks in
            # `redraw_annotations`/`_draw_annotation`; it used to be 'Text'
            # here and 'line' in the distance path, so the text branch of
            # `redraw_annotations` never matched.
            'Type': 'text',
            'X1': x,
            'Y1': y,
            'Text': txt,
            'Color': overlay_color,
            'Size': font_size,
            'Visible': True,
            'object': annotation_obj,
            'text_object': None,
        }
        self.annotations.append(new)
        # Join the sample's map layer, so this label shows on every map of
        # the sample. On a canvas with its own axes it stays here.
        self._store_map_annotation(new)
        self.annotationsUpdated.emit(self.annotation_records())

    def redraw_annotations(self):
        """Re-draw this canvas's annotations.

        Called before the figure is popped into its own window. It used to
        add a *second* set of artists on top of the ones already on the
        axes, and read fields that no longer exist in this format
        (``'Line Width'``, and ``'Text'`` as a placement dict), so a
        popped-out figure with a distance measurement on it raised.
        Rebuilding from the sample's layer clears the old artists first, so
        it is idempotent; a canvas with no layer behind it already has its
        artists drawn and needs nothing.
        """
        if self.is_annotatable():
            self._load_annotations()
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
 
    def plot_text(self, p1, p2, label=None):
        """Adds distance to plot and updates distance label

        Updates distance in ``MainWindow.labelInfoDistance`` and adds distance
        at the end of the measuring line.

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.
        label : str, optional
            Text to draw instead of the distance computed here. Used when
            redrawing a stored annotation, whose label was measured once on
            the map it was made on; recomputing it would re-derive the same
            number from `dx`/`dy` that this particular figure happens to
            carry, which is not necessarily the same.

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

        if label is None:
            # compute distance
            self.distance = self.calculate_distance(p1, p2)

            units = self.distance_units or ''

            # Update distance label in widget
            distance_text = f"{self.distance:.4g} {units}"
        else:
            distance_text = label

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
                # Second click. The measurement is finished the moment the
                # two endpoints are known, so the state is cleared here --
                # before the bookkeeping below -- rather than at the end.
                # It used to be reset last, and the dict built in between
                # read `self.ui.style.font_size`: `MainWindow` has no
                # `style`, so that resolved to `QWidget.style`, the method,
                # and raised AttributeError. Matplotlib callbacks swallow
                # exceptions into stderr, so the user saw no error -- just a
                # first_point left pointing at the start of the very first
                # measurement, which every later click then measured from.
                # Turning the tool off did not help either; see
                # `disable_distance_mode`.
                first_point = self.first_point
                second_point = (event.xdata, event.ydata)
                self._clear_pending_measurement()

                # Plot permanent line and text
                line_obj = self.plot_line(first_point, second_point)
                text_obj, text_dict = self.plot_text(first_point, second_point)

                # saved_line/saved_dtext are only for a canvas with no
                # annotation layer behind it. On a map, storing the
                # measurement re-draws the layer and these very artists are
                # replaced, so keeping them here would leave the lists full
                # of artists already taken off the axes -- and the code that
                # empties them calls .remove() on each.
                if not self.is_annotatable():
                    if line_obj is not None:
                        self.saved_line.append(line_obj)
                    if text_obj is not None:
                        self.saved_dtext.append(text_obj)

                new = {
                    "Type": "line",
                    'X1': first_point[0],
                    'Y1': first_point[1],
                    'X2': second_point[0],
                    'Y2': second_point[1],
                    'Text': text_dict,
                    'Label': text_obj.get_text() if text_obj is not None else '',
                    'Color': self.ui.style_data.line_color,
                    'Size': self.ui.style_data.font_size,
                    'Width': self.ui.style_data.line_width,
                    'Visible': True,
                    'object': line_obj,
                    'text_object': text_obj
                }
                self.annotations.append(new)
                # A distance is a fact about the sample, not about whichever
                # element was displayed, so it joins the sample's map layer
                # and appears on every map of it.
                self._store_map_annotation(new)
                # `notify_observers` was called here, but MplCanvas does not
                # inherit Observable and nothing registers for "annotations"
                # -- so this raised too, immediately after the font_size line
                # above. The sibling text path (`textOnClick`) emits the Qt
                # signal declared for exactly this, so do the same.
                self.annotationsUpdated.emit(self.annotation_records())
                self.distance = None

        self.draw()

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
        self._clear_pending_measurement()
        self.draw()
        if self.active_tool != 'distance':
            self.distance = None

    # ==========================================
    # MAP ANNOTATION LAYER
    # ==========================================
    # Annotations on a map belong to the sample, not to the plot that
    # happened to be on screen when they were made -- every map of a sample
    # shares the same stage axes, so a label or a measurement is as true of
    # one element map as of the next. They behave like the other per-sample
    # layers (masks, polygons, ROIs): always present, each entry switched
    # off individually in the Info dock's annotations table when a
    # particular figure should not carry it.
    #
    # `self.annotations` is this canvas's working copy: the stored record
    # plus the matplotlib artists drawing it, which belong to this figure
    # alone. `sample_obj.map_annotations` holds the records themselves.

    def is_annotatable(self):
        """Whether annotations made here are stored rather than lost.

        Returns
        -------
        bool
            False only for a canvas with no sample behind it at all.
        """
        # getattr, not plain attribute access: `__init__` returns early for
        # a canvas built with no parent, leaving none of this set.
        return getattr(self, 'sample_obj', None) is not None

    def attach_plot_annotations(self, sample_obj, key):
        """Give a non-map canvas its own annotation list and draw it.

        Called once the plot has finished naming itself (see
        `src.plotting.LamePlot.create_plot`), which is the first point at
        which a stable `plot_key` can be derived. A map canvas is given its
        sample at construction instead, because its layer is shared and has
        to be on the axes before the figure is first shown.

        Parameters
        ----------
        sample_obj : SampleObj
        key : str
            From `src.tree.PlotRegistry.plot_key`.
        """
        if sample_obj is None or not key:
            return
        self.sample_obj = sample_obj
        self.plot_key = key
        self._load_annotations()
        if self._annotation_slot is None:
            self._annotation_slot = self._on_map_annotations_changed
            self.sample_obj.mapAnnotationsChanged.connect(self._annotation_slot)

    def annotation_scope(self):
        """Which bucket this canvas's annotations live in.

        Returns
        -------
        str
            ``'map'`` when they are shared across every map of the sample,
            ``'plot'`` when they belong to this plot alone, or ``'none'``
            when there is nowhere to store them.
        """
        if not self.is_annotatable():
            return 'none'
        return 'plot' if getattr(self, 'plot_key', None) else 'map'

    def annotation_records(self):
        """This canvas's annotations without their matplotlib artists.

        What `annotationsUpdated` carries. The artists belong to this
        figure and cannot be deep-copied or handed to anyone else, so they
        are dropped rather than shipped to listeners.

        Returns
        -------
        list of dict
        """
        return [{k: v for k, v in ann.items()
                 if k not in ('object', 'text_object')}
                for ann in self.annotations]

    def disconnect_sample_signals(self):
        """Stop listening to the sample's annotation layer.

        Drops only this canvas's own slot -- a bare ``disconnect()`` would
        take every other canvas and the annotations table with it.
        """
        if self.sample_obj is not None and self._annotation_slot is not None:
            try:
                self.sample_obj.mapAnnotationsChanged.disconnect(self._annotation_slot)
            except (RuntimeError, TypeError):
                pass
            self._annotation_slot = None

    def _on_map_annotations_changed(self):
        """Re-draw after the stored annotations changed somewhere else.

        One signal covers both buckets, so this fires on every canvas of
        the sample whenever *any* annotation changes -- including map
        canvases when a scatter plot's own annotation is added, and
        canvases that have been replaced in the layout but are still held
        by the plot registry. Redrawing those is wasted work at best; at
        worst a canvas that has been detached has no usable size, and
        matplotlib fails to rasterise the label on it
        ("FT_Render_Glyph ... raster overflow"). Comparing what this
        canvas last drew against what it should be drawing skips all of
        that.
        """
        try:
            if self._annotation_fingerprint() == self._drawn_annotations:
                return
            self._load_annotations()
            self.draw_idle()
        except RuntimeError:
            # Canvas already destroyed by Qt; nothing to redraw.
            pass

    def _annotation_fingerprint(self):
        """What this canvas should currently be drawing, as a comparable."""
        return repr(self.stored_annotations())

    def stored_annotations(self):
        """The records this canvas should be drawing.

        Returns
        -------
        list of dict
        """
        if self.sample_obj is None:
            return []
        if self.annotation_scope() == 'plot':
            return self.sample_obj.get_plot_annotations(self.plot_key)
        return self.sample_obj.get_map_annotations()

    def _load_annotations(self):
        """Rebuild this canvas's annotations from whichever bucket it uses.

        Removes the artists drawn for the previous state first, so this is
        safe to call repeatedly -- it is both the initial draw and the
        refresh after any change.
        """
        if self.sample_obj is None:
            return
        self._drawn_annotations = self._annotation_fingerprint()
        self._remove_annotation_artists()
        self.annotations = []
        for record in self.stored_annotations():
            canvas_ann = self._record_to_canvas(record)
            if canvas_ann is None:
                continue
            self._draw_annotation(canvas_ann)
            self.annotations.append(canvas_ann)

    def _remove_annotation_artists(self):
        """Take this canvas's annotation artists off the axes."""
        for ann in self.annotations:
            for key in ('object', 'text_object'):
                artist = ann.get(key)
                if artist is None:
                    continue
                try:
                    artist.remove()
                except (ValueError, AttributeError):
                    pass
                ann[key] = None

    def _store_map_annotation(self, canvas_ann):
        """Commit a newly drawn annotation to the sample's layer.

        Parameters
        ----------
        canvas_ann : dict
            A canvas-format record, as ``textOnClick``/``distanceOnClick``
            build it. Its ``'annotation_id'`` is filled in on return.

        Returns
        -------
        bool
            Whether it was stored -- False on a canvas with its own axes,
            where the annotation stays local to the figure.
        """
        if not self.is_annotatable():
            return False
        record = self._canvas_to_record(canvas_ann)
        if record is None:
            return False
        if self.annotation_scope() == 'plot':
            stored = self.sample_obj.add_plot_annotation(self.plot_key, record)
        else:
            stored = self.sample_obj.add_map_annotation(record)
        canvas_ann['annotation_id'] = stored['id']
        return True

    def update_stored_annotation(self, annotation_id, updates):
        """Change a stored annotation, whichever bucket it is in.

        The single entry point for the annotations dock, so it does not
        have to know whether this canvas is a map or a plot of its own.

        Returns
        -------
        bool
            Whether a matching annotation was found.
        """
        if not self.is_annotatable():
            return False
        if self.annotation_scope() == 'plot':
            return self.sample_obj.update_plot_annotation(
                self.plot_key, annotation_id, updates)
        return self.sample_obj.update_map_annotation(annotation_id, updates)

    def remove_stored_annotation(self, annotation_id):
        """Delete a stored annotation, whichever bucket it is in.

        Returns
        -------
        bool
            Whether a matching annotation was found.
        """
        if not self.is_annotatable():
            return False
        if self.annotation_scope() == 'plot':
            return self.sample_obj.remove_plot_annotation(
                self.plot_key, annotation_id)
        return self.sample_obj.remove_map_annotation(annotation_id)

    # --- the two record shapes -----------------------------------------

    def _canvas_to_record(self, canvas_ann):
        """Canvas-format annotation -> the sample layer's JSON-ready record.

        Returns
        -------
        dict or None
        """
        try:
            kind = canvas_ann['Type'].lower()
            if kind == 'text':
                return {
                    'type': 'text',
                    'text': canvas_ann['Text'],
                    'position': [[float(canvas_ann['X1']), float(canvas_ann['Y1'])]],
                    'style': {
                        'color': canvas_ann['Color'],
                        'font_size': float(canvas_ann.get('Size', 12)),
                    },
                    'visible': bool(canvas_ann.get('Visible', True)),
                }
            if kind == 'line':
                label = canvas_ann.get('Text', '')
                if isinstance(label, dict):
                    # distanceOnClick puts plot_text's placement dict here;
                    # only the string belongs in the record, since the
                    # offsets are recomputed per figure from its own limits.
                    label = label.get('Text', '')
                return {
                    'type': 'line',
                    'text': label,
                    'position': [[float(canvas_ann['X1']), float(canvas_ann['Y1'])],
                                 [float(canvas_ann['X2']), float(canvas_ann['Y2'])]],
                    'style': {
                        'color': canvas_ann['Color'],
                        'font_size': float(canvas_ann.get('Size', 12)),
                        'line_width': float(canvas_ann.get('Width', 1.0) or 1.0),
                    },
                    'visible': bool(canvas_ann.get('Visible', True)),
                }
        except (KeyError, TypeError, ValueError) as e:
            log(f"Could not store annotation: {e}", prefix="Error")
        return None

    def _record_to_canvas(self, record):
        """The sample layer's record -> this canvas's working format.

        Returns
        -------
        dict or None
        """
        try:
            style = record.get('style', {})
            position = record['position']
            common = {
                'Text': record.get('text', ''),
                'Color': style.get('color', '#1f77b4'),
                'Size': style.get('font_size', 12),
                'Visible': record.get('visible', True),
                'annotation_id': record['id'],
                'object': None,
                'text_object': None,
            }
            if record['type'] == 'text':
                return {**common, 'Type': 'text',
                        'X1': position[0][0], 'Y1': position[0][1]}
            if record['type'] == 'line':
                return {**common, 'Type': 'line',
                        'X1': position[0][0], 'Y1': position[0][1],
                        'X2': position[-1][0], 'Y2': position[-1][1],
                        'Width': style.get('line_width', 1.0)}
        except (KeyError, IndexError, TypeError) as e:
            log(f"Could not read annotation: {e}", prefix="Error")
        return None

    def _draw_annotation(self, canvas_ann):
        """Draw one annotation on these axes, filling in its artists.

        A hidden annotation is still drawn, as an invisible artist, so
        switching it back on in the table costs only a repaint.
        """
        visible = bool(canvas_ann.get('Visible', True))
        try:
            if canvas_ann['Type'] == 'text':
                canvas_ann['object'] = self.axes.text(
                    canvas_ann['X1'], canvas_ann['Y1'], canvas_ann['Text'],
                    color=canvas_ann['Color'], fontsize=canvas_ann['Size'],
                    visible=visible,
                )
            elif canvas_ann['Type'] == 'line':
                p1 = (canvas_ann['X1'], canvas_ann['Y1'])
                p2 = (canvas_ann['X2'], canvas_ann['Y2'])
                line_obj = self.plot_line(p1, p2)
                line_obj.set_visible(visible)
                canvas_ann['object'] = line_obj
                if canvas_ann.get('Text'):
                    # Re-place the label from this figure's own limits
                    # rather than reusing an offset computed on another.
                    text_obj, text_dict = self.plot_text(p1, p2, label=canvas_ann['Text'])
                    if text_obj is not None:
                        text_obj.set_visible(visible)
                        canvas_ann['text_object'] = text_obj
                        canvas_ann['Text Placement'] = text_dict
        except Exception as e:
            log(f"Could not draw annotation: {e}", prefix="Error")

    def set_annotation_visible(self, annotation_id, visible):
        """Show or hide one annotation wherever it is stored."""
        self.update_stored_annotation(annotation_id, {'visible': bool(visible)})

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


