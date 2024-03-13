import numpy as np
import matplotlib.pyplot as plt

class scalebar:
    def __init__(self, width, units=None, location='southeast', color=[0, 0, 0], ax=None):
        self.units = units
        self.width = width
        self.location = location
        self.color = color

        if ax is None:
            self.ax = plt.gca()
        else:
            self.ax = ax


    def create(self):        
        if self.units is None:
            unitstr = num2str(self.width)
        else:
            unitstr = [num2str(self.width),' ',self.units]

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
        xp = buff*dx + np.array([0, self.width, self.width, 0, 0])
        yp = (buff + np.array([0, 0, height, height, 0]))*dy

        if xl[0] < xl[1]:
            ydir = 'normal'
        else:
            ydir = 'reverse'

        if ydir == 'reverse':
            match location:
                case 'southeast':
                    location = 'northeast'
                case 'southwest':
                    location = 'northwest'
                case 'northeast':
                    location = 'southeast'
                case 'northwest':
                    location = 'soutwest'

        # move to correct postion
        match location:
            case 'southeast':
                xbar = xl[1] - xp
                ybar = yl[0] + yp
                xt = (xbar[0] - xbar[1])/2 + xbar[1]
                yt = ybar[3] + 0.01*dy
                valign = 'bottom'
            case 'southwest':
                xbar = xl[1] + xp
                ybar = yl[1] + yp
                xt = (xbar[1] - xbar[0])/2 + xbar[0]
                yt = ybar[2]+0.01*dy
                valign = 'bottom'
            case 'northeast':
                xbar = xl[1] - xp
                ybar = yl[1] - yp
                xt = (xbar[0] - xbar[1])/2 + xbar[1]
                yt = ybar[2]-0.01*dy
                valign = 'top'
            case 'northwest':
                xbar = xl[0] + xp
                ybar = yl[1] - yp
                yt = ybar[3]-0.01*dy
                xt = (xbar[1] - xbar[0])/2 + xbar[0]
                valign = 'top'

        if ydir == 'right':
            if valign == 'top':
                valign = 'bottom'
            else:
                valign = 'top'


        ax.fill(xbar, ybar, color=color, linestyle='none')
        ax.text(xt, yt, f'{width} {units}', horizontalalignment='center', verticalalignment=valign, color=color, fontweight='bold')