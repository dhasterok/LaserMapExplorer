#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  1 11:57:27 2023

@author: a1904121
"""

#!/usr/bin/env python

from PyQt5.QtCore import *
from PyQt5.QtWidgets import QHeaderView

class RotatedHeaderView(QHeaderView):
    """Rotates the column header of a table by 90 degrees

    Parameters
    ----------
    parent : obj, optional
        Parent table object
    """    
    def __init__(self, parent=None):
        super(RotatedHeaderView, self).__init__(Qt.Horizontal, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex ):
        painter.save()
        # translate the painter to the appropriate position
        painter.translate(rect.x(), rect.y() + rect.height())
        painter.rotate(-90)  # rotate by -90 degrees
        # and have parent code paint at this location
        newrect = QRect(0,0,rect.height(),rect.width())
        super(RotatedHeaderView, self).paintSection(painter, newrect, logicalIndex)
        painter.restore()

    def minimumSizeHint(self):
        size = super(RotatedHeaderView, self).minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        size = super(RotatedHeaderView, self).sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size