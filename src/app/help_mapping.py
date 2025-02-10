def create_help_mapping(parent):
    """Generates a help mapping for the given parent widget.

    Parameters
    ----------
    parent : QMainWindow
        The parent widget to map.

    Returns
    -------
    dict
        A dictionary mapping widgets to help topics.
    """
    help_mapping = {
        parent.centralwidget: 'center_pane',
        parent.canvasWindow: 'center_pane',
        parent.dockWidgetLeftToolbox: 'left_toolbox',
        parent.toolBox: 'left_toolbox',
        parent.dockWidgetPlotTree: 'right_toolbox',
        parent.dockWidgetStyling: 'right_toolbox',
    }
    if hasattr(parent, "mask_dock"):
        help_mapping[parent.mask_dock] = 'lower_tabs'
        help_mapping[parent.mask_tab_widget] = 'lower_tabs'

    return help_mapping
