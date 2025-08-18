from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Any
from src.common.Observable import Observable

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
    scale_length: str | None = None
    overlay_color: str = "#ffffff"
    show_mass: bool = False
    marker: str = "circle"
    marker_size: float = 6.0
    marker_color: str = "#1c75bc"
    marker_alpha: int = 30
    line_style: str = "solid"
    line_width: float = 1.5
    line_multiplier: float = 1.0
    line_color: str = "#1c75bc"
    cmap: str = "viridis"
    cbar_reverse: bool = False
    cbar_dir: str = "vertical"
    resolution: int = 10

    OPTIONS: ClassVar[Dict[str, Dict[str, str]]] = {
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
    }

    @classmethod
    def normalize_and_validate(cls, field_name: str, value: Any) -> Any:
        # Categorical fields: ensure value is in OPTIONS
        if field_name in cls.OPTIONS:
            allowed = cls.OPTIONS[field_name]
            if value not in allowed:
                raise ValueError(f"{field_name} must be one of {list(allowed.keys())}, got {value!r}")
            return value

        # Range-like fields: exactly two numbers, store as tuple[float, float]
        if field_name in ("xlim", "ylim", "zlim", "clim"):
            if not (isinstance(value, (list, tuple)) and len(value) == 2 and
                    all(isinstance(v, (int, float)) for v in value)):
                raise ValueError(f"{field_name} must be exactly two numbers [min, max], got {value!r}")
            return (float(value[0]), float(value[1]))

        # No special rules
        return value

    # ---- UI helpers ----
    @classmethod
    def option_pairs(cls, field_name: str) -> List[Tuple[str, str]]:
        """Return [(value, label), ...] for combobox population."""
        mapping = cls.OPTIONS.get(field_name, {})
        return list(mapping.items())

    @classmethod
    def option_values(cls, field_name: str) -> List[str]:
        """Return just the valid values for a categorical field."""
        return list(cls.OPTIONS.get(field_name, {}).keys())

    @classmethod
    def label_for(cls, field_name: str, value: str) -> str:
        """Return the display label for a given value (value itself if none)."""
        return cls.OPTIONS.get(field_name, {}).get(value, str(value))

@dataclass
class ObservableStyleDict(Observable):
    styles: Dict[str, PlotStyle] = field(default_factory=dict)

    def set_style(self, plot_type: str, style: PlotStyle):
        """Replace the entire style object for a plot type.
        Sends notifications for each field that changes value.
        """
        old_style = self.styles.get(plot_type)
        self.styles[plot_type] = style

        # Notify only for fields whose values actually changed
        for field_name, field_def in style.__dataclass_fields__.items():
            new_value = getattr(style, field_name)
            old_value = getattr(old_style, field_name) if old_style else None
            if new_value != old_value:
                self.notify_observers(f"style_changed.{field_name}",
                                      plot_type=plot_type,
                                      value=new_value)

    def update_style_field(self, plot_type: str, field_name: str, value):
        """Update a single field and notify only if the value actually changes."""
        style = self.styles.get(plot_type)
        if style and hasattr(style, field_name):
            current_value = getattr(style, field_name)
            if current_value != value:  # Only notify if value changes
                setattr(style, field_name, value)
                self.notify_observers(f"style_changed.{field_name}",
                                      plot_type=plot_type,
                                      value=value)

def default_style_dict() -> ObservableStyleDict:
    """Create and return an ObservableStyleDict with all plot types and their customized settings."""
    
    # Create the observable style dictionary
    style_dict = ObservableStyleDict()
    
    # Define all plot types
    plot_types = [
        'field map', 'correlation', 'histogram', 'gradient map', 'scatter', 
        'heatmap', 'ternary map', 'TEC', 'radar', 'variance', 'basis vectors',
        'dimension scatter', 'dimension heatmap', 'dimension score map',
        'cluster map', 'cluster score map', 'cluster performance', 'profile', 'polygon'
    ]
    
    # Initialize all plot types with default PlotStyle
    for plot_type in plot_types:
        style_dict.styles[plot_type] = PlotStyle()
    
    # Customize specific plot types
    
    # Field map
    style_dict.styles['field map'].cmap = 'plasma'
    style_dict.styles['field map'].xfield = 'Xc'
    style_dict.styles['field map'].yfield = 'Yc'
    
    # Correlation
    style_dict.styles['correlation'].aspect_ratio = 1.0
    style_dict.styles['correlation'].font_size = 8.0
    style_dict.styles['correlation'].cmap = 'RdBu'
    style_dict.styles['correlation'].cbar_dir = 'vertical'
    style_dict.styles['correlation'].clim = [-1.0, 1.0]
    
    # Basis vectors
    style_dict.styles['basis vectors'].aspect_ratio = 1.0
    style_dict.styles['basis vectors'].cmap = 'RdBu'
    style_dict.styles['basis vectors'].clim = [-1.0, 1.0]
    
    # Gradient map
    style_dict.styles['gradient map'].cmap = 'RdYlBu'
    style_dict.styles['gradient map'].xfield = 'Xc'
    style_dict.styles['gradient map'].yfield = 'Yc'
    
    # Cluster score map
    style_dict.styles['cluster score map'].cmap = 'plasma'
    style_dict.styles['cluster score map'].xfield = 'Xc'
    style_dict.styles['cluster score map'].yfield = 'Yc'
    
    # Dimension score map
    style_dict.styles['dimension score map'].cmap = 'viridis'
    style_dict.styles['dimension score map'].xfield = 'Xc'
    style_dict.styles['dimension score map'].yfield = 'Yc'
    
    # Cluster map
    style_dict.styles['cluster map'].cscale = 'discrete'
    style_dict.styles['cluster map'].marker_alpha = 100
    style_dict.styles['cluster map'].cfield_type = 'Cluster'  # Note: mapped from 'FieldType'
    
    # Cluster performance
    style_dict.styles['cluster performance'].aspect_ratio = 0.62
    
    # Scatter
    style_dict.styles['scatter'].aspect_ratio = 1.0
    style_dict.styles['scatter'].xfield_type = 'Analyte'
    style_dict.styles['scatter'].yfield_type = 'Analyte'
    style_dict.styles['scatter'].zfield_type = 'none'
    style_dict.styles['scatter'].cfield_type = 'none'
    
    # Heatmap
    style_dict.styles['heatmap'].aspect_ratio = 1.0
    style_dict.styles['heatmap'].clim = [1.0, 1000.0]
    style_dict.styles['heatmap'].cscale = 'log'
    style_dict.styles['heatmap'].xfield_type = 'Analyte'
    style_dict.styles['heatmap'].yfield_type = 'Analyte'
    
    # TEC
    style_dict.styles['TEC'].aspect_ratio = 0.62
    
    # Variance
    style_dict.styles['variance'].aspect_ratio = 0.62
    style_dict.styles['variance'].font_size = 8.0
    
    # Dimension scatter
    style_dict.styles['dimension scatter'].line_color = '#4d4d4d'
    style_dict.styles['dimension scatter'].line_width = 0.5
    style_dict.styles['dimension scatter'].aspect_ratio = 1.0
    style_dict.styles['dimension scatter'].xfield_type = 'PCA score'
    style_dict.styles['dimension scatter'].yfield_type = 'PCA score'
    
    # Dimension heatmap
    style_dict.styles['dimension heatmap'].aspect_ratio = 1.0
    style_dict.styles['dimension heatmap'].line_color = '#ffffff'
    style_dict.styles['dimension heatmap'].xfield_type = 'PCA score'
    style_dict.styles['dimension heatmap'].yfield_type = 'PCA score'
    
    # Histogram
    style_dict.styles['histogram'].aspect_ratio = 0.62
    style_dict.styles['histogram'].line_width = 0.0
    style_dict.styles['histogram'].xfield_type = 'Analyte'
    style_dict.styles['histogram'].cfield_type = 'none'
    
    # Profile
    style_dict.styles['profile'].aspect_ratio = 0.62
    style_dict.styles['profile'].line_width = 1.0
    style_dict.styles['profile'].marker_size = 12.0
    style_dict.styles['profile'].marker_color = '#d3d3d3'
    style_dict.styles['profile'].line_color = '#d3d3d3'
    
    return style_dict