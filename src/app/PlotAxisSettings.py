"""
Plot axis configuration module.

This module defines the schema and settings that control axis-related
UI elements and field type options for each supported plot type.

Classes
-------
AxisControls
    Flags and options controlling the availability of UI elements
    (scales, widgets, spinboxes, etc.) for a single axis.
PlotSettings
    Grouped settings for a single plot type, mapping each axis
    (``'x'``, ``'y'``, ``'z'``, ``'c'``) to its AxisControls and
    specifying the allowed field types.

Constants
---------
AXES : list of str
    List of all possible axis identifiers: ``["x", "y", "z", "c"]``.

Variables
---------
axis_settings_dict : dict of str -> PlotSettings
    Dictionary mapping plot type names (e.g., ``"scatter"``,
    ``"heatmap"``, ``"field map"``) to their corresponding
    PlotSettings. This serves as the central lookup table for
    configuring which axes, fields, and controls are available
    for each plot type.

Created on Wed Aug 27 2025

@author: Shavin Kaluthantri and Derrick Hasterok
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# All possible axes
AXES = ["x", "y", "z", "c"]

@dataclass
class AxisControls:
    """
    Configuration flags and options for controlling axis-related UI elements.

    This class defines which controls (scale, widgets, spinboxes, etc.)
    are enabled for a given axis in the plotting interface.

    Attributes
    ----------
    enabled : bool, default=False
        Whether the axis is active and its controls should be displayed.
    scale : bool, default=False
        Whether a scale (e.g., linear/log) selection is available for this axis.
    widgets : bool, default=False
        Whether additional widgets associated with this axis are available.
    lim_precision : int or None, optional
        Precision (number of decimal places) for axis limit controls.
        If None, no precision override is applied.
    add_none : bool, default=False
        Whether to include a ``'none'`` option in the field selection dropdown.
    spinbox : bool, default=False
        Whether a spinbox control is available for this axis.
    """
    enabled: bool = False
    scale: bool = False
    widgets: bool = False
    lim_precision: Optional[int] = None
    add_none: bool = False
    spinbox: bool = False

@dataclass
class PlotSettings:
    """
    Settings for plot configuration, including axis controls and field types.

    This class groups together axis-specific controls and the allowed
    field types for a given plot type.

    Attributes
    ----------
    axes : dict of str -> AxisControls
        A mapping of axis identifiers (``'x'``, ``'y'``, ``'z'``, ``'c'``)
        to their corresponding axis control settings.
    field_type : list of str, optional
        List of valid field types for the x/y/z axes.
        If None, all field types are considered valid.
    cfield_type : list of str, optional
        List of valid field types for the color axis (``'c'``).
        If None, all field types are considered valid.
    """
    axes: Dict[str, AxisControls] = field(default_factory=dict)
    field_type: Optional[List[str]] = None     # available field types for x/y/z
    cfield_type: Optional[List[str]] = None    # available field types for c


# create dictionary for setting axis controls
axis_settings_dict: Dict[str, PlotSettings] = {
    "": PlotSettings(
        axes={
            "x": AxisControls(False, False, False, None, False, False),
            "y": AxisControls(False, False, False, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(False, False, False, None, False, False),
        },
        field_type=['']
    ),
    "field map": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        }
    ),
    "gradient map": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','Special']
    ),
    "correlation": PlotSettings(
        axes={
            "x": AxisControls(False, False, False, None, False, False),
            "y": AxisControls(False, False, False, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, None, True, True),
        },
        cfield_type=['Cluster']
    ),
    "histogram": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, 3, False, True),
            "y": AxisControls(False, True, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, True, True),
        },
        cfield_type=['Cluster']
    ),
    "scatter": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, 3, False, True),
            "y": AxisControls(True, True, True, 3, False, True),
            "z": AxisControls(True, True, True, 3, True,  True),
            "c": AxisControls(True, True, True, 3, True,  True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
    ),
    "heatmap": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, 3, False, True),
            "y": AxisControls(True, True, True, 3, False, True),
            "z": AxisControls(True, True, True, 3, True,  True),
            "c": AxisControls(False, True, True, 3, False,  False),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
    ),
    "ternary map": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, None, False, True),
            "y": AxisControls(True, True, True, None, False, True),
            "z": AxisControls(True, False, False, None, False, True),
            "c": AxisControls(False, False, False, 3, False, False),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Special']
    ),
    "TEC": PlotSettings(
        axes={
            "x": AxisControls(False, False, False, None, False, False),
            "y": AxisControls(False, True, True, 3, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, False, None, True, True),
        },
        field_type=['Analyte'],
        cfield_type=['Cluster']
    ),
    "radar": PlotSettings(
        axes={
            "x": AxisControls(False, True, False, None, False, False),
            "y": AxisControls(False, False, False, 3, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, False, None, True, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Special']
    ),
    "variance": PlotSettings(
        axes={
            "x": AxisControls(False, False, False, None, False, False),
            "y": AxisControls(False, False, False, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(False, False, True, None, False, False),
        }
    ),
    "basis vectors": PlotSettings(
        axes={
            "x": AxisControls(False, False, False, None, False, True),
            "y": AxisControls(False, False, False, None, False, True),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(False, False, False, None, False, False),
        }
    ),
    "dimension score map": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        },
        field_type=['PCA score']
    ),
    "dimension scatter": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, 3, False, True),
            "y": AxisControls(True, True, True, 3, False, True),
            "z": AxisControls(False, True, True, 3, False, False),
            "c": AxisControls(True, True, True, 3, True, True),
        },
        field_type=['PCA score']
    ),
    "dimension heatmap": PlotSettings(
        axes={
            "x": AxisControls(True, True, True, 3, False, True),
            "y": AxisControls(True, True, True, 3, False, True),
            "z": AxisControls(False, True, True, 3, False, False),
            "c": AxisControls(False, True, True, 3, False, False),
        },
        field_type=['PCA score']
    ),
    "cluster map": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, False, 3, False, False),
        },
        field_type=['Cluster']
    ),
    "cluster score map": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        },
        field_type=['Cluster score']
    ),
    "cluster performance": PlotSettings(
        axes={
            "x": AxisControls(False, True, True, 3, False, False),
            "y": AxisControls(False, True, True, 3, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, False, None, False, False),
        },
        field_type=['Cluster']
    ),
    "profile": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
    ),
    "polygon": PlotSettings(
        axes={
            "x": AxisControls(False, False, True, None, False, False),
            "y": AxisControls(False, False, True, None, False, False),
            "z": AxisControls(False, False, False, None, False, False),
            "c": AxisControls(True, False, True, 3, False, True),
        },
        field_type=['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
    ),
}