import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QToolBar, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QCursor, QAction, 
                        QIcon, QScreen, QPalette, QImage)


class ColorDropperWidget(QWidget):
    """
    A color dropper widget that captures screen colors with magnified preview.
    Emits colorSelected signal with hex color string when a color is picked.
    """
    colorSelected = pyqtSignal(str)  # Emits hex color string
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        # Removed WA_TranslucentBackground - this was causing color darkening!
        
        # Configuration
        self.zoom_factor = 8
        self.preview_size = 120
        self.grid_size = 15  # 15x15 grid in preview
        self.pixel_size = self.preview_size // self.grid_size
        
        # State variables
        self.screen_pixmap = None
        self.mouse_pos = QPoint(0, 0)
        self.preview_offset = QPoint(20, 20)  # Offset from mouse position
        
        # Setup UI
        self.setup_ui()
        
        # Timer for updating mouse position
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_preview)
        
    def setup_ui(self):
        """Setup the preview widget UI"""
        self.setFixedSize(self.preview_size + 40, self.preview_size + 40)
        
        # Create frame for preview
        self.preview_frame = QFrame(self)
        self.preview_frame.setGeometry(10, 10, self.preview_size + 20, self.preview_size + 20)
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: none;
                border: 2px solid #888;
                border-radius: 5px;
            }
        """)
        
        # Ensure widget has proper color management
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        
    def start_color_picking(self):
        """Start the color picking process"""
        # Capture the entire screen (all screens if multiple)
        screen = QApplication.primaryScreen()
        # Get the full desktop geometry including all screens
        desktop_geometry = QApplication.primaryScreen().virtualGeometry()
        self.screen_pixmap = screen.grabWindow(0, desktop_geometry.x(), desktop_geometry.y(), 
                                             desktop_geometry.width(), desktop_geometry.height())
        
        # Enable mouse tracking globally
        self.setMouseTracking(True)
        self.grabMouse()  # Capture mouse globally
        
        # Set cursor and show widget
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Start update timer
        self.update_timer.start(16)  # ~60 FPS
        
    def stop_color_picking(self):
        """Stop the color picking process"""
        self.update_timer.stop()
        self.hide()
        self.releaseMouse()  # Release mouse capture
        QApplication.restoreOverrideCursor()
        self.setMouseTracking(False)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        self.mouse_pos = QCursor.pos()  # Get global mouse position
        self.update_position()
        
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.pick_color_at_mouse()
        elif event.button() == Qt.MouseButton.RightButton:
            self.stop_color_picking()
            
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key.Key_Escape:
            self.stop_color_picking()
        super().keyPressEvent(event)
        
    def update_position(self):
        """Update widget position relative to mouse"""
        screen_rect = QApplication.primaryScreen().geometry()
        widget_pos = self.mouse_pos + self.preview_offset
        
        # Keep widget on screen
        if widget_pos.x() + self.width() > screen_rect.right():
            widget_pos.setX(self.mouse_pos.x() - self.width() - self.preview_offset.x())
        if widget_pos.y() + self.height() > screen_rect.bottom():
            widget_pos.setY(self.mouse_pos.y() - self.height() - self.preview_offset.y())
            
        self.move(widget_pos)
        
    def update_preview(self):
        """Update the magnified preview"""
        if not self.screen_pixmap:
            return
            
        self.update()
        
    def pick_color_at_mouse(self):
        """Pick color at current mouse position and emit signal"""
        if not self.screen_pixmap:
            return

        desktop_geometry = QApplication.primaryScreen().virtualGeometry()
        mouse_x = self.mouse_pos.x() - desktop_geometry.x()
        mouse_y = self.mouse_pos.y() - desktop_geometry.y()

        screen_image = self.screen_pixmap.toImage()
        if screen_image.format() != screen_image.Format.Format_RGB32:
            screen_image = screen_image.convertToFormat(screen_image.Format.Format_RGB32)

        if 0 <= mouse_x < screen_image.width() and 0 <= mouse_y < screen_image.height():
            color = screen_image.pixelColor(mouse_x, mouse_y)
            hex_color = color.name()

            self.colorSelected.emit(hex_color)
            self.stop_color_picking()
        
    def paintEvent(self, event):
        """Paint a true 8x magnified preview centered on the mouse. 1 desktop pixel = 8 preview pixels. Center is color under mouse."""
        if not self.screen_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        screen_image = self.screen_pixmap.toImage()
        if screen_image.format() != screen_image.Format.Format_RGB32:
            screen_image = screen_image.convertToFormat(screen_image.Format.Format_RGB32)

        # Map mouse position to pixmap coordinates (handle multi-monitor)
        desktop_geometry = QApplication.primaryScreen().virtualGeometry()
        mouse_x = self.mouse_pos.x() - desktop_geometry.x()
        mouse_y = self.mouse_pos.y() - desktop_geometry.y()

        half_grid = self.grid_size // 2
        src_x = mouse_x - half_grid
        src_y = mouse_y - half_grid

        # Fill a region_img with gray, then copy valid screen pixels
        region_img = QImage(self.grid_size, self.grid_size, screen_image.format())
        region_img.fill(QColor(64, 64, 64))
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                sx = src_x + col
                sy = src_y + row
                if 0 <= sx < screen_image.width() and 0 <= sy < screen_image.height():
                    region_img.setPixel(col, row, screen_image.pixel(sx, sy))

        # Scale up by zoom_factor (should be integer)
        zoomed = region_img.scaled(self.grid_size * self.zoom_factor, self.grid_size * self.zoom_factor, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        # Draw the zoomed region at (20,20)
        painter.drawImage(20, 20, zoomed)

        # Draw grid lines (every zoom_factor pixels)
        painter.setPen(QPen(QColor(128, 128, 128, 80), 1))
        for i in range(self.grid_size + 1):
            x = 20 + (i * self.zoom_factor)
            y = 20 + (i * self.zoom_factor)
            painter.drawLine(x, 20, x, 20 + self.grid_size * self.zoom_factor)
            painter.drawLine(20, y, 20 + self.grid_size * self.zoom_factor, y)

        # Highlight center pixel (the one under the mouse) with high contrast
        center_x = 20 + (half_grid * self.zoom_factor)
        center_y = 20 + (half_grid * self.zoom_factor)
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawRect(center_x - 1, center_y - 1, self.zoom_factor + 2, self.zoom_factor + 2)
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawRect(center_x, center_y, self.zoom_factor, self.zoom_factor)


class ColorDropperAction(QAction):
    """
    A QAction that can be added to toolbars to trigger color picking.
    Emits colorPicked signal with hex color string.
    """
    colorPicked = pyqtSignal(str)
    
    def __init__(self, text="Pick Color", parent=None):
        super().__init__(text, parent)
        
        # Create color dropper widget
        self.color_dropper = ColorDropperWidget()
        self.color_dropper.colorSelected.connect(self.colorPicked.emit)
        
        # Connect action trigger to start color picking
        self.triggered.connect(self.start_picking)
        
        # Set icon (optional - you can set your own icon)
        self.setText("🎨 " + text)  # Using emoji as simple icon
        
    def start_picking(self):
        """Start the color picking process"""
        self.color_dropper.start_color_picking()


# Test version with colorful content for easier testing
class TestColorWidget(QWidget):
    """Widget with colorful content for testing the color picker"""
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 200)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw colorful test pattern
        colors = [
            QColor(255, 0, 0),    # Red
            QColor(0, 255, 0),    # Green  
            QColor(0, 0, 255),    # Blue
            QColor(255, 255, 0),  # Yellow
            QColor(255, 0, 255),  # Magenta
            QColor(0, 255, 255),  # Cyan
            QColor(128, 128, 128), # Gray
            QColor(255, 128, 0),  # Orange
        ]
        
        # Draw color squares
        square_size = 75
        for i, color in enumerate(colors):
            x = (i % 4) * square_size
            y = (i // 4) * square_size
            painter.fillRect(x, y, square_size, square_size, color)
            
        # Draw some text
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(10, 160, "Test different colors!")


# Example usage and demo
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Dropper Demo - Test Version")
        self.setGeometry(100, 100, 600, 500)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create color display label
        self.color_label = QLabel("No color selected")
        self.color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_label.setStyleSheet("""
            QLabel {
                border: 2px solid gray;
                border-radius: 5px;
                padding: 20px;
                font-size: 14px;
                background-color: white;
            }
        """)
        layout.addWidget(self.color_label)
        
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Create color dropper action
        self.color_dropper_action = ColorDropperAction("Pick Color", self)
        self.color_dropper_action.colorPicked.connect(self.on_color_picked)
        toolbar.addAction(self.color_dropper_action)
        
        # Add regular button as alternative
        pick_button = QPushButton("Pick Color (Button)")
        pick_button.clicked.connect(self.color_dropper_action.start_picking)
        layout.addWidget(pick_button)
        
        # Add test widget with colors
        test_widget = TestColorWidget()
        layout.addWidget(test_widget)
        
        # Instructions
        instructions = QLabel("""
        Instructions:
        1. Click the toolbar action or button to start color picking
        2. Move mouse around to see magnified preview
        3. Left-click to select a color
        4. Right-click or press Escape to cancel
        
        Note: On macOS, you may need to grant screen recording permissions 
        in System Preferences > Security & Privacy > Screen Recording
        for full-screen color picking to work.
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
    def on_color_picked(self, hex_color):
        """Handle color selection"""
        self.color_label.setText(f"Selected Color: {hex_color}")
        self.color_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid gray;
                border-radius: 5px;
                padding: 20px;
                font-size: 14px;
                background-color: {hex_color};
                color: {'white' if self.is_dark_color(hex_color) else 'black'};
            }}
        """)
        
    def is_dark_color(self, hex_color):
        """Determine if color is dark for text contrast"""
        color = QColor(hex_color)
        # Calculate luminance
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        return luminance < 0.5


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())