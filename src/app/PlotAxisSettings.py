from dataclasses import dataclass, field
from typing import Dict, List, Optional

# All possible axes
AXES = ["x", "y", "z", "c"]

@dataclass
class AxisSettings:
    enabled: bool = False
    scale: bool = False
    widgets: bool = False
    lim_precision: Optional[int] = None
    add_none: bool = False
    spinbox: bool = False

@dataclass
class PlotSettings:
    axes: Dict[str, AxisSettings] = field(default_factory=dict)
    field_type: Optional[List[str]] = None     # available field types for x/y/z
    cfield_type: Optional[List[str]] = None    # available field types for c

    # def get_field_types(plot: PlotSettings, axis: str) -> List[str]:
    #     if axis == "c" and plot.cfield_type is not None:
    #         return plot.cfield_type
    #     elif plot.field_type is not None:
    #         return plot.field_type
    #     else:
    #         return all_field_types()  # your existing fallback

plot_axis_dict: Dict[str, PlotSettings] = {
    "": PlotSettings(
        axes={
            "x": AxisSettings(False, False, False, None, False, False),
            "y": AxisSettings(False, False, False, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(False, False, False, None, False, False),
        },
        field_type=['']
    ),
    "field map": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        }
    ),
    "gradient map": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','Special']
    ),
    "correlation": PlotSettings(
        axes={
            "x": AxisSettings(False, False, False, None, False, False),
            "y": AxisSettings(False, False, False, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, None, True, True),
        },
        cfield_type=['Cluster']
    ),
    "histogram": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, 3, False, True),
            "y": AxisSettings(False, True, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, True, True),
        },
        cfield_type=['Cluster']
    ),
    "scatter": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, 3, False, True),
            "y": AxisSettings(True, True, True, 3, False, True),
            "z": AxisSettings(True, True, True, 3, True,  True),
            "c": AxisSettings(True, True, True, 3, True,  True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
    ),
    "heatmap": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, 3, False, True),
            "y": AxisSettings(True, True, True, 3, False, True),
            "z": AxisSettings(True, True, True, 3, True,  True),
            "c": AxisSettings(False, True, True, 3, False,  False),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
    ),
    "ternary map": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, None, False, True),
            "y": AxisSettings(True, True, True, None, False, True),
            "z": AxisSettings(True, False, False, None, False, True),
            "c": AxisSettings(False, False, False, 3, False, False),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Special']
    ),
    "TEC": PlotSettings(
        axes={
            "x": AxisSettings(False, False, False, None, False, False),
            "y": AxisSettings(False, True, True, 3, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, False, None, True, True),
        },
        field_type=['Analyte'],
        cfield_type=['Cluster']
    ),
    "radar": PlotSettings(
        axes={
            "x": AxisSettings(False, True, False, None, False, False),
            "y": AxisSettings(False, False, False, 3, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, False, None, True, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Special']
    ),
    "variance": PlotSettings(
        axes={
            "x": AxisSettings(False, False, False, None, False, False),
            "y": AxisSettings(False, False, False, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(False, False, True, None, False, False),
        }
    ),
    "basis vectors": PlotSettings(
        axes={
            "x": AxisSettings(False, False, False, None, False, True),
            "y": AxisSettings(False, False, False, None, False, True),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(False, False, False, None, False, False),
        }
    ),
    "dimension score map": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        },
        field_type=['PCA score']
    ),
    "dimension scatter": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, 3, False, True),
            "y": AxisSettings(True, True, True, 3, False, True),
            "z": AxisSettings(False, True, True, 3, False, False),
            "c": AxisSettings(True, True, True, 3, True, True),
        },
        field_type=['PCA score']
    ),
    "dimension heatmap": PlotSettings(
        axes={
            "x": AxisSettings(True, True, True, 3, False, True),
            "y": AxisSettings(True, True, True, 3, False, True),
            "z": AxisSettings(False, True, True, 3, False, False),
            "c": AxisSettings(False, True, True, 3, False, False),
        },
        field_type=['PCA score']
    ),
    "cluster map": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, False, 3, False, False),
        },
        field_type=['Cluster']
    ),
    "cluster score map": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        },
        field_type=['Cluster score']
    ),
    "cluster performance": PlotSettings(
        axes={
            "x": AxisSettings(False, True, True, 3, False, False),
            "y": AxisSettings(False, True, True, 3, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, False, None, False, False),
        },
        field_type=['Cluster']
    ),
    "profile": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
    ),
    "polygon": PlotSettings(
        axes={
            "x": AxisSettings(False, False, True, None, False, False),
            "y": AxisSettings(False, False, True, None, False, False),
            "z": AxisSettings(False, False, False, None, False, False),
            "c": AxisSettings(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
    ),
}