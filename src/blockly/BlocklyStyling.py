import src.common.format as fmt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import src.common.csvdict as csvdict
# Removed unused imports: get_hex_color, get_rgb_color
from src.app.config import BASEDIR
from src.app.StyleToolbox import StyleData, StyleTheme
from src.common.ScheduleTimer import Scheduler
from src.common.Logger import auto_log_methods, log

@auto_log_methods(logger_key='Style')
class StylingBlocks(StyleData, StyleTheme):
    def __init__(self, parent):
        self.ui = parent
        self.app_data = parent.app_data

        super().__init__(self)

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.add_observer("plot_type", self.update_plot_type)
        self.add_observer("xlim", self.update_axis_limits)
        self.add_observer("xlabel", self.update_axis_label)
        self.add_observer("xscale", self.update_axis_scale)
        self.add_observer("ylim", self.update_axis_limits)
        self.add_observer("ylabel", self.update_axis_label)
        self.add_observer("yscale", self.update_axis_scale)
        self.add_observer("zlim", self.update_axis_limits)
        self.add_observer("zlabel", self.update_axis_label)
        self.add_observer("zscale", self.update_axis_scale)
        self.add_observer("aspect_ratio", self.update_aspect_ratio)
        self.add_observer("tick_dir", self.update_tick_dir)
        self.add_observer("font_family", self.update_font_family)
        self.add_observer("font_size", self.update_font_size)
        self.add_observer("scale_dir", self.update_scale_direction)
        self.add_observer("scale_location", self.update_scale_location)
        self.add_observer("scale_length", self.update_scale_length)
        self.add_observer("overlay_color", self.update_overlay_color)
        self.add_observer("show_mass", self.update_show_mass)
        self.add_observer("marker_symbol", self.update_marker_symbol)
        self.add_observer("marker_size", self.update_marker_size)
        self.add_observer("marker_color", self.update_marker_color)
        self.add_observer("marker_alpha", self.update_marker_transparency)
        self.add_observer("line_width", self.update_line_width)
        self.add_observer("length_multiplier", self.update_length_multiplier)
        self.add_observer("line_color", self.update_line_color)
        self.add_observer("cmap", self.update_field_colormap)
        self.add_observer("cbar_reverse", self.update_cbar_reverse)
        self.add_observer("cbar_direction", self.update_cbar_direction)
        self.add_observer("clim", self.update_axis_limits)
        self.add_observer("clabel", self.update_axis_label)
        self.add_observer("cscale", self.update_axis_scale)
        self.add_observer("resolution", self.update_resolution)

        # ternary maps
        self.ternaryColormapChanged.connect(lambda cmap: self.update_ternary_colormap(cmap))
        self.ternaryColorChanged.connect(lambda ax, color: self.update_ternary_color(ax, color))




    


    def update_axis_limits(self,style_dict, field =None):
        # Check if user changed XLim, YLim, ZLim, or CLim
        if "XLim" in style_dict:
            lowerVal = style_dict["XLim"][0]
            upperVal = style_dict["XLim"][1]
            self.axis_limit_edit_callback("x", 0, float(lowerVal), field = 'X', ui_update=False)
            self.axis_limit_edit_callback("x", 1, float(upperVal), field = 'X', ui_update=False)

        if "YLim" in style_dict:
            lowerVal = style_dict["YLim"][0]
            upperVal = style_dict["YLim"][1]
            self.axis_limit_edit_callback("y", 0, float(lowerVal), field = 'Y', ui_update=False)
            self.axis_limit_edit_callback("y", 1, float(upperVal), field = 'Y', ui_update=False)

        if "ZLim" in style_dict:
            lowerVal = style_dict["ZLim"][0]
            upperVal = style_dict["ZLim"][1]
            self.axis_limit_edit_callback("z", 0, float(lowerVal), ui_update=False)
            self.axis_limit_edit_callback("z", 1, float(upperVal), ui_update=False)

        if "CLim" in style_dict:
            lowerVal = style_dict["CLim"][0]
            upperVal = style_dict["CLim"][1]
            self.axis_limit_edit_callback("c", 0, float(lowerVal), field, ui_update=False)
            self.axis_limit_edit_callback("c", 1, float(upperVal), field, ui_update=False)
