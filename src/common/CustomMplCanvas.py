from PyQt5 import QtGui
from PyQt5.QtCore import (
    Qt, QSize
)
from PyQt5.QtWidgets import (
    QVBoxLayout, QDialog, QInputDialog, QDialogButtonBox
)
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar


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
    def __init__(self,fig=None, sub=111, parent=None, width=5, height=4, proj=None):
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

        self.parent = parent

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
        if self.parent is not None:
            if self.parent.comboBoxPlotType.currentText() in self.parent.style.map_plot_types:
                self.map_flag = True
            else:
                self.map_flag = False

            # Connect the button and canvas events
            self.mpl_connect('button_press_event', self.distanceOnClick)
            self.mpl_connect('motion_notify_event', self.distanceOnMove)
            self.mpl_connect('motion_notify_event', self.mouseLocation)

    def enterEvent(self, event):
        # Set cursor to cross when the mouse enters the window
        self.setCursor(Qt.CrossCursor)

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
                x_i = self.array.shape[1]
            
            y_i = round(event.ydata)
            if y_i < 0:
                y_i = 0
            elif y_i > self.array.shape[0]-1:
                y_i = self.array.shape[0]
            
            #x = x_i*self.parent.dx
            #y = y_i*self.parent.dy
            x = x_i*self.parent.data[self.parent.sample_id].dx
            y = y_i*self.parent.data[self.parent.sample_id].dy

            label =  f" {self.parent.preferences['Units']['Concentration']}"
        else:
            x = event.xdata
            y = event.ydata
            self.parent.labelSVInfoValue.setText(f"V: N/A")

            if self.array is not None:
                x_i = round(x)
                y_i = round(y)

                label = ''
        

        if self.array is not None:
            value = self.array[y_i][x_i]
            txt = f"V: {value:.4g}{label}"
            self.parent.labelSVInfoValue.setText(txt)

        txt = f'X: {x:.4g}'
        self.parent.labelSVInfoX.setText(txt)
        txt = f'Y: {y:.4g}'
        self.parent.labelSVInfoY.setText(txt)

    def set_initial_extent(self):
        """Initial extent of the plot

        Sets the initital extent of the plot.
        """
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        self.initial_extent = [xlim[0], xlim[1], ylim[0], ylim[1]]
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
        if (self.parent.canvasWindow.currentIndex() != self.parent.canvas_tab['sv']) or (not self.parent.toolButtonAnnotate.isChecked()):
            return

        x,y = event.xdata, event.ydata
        # get text
        txt, ok = QInputDialog.getText(self, 'Figure', 'Enter text:')
        if not ok:
            return

        style = self.parent.styles[self.parent.comboBoxPlotType.currentText()]
        self.axes.text(x,y,txt, color=style['Scale']['OverlayColor'], fontsize=style['Text']['FontSize'])
        self.draw()

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
            dx = self.parent.data[self.parent.sample_id].dx
            dy = self.parent.data[self.parent.sample_id].dy
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
        plot_type = self.parent.plot_info['plot_type']
        style = self.parent.styles[plot_type]

        # plot line (keep only first returned handle)
        p = self.axes.plot([p1[0], p2[0]], [p1[1], p2[1]],
                ':', c=style['Scale']['OverlayColor'], lw=style['Lines']['LineWidth']
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
        plot_type = self.parent.plot_info['plot_type']
        style = self.parent.styles[plot_type]

        # compute distance
        distance = self.calculate_distance(p1, p2)

        # Update distance label in widget 
        distance_text = f"{distance:.4g} {self.parent.preferences['Units']['Distance']}"
        self.parent.labelSVInfoDistance.setText(f"D: {distance_text}")

        # Update distance label on map
        if self.map_flag:
            xrange = self.parent.data[self.parent.sample_id].x.nunique()*self.parent.data[self.parent.sample_id].aspect_ratio
            yrange = self.parent.data[self.parent.sample_id].y.nunique()
        else:
            xl = self.axes.get_xlim
            xrange = xl[1] - xl[0]
            yl = self.axes.get_ylim
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
        font = {'family':style['Text']['Font'], 'size':style['Text']['FontSize']-2}
        t = self.axes.text(p2[0]+dx, p2[1]+dy, distance_text, ha=halign, va=valign, fontdict=font, c=style['Scale']['OverlayColor'])

        return t

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
        self.setCursor(Qt.CrossCursor)
        if self.parent.toolButtonDistance.isChecked():
            if event.inaxes:
                if self.first_point is None:
                    # First click
                    self.first_point = (event.xdata, event.ydata)
                    self.parent.labelSVInfoDistance.setText(f"D: 0 {self.parent.preferences['Units']['Distance']}")
                else:
                    # Second click
                    second_point = (event.xdata, event.ydata)

                    self.saved_line.append(self.plot_line(self.first_point, second_point))
                    self.saved_dtext.append(self.plot_text(self.first_point, second_point))
                    
                    self.distance_reset()

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
        self.setCursor(Qt.CrossCursor)
        if (self.parent.toolButtonDistance.isChecked()) and (self.first_point is not None) and event.inaxes:
            if self.line:
                self.line.remove()
            if self.dtext:
                self.dtext.remove()

            second_point = (event.xdata,event.ydata)
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
        if not self.parent.toolButtonDistance.isChecked():
            self.parent.labelSVInfoDistance.setText("D: N/A")


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


