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
        parent.dockWidgetRightToolbox: 'right_toolbox',
        parent.toolBoxTreeView: 'right_toolbox',
        parent.dockWidgetBottomTabs: 'lower_tabs',
        parent.tabWidget: 'lower_tabs',
    }

    return help_mapping
