import src.common.format as fmt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import src.common.csvdict as csvdict
from src.common.colorfunc import get_hex_color, get_rgb_color
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
