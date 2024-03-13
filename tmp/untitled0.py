#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: shavinkalu
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtGui import QIcon

class CustomPlotToolbar(QToolBar):
    def __init__(self, matplotlib_canvas=None, pyqtgraph_widget=None, parent=None):
        super().__init__(parent)
        
        self.matplotlib_canvas = matplotlib_canvas
        self.pyqtgraph_widget = pyqtgraph_widget

        self.initUI()

    def initUI(self):
        # Add toolbar actions
        self.addAction(QIcon('path/to/zoom_icon.png'), 'Zoom', self.zoom)
        self.addAction(QIcon('path/to/pan_icon.png'), 'Pan', self.pan)
        self.addAction(QIcon('path/to/save_icon.png'), 'Save', self.save)

    def zoom(self):
        if self.matplotlib_canvas:
            # Implement zoom for Matplotlib
            pass
        if self.pyqtgraph_widget:
            # Implement zoom for pyqtgraph
            pass

    def pan(self):
        if self.matplotlib_canvas:
            # Implement pan for Matplotlib
            pass
        if self.pyqtgraph_widget:
            # Implement pan for pyqtgraph
            pass

    def save(self):
        if self.matplotlib_canvas:
            # Implement save for Matplotlib
            pass
        if self.pyqtgraph_widget:
            # Implement save for pyqtgraph
            pass