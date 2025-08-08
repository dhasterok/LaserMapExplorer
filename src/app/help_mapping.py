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
        parent.canvas_widget: 'center_pane',
        parent.canvas_widget.canvasWindow: 'center_pane',
        parent.control_dock: 'left_toolbox',
        parent.control_dock.toolbox: 'left_toolbox',
        parent.style_dock: 'right_toolbox',
        parent.style_dock.toolbox: 'right_toolbox',
    }
    if hasattr(parent, "mask_dock"):
        help_mapping[parent.mask_dock] = 'lower_tabs'
        help_mapping[parent.mask_tab_widget] = 'lower_tabs'
    if hasattr(parent, "plot_tree"):
        help_mapping[parent.plot_tree] = 'right_toolbox'

    return help_mapping
