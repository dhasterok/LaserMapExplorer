from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import ( Qt, QRectF, QPointF )
from PyQt6.QtWidgets import ( QGraphicsRectItem )
from PyQt6.QtGui import ( QColor, QPen, QCursor )
import numpy as np

# Cropping
# -------------------------------
class CropTool:
    """Crop maps

    Cropping maps sets the maximum extent of the map for analysis.

    Attributes
    ----------
    overlays: QGraphicsRectItem()
        contains data for the figure overlay showing crop region
    """
    def __init__(self, parent):
        self.parent = parent

        # Initialize overlay rectangles
        self.overlays = []

    def init_crop(self):
        """Sets intial crop region as full map extent."""

        data = self.parent.data[self.parent.sample_id]


        if self.parent.actionCrop.isChecked():
            if data.crop:
                # reset to full view and remove overlays if user unselects crop tool
                self.parent.toolbar_action.reset_to_full_view()
            # Original extent of map
            self.x_range = data.x_range
            self.y_range = data.y_range

            # Central crop rectangle dimensions (half width and height of the plot)
            crop_rect_width = self.x_range / 2
            crop_rect_height =self.y_range / 2

            # Position the crop_rect at the center of the plot
            crop_rect_x = (self.x_range - crop_rect_width) / 2
            crop_rect_y = (self.y_range - crop_rect_height) / 2

            self.crop_rect = ResizableRectItem(parent=self, rect=QRectF(crop_rect_x, crop_rect_y, crop_rect_width, crop_rect_height))
            self.crop_rect.setPen(QPen(QColor(255, 255, 255), 4, Qt.DashLine))
            self.crop_rect.setZValue(1e9)
            
            self.parent.sv_widget.scene().addItem(self.crop_rect)

            for _ in range(4):
                overlay = QGraphicsRectItem()
                overlay.setBrush(QColor(0, 0, 0, 120))  # Semi-transparent dark overlay
                self.crop_rect.setZValue(1e9)
                self.parent.plot.addItem(overlay)
                self.overlays.append(overlay)

            self.update_overlay(self.crop_rect.rect())

            self.parent.actionFullMap.setEnabled(True)
        else:
            # reset to full view and remove overlays if user unselects crop tool
            self.parent.toolbar_action.reset_to_full_view()
            self.parent.actionCrop.setChecked(False)
            self.parent.actionFullMap.setEnabled(False)

    def remove_overlays(self):
        """Removes darkened overlay following completion of crop."""
        if len(self.overlays)> 0: #remove crop rect and overlays
            self.parent.plot.removeItem(self.crop_rect)
            for overlay in self.overlays:
                self.parent.plot.removeItem(overlay)
            self.overlays = []

    def update_overlay(self, rect):
        """Updates the overlay after user moves a boundary.

        Parameters
        ----------
        rect:
        """
        # Adjust the overlay rectangles based on the new crop_rect
        plot_rect = self.parent.plot.viewRect()

        # Top overlay
        self.overlays[0].setRect(QRectF(plot_rect.topLeft(), QPointF(plot_rect.right(), rect.top())))
        # Bottom overlay
        self.overlays[1].setRect(QRectF(QPointF(plot_rect.left(), rect.bottom()), plot_rect.bottomRight()))
        # Left overlay
        self.overlays[2].setRect(QRectF(QPointF(plot_rect.left(), rect.top()), QPointF(rect.left(), rect.bottom())))
        # Right overlay
        self.overlays[3].setRect(QRectF(QPointF(rect.right(), rect.top()), QPointF(plot_rect.right(), rect.bottom())))

    def apply_crop(self):
        """Uses selected crop extent to set viewable area and map region for analysis."""
        if self.crop_rect:
            crop_rect = self.crop_rect.rect()  # self.crop_rect is ResizableRectItem
            self.parent.data[self.parent.sample_id].xlim = [crop_rect.left(), crop_rect.right()]
            self.parent.data[self.parent.sample_id].ylim = [crop_rect.top(), crop_rect.bottom()]
            if len(self.overlays)> 0: #remove crop rect and overlays
                self.parent.plot.removeItem(self.crop_rect)
                for overlay in self.overlays:
                    self.parent.plot.removeItem(overlay)
            #update plot with crop
            self.parent.apply_crop()

# Rectangle for cropping
# -------------------------------
class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, rect=None, parent=None):
        super(ResizableRectItem, self).__init__(rect)

        self.setAcceptHoverEvents(True)
        self.edgeTolerance = 50  # Adjusted for better precision
        self.resizing = False
        self.dragStartPos = None
        self.dragStartRect = None
        self.cursorChangeThreshold = 50  # Distance from corner to change cursor
        self.parent = parent
        self.pos = None

    def hoverMoveEvent(self, event):
        if event is None:
            return

        pos = event.pos()
        rect = self.rect()
        if (abs(pos.x() - rect.left()) < self.edgeTolerance and abs(pos.y() - rect.top()) < self.edgeTolerance) or \
           (abs(pos.x() - rect.right()) < self.edgeTolerance and abs(pos.y() - rect.bottom()) < self.edgeTolerance):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif (abs(pos.x() - rect.left()) < self.edgeTolerance and abs(pos.y() - rect.bottom()) < self.edgeTolerance) or \
           (abs(pos.x() - rect.right()) < self.edgeTolerance and abs(pos.y() - rect.top()) < self.edgeTolerance):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        super(ResizableRectItem, self).hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event is None:
            return

        if self.onEdge(event.pos()):
            self.resizing = True
            self.dragStartPos = event.pos()
            self.dragStartRect = self.rect()
        else:
            super(ResizableRectItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event is None:
            return

        if self.resizing:
            self.resizeRect(event.pos())
        else:
            super(ResizableRectItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super(ResizableRectItem, self).mouseReleaseEvent(event)

    def onEdge(self, pos):
        rect = self.rect()
        if (abs(pos.x() - rect.left()) < self.cursorChangeThreshold and abs(pos.y() - rect.top()) < self.cursorChangeThreshold):
            self.pos = 'TL' # top, left
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BR' # bottom, right
            return True
        elif (abs(pos.x() - rect.left()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BL' # bottom, left
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.top()) < self.cursorChangeThreshold):
            self.pos = 'TR' # top, right
            return True
        return False

    def resizeRect(self, newPos):
        rect = self.dragStartRect.normalized()
        if self.pos:
            if self.pos =='TL' or self.pos =='BL':  # left
                rect.setLeft(newPos.x())
            elif self.pos =='TR' or self.pos =='BR': # right
                rect.setRight(newPos.x())
            if self.pos =='TR' or self.pos =='TL': # top
                rect.setTop(newPos.y())
            elif self.pos =='BR' or self.pos =='BL': # bottom
                rect.setBottom(newPos.y())

        # Ensure the rectangle does not exceed plot boundaries
        rect = self.validateRect(rect)

        self.setRect(rect)
        self.parent.update_overlay(rect)

    def validateRect(self, rect):
        x_range = self.parent.parent.data[self.parent.parent.sample_id].x_range
        y_range = self.parent.parent.data[self.parent.parent.sample_id].y_range

        plot_width, plot_height = x_range, y_range  # Assuming these are the plot dimensions
        if rect.left() < 0:
            rect.setLeft(0)
        if rect.top() < 0:
            rect.setTop(0)
        if rect.right() > plot_width:
            rect.setRight(plot_width)
        if rect.bottom() > plot_height:
            rect.setBottom(plot_height)
        return rect
