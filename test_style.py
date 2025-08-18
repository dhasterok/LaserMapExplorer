
"""
PyQt6 Test GUI for ObservableStyleDict
Demonstrates the observer pattern with style changes
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QLineEdit, QCheckBox,
    QGroupBox, QGridLayout, QColorDialog, QPushButton, QScrollArea,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont, QFontDatabase

# Import your classes (assuming they're in the same directory or properly installed)
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Any, Tuple
from abc import ABC, abstractmethod
from src.common.Observable import Observable


from typing import Callable
from collections import defaultdict

# Style options - moved outside class for efficiency
STYLE_OPTIONS = {
    "tick_dir": {
        "in": "in",
        "out": "out",
        "both": "both",
        "none": "none",
    },
    "scale_dir": {
        "none": "none",
        "horizontal": "horizontal",
        "vertical": "vertical",
    },
    "scale_location": {
        "northeast": "northeast",
        "northwest": "northwest",
        "southwest": "southwest",
        "southeast": "southeast",
    },
    "marker": {
        "o": "circle",
        "s": "square",
        "d": "diamond",
        "^": "triangle (up)",
        "v": "triangle (down)",
        "h": "hexagon",
        "p": "pentagon",
        "x": "x",
        "+": "plus",
    },
    "line_style": {
        "-": "solid",
        "--": "dashed",
        "-.": "dash-dot",
        ":": "dotted",
    },
    "cbar_dir": {
        "none": "none",
        "horizontal": "horizontal",
        "vertical": "vertical",
    },
    "xscale": {
        "linear": "linear",
        "log": "log",
        "discrete": "discrete",
    },
    "yscale": {
        "linear": "linear",
        "log": "log", 
        "discrete": "discrete",
    },
    "cscale": {
        "linear": "linear",
        "log": "log",
        "discrete": "discrete",
    },
    "cmap": {
        "viridis": "viridis",
        "plasma": "plasma",
        "RdBu": "RdBu",
        "RdYlBu": "RdYlBu",
    }
}


class ColormapComboBox(QComboBox):
    """Custom combobox for colormap selection with categorized options."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.populate_colormaps()
    
    def populate_colormaps(self):
        """Populate the combobox with categorized colormaps."""
        # Basic matplotlib colormaps (simplified list for demo)
        matplotlib_maps = [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis',
            'Blues', 'Greens', 'Reds', 'Oranges', 'Purples',
            'RdBu', 'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm',
            'seismic', 'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy',
            'gray', 'bone', 'pink', 'spring', 'summer', 'autumn', 'winter',
            'cool', 'hot', 'copper', 'jet', 'rainbow', 'nipy_spectral'
        ]
        
        # Add separator and matplotlib colormaps
        self.addItem("--- Matplotlib ---")
        self.model().item(self.count() - 1).setEnabled(False)
        
        for cmap in sorted(matplotlib_maps):
            self.addItem(cmap)
        
        # Add separator for custom colormaps
        self.addItem("--- Custom ---")
        self.model().item(self.count() - 1).setEnabled(False)
        
        # Placeholder for custom colormaps (you can populate this from your CSV)
        custom_maps = ['custom1', 'custom2']  # Replace with actual custom colormap loading
        for cmap in custom_maps:
            self.addItem(cmap)
    
    def setCurrentColormap(self, colormap_name: str):
        """Set the current colormap by name."""
        index = self.findText(colormap_name)
        if index >= 0:
            self.setCurrentIndex(index)#!/usr/bin/env python3

@dataclass
class PlotStyle:
    xfield_type: str = "none"
    yfield_type: str = "none"
    zfield_type: str = "none"
    cfield_type: str = "none"
    xfield: str = "none"
    yfield: str = "none"
    zfield: str = "none"
    cfield: str = "none"
    xlim: List[float] = field(default_factory=lambda: [0.0, 1.0])
    ylim: List[float] = field(default_factory=lambda: [0.0, 1.0])
    zlim: List[float] = field(default_factory=lambda: [0.0, 1.0])
    clim: List[float] = field(default_factory=lambda: [0.0, 1.0])
    xscale: str = "linear"
    yscale: str = "linear"
    zscale: str = "linear"
    cscale: str = "linear"
    xlabel: str = ""
    ylabel: str = ""
    zlabel: str = ""
    clabel: str = ""
    aspect_ratio: float = 1.0
    tick_dir: str = "out"
    font: str = ""
    font_size: float = 11.0
    scale_dir: str = "none"
    scale_location: str = "northeast"
    scale_length: str = ""
    overlay_color: str = "#ffffff"
    show_mass: bool = False
    marker: str = "o"
    marker_size: float = 6.0
    marker_color: str = "#1c75bc"
    marker_alpha: int = 30
    line_style: str = "-"
    line_width: float = 1.5
    line_multiplier: float = 1.0
    line_color: str = "#1c75bc"
    cmap: str = "viridis"
    cbar_reverse: bool = False
    cbar_dir: str = "vertical"
    resolution: int = 10

    @classmethod
    def option_pairs(cls, field_name: str) -> List[Tuple[str, str]]:
        """Return [(key, label), ...] for combobox population."""
        mapping = STYLE_OPTIONS.get(field_name, {})
        return list(mapping.items())

    @classmethod
    def option_labels(cls, field_name: str) -> List[str]:
        """Return just the display labels for a categorical field."""
        return list(STYLE_OPTIONS.get(field_name, {}).values())

    @classmethod
    def option_keys(cls, field_name: str) -> List[str]:
        """Return just the valid keys for a categorical field."""
        return list(STYLE_OPTIONS.get(field_name, {}).keys())

    @classmethod
    def key_for_label(cls, field_name: str, label: str) -> str:
        """Return the key for a given display label."""
        mapping = STYLE_OPTIONS.get(field_name, {})
        for key, value in mapping.items():
            if value == label:
                return key
        return label  # fallback to label if not found

    @classmethod
    def label_for_key(cls, field_name: str, key: str) -> str:
        """Return the display label for a given key."""
        return STYLE_OPTIONS.get(field_name, {}).get(key, str(key))


@dataclass
class ObservableStyleDict(Observable):
    styles: Dict[str, PlotStyle] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the Observable parent class after dataclass initialization."""
        super().__init__()

    def set_style(self, plot_type: str, style: PlotStyle):
        """Replace the entire style object for a plot type."""
        old_style = self.styles.get(plot_type)
        self.styles[plot_type] = style

        # Notify only for fields whose values actually changed
        for field_name, field_def in style.__dataclass_fields__.items():
            new_value = getattr(style, field_name)
            old_value = getattr(old_style, field_name) if old_style else None
            if new_value != old_value:
                self.notify_observers(f"style_changed.{field_name}",
                                      plot_type=plot_type,
                                      field_name=field_name,
                                      value=new_value)

    def update_style_field(self, plot_type: str, field_name: str, value):
        """Update a single field and notify only if the value actually changes."""
        style = self.styles.get(plot_type)
        if style and hasattr(style, field_name):
            current_value = getattr(style, field_name)
            if current_value != value:
                setattr(style, field_name, value)
                self.notify_observers(f"style_changed.{field_name}",
                                      plot_type=plot_type,
                                      field_name=field_name,
                                      value=value)


def create_default_observable_style_dict() -> ObservableStyleDict:
    """Create and return an ObservableStyleDict with all plot types and their customized settings."""
    style_dict = ObservableStyleDict()
    
    plot_types = [
        'field map', 'correlation', 'histogram', 'gradient map', 'scatter', 
        'heatmap', 'ternary map', 'TEC', 'radar', 'variance', 'basis vectors',
        'dimension scatter', 'dimension heatmap', 'dimension score map',
        'cluster map', 'cluster score map', 'cluster performance', 'profile', 'polygon'
    ]
    
    # Initialize all plot types with default PlotStyle
    for plot_type in plot_types:
        style_dict.styles[plot_type] = PlotStyle()
    
    # Apply customizations
    style_dict.styles['field map'].cmap = 'plasma'
    style_dict.styles['field map'].xfield = 'Xc'
    style_dict.styles['field map'].yfield = 'Yc'
    
    style_dict.styles['correlation'].aspect_ratio = 1.0
    style_dict.styles['correlation'].font_size = 8.0
    style_dict.styles['correlation'].cmap = 'RdBu'
    style_dict.styles['correlation'].clim = [-1.0, 1.0]
    
    style_dict.styles['scatter'].aspect_ratio = 1.0
    style_dict.styles['scatter'].xfield_type = 'Analyte'
    style_dict.styles['scatter'].yfield_type = 'Analyte'
    
    style_dict.styles['heatmap'].aspect_ratio = 1.0
    style_dict.styles['heatmap'].clim = [1.0, 1000.0]
    style_dict.styles['heatmap'].cscale = 'log'
    
    return style_dict


class ColorButton(QPushButton):
    """A button that displays and allows selection of colors."""
    colorChanged = pyqtSignal(str)
    
    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self._color = color
        self.clicked.connect(self.choose_color)
        self.update_display()
    
    def set_color(self, color: str):
        if color != self._color:
            self._color = color
            self.update_display()
    
    def get_color(self) -> str:
        return self._color
    
    def update_display(self):
        if self._color is None or self._color.lower() == 'none':
            self.setStyleSheet("background-color: none; border: 1px solid black;")
            self.setText("None")
        else:
            self.setStyleSheet(f"background-color: {self._color}; border: 1px solid black;")
            self.setText(self._color)
    
    def choose_color(self):
        color = QColorDialog.getColor(QColor(self._color) if self._color not in [None, 'none'] else QColor("#ffffff"), self)
        if color.isValid():
            self._color = color.name()
            self.update_display()
            self.colorChanged.emit(self._color)


class RangeWidget(QWidget):
    """Widget for editing range values like [min, max]."""
    valueChanged = pyqtSignal(list)
    
    def __init__(self, initial_values=[0.0, 1.0], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-999999, 999999)
        self.min_spin.setDecimals(3)
        self.min_spin.setValue(initial_values[0])
        self.min_spin.valueChanged.connect(self.emit_change)
        
        layout.addWidget(QLabel("Min:"))
        layout.addWidget(self.min_spin)
        
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-999999, 999999)
        self.max_spin.setDecimals(3)
        self.max_spin.setValue(initial_values[1])
        self.max_spin.valueChanged.connect(self.emit_change)
        
        layout.addWidget(QLabel("Max:"))
        layout.addWidget(self.max_spin)
    
    def set_values(self, values: List[float]):
        self.min_spin.blockSignals(True)
        self.max_spin.blockSignals(True)
        self.min_spin.setValue(values[0])
        self.max_spin.setValue(values[1])
        self.min_spin.blockSignals(False)
        self.max_spin.blockSignals(False)
    
    def get_values(self) -> List[float]:
        return [self.min_spin.value(), self.max_spin.value()]
    
    def emit_change(self):
        self.valueChanged.emit(self.get_values())


class StyleEditorWidget(QWidget):
    """Main widget for editing plot styles."""
    
    def __init__(self, style_dict: ObservableStyleDict, parent=None):
        super().__init__(parent)
        self.style_dict = style_dict
        self.current_plot_type = None
        self.widgets = {}
        self.default_font = self.get_default_font()
        
        self.setup_ui()
        self.setup_observers()
        
        # Set initial plot type
        if self.style_dict.styles:
            first_plot_type = list(self.style_dict.styles.keys())[0]
            self.plot_type_combo.setCurrentText(first_plot_type)
            self.on_plot_type_changed(first_plot_type)
    
    def get_default_font(self) -> str:
        """Get the default font from a preferred list."""
        default_fonts = ['Avenir', 'Futura', 'Candara', 'Myriad Pro', 'Myriad', 'Aptos',
                        'Calibri', 'Helvetica', 'Arial', 'Verdana', 'Segoe UI',
                        'Arial', 'Helvetica', 'Ubuntu', 'Calibri', 'DejaVu Sans',
                        'Verdana', 'Tahoma', 'Aptos']
        
        available_fonts = QFontDatabase.families()
        for font in default_fonts:
            if font in available_fonts:
                return QFont(font, 11).family()
        
        # Fallback to system default
        return QFont().family()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Plot type selection
        plot_type_group = QGroupBox("Plot Type")
        plot_type_layout = QHBoxLayout(plot_type_group)
        
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(sorted(self.style_dict.styles.keys()))
        self.plot_type_combo.currentTextChanged.connect(self.on_plot_type_changed)
        plot_type_layout.addWidget(QLabel("Type:"))
        plot_type_layout.addWidget(self.plot_type_combo)
        plot_type_layout.addStretch()
        
        layout.addWidget(plot_type_group)
        
        # Scrollable area for style controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.style_widget = QWidget()
        self.style_layout = QGridLayout(self.style_widget)
        scroll_area.setWidget(self.style_widget)
        
        layout.addWidget(scroll_area)
        
        self.create_style_controls()
    
    def create_style_controls(self):
        """Create all the style editing controls."""
        row = 0
        
        # Field types
        field_types_group = QGroupBox("Field Types")
        field_types_layout = QGridLayout(field_types_group)
        
        field_type_options = ["none", "Analyte", "PCA score", "Cluster", "Custom"]
        
        for i, field_name in enumerate(['xfield_type', 'yfield_type', 'zfield_type', 'cfield_type']):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            combo = QComboBox()
            combo.addItems(field_type_options)
            # Store the key-to-label mapping for this combo
            combo.setProperty('field_name', field_name)
            combo.currentTextChanged.connect(
                lambda label_text, fn=field_name: self.on_categorical_field_changed(fn, label_text)
            )
            self.widgets[field_name] = combo
            field_types_layout.addWidget(label, i // 2, (i % 2) * 2)
            field_types_layout.addWidget(combo, i // 2, (i % 2) * 2 + 1)
        
        self.style_layout.addWidget(field_types_group, row, 0, 1, 2)
        row += 1
        
        # Fields
        fields_group = QGroupBox("Field Names")
        fields_layout = QGridLayout(fields_group)
        
        for i, field_name in enumerate(['xfield', 'yfield', 'zfield', 'cfield']):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            line_edit = QLineEdit()
            line_edit.textChanged.connect(
                lambda value, fn=field_name: self.on_field_changed(fn, value)
            )
            self.widgets[field_name] = line_edit
            fields_layout.addWidget(label, i // 2, (i % 2) * 2)
            fields_layout.addWidget(line_edit, i // 2, (i % 2) * 2 + 1)
        
        self.style_layout.addWidget(fields_group, row, 0, 1, 2)
        row += 1
        
        # Limits (ranges)
        limits_group = QGroupBox("Limits")
        limits_layout = QGridLayout(limits_group)
        
        for i, field_name in enumerate(['xlim', 'ylim', 'zlim', 'clim']):
            label = QLabel(f"{field_name.replace('lim', ' limit').title()}:")
            range_widget = RangeWidget()
            range_widget.valueChanged.connect(
                lambda value, fn=field_name: self.on_field_changed(fn, value)
            )
            self.widgets[field_name] = range_widget
            limits_layout.addWidget(label, i, 0)
            limits_layout.addWidget(range_widget, i, 1)
        
        self.style_layout.addWidget(limits_group, row, 0, 1, 2)
        row += 1
        
        # Scales with options
        scales_group = QGroupBox("Scales")
        scales_layout = QGridLayout(scales_group)
        
        for i, field_name in enumerate(['xscale', 'yscale', 'cscale']):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            combo = QComboBox()
            labels = PlotStyle.option_labels(field_name)
            if labels:
                combo.addItems(labels)
            else:
                combo.addItems(['linear', 'log', 'discrete'])
            combo.setProperty('field_name', field_name)
            combo.currentTextChanged.connect(
                lambda label_text, fn=field_name: self.on_categorical_field_changed(fn, label_text)
            )
            self.widgets[field_name] = combo
            scales_layout.addWidget(label, i // 2, (i % 2) * 2)
            scales_layout.addWidget(combo, i // 2, (i % 2) * 2 + 1)
        
        self.style_layout.addWidget(scales_group, row, 0, 1, 2)
        row += 1
        
        # Numeric values
        numeric_group = QGroupBox("Numeric Properties")
        numeric_layout = QGridLayout(numeric_group)
        
        numeric_fields = {
            'aspect_ratio': (0.1, 10.0, 2),
            'font_size': (6.0, 72.0, 1),
            'marker_size': (1.0, 50.0, 1),
            'line_width': (0.0, 10.0, 1),
            'line_multiplier': (0.1, 10.0, 2),
            'marker_alpha': (0, 255, 0),
            'resolution': (1, 100, 0)
        }
        
        for i, (field_name, (min_val, max_val, decimals)) in enumerate(numeric_fields.items()):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            if decimals == 0:
                spin = QSpinBox()
                spin.setRange(int(min_val), int(max_val))
            else:
                spin = QDoubleSpinBox()
                spin.setRange(min_val, max_val)
                spin.setDecimals(decimals)
            
            spin.valueChanged.connect(
                lambda value, fn=field_name: self.on_field_changed(fn, value)
            )
            self.widgets[field_name] = spin
            numeric_layout.addWidget(label, i // 2, (i % 2) * 2)
            numeric_layout.addWidget(spin, i // 2, (i % 2) * 2 + 1)
        
        self.style_layout.addWidget(numeric_group, row, 0, 1, 2)
        row += 1
        
        # Colors
        colors_group = QGroupBox("Colors")
        colors_layout = QGridLayout(colors_group)
        
        color_fields = ['marker_color', 'line_color', 'overlay_color']
        for i, field_name in enumerate(color_fields):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            color_button = ColorButton()
            color_button.colorChanged.connect(
                lambda value, fn=field_name: self.on_field_changed(fn, value)
            )
            self.widgets[field_name] = color_button
            colors_layout.addWidget(label, i, 0)
            colors_layout.addWidget(color_button, i, 1)
        
        self.style_layout.addWidget(colors_group, row, 0, 1, 2)
        row += 1
        
        # Combobox options
        combo_group = QGroupBox("Style Options")
        combo_layout = QGridLayout(combo_group)
        
        combo_fields = ['tick_dir', 'scale_dir', 'scale_location', 'marker', 'line_style', 'cbar_dir']
        for i, field_name in enumerate(combo_fields):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            combo = QComboBox()
            labels = PlotStyle.option_labels(field_name)
            if labels:
                combo.addItems(labels)
            combo.setProperty('field_name', field_name)
            combo.currentTextChanged.connect(
                lambda label_text, fn=field_name: self.on_categorical_field_changed(fn, label_text)
            )
            self.widgets[field_name] = combo
            combo_layout.addWidget(label, i // 3, (i % 3) * 2)
            combo_layout.addWidget(combo, i // 3, (i % 3) * 2 + 1)
        
        # Special colormap combo
        cmap_label = QLabel("Colormap:")
        cmap_combo = ColormapComboBox()
        cmap_combo.currentTextChanged.connect(
            lambda value: self.on_field_changed('cmap', value)
        )
        self.widgets['cmap'] = cmap_combo
        combo_layout.addWidget(cmap_label, len(combo_fields) // 3, 0)
        combo_layout.addWidget(cmap_combo, len(combo_fields) // 3, 1)
        
        self.style_layout.addWidget(combo_group, row, 0, 1, 2)
        row += 1
        
        # Checkboxes
        checkbox_group = QGroupBox("Boolean Options")
        checkbox_layout = QGridLayout(checkbox_group)
        
        bool_fields = ['show_mass', 'cbar_reverse']
        for i, field_name in enumerate(bool_fields):
            checkbox = QCheckBox(field_name.replace('_', ' ').title())
            checkbox.toggled.connect(
                lambda checked, fn=field_name: self.on_field_changed(fn, checked)
            )
            self.widgets[field_name] = checkbox
            checkbox_layout.addWidget(checkbox, i // 2, i % 2)
        
        self.style_layout.addWidget(checkbox_group, row, 0, 1, 2)
        
        # Labels
        labels_group = QGroupBox("Labels")
        labels_layout = QGridLayout(labels_group)
        
        label_fields = ['xlabel', 'ylabel', 'zlabel', 'clabel', 'scale_length']
        for i, field_name in enumerate(label_fields):
            label = QLabel(f"{field_name.replace('_', ' ').title()}:")
            line_edit = QLineEdit()
            line_edit.textChanged.connect(
                lambda value, fn=field_name: self.on_field_changed(fn, value)
            )
            self.widgets[field_name] = line_edit
            labels_layout.addWidget(label, i // 2, (i % 2) * 2)
            labels_layout.addWidget(line_edit, i // 2, (i % 2) * 2 + 1)
        
        # Font field with default
        font_label = QLabel("Font:")
        font_edit = QLineEdit()
        font_edit.setPlaceholderText(self.default_font)
        font_edit.textChanged.connect(
            lambda value: self.on_field_changed('font', value)
        )
        self.widgets['font'] = font_edit
        labels_layout.addWidget(font_label, len(label_fields) // 2, 0)
        labels_layout.addWidget(font_edit, len(label_fields) // 2, 1)
        
        row += 1
        self.style_layout.addWidget(labels_group, row, 0, 1, 2)
    
    def setup_observers(self):
        """Set up observers for style changes."""
        # Observe all style change events
        for field_name in PlotStyle.__dataclass_fields__.keys():
            self.style_dict.add_observer(
                f"style_changed.{field_name}",
                self.on_style_changed
            )
    
    def on_plot_type_changed(self, plot_type: str):
        """Handle plot type selection change."""
        self.current_plot_type = plot_type
        self.update_widgets_from_style()
    
    def on_categorical_field_changed(self, field_name: str, label_text: str):
        """Handle categorical field changes, converting display label to internal key."""
        if self.current_plot_type:
            # Convert display label back to internal key
            key = PlotStyle.key_for_label(field_name, label_text)
            self.style_dict.update_style_field(self.current_plot_type, field_name, key)
    
    def on_field_changed(self, field_name: str, value):
        """Handle non-categorical field value changes from UI widgets."""
        if self.current_plot_type:
            self.style_dict.update_style_field(self.current_plot_type, field_name, value)
    
    def on_style_changed(self, *args, **kwargs):
        """Handle style change notifications from the observable."""
        plot_type = kwargs.get('plot_type')
        if plot_type == self.current_plot_type:
            # Update the specific widget that changed
            field_name = kwargs.get('field_name')
            value = kwargs.get('value')
            if field_name:
                self.update_widget(field_name, value)
    
    def update_widgets_from_style(self):
        """Update all widgets to reflect the current style."""
        if not self.current_plot_type:
            return
        
        style = self.style_dict.styles[self.current_plot_type]
        for field_name in PlotStyle.__dataclass_fields__.keys():
            value = getattr(style, field_name)
            self.update_widget(field_name, value)
    
    def update_widget(self, field_name: str, value):
        """Update a specific widget with a new value."""
        widget = self.widgets.get(field_name)
        if not widget:
            return
        
        # Block signals to prevent recursive updates
        widget.blockSignals(True)
        
        try:
            if isinstance(widget, QComboBox):
                # Check if this is a categorical field that needs label lookup
                field_name = widget.property('field_name')
                if field_name and field_name in STYLE_OPTIONS:
                    # This is a categorical field - show the display label
                    label = PlotStyle.label_for_key(field_name, str(value))
                    index = widget.findText(label)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                else:
                    # Regular combobox - use value directly
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, ColorButton):
                widget.set_color(str(value) if value is not None else 'none')
            elif isinstance(widget, ColormapComboBox):
                widget.setCurrentColormap(str(value))
            elif isinstance(widget, RangeWidget):
                widget.set_values(list(value))
        finally:
            widget.blockSignals(False)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plot Style Dictionary Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create the style dictionary
        self.style_dict = create_default_observable_style_dict()
        
        # Create and set the central widget
        self.style_editor = StyleEditorWidget(self.style_dict)
        self.setCentralWidget(self.style_editor)


def main():
    app = QApplication(sys.argv)
    
    # Set a nice style
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())