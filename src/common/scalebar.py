import numpy as np
import matplotlib.pyplot as plt

class scalebar:
    def __init__(self, width, pixel_width, units=None, location='southeast', orientation='horizontal', color=[0, 0, 0], ax=None):
        """Produces a scalebar on x,y maps

        Produce a scalebar on (x,y) maps, just inside one corner of the map.

        Methods
        -------
        create : Add scalebar to axes

        Parameters
        ----------
        width : float
            Absolute width of the scalebar in *units*
        pixel_width : float
            Pixel dimensions in the *orientation* direction.  Since ``matplotlib.pyplot.imshow`` does not allow for x, y values,
            the pixel_width is important for converting between absolute units and image units.
        units : str, optional
            Units to include on plot e.g., 'mm', by default None
        location : str, optional
            Scalebar location, defined by corner.  Options include ``'northeast'``, ``'northwest'``, ``'southeast'``, and ``'southwest'``, by default ``'southeast'``
        orientation : str, optional
            Scalebar orientation, either ``'horizontal'`` or ``'vertical'``, by default ``'horizontal'``
        color : list, optional
            Color of scalebar in matplotlib color spec., by default [0, 0, 0]
        ax : matplotlib.axes, optional
            Axis to add scalebar onto, by default None

        Raises
        ------
        ValueError
            'Unknown location, choose from [northeast, northwest, southwest, southeast].'
        ValueError
            'Unknown location, choose from [horizontal, vertical].'
        """        
        self.units = units
        self.width = width
        self.pixel_width = pixel_width
        self.location = location
        self.orientation = orientation
        self.color = color

        if self.location not in ['northeast','northwest','southwest','southeast']:
            raise ValueError('Unknown location, choose from [northeast, northwest, southwest, southeast].')
        if self.orientation not in ['horizontal','vertical']:
            raise ValueError('Unknown location, choose from [horizontal, vertical].')

        if ax is None:
            self.ax = plt.gca()
        else:
            self.ax = ax

    def create(self):        
        """_summary_

        _extended_summary_
        """        
        if self.units is None:
            unitstr = f'{self.width}'
        else:
            unitstr = f'{self.width} {self.units}'

        # axes limits
        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()

        # axes ranges
        dx = np.diff(xl)
        dy = np.diff(yl)

        # buffer at edge, 5% of plot
        buff = 0.05

        # height of scalebar, 2% of plot
        height = 0.02

        # absolute width and length
        npixels = self.width/self.pixel_width    # number of pixels wide (decimal value)

        # scalebar coordinates
        if self.orientation == 'horizontal':
            xp = buff*dx + np.array([0, npixels, npixels, 0, 0])
            yp = (buff + np.array([0, 0, height, height, 0]))*dy
        elif self.orientation == 'vertical':
            xp = (buff + np.array([0, 0, height, height, 0]))*dx
            yp = buff*dy + np.array([0, npixels, npixels, 0, 0])

        if xl[0] < xl[1]:
            ydir = 'normal'
        else:
            ydir = 'reverse'

        if ydir == 'reverse':
            match self.location:
                case 'southeast':
                    self.location = 'northeast'
                case 'southwest':
                    self.location = 'southwest'
                case 'northeast':
                    self.location = 'southeast'
                case 'northwest':
                    self.location = 'soutwest'

        # move to correct position
        if self.orientation == 'horizontal':
            match self.location:
                case 'southeast':
                    xbar = xl[1] - xp
                    ybar = yl[0] + yp
                    xt = (xbar[0] - xbar[1])/2 + xbar[1]
                    yt = ybar[3] + 0.01*dy
                    valign = 'bottom'
                case 'southwest':
                    xbar = xl[0] + xp
                    ybar = yl[0] + yp
                    xt = (xbar[1] - xbar[0])/2 + xbar[0]
                    yt = ybar[2] + 0.01*dy
                    valign = 'bottom'
                case 'northeast':
                    xbar = xl[1] - xp
                    ybar = yl[1] - yp
                    xt = (xbar[0] - xbar[1])/2 + xbar[1]
                    yt = ybar[2] - 0.01*dy
                    valign = 'top'
                case 'northwest':
                    xbar = xl[0] + xp
                    ybar = yl[1] - yp
                    yt = ybar[3] - 0.01*dy
                    xt = (xbar[1] - xbar[0])/2 + xbar[0]
                    valign = 'top'

            if ydir == 'right':
                if valign == 'top':
                    valign = 'bottom'
                else:
                    valign = 'top'

        elif self.orientation == 'vertical':
            ym = yp + npixels/2
            match self.location:
                case 'southeast':
                    xbar = xl[1] - xp
                    ybar = yl[0] - ym
                    xt = xbar[3] - 0.01*dx
                    yt = (ybar[0] - ybar[1])/2 + ybar[1]
                    halign = 'right'
                case 'southwest':
                    xbar = xl[0] + xp
                    ybar = yl[0] - ym
                    xt = xbar[2] + 0.01*dx
                    yt = (ybar[1] - ybar[0])/2 + ybar[0]
                    halign = 'left'
                case 'northeast':
                    xbar = xl[1] - xp
                    ybar = yl[1] + ym
                    xt = xbar[2] - 0.01*dx
                    yt = (ybar[0] - ybar[1])/2 + ybar[1]
                    halign = 'right'
                case 'northwest':
                    xbar = xl[0] + xp
                    ybar = yl[1] + ym
                    xt = xbar[3] + 0.01*dx
                    yt = (ybar[1] - ybar[0])/2 + ybar[0]
                    halign = 'left'

        # plot scalebar
        self.ax.fill(xbar, ybar, color=self.color, linestyle='none')
        # add scale label
        if self.orientation == 'horizontal':
            self.ax.text(xt, yt, f'{self.width} {self.units}', horizontalalignment='center', verticalalignment=valign, color=self.color, fontweight='bold')
        else:
            self.ax.text(xt, yt, f'{self.width} {self.units}', horizontalalignment=halign, verticalalignment='center', color=self.color, fontweight='bold', rotation=90)