#!/usr/bin/env python3
"""
Enhanced Custom Colormap Editor Dialog
Features triangular control points with selection, deletion, and insertion
"""

import sys
import csv
from pathlib import Path
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QComboBox, QLabel, QPushButton, QWidget, QFrame, QScrollArea,
    QColorDialog, QFileDialog, QMessageBox, QCheckBox, QSpinBox,
    QSlider, QGroupBox, QSizePolicy, QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QPolygonF,
    QPixmap, QPalette, QMouseEvent, QCursor, QPainterPath, QDrag
)
from PyQt6.QtCore import QMimeData
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.image as mpimg

from src.common.CustomWidgets import CustomAction
from src.app.config import RESOURCE_PATH, ICONPATH

@dataclass
class ColorPoint:
    """Represents a control point in a continuous colormap."""
    position: float  # 0.0 to 1.0
    color: QColor
    
    def to_rgb_tuple(self) -> Tuple[float, float, float]:
        """Convert to matplotlib RGB tuple (0-1 range)."""
        return (self.color.redF(), self.color.greenF(), self.color.blueF())


class DraggableColorButton(QPushButton):
    """A draggable color button for discrete colormap editing."""
    
    def __init__(self, color: QColor, index: int, parent=None):
        super().__init__(parent)
        self.color = color
        self.index = index
        self.is_selected = False
        self.drag_start_position = None
        self.dragging = False
        self.setFixedSize(40, 40)
        self.setAcceptDrops(True)
        self.update_style()
    
    def update_style(self):
        """Update the button style based on selection state."""
        border_width = 3 if self.is_selected else 1
        self.setStyleSheet(f"background-color: {self.color.name()}; border: {border_width}px solid black;")
    
    def set_selected(self, selected: bool):
        """Set the selection state."""
        self.is_selected = selected
        self.update_style()
    
    def set_color(self, color: QColor):
        """Update the color."""
        self.color = color
        self.update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.dragging = False
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # Use a smaller drag distance threshold for easier dragging
        if ((event.pos() - self.drag_start_position).manhattanLength() < 10):
            return
        
        # Mark as dragging to prevent click event
        self.dragging = True
        print(f"Starting drag for button {self.index}")  # Debug print
        
        # Start drag operation
        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setText(str(self.index))
        drag.setMimeData(mimeData)
        
        # Create a simple drag pixmap without composition mode
        pixmap = QPixmap(self.size())
        pixmap.fill(self.color)
        
        # Add a simple border to make it visible during drag
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRect(pixmap.rect().adjusted(1, 1, -1, -1))
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_position)
        
        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction)
        print(f"Drag result: {result}")  # Debug print
    
    def mouseReleaseEvent(self, event):
        # Reset dragging flag after a short delay to allow double-click detection
        QTimer.singleShot(50, lambda: setattr(self, 'dragging', False))
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        # Only process double-click if we're not in the middle of dragging
        if not self.dragging and hasattr(self.parent(), 'change_color'):
            self.parent().change_color(self.index)
        super().mouseDoubleClickEvent(event)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasText():
            source_index = int(event.mimeData().text())
            target_index = self.index
            
            print(f"Drop event: source={source_index}, target={target_index}")  # Debug print
            
            if source_index != target_index:
                # Update indices for all buttons after the move
                parent_widget = self.parent()
                if hasattr(parent_widget, 'handle_color_move'):
                    parent_widget.handle_color_move(source_index, target_index)
                    print("Color move handled")  # Debug print
                else:
                    print("Parent doesn't have handle_color_move method")  # Debug print
            
            event.acceptProposedAction()
        else:
            event.ignore()


class DiscreteColorWidget(QWidget):
    """Widget for editing discrete colormaps with draggable color squares."""
    colorChanged = pyqtSignal()  # General change signal
    selectionChanged = pyqtSignal()  # Selection changed signal
    
    def __init__(self, colors: List[QColor], parent=None):
        super().__init__(parent)
        self.colors = colors.copy()
        self.selected_indices = set()
        self.setup_ui()
    
    def setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(2)
        self.buttons = []
        self.update_buttons()
    
    def update_buttons(self):
        # Clear existing buttons
        for button in self.buttons:
            button.deleteLater()
        self.buttons.clear()
        
        # Create new buttons
        for i, color in enumerate(self.colors):
            button = DraggableColorButton(color, i, self)
            button.clicked.connect(lambda checked, idx=i: self.handle_color_click(idx))
            self.buttons.append(button)
            self.layout.addWidget(button)
        
        # Update selection states
        self.update_selection_display()
        
        # Force layout update
        self.layout.update()
        self.update()
    
    def handle_color_click(self, index: int):
        """Handle color button clicks for selection."""
        if index in self.selected_indices:
            # Already selected - deselect
            self.selected_indices.remove(index)
        else:
            # Not selected - add to selection
            self.selected_indices.add(index)
        
        self.update_selection_display()
        self.selectionChanged.emit()
    
    def change_color(self, index: int):
        """Open color dialog to change a color."""
        if 0 <= index < len(self.colors):
            color = QColorDialog.getColor(self.colors[index], self)
            if color.isValid():
                self.colors[index] = color
                self.buttons[index].set_color(color)
                self.colorChanged.emit()
    
    def update_selection_display(self):
        """Update the visual selection state of all buttons."""
        for i, button in enumerate(self.buttons):
            button.set_selected(i in self.selected_indices)
    
    def handle_color_move(self, source_index: int, target_index: int):
        """Handle drag-and-drop reordering."""
        if source_index == target_index:
            return
        
        print(f"Moving color from index {source_index} to {target_index}")  # Debug print
        
        # Move the color in the list
        color = self.colors.pop(source_index)
        self.colors.insert(target_index, color)
        
        print(f"Colors after move: {[c.name() for c in self.colors]}")  # Debug print
        
        # Update selected indices based on the move
        new_selected = set()
        for idx in self.selected_indices:
            if idx == source_index:
                # The moved item goes to target_index
                new_selected.add(target_index)
            elif source_index < target_index:
                # Moving right: items between source and target shift left
                if source_index < idx <= target_index:
                    new_selected.add(idx - 1)
                else:
                    new_selected.add(idx)
            else:  # source_index > target_index
                # Moving left: items between target and source shift right
                if target_index <= idx < source_index:
                    new_selected.add(idx + 1)
                else:
                    new_selected.add(idx)
        
        self.selected_indices = new_selected
        
        # Rebuild all buttons to reflect new order
        self.update_buttons()
        self.colorChanged.emit()
    
    def add_color(self):
        """Add a new color based on selection."""
        if len(self.selected_indices) == 0:
            # No selection - add at end with same color as rightmost
            new_color = self.colors[-1] if self.colors else QColor(Qt.GlobalColor.white)
            self.colors.append(new_color)
            new_index = len(self.colors) - 1
        elif len(self.selected_indices) == 1:
            # Single selection - add after it with same color
            selected_idx = next(iter(self.selected_indices))
            new_color = self.colors[selected_idx]
            self.colors.insert(selected_idx + 1, new_color)
            new_index = selected_idx + 1
            
            # Update selected indices for items that shifted
            new_selected = set()
            for idx in self.selected_indices:
                if idx > selected_idx:
                    new_selected.add(idx + 1)
                else:
                    new_selected.add(idx)
            self.selected_indices = new_selected
        else:
            # Multiple selections - add between them
            sorted_indices = sorted(self.selected_indices)
            
            # Find the best position (between first two selections)
            insert_pos = sorted_indices[0] + 1
            
            # Calculate interpolated color between the two selected colors
            color1 = self.colors[sorted_indices[0]]
            color2 = self.colors[sorted_indices[1]]
            
            # Simple interpolation
            r = (color1.red() + color2.red()) // 2
            g = (color1.green() + color2.green()) // 2
            b = (color1.blue() + color2.blue()) // 2
            new_color = QColor(r, g, b)
            
            self.colors.insert(insert_pos, new_color)
            new_index = insert_pos
            
            # Update selected indices for items that shifted
            new_selected = set()
            for idx in self.selected_indices:
                if idx >= insert_pos:
                    new_selected.add(idx + 1)
                else:
                    new_selected.add(idx)
            self.selected_indices = new_selected
        
        # Select the new color
        self.selected_indices.add(new_index)
        
        self.update_buttons()
        self.colorChanged.emit()
        self.selectionChanged.emit()
        return True
    
    def delete_selected(self):
        """Delete selected colors."""
        if not self.selected_indices or len(self.colors) <= len(self.selected_indices):
            return False  # Can't delete all colors
        
        # Sort indices in reverse order to delete from end to beginning
        sorted_indices = sorted(self.selected_indices, reverse=True)
        
        for idx in sorted_indices:
            del self.colors[idx]
        
        self.selected_indices.clear()
        self.update_buttons()
        self.colorChanged.emit()
        self.selectionChanged.emit()
        return True
    
    def get_selected_count(self) -> int:
        """Get the number of selected colors."""
        return len(self.selected_indices)
    
    def set_colors(self, colors: List[QColor]):
        """Set new colors and update display."""
        self.colors = colors.copy()
        self.selected_indices.clear()
        self.update_buttons()
    
    def get_colors(self) -> List[QColor]:
        """Get current colors."""
        return self.colors.copy()


class ContinuousColorWidget(QWidget):
    """Widget for editing continuous colormaps with draggable triangular control points."""
    colorChanged = pyqtSignal()
    selectionChanged = pyqtSignal(int)  # Selected point index (-1 for none)
    
    def __init__(self, color_points: List[ColorPoint], parent=None):
        super().__init__(parent)
        self.color_points = sorted(color_points, key=lambda cp: cp.position)
        #self.setMinimumHeight(120)
        self.dragging_point = None
        self.selected_point = -1
        self.setMouseTracking(True)
        
        # Add margins to accommodate triangular handles
        self.margin_left = 15  # Half triangle width + some padding
        self.margin_right = 15
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        # Calculate the colormap area (excluding margins)
        colormap_left = self.margin_left
        colormap_width = rect.width() - self.margin_left - self.margin_right
        colormap_rect = QRectF(colormap_left, 0, colormap_width, 60)
        
        # Draw colormap gradient
        gradient = QLinearGradient(colormap_left, 0, colormap_left + colormap_width, 0)
        for point in self.color_points:
            gradient.setColorAt(point.position, point.color)
        
        painter.fillRect(colormap_rect, QBrush(gradient))
        
        # Draw black border around colormap (1 pixel)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(colormap_rect)
        
        # Draw control points as triangles
        for i, point in enumerate(self.color_points):
            x = colormap_left + point.position * colormap_width
            
            # Draw control point line
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawLine(int(x), 0, int(x), 60)
            
            # Create triangular handle with rounded corners
            self.draw_triangular_handle(painter, x, point.color, i == self.selected_point)
    
    def draw_triangular_handle(self, painter: QPainter, x: float, color: QColor, is_selected: bool):
        """Draw an equilateral triangular handle with convex rounded corners."""
        # Triangle size
        side = 20
        r = 1  # corner radius
        top_y = 65
        # Equilateral triangle height
        h = np.sqrt(3) / 2 * side
        # Vertices (pointing up)
        top = np.array([x, top_y])
        left = np.array([x - side/2, top_y + h])
        right = np.array([x + side/2, top_y + h])
        vertices = [top, right, left]
        path = QPainterPath()
        for i, v in enumerate(vertices):
            v_prev = vertices[(i - 1) % 3]
            v_next = vertices[(i + 1) % 3]
            # Unit vectors along the two edges from vertex v
            u1 = (v_prev - v) / np.linalg.norm(v_prev - v)
            u2 = (v_next - v) / np.linalg.norm(v_next - v)
            # Distance along each edge to arc tangent points
            d = r / np.tan(np.deg2rad(30))  # r / tan(θ/2), θ=60°
            p1 = v + u1 * d
            p2 = v + u2 * d
            # Arc center (external bisector direction)
            bis = (u1 + u2)
            bis /= np.linalg.norm(bis)
            center = v + bis * (r / np.sin(np.deg2rad(30)))  # r/sin(θ/2), θ=60°
            # Add line from previous arc to first tangent
            if i == 0:
                path.moveTo(QPointF(*p1))
            else:
                path.lineTo(QPointF(*p1))
            # Arc rectangle
            rect = QRectF(center[0]-r, center[1]-r, 2*r, 2*r)
            # Angles
            a1 = np.degrees(np.arctan2(p1[1]-center[1], p1[0]-center[0]))
            a2 = np.degrees(np.arctan2(p2[1]-center[1], p2[0]-center[0]))
            sweep = (a2 - a1) % 360
            if sweep > 180:
                sweep -= 360
            path.arcTo(rect, -a1, -sweep)
        path.closeSubpath()
        # Fill
        painter.fillPath(path, QBrush(color))
        # Stroke
        border_width = 3 if is_selected else 1
        painter.setPen(QPen(Qt.GlobalColor.black, border_width))
        painter.drawPath(path)
    
    def get_handle_bounds(self, x: float) -> QRectF:
        """Get the bounding rectangle for a triangular handle."""
        return QRectF(x - 10, 65, 20, 20)  # Adjusted for equilateral triangle
    
    def get_colormap_x(self, position: float) -> float:
        """Convert a position (0-1) to widget x coordinate."""
        colormap_width = self.width() - self.margin_left - self.margin_right
        return self.margin_left + position * colormap_width
    
    def get_position_from_x(self, x: float) -> float:
        """Convert widget x coordinate to position (0-1)."""
        colormap_width = self.width() - self.margin_left - self.margin_right
        pos = (x - self.margin_left) / colormap_width
        return max(0.0, min(1.0, pos))
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on a control point
            clicked_point = -1
            for i, point in enumerate(self.color_points):
                x = self.get_colormap_x(point.position)
                handle_rect = self.get_handle_bounds(x)
                if handle_rect.contains(event.position()):
                    clicked_point = i
                    break
            
            if clicked_point >= 0:
                # Clicked on a control point
                if self.selected_point == clicked_point:
                    # Same point clicked again - deselect it
                    self.selected_point = -1
                    self.selectionChanged.emit(-1)
                    self.update()
                else:
                    # Select this point and prepare for potential drag
                    self.selected_point = clicked_point
                    self.dragging_point = clicked_point  # Allow immediate dragging
                    self.selectionChanged.emit(clicked_point)
                    self.update()
            else:
                # Clicked on colormap background - deselect
                self.selected_point = -1
                self.selectionChanged.emit(-1)
                self.update()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Check if double-clicking on a control point first
        for i, point in enumerate(self.color_points):
            x = self.get_colormap_x(point.position)
            handle_rect = self.get_handle_bounds(x)
            if handle_rect.contains(event.position()):
                self.change_point_color(i)
                return
        
        # Double-clicked on colormap background - add new control point
        if event.position().y() <= 60:  # Only if clicking on the gradient area
            new_pos = self.get_position_from_x(event.position().x())
            new_color = self.get_color_at_position(new_pos)
            new_point = ColorPoint(new_pos, new_color)
            
            self.color_points.append(new_point)
            self.color_points.sort(key=lambda cp: cp.position)
            
            # Select the new point
            self.selected_point = self.color_points.index(new_point)
            self.selectionChanged.emit(self.selected_point)
            
            self.update()
            self.colorChanged.emit()
        
        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging_point is not None:
            # Update position of dragged point
            new_pos = self.get_position_from_x(event.position().x())
            old_point = self.color_points[self.dragging_point]
            old_point.position = new_pos
            
            # Keep points sorted by position and update selection
            self.color_points.sort(key=lambda cp: cp.position)
            self.selected_point = self.color_points.index(old_point)
            
            self.update()
            self.colorChanged.emit()
        else:
            # Update cursor when hovering over control points
            cursor = Qt.CursorShape.ArrowCursor
            for point in self.color_points:
                x = self.get_colormap_x(point.position)
                handle_rect = self.get_handle_bounds(x)
                if handle_rect.contains(event.position()):
                    cursor = Qt.CursorShape.SizeHorCursor
                    break
            self.setCursor(cursor)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging_point = None
        super().mouseReleaseEvent(event)
    
    def get_color_at_position(self, position: float) -> QColor:
        """Calculate the interpolated color at a given position."""
        if not self.color_points:
            return QColor(Qt.GlobalColor.black)
        
        # Find surrounding points
        left_point = None
        right_point = None
        
        for point in self.color_points:
            if point.position <= position:
                left_point = point
            if point.position >= position and right_point is None:
                right_point = point
                break
        
        if left_point is None:
            return self.color_points[0].color
        if right_point is None:
            return self.color_points[-1].color
        if left_point == right_point:
            return left_point.color
        
        # Interpolate between left and right points
        t = (position - left_point.position) / (right_point.position - left_point.position)
        
        r = left_point.color.red() * (1-t) + right_point.color.red() * t
        g = left_point.color.green() * (1-t) + right_point.color.green() * t
        b = left_point.color.blue() * (1-t) + right_point.color.blue() * t
        
        return QColor(int(r), int(g), int(b))
    
    def change_point_color(self, index: int):
        """Open color dialog to change a control point color."""
        if 0 <= index < len(self.color_points):
            color = QColorDialog.getColor(self.color_points[index].color, self)
            if color.isValid():
                self.color_points[index].color = color
                self.update()
                self.colorChanged.emit()
    
    def delete_selected_point(self):
        """Delete the currently selected control point."""
        if self.selected_point >= 0 and len(self.color_points) > 2:  # Keep at least 2 points
            del self.color_points[self.selected_point]
            self.selected_point = -1
            self.selectionChanged.emit(-1)
            self.update()
            self.colorChanged.emit()
            return True
        return False
    
    def add_control_point(self):
        """Add a new control point, redistributing existing points to maintain colormap."""
        if len(self.color_points) < 10:  # Reasonable maximum
            # Find the best position to insert a new point
            best_pos = 0.5
            max_distance = 0
            
            # Find the largest gap between consecutive points
            for i in range(len(self.color_points) - 1):
                distance = self.color_points[i + 1].position - self.color_points[i].position
                if distance > max_distance:
                    max_distance = distance
                    best_pos = (self.color_points[i].position + self.color_points[i + 1].position) / 2
            
            # Add new point at the best position
            new_color = self.get_color_at_position(best_pos)
            new_point = ColorPoint(best_pos, new_color)
            
            self.color_points.append(new_point)
            self.color_points.sort(key=lambda cp: cp.position)
            
            # Select the new point
            self.selected_point = self.color_points.index(new_point)
            self.selectionChanged.emit(self.selected_point)
            
            self.update()
            self.colorChanged.emit()
            return True
        return False
    
    def set_color_points(self, color_points: List[ColorPoint]):
        """Set new color points."""
        self.color_points = sorted(color_points, key=lambda cp: cp.position)
        self.selected_point = -1
        self.selectionChanged.emit(-1)
        self.update()
    
    def get_color_points(self) -> List[ColorPoint]:
        """Get current color points."""
        return self.color_points.copy()
    
    def get_selected_point(self) -> int:
        """Get the index of the selected point (-1 if none)."""
        return self.selected_point


class ColormapPreviewWidget(FigureCanvas):
    """Widget for previewing colormaps with colorblindness simulation."""
    
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 4))
        super().__init__(self.figure)
        self.setParent(parent)
        
        # Create test data - using a simple pattern if image not available
        try:
            # Try to load the image
            self.test_data = mpimg.imread(RESOURCE_PATH / "misc" / "Heart_of_the_Phantom_Galaxy.jpg")
            # If the image is RGB (shape = H, W, 3), convert to grayscale so cmap applies
            if self.test_data.ndim == 3 and self.test_data.shape[2] >= 3:
                self.test_data = np.mean(self.test_data[..., :3], axis=-1)
        except:
            # Fallback to test pattern if image not available
            x = np.linspace(-2, 2, 100)
            y = np.linspace(-2, 2, 100)
            X, Y = np.meshgrid(x, y)
            self.test_data = np.sin(X*Y) * np.exp(-X**2 - Y**2)
        
        self.current_colormap = None
        self.preview_mode = 'normal'
        
    def set_colormap(self, colormap_data, is_discrete: bool = False):
        """Set the colormap to preview."""
        self.current_colormap = colormap_data
        self.is_discrete = is_discrete
        self.update_preview()
    
    def set_preview_mode(self, mode: str):
        """Set the preview mode (normal, grayscale, colorblind types)."""
        self.preview_mode = mode
        self.update_preview()
    
    def update_preview(self):
        """Update the preview display."""
        if self.current_colormap is None:
            return
            
        self.figure.clear()
        
        # Create axis for the visualization
        ax1 = self.figure.add_subplot(1, 1, 1)
        
        # Create colormap from current data
        if hasattr(self.current_colormap, '__iter__') and len(self.current_colormap) > 0:
            if isinstance(self.current_colormap[0], ColorPoint):
                # Continuous colormap
                colors = []
                positions = []
                for cp in sorted(self.current_colormap, key=lambda x: x.position):
                    positions.append(cp.position)
                    colors.append(cp.to_rgb_tuple())
                
                if len(colors) >= 2:
                    cmap = mcolors.LinearSegmentedColormap.from_list('custom', list(zip(positions, colors)))
                else:
                    cmap = 'viridis'  # fallback
            else:
                # Discrete colormap
                rgb_colors = [(c.redF(), c.greenF(), c.blueF()) for c in self.current_colormap]
                cmap = mcolors.ListedColormap(rgb_colors)
        else:
            cmap = 'viridis'  # fallback
        
        # Apply colorblindness simulation if needed
        if self.preview_mode != 'normal':
            cmap = self.simulate_colorblind_view(cmap)
        
        # Create main visualization
        im = ax1.imshow(self.test_data, cmap=cmap, aspect='equal')
        ax1.axis('off')
        
        self.figure.tight_layout()
        self.draw()
    
    def simulate_colorblind_view(self, cmap):
        """Simulate different types of colorblindness on a colormap."""
        
        # Define transformation matrices
        cb_matrices = {
            "deuteranopia": np.array([
                [0.367, 0.861, -0.228],
                [0.280, 0.673,  0.047],
                [-0.012, 0.043, 0.969]
            ]),
            "protanopia": np.array([
                [0.152, 1.053, -0.205],
                [0.114, 0.786,  0.100],
                [-0.003, -0.048, 1.051]
            ]),
            "tritanopia": np.array([
                [1.255, -0.077, -0.178],
                [-0.078, 0.931,  0.148],
                [0.004, 0.691,  0.304]
            ]),
        }

        if self.preview_mode == "grayscale":
            return plt.cm.gray
        
        if self.preview_mode not in cb_matrices:
            return cmap  # fallback

        matrix = cb_matrices[self.preview_mode]

        # Extract colors from colormap
        if isinstance(cmap, mcolors.Colormap):
            colors = cmap(np.linspace(0, 1, 256))[:, :3]  # RGB only
        else:
            return cmap  # fallback
        
        # Apply colorblind transformation
        transformed = np.dot(colors, matrix.T)
        transformed = np.clip(transformed, 0, 1)

        # Build new colormap
        return mcolors.LinearSegmentedColormap.from_list(
            f"{cmap.name}_{self.preview_mode}", transformed
        )


class ColormapEditorDialog(QDialog):
    """Main colormap editor dialog."""
    
    def __init__(self, existing_colormaps: Dict[str, any] = None, parent=None):
        super().__init__(parent)
        self.existing_colormaps = existing_colormaps or {}
        self.current_colormap_data = None
        self.is_discrete = True
        
        self.setWindowTitle("Colormap Editor")
        self.setMinimumSize(600, 250)
        # Allow dynamic resizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setup_ui()
        self.load_default_colormap()
        # Initial resize without preview
        self.resize(800, 250)
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(3,3,3,3)
        
        # Top controls
        toolbar = QToolBar(self)
        toolbar.setContentsMargins(3,3,3,3)
        
        # Colormap selection
        self.colormap_combo = QComboBox(toolbar)
        self.populate_colormap_combo()
        self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)

        self.add_point_action = CustomAction(
            text="Add\nPoint",
            light_icon_unchecked="icon-accept-64.svg",
            parent=toolbar,
        )
        self.add_point_action.triggered.connect(self.add_control_point)
        self.add_point_action.setToolTip("Add control point")

        self.remove_point_action = CustomAction(
            text="Remove\nPoint",
            light_icon_unchecked="icon-reject-64.svg",
            parent=toolbar,
        )
        self.remove_point_action.triggered.connect(self.delete_control_point)
        self.remove_point_action.setEnabled(False)
        self.remove_point_action.setToolTip("Remove control point")

        self.preview_action = CustomAction(
            text="Preview",
            light_icon_checked="icon-show-64.svg",
            light_icon_unchecked="icon-show-hide-64.svg",
            parent=toolbar,
        )
        self.preview_action.setChecked(False)
        self.preview_action.setToolTip("Show/hide preview")
        self.preview_action.triggered.connect(self.toggle_preview)
        
        # Preview mode selection
        self.preview_combo = QComboBox()
        self.preview_combo.addItems(['normal', 'grayscale', 'deuteranopia', 'protanopia', 'tritanopia'])
        self.preview_combo.currentTextChanged.connect(self.on_preview_mode_changed)
        
        # Discrete/Continuous toggle
        self.discrete_checkbox = QCheckBox("Discrete")
        self.discrete_checkbox.setChecked(True)
        self.discrete_checkbox.toggled.connect(self.on_discrete_toggled)

        toolbar.addWidget(QLabel("Colormap:"))
        toolbar.addWidget(self.colormap_combo)
        toolbar.addWidget(self.discrete_checkbox)
        toolbar.addAction(self.add_point_action)
        toolbar.addAction(self.remove_point_action)
        toolbar.addAction(self.preview_action)
        toolbar.addWidget(QLabel("Colorblind Simulation:"))
        toolbar.addWidget(self.preview_combo)
        
        self.main_layout.addWidget(toolbar)
        
        # Colormap display area
        display_group = QGroupBox("Colormap Editor")
        display_group.setMinimumSize(600, 150)
        display_layout = QVBoxLayout(display_group)
        
        # Discrete color editor (default)
        self.discrete_widget = DiscreteColorWidget([
            QColor("#440154"), QColor("#31688e"), QColor("#35b779"), 
            QColor("#fde725"), QColor("#ffffff")
        ])
        self.discrete_widget.colorChanged.connect(self.on_colormap_modified)
        self.discrete_widget.selectionChanged.connect(self.on_discrete_selection_changed)
        display_layout.addWidget(self.discrete_widget)
        
        # Continuous color editor (hidden initially)
        self.continuous_widget = ContinuousColorWidget([
            ColorPoint(0.0, QColor("#440154")),
            ColorPoint(0.25, QColor("#31688e")),
            ColorPoint(0.5, QColor("#35b779")),
            ColorPoint(0.75, QColor("#fde725")),
            ColorPoint(1.0, QColor("#ffffff"))
        ])
        self.continuous_widget.colorChanged.connect(self.on_colormap_modified)
        self.continuous_widget.selectionChanged.connect(self.on_selection_changed)
        self.continuous_widget.hide()
        display_layout.addWidget(self.continuous_widget)
        
        self.main_layout.addWidget(display_group)

        colorblind_group = QGroupBox("Colorblind Simulation")
        colorblind_group.setMinimumSize(600, 150)
        colorblind_layout = QVBoxLayout(colorblind_group)

        #colorblind_layout.addWidget()

        self.main_layout.addWidget(colorblind_group)
        
        # Preview area - initially not added to layout
        self.preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(self.preview_group)
        
        self.preview_widget = ColormapPreviewWidget()
        self.preview_widget.setMinimumHeight(300)  # Set minimum height for preview
        preview_layout.addWidget(self.preview_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # File operations
        load_button = QPushButton("Load CSV")
        load_button.clicked.connect(self.load_csv)
        button_layout.addWidget(load_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_colormap)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        self.main_layout.addLayout(button_layout)
    
    def populate_colormap_combo(self):
        """Populate the colormap selection combo."""
        self.colormap_combo.clear()  # Clear existing items
        
        # Add built-in matplotlib colormaps
        builtin_maps = ['viridis', 'plasma', 'inferno', 'magma', 'Blues', 'Greens', 'Reds']
        self.colormap_combo.addItems(builtin_maps)
        
        # Add separator if there are custom colormaps
        if self.existing_colormaps:
            self.colormap_combo.insertSeparator(self.colormap_combo.count())
            # Add existing custom colormaps
            self.colormap_combo.addItems(list(self.existing_colormaps.keys()))
    
    def load_default_colormap(self):
        """Load a default colormap."""
        # Set up default discrete colormap (viridis-like)
        default_colors = [
            QColor("#440154"), QColor("#31688e"), QColor("#35b779"), 
            QColor("#fde725"), QColor("#ffffff")
        ]
        self.discrete_widget.set_colors(default_colors)
        self.current_colormap_data = default_colors
        self.update_preview()
    
    def on_colormap_changed(self, colormap_name: str):
        """Handle colormap selection change."""
        if not colormap_name or not colormap_name.strip():  # Handle empty or whitespace selection
            return
            
        print(f"Loading colormap: {colormap_name}")  # Debug print
        print(f"Available custom colormaps: {list(self.existing_colormaps.keys())}")  # Debug print
            
        if colormap_name in self.existing_colormaps:
            # Load custom colormap from loaded CSV data
            colors = self.existing_colormaps[colormap_name]
            print(f"Found custom colormap with {len(colors)} colors")  # Debug print
            
            if self.is_discrete:
                # Load as discrete colormap
                self.discrete_widget.set_colors(colors)
                self.current_colormap_data = colors
            else:
                # Convert to continuous color points
                points = []
                for i, color in enumerate(colors):
                    pos = i / (len(colors) - 1) if len(colors) > 1 else 0.0
                    points.append(ColorPoint(pos, color))
                self.continuous_widget.set_color_points(points)
                self.current_colormap_data = points
            
            self.update_preview()
        else:
            # Load matplotlib colormap
            print(f"Loading matplotlib colormap: {colormap_name}")  # Debug print
            try:
                cmap = plt.cm.get_cmap(colormap_name)
                # Convert to discrete colors for simplicity
                colors = []
                for i in range(5):  # Sample 5 colors
                    rgba = cmap(i / 4.0)
                    colors.append(QColor.fromRgbF(rgba[0], rgba[1], rgba[2]))
                
                if self.is_discrete:
                    self.discrete_widget.set_colors(colors)
                    self.current_colormap_data = colors
                else:
                    # Convert to continuous color points
                    points = []
                    for i, color in enumerate(colors):
                        pos = i / (len(colors) - 1) if len(colors) > 1 else 0.0
                        points.append(ColorPoint(pos, color))
                    self.continuous_widget.set_color_points(points)
                    self.current_colormap_data = points
                
                self.update_preview()
            except Exception as e:
                print(f"Error loading matplotlib colormap {colormap_name}: {e}")  # Debug print
                pass  # Handle error gracefully

    def on_preview_mode_changed(self, mode: str):
        """Handle preview mode change."""
        self.preview_widget.set_preview_mode(mode)
    
    def on_discrete_toggled(self, is_discrete: bool):
        """Handle discrete/continuous mode toggle."""
        self.is_discrete = is_discrete
        
        if is_discrete:
            self.continuous_widget.hide()
            self.discrete_widget.show()
            # Update button text for discrete mode
            self.add_point_action.setText("Add\nColor")
            self.remove_point_action.setText("Delete\nColor")
        else:
            self.discrete_widget.hide()
            self.continuous_widget.show()
            # Update button text for continuous mode
            self.add_point_action.setText("Add\nPoint")
            self.remove_point_action.setText("Delete\nPoint")
        
        # Reload current colormap in the new mode
        current_colormap = self.colormap_combo.currentText()
        if current_colormap:
            self.on_colormap_changed(current_colormap)
        
        # Update button states
        self.update_button_states()
    
    def on_colormap_modified(self):
        """Handle colormap modifications."""
        if self.is_discrete:
            self.current_colormap_data = self.discrete_widget.get_colors()
        else:
            self.current_colormap_data = self.continuous_widget.get_color_points()
        
        self.update_preview()
    
    def on_selection_changed(self, selected_index: int):
        """Handle control point selection changes in continuous mode."""
        self.update_button_states()
    
    def on_discrete_selection_changed(self):
        """Handle color selection changes in discrete mode."""
        self.update_button_states()
    
    def update_button_states(self):
        """Update the state of add/delete buttons based on current mode and selection."""
        if self.is_discrete:
            # Discrete mode
            selected_count = self.discrete_widget.get_selected_count()
            total_colors = len(self.discrete_widget.get_colors())
            
            self.add_point_action.setEnabled(True)  # Can always add colors
            # Can delete if something is selected and won't delete all colors
            self.remove_point_action.setEnabled(selected_count > 0 and selected_count < total_colors)
        else:
            # Continuous mode
            selected_index = self.continuous_widget.get_selected_point()
            total_points = len(self.continuous_widget.get_color_points())
            
            self.add_point_action.setEnabled(total_points < 10)  # Reasonable maximum
            # Can delete if something is selected and at least 2 points will remain
            self.remove_point_action.setEnabled(selected_index >= 0 and total_points > 2)
    
    def add_control_point(self):
        """Add a new control point or color."""
        if self.is_discrete:
            if self.discrete_widget.add_color():
                self.on_colormap_modified()
        else:
            if self.continuous_widget.add_control_point():
                self.on_colormap_modified()
    
    def delete_control_point(self):
        """Delete the selected control point or colors."""
        if self.is_discrete:
            if self.discrete_widget.delete_selected():
                self.on_colormap_modified()
        else:
            if self.continuous_widget.delete_selected_point():
                self.on_colormap_modified()
    
    def toggle_preview(self):
        """Toggle preview visibility."""
        if self.preview_action.isChecked():
            # Add preview to layout
            preview_insert_index = self.main_layout.count() - 1  # Before button layout
            self.main_layout.insertWidget(preview_insert_index, self.preview_group)
            self.preview_group.show()
            self.preview_action.setText("Hide\nPreview")
            self.update_preview()
        else:
            # Remove preview from layout and hide
            self.main_layout.removeWidget(self.preview_group)
            self.preview_group.hide()
            self.preview_action.setText("Show\nPreview")
        
        # Let the layout system handle the resizing automatically
        self.adjustSize()
    
    def update_preview(self):
        """Update the preview if visible."""
        if self.preview_action.isChecked() and self.current_colormap_data:
            self.preview_widget.set_colormap(self.current_colormap_data, self.is_discrete)
    
    def load_csv(self):
        """Load all colormaps from CSV file and add them to the combo box."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Colormap CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                loaded_colormaps = {}
                with open(file_path, 'r') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        if len(row) >= 2:  # At least name and one color
                            colormap_name = row[0].strip()
                            colors = []
                            
                            # Parse hex colors from remaining columns
                            for hex_color in row[1:]:
                                hex_color = hex_color.strip()
                                if hex_color:  # Skip empty columns
                                    # Ensure hex color starts with #
                                    if not hex_color.startswith('#'):
                                        hex_color = '#' + hex_color
                                    
                                    # Validate hex color format
                                    if len(hex_color) == 7:  # #rrggbb
                                        try:
                                            color = QColor(hex_color)
                                            if color.isValid():
                                                colors.append(color)
                                        except:
                                            continue  # Skip invalid colors
                            
                            if colors:  # Only add if we have valid colors
                                loaded_colormaps[colormap_name] = colors
                
                if loaded_colormaps:
                    # Add loaded colormaps to existing colormaps
                    self.existing_colormaps.update(loaded_colormaps)
                    print(f"Updated existing_colormaps: {list(self.existing_colormaps.keys())}")  # Debug print
                    
                    # Store current selection to restore if possible
                    current_selection = self.colormap_combo.currentText()
                    
                    # Repopulate the combo box to include new colormaps
                    self.colormap_combo.blockSignals(True)  # Prevent triggering change event
                    self.populate_colormap_combo()
                    self.colormap_combo.blockSignals(False)
                    
                    # Try to restore previous selection, or select first loaded colormap
                    if current_selection and current_selection in [self.colormap_combo.itemText(i) for i in range(self.colormap_combo.count())]:
                        index = self.colormap_combo.findText(current_selection)
                        if index >= 0:
                            self.colormap_combo.setCurrentIndex(index)
                    else:
                        # Select first loaded colormap
                        first_loaded = list(loaded_colormaps.keys())[0]
                        index = self.colormap_combo.findText(first_loaded)
                        if index >= 0:
                            self.colormap_combo.setCurrentIndex(index)
                    
                    # Manually trigger the change event to load the selected colormap
                    self.on_colormap_changed(self.colormap_combo.currentText())
                    
                    QMessageBox.information(self, "Success", 
                                          f"Loaded {len(loaded_colormaps)} colormaps from CSV")
                else:
                    QMessageBox.warning(self, "Warning", "No valid colormaps found in CSV file")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load CSV: {str(e)}")
    
    def save_colormap(self):
        """Save the current colormap to CSV file."""
        if not self.current_colormap_data:
            QMessageBox.warning(self, "Warning", "No colormap data to save")
            return
        
        # Get colormap name from user
        from PyQt6.QtWidgets import QInputDialog
        colormap_name, ok = QInputDialog.getText(
            self, "Save Colormap", "Enter colormap name:"
        )
        
        if not ok or not colormap_name.strip():
            return
        
        colormap_name = colormap_name.strip()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Colormap CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Get colors based on current mode
                if self.is_discrete:
                    colors = self.current_colormap_data
                else:
                    # Extract colors from continuous color points
                    colors = [point.color for point in sorted(self.current_colormap_data, key=lambda x: x.position)]
                
                # Convert colors to hex strings
                hex_colors = [color.name() for color in colors]  # QColor.name() returns hex format
                
                # Check if file exists to determine if we should append or create new
                import os
                file_exists = os.path.exists(file_path)
                existing_data = []
                
                if file_exists:
                    # Read existing data
                    with open(file_path, 'r') as file:
                        reader = csv.reader(file)
                        existing_data = list(reader)
                
                # Check if colormap name already exists
                colormap_found = False
                for i, row in enumerate(existing_data):
                    if len(row) > 0 and row[0].strip() == colormap_name:
                        # Update existing colormap
                        existing_data[i] = [colormap_name] + hex_colors
                        colormap_found = True
                        break
                
                if not colormap_found:
                    # Add new colormap
                    existing_data.append([colormap_name] + hex_colors)
                
                # Write all data back to file
                with open(file_path, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(existing_data)
                
                action = "updated" if colormap_found else "added"
                QMessageBox.information(self, "Success", 
                                      f"Colormap '{colormap_name}' {action} successfully with {len(hex_colors)} colors")
                self.accept()
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save CSV: {str(e)}")
    
    def get_colormap_data(self):
        """Get the current colormap data."""
        return self.current_colormap_data, self.is_discrete


# Example usage and test
def main():
    app = QApplication(sys.argv)
    
    # Sample existing colormaps
    existing_maps = {
        "Custom1": [QColor("#ff0000"), QColor("#00ff00"), QColor("#0000ff")],
        "Custom2": [QColor("#000000"), QColor("#ffffff")]
    }
    
    dialog = ColormapEditorDialog(existing_maps)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        colormap_data, is_discrete = dialog.get_colormap_data()
        print(f"Colormap saved: {len(colormap_data)} {'discrete' if is_discrete else 'continuous'} colors")
        
        if is_discrete:
            for i, color in enumerate(colormap_data):
                print(f"  Color {i}: {color.name()}")
        else:
            for i, point in enumerate(colormap_data):
                print(f"  Point {i}: {point.color.name()} at position {point.position:.3f}")
    
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())