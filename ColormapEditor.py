#!/usr/bin/env python3
"""
Enhanced Custom Colormap Editor Dialog
Features triangular control points with selection, deletion, and insertion
"""

import sys
import csv
from pathlib import Path
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QWidget, QFrame, QScrollArea, QColorDialog, QFileDialog,
    QMessageBox, QLineEdit, QGroupBox, QSizePolicy, QToolBar,
    QWidgetAction, QInputDialog, QMenuBar, QMenu,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPointF, QRectF, QTimer, QSize, QRegularExpression, QObject
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QPolygonF, QPixmap,
    QPalette, QMouseEvent, QCursor, QPainterPath, QDrag, QIcon,
    QRegularExpressionValidator, QAction, QUndoCommand, QUndoStack,
    QKeySequence,
)
from PyQt6.QtCore import QMimeData
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.image as mpimg
import cmcrameri.cm as cmr

from src.common.CustomWidgets import CustomAction, ToggleSwitch
from src.common.ColorSelector import select_color, ColorSelectorDialog
from src.app.config import RESOURCE_PATH, ICONPATH
from src.common.ternary_plot import ternary
from src.common.ColorManager2 import convert_color, convert_color_list
from src.common.ColorPicker import ImageColorPicker

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
    "grayscale": np.array([
        [0.299, 0.587, 0.114],
        [0.299, 0.587, 0.114],
        [0.299, 0.587, 0.114]
    ])
}

# --- Collect colormap names ---
def get_cmr_colormap_names():
    """Return a flat list of all Crameri colormap names."""
    names = []
    for attr in dir(cmr):
        if attr.startswith("_cmap_names"):
            val = getattr(cmr, attr)
            if isinstance(val, (list, tuple)):
                names.extend(val)
    return sorted(set(names))

def fix_positions(model):
    if getattr(model, "is_discrete", False):
        n = len(model.color_points)
        if n > 1:
            for i, cp in enumerate(model.color_points):
                cp.position = i / (n - 1)
        elif n == 1:
            model.color_points[0].position = 0.5  # Single point in middle
    else:
        # For continuous colormaps, ensure positions are valid
        n = len(model.color_points)
        if n == 0:
            return model
        elif n == 1:
            # Single point should be at 0.5 or we need to add boundary points
            model.color_points[0].position = 0.5
        else:
            # Sort points by position first
            model.color_points.sort(key=lambda cp: cp.position)
            
            # Ensure first point is at 0.0 and last point is at 1.0
            if model.color_points[0].position != 0.0:
                model.color_points[0].position = 0.0
            if model.color_points[-1].position != 1.0:
                model.color_points[-1].position = 1.0
                
            # If we have intermediate points, redistribute them proportionally
            if n > 2:
                # Keep the boundary positions fixed, redistribute middle points
                for i in range(1, n - 1):
                    model.color_points[i].position = i / (n - 1)
    
    return model

def fix_positions_after_removal(model, removed_position=None):
    """Fix positions after removing a point - linearly adjust if endpoint was removed."""
    if getattr(model, "is_discrete", False):
        # Discrete colormap logic (unchanged from original)
        n = len(model.color_points)
        if n > 1:
            for i, cp in enumerate(model.color_points):
                cp.position = i / (n - 1)
        elif n == 1:
            model.color_points[0].position = 0.0
    else:
        # Continuous colormap - handle endpoint removal with linear scaling
        if not model.color_points:
            return model
        
        n = len(model.color_points)
        if n == 1:
            # Single point - keep at current position or move to center
            pass
        elif removed_position is not None:
            # Check if an endpoint was removed
            was_start_endpoint = abs(removed_position - 0.0) < 1e-10
            was_end_endpoint = abs(removed_position - 1.0) < 1e-10
            
            if was_start_endpoint or was_end_endpoint:
                # Sort points by position
                model.color_points.sort(key=lambda cp: cp.position)
                
                if was_start_endpoint:
                    # Removed point at 0.0 - scale remaining points to start at 0.0
                    if model.color_points:
                        min_pos = model.color_points[0].position
                        max_pos = model.color_points[-1].position
                        
                        if max_pos > min_pos:  # Avoid division by zero
                            for cp in model.color_points:
                                # Scale from [min_pos, max_pos] to [0.0, max_pos]
                                cp.position = (cp.position - min_pos) / (max_pos - min_pos) * max_pos
                        
                        # Ensure first point is at 0.0
                        model.color_points[0].position = 0.0
                
                elif was_end_endpoint:
                    # Removed point at 1.0 - scale remaining points to end at 1.0
                    if model.color_points:
                        min_pos = model.color_points[0].position
                        max_pos = model.color_points[-1].position
                        
                        if max_pos > min_pos:  # Avoid division by zero
                            for cp in model.color_points:
                                # Scale from [min_pos, max_pos] to [min_pos, 1.0]
                                cp.position = min_pos + (cp.position - min_pos) / (max_pos - min_pos) * (1.0 - min_pos)
                        
                        # Ensure last point is at 1.0
                        model.color_points[-1].position = 1.0
        
    return model

def fix_positions_discrete_only(model):
    """Original fix_positions logic for discrete colormaps only."""
    if getattr(model, "is_discrete", False):
        n = len(model.color_points)
        if n > 1:
            for i, cp in enumerate(model.color_points):
                cp.position = i / (n - 1)
        elif n == 1:
            model.color_points[0].position = 0.0
    return model

@dataclass
class ColorPoint:
    """Represents a control point in a continuous colormap."""
    position: float  # 0.0 to 1.0
    color: QColor
    
    def to_rgb_tuple(self) -> Tuple[float, float, float]:
        """Convert to matplotlib RGB tuple (0-1 range)."""
        return (self.color.redF(), self.color.greenF(), self.color.blueF())

class ColorMapModel(QObject):
    """Shared model that holds color points + undo/redo stack."""
    modelChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color_points: list[ColorPoint] = []
        self.undo_stack = QUndoStack(self)
        self.unsaved = False

        self.is_discrete = False

        self.undo_stack.cleanChanged.connect(self.on_clean_changed)
        self.undo_stack.indexChanged.connect(self.on_index_changed)

    # --- API for both discrete and continuous widgets ---
    def add_point(self, position: float, color: QColor, index: int = None):
        """Add a ColorPoint at a given position (continuous) or index (discrete)."""
        self.undo_stack.push(AddColorPoint(self, position, color, index))

    def remove_point(self, index: int):
        if 0 <= index < len(self.color_points):
            self.undo_stack.push(RemoveColorPoint(self, index))

    def move_point(self, source_index: int, target_index: int):
        if source_index == target_index or not (0 <= source_index < len(self.color_points)) or not (0 <= target_index < len(self.color_points)):
            return
        self.undo_stack.push(MoveColorPoint(self, source_index, target_index))
    
    def space_evenly_points(self):
        self.undo_stack.push(SpaceEvenlyPointsCommand(self))

    def change_color(self, index: int, new_color: QColor):
        if 0 <= index < len(self.color_points):
            self.undo_stack.push(ChangeColor(self, index, new_color))

    def reverse_points(self):
        self.undo_stack.push(ReverseColorPoints(self))

    def set_points(self, points: list[ColorPoint]):
        """Directly set all color points (used for loading colormaps)."""
        self.color_points = list(points)
        self.modelChanged.emit()

    def is_circular_colormap(self):
        if len(self.color_points) < 2:
            return False
        first_color = self.color_points[0].color
        last_color = self.color_points[-1].color
        # Compare RGB values with some tolerance
        return (abs(first_color.red() - last_color.red()) < 10 and
                abs(first_color.green() - last_color.green()) < 10 and
                abs(first_color.blue() - last_color.blue()) < 10)

    def is_ternary_colormap(self):
        return len(self.color_points) in (3, 4)

    def get_colors(self) -> List[QColor]:
        """Get current colors."""
        return [cp.color for cp in self.color_points]

    def to_mpl_colormap(self):
        """Convert to matplotlib colormap, adjusting model positions if needed."""
        if not self.color_points:
            return plt.get_cmap('viridis')
            
        if self.is_discrete:
            # Discrete colormap
            rgb_colors = [cp.to_rgb_tuple() for cp in self.color_points]
            return mcolors.ListedColormap(rgb_colors)
        else:
            # Continuous colormap
            if len(self.color_points) < 1:
                return plt.get_cmap('viridis')
            
            if len(self.color_points) == 1:
                # Single point - create a flat colormap, adjust position to 0.5
                self.color_points[0].position = 0.5
                color = self.color_points[0].to_rgb_tuple()
                return mcolors.LinearSegmentedColormap.from_list(
                    'custom', [(0.0, color), (1.0, color)]
                )
            
            # Sort points by position
            self.color_points.sort(key=lambda cp: cp.position)
            
            # Check and adjust for matplotlib compatibility
            positions_adjusted = False
            
            # Ensure we have a point at 0.0
            if abs(self.color_points[0].position - 0.0) > 1e-10:
                self.color_points[0].position = 0.0
                positions_adjusted = True
            
            # Ensure we have a point at 1.0
            if abs(self.color_points[-1].position - 1.0) > 1e-10:
                self.color_points[-1].position = 1.0
                positions_adjusted = True
            
            # If positions were adjusted, emit signal
            if positions_adjusted:
                self.modelChanged.emit()
            
            # Create position and color arrays
            positions = [cp.position for cp in self.color_points]
            colors = [cp.to_rgb_tuple() for cp in self.color_points]
            
            # Create the colormap
            try:
                return mcolors.LinearSegmentedColormap.from_list(
                    'custom', list(zip(positions, colors))
                )
            except ValueError as e:
                # Fallback if there are still issues
                print(f"Colormap creation failed: {e}")
                print(f"Positions: {positions}")
                # Force valid positions as last resort
                n = len(self.color_points)
                for i, cp in enumerate(self.color_points):
                    cp.position = i / (n - 1) if n > 1 else 0.5
                self.modelChanged.emit()
                
                positions = [cp.position for cp in self.color_points]
                return mcolors.LinearSegmentedColormap.from_list(
                    'custom', list(zip(positions, colors))
                )

    def on_clean_changed(self, clean: bool):
        """Called when the undo stack's clean state changes."""
        # clean=True means saved/undo stack marked clean → unsaved=False
        self.unsaved = not clean

    def on_index_changed(self, index: int):
        """Called when undo/redo changes the stack index."""
        # If we've undone everything back to the clean state
        if self.undo_stack.isClean():
            self.unsaved = False
        else:
            self.unsaved = True


# --- Undo Commands ---
class AddColorPoint(QUndoCommand):
    def __init__(self, model, position, color, index=None):
        super().__init__("Add Point")
        self.model = model
        self.position = position
        self.color = color
        self.index = index  # If None, append at end

    def redo(self):
        cp = ColorPoint(self.position, self.color)
        if self.index is not None and 0 <= self.index <= len(self.model.color_points):
            self.model.color_points.insert(self.index, cp)
        else:
            # Insert in sorted order by position
            points = self.model.color_points
            insert_at = next((i for i, p in enumerate(points) if p.position > self.position), len(points))
            self.model.color_points.insert(insert_at, cp)
            self.index = insert_at
        self.model.modelChanged.emit()

    def undo(self):
        if self.index is None:
            return

        if 0 <= self.index < len(self.model.color_points):
            self.model.color_points.pop(self.index)
            self.model = fix_positions(self.model)
            self.model.modelChanged.emit()

class RemoveColorPoint(QUndoCommand):
    def __init__(self, model, index):
        super().__init__("Remove Point")
        self.model = model
        self.index = index
        self.point = None
        self.original_positions = None  # Store positions before adjustment for undo
    
    def redo(self):
        if 0 <= self.index < len(self.model.color_points):
            self.point = self.model.color_points.pop(self.index)
            
            # Store original positions for undo
            self.original_positions = [cp.position for cp in self.model.color_points]
            
            # Apply position fixes with knowledge of removed point
            self.model = fix_positions_after_removal(self.model, self.point.position)
            self.model.modelChanged.emit()
    
    def undo(self):
        if self.point is not None:
            # Restore original positions first
            if self.original_positions:
                for i, cp in enumerate(self.model.color_points):
                    if i < len(self.original_positions):
                        cp.position = self.original_positions[i]
            
            # Insert the point back
            self.model.color_points.insert(self.index, self.point)
            self.model.modelChanged.emit()

class MoveColorPoint(QUndoCommand):
    def __init__(self, model, source_index, target_index):
        super().__init__("Move Point")
        self.model = model
        self.source_index = source_index
        self.target_index = target_index

    def redo(self):
        points = self.model.color_points
        point = points.pop(self.source_index)
        points.insert(self.target_index, point)
        self.model = fix_positions(self.model)
        self.model.modelChanged.emit()

    def undo(self):
        points = self.model.color_points
        point = points.pop(self.target_index)
        points.insert(self.source_index, point)
        self.model = fix_positions(self.model)
        self.model.modelChanged.emit()

class MoveContinuousPointCommand(QUndoCommand):
    def __init__(self, model, index, old_pos, new_pos):
        super().__init__("Move Point")
        self.model = model
        self.index = index
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):
        self.model.color_points[self.index].position = self.new_pos
        self.model.color_points.sort(key=lambda cp: cp.position)
        self.model.modelChanged.emit()

    def undo(self):
        self.model.color_points[self.index].position = self.old_pos
        self.model.color_points.sort(key=lambda cp: cp.position)
        self.model.modelChanged.emit()

class SpaceEvenlyPointsCommand(QUndoCommand):
    def __init__(self, model):
        super().__init__("Space Evenly")
        self.model = model
        self.old_positions = [cp.position for cp in model.color_points]

    def redo(self):
        n = len(self.model.color_points)
        if n < 2:
            return
        for i, cp in enumerate(self.model.color_points):
            cp.position = i / (n - 1)
        self.model.color_points.sort(key=lambda cp: cp.position)
        self.model.modelChanged.emit()

    def undo(self):
        for cp, pos in zip(self.model.color_points, self.old_positions):
            cp.position = pos
        self.model.color_points.sort(key=lambda cp: cp.position)
        self.model.modelChanged.emit()

class ChangeColor(QUndoCommand):
    def __init__(self, model, index, new_color):
        super().__init__("Change Color")
        self.model = model
        self.index = index
        self.old_color = model.color_points[index].color
        self.new_color = new_color

    def redo(self):
        self.model.color_points[self.index].color = self.new_color
        self.model.modelChanged.emit()

    def undo(self):
        self.model.color_points[self.index].color = self.old_color
        self.model.modelChanged.emit()

class ReverseColorPoints(QUndoCommand):
    def __init__(self, model):
        super().__init__("Reverse Map")
        self.model = model

    def redo(self):
        self._reverse_points()

    def undo(self):
        self._reverse_points()

    def _reverse_points(self):
        reversed_points = [
            ColorPoint(1.0 - cp.position, cp.color)
            for cp in reversed(self.model.color_points)
        ]
        self.model.color_points = reversed_points
        self.model.modelChanged.emit()


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
    """Widget for editing discrete colormaps with draggable color squares, using ColorMapModel."""
    selectionChanged = pyqtSignal(int)  # Selection changed signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = parent.model
        self.model.modelChanged.connect(self.update_buttons)
        self.selected_indices = set()
        self.setup_ui()

    def setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)
        self.buttons = []
        self.update_buttons()

    def update_buttons(self):
        # Clear existing buttons
        for button in self.buttons:
            button.deleteLater()
        self.buttons.clear()

        # Create new buttons from model color_points (ignore position for display)
        for i, cp in enumerate(self.model.color_points):
            button = DraggableColorButton(cp.color, i, self)
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
        self.selectionChanged.emit(index)

    def change_color(self, index: int):
        """Open color dialog to change a color."""
        if 0 <= index < len(self.model.color_points):
            #color = QColorDialog.getColor(self.model.color_points[index].color, self)
            initial_color = convert_color(self.model.color_points[index].color, "qcolor", "hex")
            print(initial_color)
            color = QColor(select_color(initial_color, self))
            if color.isValid():
                self.model.change_color(index, color)

    def update_selection_display(self):
        """Update the visual selection state of all buttons."""
        for i, button in enumerate(self.buttons):
            button.set_selected(i in self.selected_indices)

    def handle_color_move(self, source_index: int, target_index: int):
        """Handle drag-and-drop reordering."""
        if source_index == target_index:
            return

        # Move the ColorPoint in the model
        points = self.model.color_points
        point = points.pop(source_index)
        points.insert(target_index, point)

        # Reassign positions to be evenly spaced
        n = len(points)
        for i, p in enumerate(points):
            p.position = i / (n - 1) if n > 1 else 0.0

        # Update selection indices
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
        self.model.modelChanged.emit()

    def add_color(self):
        """Add a new color based on selection."""
        points = self.model.color_points
        n = len(points)
        if n == 0:
            # Add first color
            self.model.add_point(0.0, QColor(Qt.GlobalColor.white))
            self.selected_indices = {0}
            return True

        if len(self.selected_indices) == 0:
            # No selection - add at end, position 1.0
            color = points[-1].color
            self.model.add_point(1.0, color)
            self.selected_indices = {n}
            return True

        sorted_indices = sorted(self.selected_indices)
        if len(sorted_indices) == 1:
            idx = sorted_indices[0]
            # Insert after selected, position halfway to next (or at end)
            if idx == n - 1:
                pos = 1.0
            else:
                pos = (points[idx].position + points[idx + 1].position) / 2
            color = points[idx].color
            self.model.add_point(pos, color)
            # After add, find the new point's index (may not be at end)
            self.model.color_points.sort(key=lambda cp: cp.position)
            new_idx = next((i for i, cp in enumerate(self.model.color_points) if cp.position == pos), -1)
            if new_idx >= 0:
                self.selected_indices = {new_idx}
            #self.model.color_points.sort(key=lambda cp: cp.position)
            #new_idx = self.model.color_points.index(
            #    min((cp for cp in self.model.color_points if cp.position == pos), key=lambda cp: cp.position)
            #)
            #self.selected_indices = {new_idx}
            return True

        # Multiple selections: insert between first two
        idx1, idx2 = sorted_indices[:2]
        if idx2 == idx1 + 1:
            pos = (points[idx1].position + points[idx2].position) / 2
            color1 = points[idx1].color
            color2 = points[idx2].color
            # Interpolate color
            r = (color1.red() + color2.red()) // 2
            g = (color1.green() + color2.green()) // 2
            b = (color1.blue() + color2.blue()) // 2
            color = QColor(r, g, b)
            self.model.add_point(pos, color)
            self.model.color_points.sort(key=lambda cp: cp.position)
            new_idx = next((i for i, cp in enumerate(self.model.color_points) if cp.position == pos), -1)
            if new_idx >= 0:
                self.selected_indices = {new_idx}
            #new_idx = self.model.color_points.index(
            #    min((cp for cp in self.model.color_points if cp.position == pos), key=lambda cp: cp.position)
            #)
            #self.selected_indices = {new_idx}
            return True
        return False

    def delete_selected(self):
        """Delete the currently selected color point(s)."""
        if not self.selected_indices:
            return
        
        # Sort indices in descending order to delete from end to beginning
        # This prevents index shifting issues when deleting multiple points
        indices_to_delete = sorted(self.selected_indices, reverse=True)
        
        # Delete each selected point
        for index in indices_to_delete:
            if 0 <= index < len(self.model.color_points):
                self.model.remove_point(index)
        
        # Update selection after deletion
        self.selected_indices.clear()
        
        if len(self.model.color_points) == 0:
            # No points left
            self.selectionChanged.emit(-1)  # Use -1 to indicate no selection
        else:
            # Select a reasonable point after deletion
            # Try to select the point at the position of the first deleted index
            first_deleted = min(indices_to_delete)
            if first_deleted < len(self.model.color_points):
                new_selection = first_deleted
            else:
                # If we deleted from the end, select the last remaining point
                new_selection = len(self.model.color_points) - 1
            
            self.selected_indices.add(new_selection)
            self.selectionChanged.emit(new_selection)
        
        # Trigger a repaint
        self.update()

    def get_selected_count(self) -> int:
        """Get the number of selected colors."""
        return len(self.selected_indices)

class ContinuousColorWidget(QWidget):
    """Widget for editing continuous colormaps with draggable triangular control points."""
    selectionChanged = pyqtSignal(int)  # Selected point index (-1 for none)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = parent.model
        self.model.modelChanged.connect(self.update)
        self.dragging_point = None
        self.selected_point = -1
        self._drag_start_pos = None
        self._drag_start_value = None
        self._drag_current_value = None
        self._drag_visual_pos = None
        self.setMouseTracking(True)
        self.margin_left = 15
        self.margin_right = 15

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        # Calculate the colormap area (excluding margins)
        colormap_left = self.margin_left
        colormap_width = rect.width() - self.margin_left - self.margin_right
        colormap_rect = QRectF(colormap_left, 0, colormap_width, 60)

        # Build a list of (position, color) for the current state, including drag
        points = []
        for i, point in enumerate(self.model.color_points):
            pos = point.position
            if self.dragging_point == i and self._drag_current_value is not None:
                pos = self._drag_current_value
            points.append((pos, point.color))
        # Sort by position for correct gradient
        points.sort(key=lambda pc: pc[0])

        # Draw colormap gradient
        gradient = QLinearGradient(colormap_left, 0, colormap_left + colormap_width, 0)
        for pos, color in points:
            gradient.setColorAt(pos, color)
        painter.fillRect(colormap_rect, QBrush(gradient))

        # Draw black border around colormap (1 pixel)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(colormap_rect)

        # Draw control points and lines
        for i, (pos, color) in enumerate(points):
            # Find the original index for selection
            orig_idx = next((j for j, p in enumerate(self.model.color_points)
                            if abs(p.position - pos) < 1e-6 and p.color == color), i)
            x = self.get_colormap_x(pos)
            # Draw the thin black line
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(int(x), 0, int(x), 60)
            # Draw the handle
            self.draw_triangular_handle(painter, x, color, orig_idx == self.selected_point)
    
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
            for i, point in enumerate(self.model.color_points):
                x = self.get_colormap_x(point.position)
                handle_rect = self.get_handle_bounds(x)
                if handle_rect.contains(event.position()):
                    clicked_point = i
                    break
            
            if clicked_point >= 0:
                self.selected_point = clicked_point
                self.dragging_point = clicked_point
                self._drag_start_pos = event.position().x()
                self._drag_start_value = self.model.color_points[clicked_point].position
                self._drag_current_value = self._drag_start_value
                self.selectionChanged.emit(clicked_point)
                self.update()
            else:
                # Clicked on colormap background - deselect
                self.selected_point = -1
                self.selectionChanged.emit(-1)
                self.update()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Try to add a new point at the clicked position
        if event.position().y() <= 60:
            new_pos = self.get_position_from_x(event.position().x())
            color = None

            # 1. Try color at clicked position
            if self.model.color_points:
                color = self.get_color_at_position(new_pos)

            # 2. If nothing selected, try selected point's color
            if (color is None or not color.isValid()) and self.selected_point >= 0:
                color = self.model.color_points[self.selected_point].color

            # 3. Fallback: last color in map
            if (color is None or not color.isValid()) and self.model.color_points:
                color = self.model.color_points[-1].color

            if color is None:
                color = QColor(Qt.GlobalColor.black)

            self.model.add_point(new_pos, color)
            # Select the new point
            # idx = min(
            #     (i for i, cp in enumerate(self.model.color_points) if abs(cp.position - new_pos) < 1e-6),
            #     default=-1
            # )
            idx = next((i for i, cp in enumerate(self.model.color_points) if abs(cp.position - new_pos) < 1e-6), -1)
            self.selected_point = idx
            self.selectionChanged.emit(self.selected_point)
            
            self.update()
            #self.model.modelChanged.emit()
            return

        # Otherwise, check if double-clicked on a handle to change color
        for i, point in enumerate(self.model.color_points):
            x = self.get_colormap_x(point.position)
            handle_rect = self.get_handle_bounds(x)
            if handle_rect.contains(event.position()):
                self.change_point_color(i)
                return

        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging_point is not None:
            # Only update the visual position, not the model
            new_pos = self.get_position_from_x(event.position().x())
            self._drag_current_value = min(max(new_pos, 0.0), 1.0)
            # Visual feedback: temporarily update the point's position for painting
            self.update()
            self.model.modelChanged.emit()
        else:
            # Update cursor when hovering over control points
            cursor = Qt.CursorShape.ArrowCursor
            for point in self.model.color_points:
                x = self.get_colormap_x(point.position)
                handle_rect = self.get_handle_bounds(x)
                if handle_rect.contains(event.position()):
                    cursor = Qt.CursorShape.SizeHorCursor
                    break
            self.setCursor(cursor)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.dragging_point is not None:
            idx = self.dragging_point

            old_pos = self._drag_start_value
            new_pos = self._drag_current_value
            if old_pos is None or new_pos is None:
                return

            if abs(old_pos - new_pos) > 1e-6:
                # Only push undo command if position changed
                self.model.undo_stack.push(MoveContinuousPointCommand(self.model, idx, old_pos, new_pos))

            self.dragging_point = None
            self._drag_start_pos = None
            self._drag_start_value = None
            self._drag_current_value = None

            self.update()
        super().mouseReleaseEvent(event)
    
    def get_color_at_position(self, position: float) -> QColor:
        if not self.model.color_points:
            return QColor(Qt.GlobalColor.black)
        
        # Find surrounding points
        left_point = None
        right_point = None
        for point in self.model.color_points:
            if point.position <= position:
                left_point = point
            if point.position >= position and right_point is None:
                right_point = point
                break
        
        if left_point is None:
            return self.model.color_points[0].color
        if right_point is None:
            return self.model.color_points[-1].color
        if left_point == right_point:
            return left_point.color
        
        # Interpolate between left and right points
        t = (position - left_point.position) / (right_point.position - left_point.position)
        
        r = left_point.color.red() * (1-t) + right_point.color.red() * t
        g = left_point.color.green() * (1-t) + right_point.color.green() * t
        b = left_point.color.blue() * (1-t) + right_point.color.blue() * t
        
        return QColor(int(r), int(g), int(b))

    def change_point_color(self, index: int):
        if 0 <= index < len(self.model.color_points):
            #color = QColorDialog.getColor(self.model.color_points[index].color, self)
            initial_color = convert_color(self.model.color_points[index].color, "qcolor", "hex")
            print(initial_color)
            color = QColor(select_color(initial_color, self))
            if color.isValid():
                self.model.change_color(index, color)

    def delete_selected_point(self):
        if self.selected_point >= 0 and len(self.model.color_points) > 2:
            self.model.remove_point(self.selected_point)
            self.selected_point = -1
            self.selectionChanged.emit(-1)
            self.update()
            return True
        return False
    
    def add_control_point(self):
        if len(self.model.color_points) < 10:
            # Find the largest gap between consecutive points
            best_pos = 0.5
            max_distance = 0
            points = sorted(self.model.color_points, key=lambda cp: cp.position)
            for i in range(len(points) - 1):
                distance = points[i + 1].position - points[i].position
                if distance > max_distance:
                    max_distance = distance
                    best_pos = (points[i].position + points[i + 1].position) / 2
            new_color = self.get_color_at_position(best_pos)
            self.model.add_point(best_pos, new_color)
            # Select the new point
            # idx = min(
            #     (i for i, cp in enumerate(self.model.color_points) if abs(cp.position - best_pos) < 1e-6),
            #     default=-1
            # )
            idx = next((i for i, cp in enumerate(self.model.color_points) if abs(cp.position - best_pos) < 1e-6), -1)
            self.selected_point = idx
            self.selectionChanged.emit(self.selected_point)
            
            self.update()
            return True
        return False

    def get_selected_point(self) -> int:
        """Get the index of the selected point (-1 if none)."""
        return self.selected_point

    def space_evenly_color_points(self):
        self.model.space_evenly_points()


class ColormapPreviewWidget(FigureCanvas):
    """Widget for previewing colormaps with colorblindness simulation."""
    
    def __init__(self, plot_type="linear", parent=None):
        self.plot_type = plot_type

        match self.plot_type:
            case "linear":
                self.figure = Figure(figsize=(8, 0.25))
            case "circular":
                self.figure = Figure(figsize=(3, 3))
            case "ternary":
                self.figure = Figure(figsize=(3, 3))
            case "image":
                self.figure = Figure(figsize=(8, 4))
            case _:
                raise ValueError("Plot type must be 'image', 'colorbar', 'circular', or 'ternary' ")
        super().__init__(self.figure)
        self.setParent(parent)
        self.setStyleSheet("background-color: transparent;")
        
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
        
        self.model = parent.model if parent else None
        self.preview_mode = 'normal'
        
    def set_colormap(self, model):
        """Set the colormap to preview."""
        self.models = model
        self.update_preview()
    
    def set_preview_mode(self, mode: str):
        """Set the preview mode (normal, grayscale, colorblind types)."""
        self.preview_mode = mode
        self.update_preview()
    
    def update_preview(self):
        """Update the preview display."""
        if self.model is None or self.model.color_points is None:
            return
            
        self.figure.clear()

        # --- Build colormap ---
        cmap = self.model.to_mpl_colormap() 

        # Apply colorblindness simulation if needed
        cmap = self.simulate_colorblind_view(cmap)

        # --- Set up ScalarMappable for colorbar ---
        vmax = 1
        if self.plot_type == "circular":
            vmax = 2*np.pi
        norm = mcolors.Normalize(vmin=0, vmax=vmax)  # Adjust vmin/vmax as needed
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])  # Required for ScalarMappable

        # Create visualization
        match self.plot_type:
            case "linear":
                ax = self.figure.add_subplot(1, 1, 1)
                cbar = self.figure.colorbar(sm, cax=ax, orientation='horizontal')
                cbar.set_ticks([])
            case "circular":
                ax = self.figure.add_subplot(1, 1, 1, projection='polar')
                r_inner = 0.75
                r_outer = 1.0

                theta = np.linspace(0, 2*np.pi, 512)
                r = np.linspace(r_inner, r_outer, 2)
                T, R = np.meshgrid(theta, r)
                
                # Normalize theta to [0,1] for colormap lookup
                Z = T  # angle determines color

                c = ax.pcolormesh(T, R, Z, cmap=cmap, norm=norm, shading='auto')

                # Add black lines on inner and outer radius
                theta_line = np.linspace(0, 2*np.pi, 512)
                ax.plot(theta_line, np.full_like(theta_line, r_inner), 'k-', linewidth=1) # inner
                ax.plot(theta_line, np.full_like(theta_line, r_outer), 'k-', linewidth=1) # outer
                
                ax.set_yticklabels([])   # hide radius labels
                ax.set_xticklabels([])   # hide angle labels
                ax.set_ylim(r_inner, r_outer)
                ax.set_aspect(1)

            case "ternary":
                ax = self.figure.add_subplot(1, 1, 1)

                tern = ternary(ax, labels=None)
                #rgb_colors = [color_to_rgb(c, normalize=True) for c in self.model.get_colors()]
                rgb_colors = convert_color_list(self.model.get_colors(), "QColor", "rgb", norm_out=True)

                if rgb_colors:
                    rgb_colors = self.simulate_colorblind_view(rgb_colors)

                    hbin = tern.hexagon(10)
                    xc = np.array([v['xc'] for v in hbin])
                    yc = np.array([v['yc'] for v in hbin])
                    at,bt,ct = tern.xy2tern(xc,yc)
                    if len(rgb_colors) == 4:
                        cv = tern.terncolor(at,bt,ct, ca=rgb_colors[0], cb=rgb_colors[1], cc=rgb_colors[2], cp=rgb_colors[3])
                    else:
                        cv = tern.terncolor(at,bt,ct, ca=rgb_colors[0], cb=rgb_colors[1], cc=rgb_colors[2])
                    for i, hb in enumerate(hbin):
                        tern.ax.fill(hb['xv'], hb['yv'], color=cv[i], edgecolor='none')

            case "image":
                ax = self.figure.add_subplot(1, 1, 1)
                im = ax.imshow(self.test_data, cmap=cmap, aspect='equal')

        ax.axis('off')
        ax.set_facecolor("none")   # transparent axes background
        ax.patch.set_alpha(0.0)
        self.figure.patch.set_alpha(0.0)
        
        self.figure.tight_layout()
        self.draw()

    def simulate_colorblind_view(self, cmap):
        """Simulate different types of colorblindness on colormaps or colors."""

        if self.preview_mode == "normal":
            return cmap

        if self.preview_mode not in cb_matrices:
            return cmap  # fallback

        matrix = cb_matrices[self.preview_mode]

        # --- Case 1: Matplotlib Colormap ---
        if isinstance(cmap, mcolors.Colormap):
            colors = cmap(np.linspace(0, 1, 256))[:, :3]  # Nx3 RGB
            transformed = np.dot(colors, matrix.T)
            transformed = np.clip(transformed, 0, 1)
            return mcolors.LinearSegmentedColormap.from_list(
                f"{cmap.name}_{self.preview_mode}", transformed
            )

        # --- Case 2: List of QColor/tuples ---
        if isinstance(cmap, (list, tuple)):
            #rgb_colors = np.array([color_to_rgb(c, normalize=True) for c in cmap])
            rgb_colors = np.array(convert_color_list(cmap, "QColor", "rgb", norm_out=True))
            transformed = np.dot(rgb_colors, matrix.T)
            transformed = np.clip(transformed, 0, 1)
            return [tuple(c) for c in transformed]

        # --- Case 3: Single QColor or tuple ---
        if isinstance(cmap, (QColor, tuple, list)):
            #rgb = np.array(color_to_rgb(cmap, normalize=True))
            rgb_colors = np.array(convert_color_list(cmap, "QColor", "rgb", norm_out=True))
            transformed = np.dot(rgb, matrix.T)
            transformed = np.clip(transformed, 0, 1)
            return tuple(transformed)

        # fallback: return unchanged
        return cmap

class ColormapSelector(QWidget):
    colormapChanged = pyqtSignal(str, str) # For change in colormap

    def __init__(self, custom_maps=None, parent=None):
        super().__init__(parent)

        # --- Data sources ---
        self.maps = {
            "Matplotlib": sorted(
                name for name in plt.colormaps()
                if not name.endswith("_r") and not name.startswith("cmc.")
            ),
            "Crameri": get_cmr_colormap_names(),
            "Custom": custom_maps or []
        }

        # --- Widgets ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.source_combobox = QComboBox()
        self.source_combobox.addItems(self.maps.keys())

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search colormaps...")

        self.cmap_combobox = QComboBox()

        layout.addWidget(self.source_combobox)
        layout.addWidget(self.search_box)
        layout.addWidget(self.cmap_combobox)

        # --- Signals ---
        self.source_combobox.currentTextChanged.connect(self.update_cmap_combo)
        self.search_box.textChanged.connect(self.update_cmap_combo)
        self.cmap_combobox.currentTextChanged.connect(self.get_selected_cmap)

        # --- Initialize ---
        self.update_cmap_combo()

    def update_cmap_combo(self):
        """Update colormap combobox based on current source and search."""
        source = self.source_combobox.currentText()
        all_items = self.maps[source]

        filter_text = self.search_box.text().lower()
        filtered = [name for name in all_items if filter_text in name.lower()]

        self.cmap_combobox.clear()
        self.cmap_combobox.addItems(filtered)

    def get_selected_cmap(self):
        """Return the currently selected colormap name."""
        self.colormapChanged.emit(self.source_combobox.currentText(), self.cmap_combobox.currentText())

class ColormapEditorDialog(QDialog):
    """Main colormap editor dialog."""
    
    def __init__(self, existing_colormaps: Dict[str, any] = None, parent=None):
        super().__init__(parent)
        self.existing_colormaps = existing_colormaps or {}
        self.counter = 0

        # create colormap model, it contains the color points (positions, colors) and undo stack
        self.model = ColorMapModel(self)
        # default colormap model
        self.model.color_points = [
            ColorPoint(0.0, QColor("#440154")),
            ColorPoint(0.25, QColor("#31688e")),
            ColorPoint(0.5, QColor("#35b779")),
            ColorPoint(0.75, QColor("#fde725")),
            ColorPoint(1.0, QColor("#ffffff"))
        ]
        
        self.setWindowTitle("Colormap Editor")
        self.setMinimumSize(600, 240)
        # Allow dynamic resizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

        if self.existing_colormaps:
            self.colormap_widget.source_combobox.setCurrentText("Custom")
        else:
            self.colormap_widget.source_combobox.setCurrentText("Matplotlib")
            idx = self.colormap_widget.cmap_combobox.findText("viridis")
            if idx >= 0:
                self.colormap_widget.cmap_combobox.setCurrentIndex(idx)
            else:
                print("viridis not in combobox yet!")


        # Initial resize without preview
        #self.resize(800, 250)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(3,3,3,3)
        
        # Top controls
        toolbar = QToolBar(self)
        toolbar.setContentsMargins(3,3,3,3)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(24,24))
        font = toolbar.font()
        font.setPixelSize(11)

        # File operations
        self.load_action = CustomAction(
            text="Load\nFile",
            light_icon_unchecked="icon-add-list-64.svg",
            dark_icon_unchecked="icon-add-list-dark-64.svg",
            parent=toolbar,
        )
        self.load_action.setToolTip("Load file with custom colormaps")
        self.load_action.triggered.connect(self.load_csv)
        self.load_action.setShortcut("Ctrl+O")
        
        self.save_action = CustomAction(
            text="Save",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=toolbar,
        )
        self.save_action.setToolTip("Save colormap")
        self.save_action.triggered.connect(self.save_colormap)
        self.save_action.setShortcut("Ctrl+S")

        
        # Colormap selection
        self.colormap_widget = ColormapSelector(parent=self)
        self.colormap_widget.colormapChanged.connect(self.on_colormap_changed)
        self.colormap_widget.search_box.hide()

        self.reverse_action = CustomAction(
            text="Invert",
            light_icon_unchecked="icon-reverse-64.svg",
            dark_icon_unchecked="icon-reverse-dark-64.svg",
            parent=toolbar,
        )
        self.reverse_action.setToolTip("Reverse colormap direction")
        self.reverse_action.triggered.connect(self.model.reverse_points)
        self.reverse_action.setShortcut("Ctrl+I")

        self.add_point_action = CustomAction(
            text="Add\nPoint",
            light_icon_unchecked="icon-accept-64.svg",
            parent=toolbar,
        )
        self.add_point_action.triggered.connect(self.add_control_point)
        self.add_point_action.setToolTip("Add control point")
        self.add_point_action.setShortcut("Ctrl+Shift+=")

        self.remove_point_action = CustomAction(
            text="Remove\nPoint",
            light_icon_unchecked="icon-reject-64.svg",
            parent=toolbar,
        )
        self.remove_point_action.triggered.connect(self.delete_control_point)
        self.remove_point_action.setEnabled(False)
        self.remove_point_action.setToolTip("Remove control point")
        self.remove_point_action.setShortcut("Ctrl+Shift+-")

        self.space_evenly_action = CustomAction(
            text="Equal\nSpacing",
            light_icon_unchecked="icon-even-spacing-64.svg",
            dark_icon_unchecked="icon-even-spacing-dark-64.svg",
            parent=toolbar,
        )
        self.space_evenly_action.setEnabled(True)
        self.space_evenly_action.setToolTip("Evenly space control points")

        # Switch axes for type of preview
        self.linear_icon = QIcon(str(ICONPATH / "icon-cmap-linear-64.svg"))
        self.circular_icon = QIcon(str(ICONPATH / "icon-cmap-circular-64.svg"))
        self.ternary_icon = QIcon(str(ICONPATH / "icon-cmap-ternary-64.svg"))

        self.axes_style_action = QAction("Axes", toolbar)
        self.axes_style_action.setEnabled(False)
        self.axes_style_action.setIcon(self.linear_icon)
        self.axes_style_action.triggered.connect(self.on_axes_style_changed)

        self.preview_action = CustomAction(
            text="Preview",
            light_icon_unchecked="icon-show-hide-64.svg",
            light_icon_checked="icon-show-64.svg",
            parent=toolbar,
        )
        self.preview_action.setChecked(False)
        self.preview_action.setToolTip("Show/hide preview")
        self.preview_action.triggered.connect(self.toggle_preview)
        self.preview_action.setShortcut("Ctrl+P")
        
        # Preview mode selection
        self.simulator_widget = QWidget(toolbar)
        simulator_layout = QVBoxLayout(self.simulator_widget)
        simulator_layout.setContentsMargins(0, 0, 0, 0)
        self.simulator_widget.setLayout(simulator_layout)

        self.simulator_combo = QComboBox()
        self.simulator_combo.addItems(['normal', 'grayscale', 'deuteranopia', 'protanopia', 'tritanopia'])
        self.simulator_combo.currentTextChanged.connect(self.on_preview_mode_changed)
        
        simulator_label = QLabel()
        simulator_label.setText("Simulate:")
        simulator_label.setFont(font)

        simulator_layout.addWidget(simulator_label)
        simulator_layout.addWidget(self.simulator_combo)

        # Discrete/Continuous toggle
        self.toggle_widget = QWidget(toolbar)
        toggle_layout = QVBoxLayout(self.toggle_widget)
        toggle_layout.setContentsMargins(0,0,0,0)
        self.toggle_widget.setLayout(toggle_layout)

        self.cmap_style_toggle = ToggleSwitch(toolbar, height=24, bg_left_color="#5798d1", bg_right_color="#d9ad86")
        self.cmap_style_toggle.setChecked(False)
        self.cmap_style_toggle.setToolTip("Toggle colormap style")
        self.cmap_style_toggle.stateChanged.connect(self.on_discrete_toggled)

        self.cmap_style_label = QLabel(toolbar)
        self.cmap_style_label.setText("Continuous")
        self.cmap_style_label.setFont(font)
        self.cmap_style_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        toggle_layout.addWidget(self.cmap_style_toggle)
        toggle_layout.addWidget(self.cmap_style_label)
        toggle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cmap_style_action = QWidgetAction(toolbar)
        self.cmap_style_action.setDefaultWidget(self.toggle_widget)
        self.cmap_style_action.setText("Colormap: continuous")
        self.cmap_style_action.setShortcut("Ctrl+T")

        self.new_colormap_action = CustomAction(
            text="Create\nNew",
            light_icon_unchecked="icon-cmap-star-64.svg",
            parent=toolbar,
        )
        self.new_colormap_action.setToolTip("Create a new colormap")
        self.new_colormap_action.triggered.connect(self.create_new_colormap)

        self.color_select_action = CustomAction(
            text="Color\nPicker",
            light_icon_unchecked="icon-dropper-64.svg",
            dark_icon_unchecked="icon-dropper-dark-64.svg",
            parent=toolbar,
        )
        self.color_select_action.setCheckable(True)
        self.color_select_action.setChecked(False)
        self.color_select_action.setToolTip("Activate the color select tool")

        self.hex_display = QLineEdit()
        self.hex_display.setFixedWidth(80)  # compact
        self.hex_display.setPlaceholderText("#RRGGBB")
        # Optional: restrict input to valid hex codes
        hex_validator = QRegularExpressionValidator(QRegularExpression("#[0-9A-Fa-f]{6}"))
        self.hex_display.setValidator(hex_validator)
        self.hex_display.editingFinished.connect(self.on_hex_changed)
        self.hex_display.setStyleSheet("""
            QLineEdit {
                border: 2px solid #000000;
                border-radius: 4px;
                padding: 2px;
            }
        """)
        self.hex_display.textChanged.connect(self.set_hex_display_color)

        toolbar.addAction(self.new_colormap_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addWidget(self.colormap_widget)
        toolbar.addAction(self.reverse_action)
        toolbar.addAction(self.cmap_style_action)
        toolbar.addSeparator()
        toolbar.addAction(self.add_point_action)
        toolbar.addAction(self.remove_point_action)
        toolbar.addAction(self.space_evenly_action)
        toolbar.addSeparator()
        toolbar.addAction(self.axes_style_action)
        toolbar.addAction(self.preview_action)
        toolbar.addWidget(self.simulator_widget)
        toolbar.addSeparator()
        toolbar.addAction(self.color_select_action)
        toolbar.addWidget(self.hex_display)
        
        self.main_layout.addWidget(toolbar)

        menubar = QMenuBar(self)
        file_menu = QMenu("&File", self)
        edit_menu = QMenu("&Edit", self)
        view_menu = QMenu("&View", self)

        menubar.addMenu(file_menu)
        menubar.addMenu(edit_menu)
        menubar.addMenu(view_menu)

        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        
        self.undo_action = self.model.undo_stack.createUndoAction(self, "&Undo")
        self.undo_action.setShortcuts(QKeySequence.StandardKey.Undo)
        self.undo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.addAction(self.undo_action)

        self.redo_action = self.model.undo_stack.createRedoAction(self, "&Redo")
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        self.redo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.addAction(self.redo_action)

        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.add_point_action)
        edit_menu.addAction(self.remove_point_action)
        edit_menu.addAction(self.space_evenly_action)
        edit_menu.addAction(self.reverse_action)

        view_menu.addAction(self.cmap_style_action)
        view_menu.addAction(self.preview_action)
        view_menu.addAction(self.color_select_action)
        
        # Colormap display area
        display_group = QGroupBox("Colormap Editor")
        display_group.setFixedHeight(140)
        display_layout = QVBoxLayout(display_group)
        
        # Discrete color editor (default)
        self.discrete_widget = DiscreteColorWidget(self)
        self.discrete_widget.selectionChanged.connect(self.on_discrete_selection_changed)
        display_layout.addWidget(self.discrete_widget)
        
        # Continuous color editor (hidden initially)
        self.continuous_widget = ContinuousColorWidget(self)
        self.continuous_widget.selectionChanged.connect(self.on_selection_changed)
        display_layout.addWidget(self.continuous_widget)
        
        self.main_layout.addWidget(display_group)

        self.colorblind_group = QGroupBox("Colorblind Simulation")
        self.colorblind_group.setFixedHeight(140)
        colorblind_layout = QVBoxLayout(self.colorblind_group)

        self.colorbar_widget = ColormapPreviewWidget(plot_type="linear", parent=self)
        self.colorbar_widget.setMinimumHeight(100)  # Set minimum height for preview

        colorblind_layout.addWidget(self.colorbar_widget)

        self.main_layout.addWidget(self.colorblind_group)
        
        # Preview area - initially not added to layout
        self.preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(self.preview_group)
        
        self.preview_widget = ColormapPreviewWidget(plot_type="image", parent=self)
        self.preview_widget.setMinimumHeight(300)  # Set minimum height for preview
        preview_layout.addWidget(self.preview_widget)

        self.picker_group = QGroupBox("Image Color Picker")
        picker_layout = QVBoxLayout(self.picker_group)
        picker_layout.setContentsMargins(3, 3, 3, 3)
        self.picker_group.setLayout(picker_layout)

        self.picker = ImageColorPicker(parent=self)
        self.picker.setMinimumHeight(350)  # Set minimum height for preview
        picker_layout.addWidget(self.picker)
        self.picker.colorPicked.connect(self.on_color_picked)
        self.picker.paletteCreated.connect(lambda colors: self.palette_from_image(colors))

        self.main_layout.addWidget(self.picker_group)
        self.picker_group.hide()

        # Ensure correct initial visibility based on self.model.is_discrete
        if self.model.is_discrete:
            self.continuous_widget.hide()
            self.discrete_widget.show()
        else:
            self.discrete_widget.hide()
            self.continuous_widget.show()

        self.space_evenly_action.triggered.connect(self.continuous_widget.space_evenly_color_points)
        self.color_select_action.triggered.connect(self.toggle_picker)
        self.model.modelChanged.connect(self.update_preview)
        self.model.modelChanged.connect(self.update_axes_style_action)
        self.model.modelChanged.connect(self.update_button_states)

        #self.cmap_style_toggle.setChecked(not self.cmap_style_toggle.isChecked())

    def closeEvent(self, event):
        """
        Reject the dialog when closed, so changes are discarded.
        """
        self.reject()
        event.accept()  # proceed with closing

    def update_axes_style_action(self):
        """Enable/disable axes style action depending on colormap."""
        allow_circular = self.model.is_circular_colormap()
        allow_ternary = self.model.is_ternary_colormap()

        # Collect allowed styles
        allowed = ['linear']
        if allow_circular:
            allowed.append('circular')
        if allow_ternary:
            allowed.append('ternary')

        # If only linear allowed, disable action (nothing to switch to)
        self.axes_style_action.setEnabled(len(allowed) > 1)

        # Store allowed styles for toggling
        self.allowed_axes_styles = allowed
        if self.colorbar_widget.plot_type not in allowed:
            self.colorbar_widget.plot_type = 'linear'
            self.colorbar_widget.update_preview()

        # update icon
        self.set_axes_style(self.colorbar_widget.plot_type)

    def on_axes_style_changed(self):
        if not self.axes_style_action.isEnabled():
            return

        idx = self.allowed_axes_styles.index(self.colorbar_widget.plot_type)
        idx = (idx + 1) % len(self.allowed_axes_styles)
        self.colorbar_widget.plot_type = self.allowed_axes_styles[idx]

        self.set_axes_style(self.colorbar_widget.plot_type)

        self.update_preview()

    def set_axes_style(self, style):
        if style == "linear":
            self.axes_style_action.setIcon(self.linear_icon)
            self.colorblind_group.setFixedHeight(140)
            # replace axes with Cartesian
        elif style == "circular":
            self.axes_style_action.setIcon(self.circular_icon)
            self.colorblind_group.setFixedHeight(350)
            # replace axes with polar
        elif style == "ternary":
            self.axes_style_action.setIcon(self.ternary_icon)
            self.colorblind_group.setFixedHeight(350)
            # draw ternary axes (custom)

    def on_colormap_changed(self, source: str="Matplotlib", colormap_name: str="viridis"):
        """Handle colormap selection change."""
        if not colormap_name or not colormap_name.strip():  # Handle empty or whitespace selection
            return

        if colormap_name == "untitled":
            # Ask user for new name
            new_name, ok = QInputDialog.getText(self, "Save Colormap", "Enter name:")
            if ok and new_name.strip():
                colormap_name = new_name.strip()
                # Replace "untitled" with actual name in combobox
                idx = self.colormap_widget.cmap_combobox.findText("untitled")
                if idx >= 0:
                    self.colormap_widget.cmap_combobox.setItemText(idx, colormap_name)

            
        print(f"Loading colormap: {colormap_name} from {source}")

        # Clear undo stack
        self.model.undo_stack.clear()
        self.model.unsaved = False

        # Load colors from custom or built-in colormap
        if source == "Custom" and colormap_name in self.existing_colormaps:
            colors = self.existing_colormaps[colormap_name]
        else:
            try:
                if source == "Matplotlib":
                    cmap = plt.get_cmap(colormap_name)
                elif source == "Crameri":
                    cmap = getattr(cmr, colormap_name)
                else:
                    return
                colors = [QColor.fromRgbF(*cmap(i / 4.0)[:3]) for i in range(5)]
            except Exception as e:
                print(f"Error loading {source} colormap {colormap_name}: {e}")
                return

        # Always update the model as the single source of truth
        n = len(colors)
        self.model.color_points = [ColorPoint(i / (n - 1) if n > 1 else 0.0, color) for i, color in enumerate(colors)]

        self.model.modelChanged.emit()

    def on_preview_mode_changed(self, mode: str):
        """Handle preview mode change."""
        self.colorbar_widget.set_preview_mode(mode)
        self.preview_widget.set_preview_mode(mode)
    
    def on_discrete_toggled(self, is_discrete: bool):
        """Handle discrete/continuous mode toggle."""
        self.model.is_discrete = is_discrete

        # Show/hide widgets appropriately and update button/action text
        if self.model.is_discrete:
            self.continuous_widget.hide()
            self.discrete_widget.show()

            self.add_point_action.setText("Add\nColor")
            self.remove_point_action.setText("Delete\nColor")
            self.cmap_style_label.setText("Discrete")
            self.space_evenly_action.setEnabled(False)
        else:
            self.discrete_widget.hide()
            self.continuous_widget.show()

            self.add_point_action.setText("Add\nPoint")
            self.remove_point_action.setText("Delete\nPoint")
            self.cmap_style_label.setText("Continuous")
            self.space_evenly_action.setEnabled(True)

        # Update views
        self.model.modelChanged.emit()

    def on_hex_changed(self):
        text = self.hex_display.text().strip()
        if len(text) == 7 and text.startswith("#"):
            qcolor = QColor(text)
            if qcolor.isValid():
                if self.model.is_discrete:
                    for i in self.discrete_widget.selected_indices:
                        self.model.change_color(i, qcolor)
                else:
                    idx = self.continuous_widget.get_selected_point()
                    if idx >= 0:
                        self.model.change_color(idx, qcolor)
    
    def set_hex_display_color(self):
        """Update QLineEdit text and border color."""
        text = self.hex_display.text().strip()
        if len(text) == 7 and text.startswith("#"):
            qcolor = QColor(text)
            if qcolor.isValid():
                hex_code = qcolor.name().upper()
                #self.hex_display.setText(hex_code)

                # set border color to match
                self.hex_display.setStyleSheet(f"""
                    QLineEdit {{
                        border: 2px solid {hex_code};
                        border-radius: 4px;
                        padding: 2px;
                    }}
                """)

    def on_color_picked(self, new_color):
        """Adds or changes colors in the colormap based from the color picker."""
        self.hex_display.setText(new_color)

        new_color = QColor(new_color)
        if self.model.is_discrete:
            if self.discrete_widget.get_selected_count() > 0:
                idx = self.discrete_widget.selected_indices
        else:
            idx = [self.continuous_widget.get_selected_point()]
        
        if len(idx) > 0 and idx[0] != -1:
            self.model.change_color(idx[0], new_color)
        else:
            idx = len(self.model.color_points)+1
            self.model.add_point(position=1.0, color=new_color, index=idx)
            self.model.color_points[idx-1].position = (self.model.color_points[idx-2].position + 1.0)/2.0
            self.model.space_evenly_points()

        self.picker.magnifier.raise_()
    
    def update_hex_display(self, qcolor):
        """Update the hexEdit box to show the currently selected color."""
        hex_str = qcolor.name().upper()  # e.g. #FF00AA
        self.hex_display.setText(hex_str)

    def on_selection_changed(self, selected_index: int):
        """Handle control point selection changes in continuous mode."""
        if selected_index >= 0:
            # Get the selected color
            qcolor = self.model.color_points[selected_index].color
            self.update_hex_display(qcolor)
        else:
            # Clear hex display when nothing selected
            self.hex_display.setText("")
        self.update_button_states()

    def on_discrete_selection_changed(self, selected_index: int):
        """Handle color selection changes in discrete mode."""
        if selected_index >= 0:
            # Get the selected color
            qcolor = self.model.color_points[selected_index].color
            self.update_hex_display(qcolor)
        else:
            # Clear hex display when nothing selected
            self.hex_display.setText("")
        self.update_button_states()
    
    def update_button_states(self):
        """Update the state of add/delete buttons based on current mode and selection."""
        if self.model.is_discrete:
            # Discrete mode
            selected_count = self.discrete_widget.get_selected_count()
            total_colors = len(self.model.get_colors())
            
            self.add_point_action.setEnabled(True)  # Can always add colors
            # Can delete if something is selected and won't delete all colors
            self.remove_point_action.setEnabled(selected_count > 0 and selected_count < total_colors)
        else:
            # Continuous mode
            selected_index = self.continuous_widget.get_selected_point()
            total_points = len(self.model.color_points)
            
            self.add_point_action.setEnabled(total_points < 10)  # Reasonable maximum
            # Can delete if something is selected and at least 2 points will remain
            self.remove_point_action.setEnabled(selected_index >= 0 and total_points > 2)
    
    def add_control_point(self):
        """Add a new control point or color."""
        if self.model.is_discrete:
            self.discrete_widget.add_color()
        else:
            self.continuous_widget.add_control_point()

    def delete_control_point(self):
        """Delete the selected control point or colors."""
        if self.model.is_discrete:
            self.discrete_widget.delete_selected()
        else:
            self.continuous_widget.delete_selected_point()
    
    def toggle_preview(self):
        """Toggle preview visibility."""
        if self.preview_action.isChecked():
            # Add preview to layout
            preview_insert_index = self.main_layout.count()
            if self.picker_group.isVisible():
                preview_insert_index += -1
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

    def toggle_picker(self):
        """Toggle color picker visibility."""
        if self.color_select_action.isChecked():
            # Add preview to layout
            picker_insert_index = self.main_layout.count()
            self.main_layout.insertWidget(picker_insert_index, self.picker_group)
            self.picker_group.show()
            self.update_preview()
        else:
            # Remove preview from layout and hide
            self.main_layout.removeWidget(self.picker_group)
            self.picker_group.hide()

        # Let the layout system handle the resizing automatically
        self.adjustSize()

    
    def update_preview(self):
        """Update the preview if visible."""
        if self.model and self.model.color_points:
            # update preview colorbar
            self.colorbar_widget.set_colormap(self.model)
            self.colorbar_widget.update_preview()

            # update preview image
            if self.preview_action.isChecked():
                self.preview_widget.set_colormap(self.model)
                self.preview_widget.update_preview()

    def create_new_colormap(self):
        """Create a new empty colormap with two points (black and white)."""
        # Define default two color points
        points = [
            ColorPoint(0.0, QColor(0, 0, 0)),   # Black at position 0
            ColorPoint(1.0, QColor(255, 255, 255))  # White at position 1
        ]

        # Update model with new points
        self.model.color_points = points
        self.model.modelChanged.emit()

        self.create_new_colormap_entry() 

        # Track current colormap
        self.current_colormap_data = points

        # Refresh preview
        self.update_preview()

    def create_new_colormap_entry(self):
        # Switch comboboxes to indicate new custom map
        idx_source = self.colormap_widget.source_combobox.findText("Custom")
        if idx_source >= 0:
            self.colormap_widget.source_combobox.setCurrentIndex(idx_source)

        # Ensure "untitled" exists in cmap_combobox
        if self.colormap_widget.cmap_combobox.findText(f"untitled-{self.counter}") == -1:
            self.colormap_widget.cmap_combobox.addItem(f"untitled-{self.counter}")
        else:
            self.counter += 1
            self.colormap_widget.cmap_combobox.addItem(f"untitled-{self.counter}")

        idx_cmap = self.colormap_widget.cmap_combobox.findText(f"untitled-{self.counter}")
        self.colormap_widget.cmap_combobox.setCurrentIndex(idx_cmap)

    
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
                            # Strip BOM from the first cell if present
                            colormap_name = row[0].lstrip('\ufeff').strip()
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
                    custom_cmap_list = list(self.existing_colormaps.keys())
                    print(f"Updated existing_colormaps: {custom_cmap_list}")  # Debug print
                    
                    # Store current selection to restore if possible
                    current_selection = self.colormap_widget.cmap_combobox.currentText()
                    self.colormap_widget.maps['Custom'] = custom_cmap_list

                    if self.colormap_widget.source_combobox.currentText() == 'Custom':
                        # Repopulate the combo box to include new colormaps
                        self.colormap_widget.cmap_combobox.blockSignals(True)  # Prevent triggering change event
                        self.colormap_widget.update_cmap_combo()
                        self.colormap_widget.cmap_combobox.blockSignals(False)
                    
                    # Try to restore previous selection, or select first loaded colormap
                    if current_selection and current_selection in [self.colormap_widget.cmap_combobox.itemText(i) for i in range(self.colormap_widget.cmap_combobox.count())]:
                        index = self.colormap_widget.cmap_combobox.findText(current_selection)
                        if index >= 0:
                            self.colormap_widget.cmap_combobox.setCurrentIndex(index)
                    else:
                        # Select first loaded colormap
                        first_loaded = list(loaded_colormaps.keys())[0]
                        index = self.colormap_widget.cmap_combobox.findText(first_loaded)
                        if index >= 0:
                            self.colormap_widget.cmap_combobox.setCurrentIndex(index)
                    
                    # Manually trigger the change event to load the selected colormap
                    self.colormap_widget.colormapChanged.emit(
                        self.colormap_widget.source_combobox.currentText(),
                        self.colormap_widget.cmap_combobox.currentText()
                    )
                    
                    QMessageBox.information(self, "Success", 
                                          f"Loaded {len(loaded_colormaps)} colormaps from CSV")
                else:
                    QMessageBox.warning(self, "Warning", "No valid colormaps found in CSV file")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load CSV: {str(e)}")
    
    def save_colormap(self):
        """Save the current colormap to CSV file."""
        if not self.model or not self.model.color_points:
            QMessageBox.warning(self, "Warning", "No colormap data to save")
            return

        # Get colormap name from user
        colormap_name, ok = QInputDialog.getText(
            self, "Save Colormap", "Enter colormap name:"
        )

        if not ok or not colormap_name.strip():
            return

        colormap_name = colormap_name.strip()

        file_path_str, _ = QFileDialog.getSaveFileName(
            self, "Save Colormap CSV", "", "CSV Files (*.csv)"
        )

        if file_path_str:
            file_path = Path(file_path_str)  # Convert to pathlib.Path

            try:
                # Extract colors from continuous color points
                colors = [point.color for point in sorted(self.model.color_points, key=lambda x: x.position)]

                # Convert colors to hex strings
                hex_colors = [color.name() for color in colors]  # QColor.name() returns hex format

                existing_data = []
                if file_path.exists():
                    # Read existing data
                    with file_path.open('r', newline='', encoding='utf-8-sig') as file:
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
                with file_path.open('w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    writer.writerows(existing_data)

                action = "updated" if colormap_found else "added"
                QMessageBox.information(
                    self, "Success",
                    f"Colormap '{colormap_name}' {action} successfully with {len(hex_colors)} colors"
                )
                self.accept()

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save CSV: {str(e)}")

        self.model.undo_stack.setClean()
        self.model.unsaved = False

    def palette_from_image(self, colors):
        n = len(colors)
        points = []
        for i, c in enumerate(colors):
            points.append(ColorPoint(position=i/(n-1), color=QColor(c)))
        self.model.color_points = points
        self.create_new_colormap_entry()

        self.model.undo_stack.clear()
        self.model.unsaved = True

        # Refresh preview
        self.model.modelChanged.emit()
    
    def get_colormodel(self):
        """Get the current colormap data."""
        return self.model


# Example usage and test
def main():
    app = QApplication(sys.argv)
    
    # Sample existing colormaps
    existing_maps = { }
    
    dialog = ColormapEditorDialog(existing_maps)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        model = dialog.get_colormodel()
        print(f"Colormap saved: {len(model.color_points)} {'discrete' if model.is_discrete else 'continuous'} colors")
        
        for i, point in enumerate(model.color_points):
            print(f"  Point {i}: {point.color.name()} at position {point.position:.3f}")
    
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())