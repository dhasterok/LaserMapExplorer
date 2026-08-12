import re, darkdetect

from PyQt6.QtCore import ( Qt, QSize, QMimeData )
from PyQt6.QtGui import ( QColor, QBrush, QStandardItemModel, QStandardItem, QAction, QDrag )
from PyQt6.QtWidgets import ( QWidget, QVBoxLayout, QSizePolicy, QDockWidget, QWidget, QToolBar, QMenu, QAbstractItemView )
from lame_core.CustomWidgets import StandardItem, CustomTreeView, CustomDockWidget, CustomAction, CustomActionMenu
from lame_core.UITheme import default_font

import src.plotting.CustomMplCanvas as mplc
from src.control.Logger import LoggerConfig, auto_log_methods, log
from src.tree.PlotRegistry import PlotRegistry

from lame_core.config import ICONPATH

# MIME type used to drag a plot leaf out of the Plot Selector tree (e.g. onto
# the Multi View canvas). Payload is "tree\x1fbranch\x1fleaf" (see get_item_path).
PLOT_TREE_MIME_TYPE = "application/x-lame-plot-leaf"

# -------------------------------
# Plot Selector (tree) functions
# -------------------------------
class PlotTreeView(CustomTreeView):
    """``CustomTreeView`` that lets a plot leaf be dragged out, e.g. onto the Multi View canvas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def startDrag(self, supportedActions):
        item = self.treeModel.itemFromIndex(self.currentIndex())
        if item is None:
            return

        # only individual plot leaves (tree/sample/field, 3 levels deep) can be dragged
        path = self.get_item_path(item)
        if len(path) != 3:
            return

        mime_data = QMimeData()
        mime_data.setData(PLOT_TREE_MIME_TYPE, "\x1f".join(path).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

@auto_log_methods(logger_key='Tree')
class PlotTree(CustomDockWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger_key = 'Tree'

        self.ui = parent
        
        # Initialize plot registry (will be properly connected when MainWindow initializes)
        self.plot_registry = None

        #create plot tree
        self.setup_ui()
        self.connect_logger()
        self.initialize_tree()

        self.show()

    def setup_ui(self):
        font = default_font()

        self.setFloating(True)
        self.setWindowTitle("Plot Tree")
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(size_policy)
        self.setMinimumSize(QSize(256, 276))
        self.setMaximumSize(QSize(300, 524287))
        self.setFont(font)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setObjectName("dockWidgetPlotTree")

        # Create a container widget for the dock contents
        container = QWidget()
        self.setWidget(container)

        # Set up the layout on the container, not self!
        container_layout = QVBoxLayout(container)
        container_layout.setObjectName("plot_tree_layout")
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        container_layout.addWidget(toolbar)

        sortmenu_items = [
            ("alphabetical", lambda: self.sort_tree("alphabetical")),
            ("atomic number", lambda: self.sort_tree("atomic number")),
            ("mass", lambda: self.sort_tree("mass")),
            ("compatibility", lambda: self.sort_tree("compatibility")),
            ("radius", lambda: self.sort_tree("radius")),
        ]
        self.action_sort = CustomActionMenu(
            text="Sort\nAnalytes",
            menu_items=sortmenu_items,
            light_icon_unchecked="icon-sort-64.svg",
            dark_icon_unchecked="icon-sort-dark-64.svg",
            parent=self
        )
        self.action_sort.setToolTip("Choose a method for sorting the analyte fields")

        self.action_remove_plot = CustomAction(
            text="Remove\nPlot",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=self,
        )
        self.action_remove_plot.setObjectName("actionRemovePlot")
        self.action_remove_plot.setToolTip("Remove selected plot from plot tree")

        self.action_remove_all = CustomAction(
            text="Remove\nAll Plots",
            light_icon_unchecked="icon-delete-all-64.svg",
            dark_icon_unchecked="icon-delete-all-dark-64.svg",
            parent=self,
        )
        self.action_remove_all.setObjectName("actionRemoveAllPlots")
        self.action_remove_all.setToolTip("Remove all plots from plot tree")

        toolbar.addAction(self.action_sort)
        toolbar.addSeparator()
        toolbar.addAction(self.action_remove_plot)
        toolbar.addAction(self.action_remove_all)

        # TreeView
        self.treeView = PlotTreeView(parent=self)
        self.treeView.setFont(font)
        self.treeView.setMouseTracking(True)
        self.treeView.setObjectName("treeView")

        container_layout.addWidget(self.treeView)

    def connect_logger(self):
        """Connects logger to actions in the plot tree."""
        self.action_sort.triggered.connect(lambda: log("PlotTree.actionSortMenu", prefix="UI"))
        self.action_remove_plot.triggered.connect(lambda: log("PlotTree.actionRemovePlot", prefix="UI"))
        self.action_remove_all.triggered.connect(lambda: log("PlotTree.actionRemoveAllPlots", prefix="UI"))

    def initialize_tree(self):
        """Initialize ``self.treeView`` with the top level items."""        
        # create tree
        treeView = self.treeView
        # hide the header row
        treeView.setHeaderHidden(True)

        # Top level branches
        self.tree = {}
        self.tree['Analyte'] = treeView.add_branch(treeView.root_node, 'Analyte')
        self.tree['Analyte (normalized)'] = treeView.add_branch(treeView.root_node, 'Analyte (normalized)')
        self.tree['Ratio'] = treeView.add_branch(treeView.root_node, 'Ratio')
        self.tree['Ratio (normalized)'] = treeView.add_branch(treeView.root_node, 'Ratio (normalized)')
        self.tree['Histogram'] = treeView.add_branch(treeView.root_node, 'Histogram')
        self.tree['Correlation'] = treeView.add_branch(treeView.root_node, 'Correlation')
        self.tree['Geochemistry'] = treeView.add_branch(treeView.root_node, 'Geochemistry')
        self.tree['Multidimensional Analysis'] = treeView.add_branch(treeView.root_node, 'Multidimensional Analysis')
        self.tree['Calculated'] = treeView.add_branch(treeView.root_node, 'Calculated')

        # Set the model to the view and expand the tree
        treeView.expandAll()

        # Connect double-click event
        #self.treeView.doubleClicked.connect(treeView.on_double_click)
        treeView.doubleClicked.connect(self.tree_double_click)

        # Write checkbox toggles (Analyte/Analyte (normalized)/Ratio/Ratio
        # (normalized) leaves only -- see add_sample()/update_tree()) back to
        # the underlying column attributes.
        treeView.treeModel.itemChanged.connect(self.on_tree_item_changed)

        # Right-click "Select All"/"Select None" on a data branch (or one of
        # its sample sub-branches) for quick bulk selection.
        treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        treeView.customContextMenuRequested.connect(self.show_tree_context_menu)

    _CHECKABLE_BRANCH_ATTR = {
        'Analyte': 'use',
        'Ratio': 'use',
        'Analyte (normalized)': 'use_normalized',
        'Ratio (normalized)': 'use_normalized',
    }

    def on_tree_item_changed(self, item):
        """Writes a leaf's checkbox toggle back to its column attribute.

        Only leaves under the four data branches (`_CHECKABLE_BRANCH_ATTR`)
        are ever made checkable (see `add_sample()`/`update_tree()`), so this
        only fires for user-driven toggles there.
        """
        if not item.isCheckable():
            return

        path = self.treeView.get_item_path(item)
        if len(path) != 3:
            return

        branch_name, sample_id, field = path
        attr = self._CHECKABLE_BRANCH_ATTR.get(branch_name)
        if attr is None:
            return

        data = self.ui.app_data.data.get(sample_id)
        if data is None:
            return

        data.processed.set_attribute(field, attr, item.checkState() == Qt.CheckState.Checked)

    def show_tree_context_menu(self, pos):
        """Right-click "Select All"/"Select None" for a data branch or one sample within it."""
        index = self.treeView.indexAt(pos)
        if not index.isValid():
            return

        item = self.treeView.treeModel.itemFromIndex(index)
        if item is None:
            return

        path = self.treeView.get_item_path(item)
        # path == [branch] for a top-level data branch, [branch, sample_id] for
        # one of its sample sub-branches -- anything deeper is a leaf, ignore.
        if len(path) not in (1, 2) or path[0] not in self._CHECKABLE_BRANCH_ATTR:
            return

        label_suffix = f' ({item.text()})' if len(path) == 2 else ''
        menu = QMenu(self.treeView)
        action_all = QAction(f'Select All{label_suffix}', self.treeView)
        action_none = QAction(f'Select None{label_suffix}', self.treeView)
        action_all.triggered.connect(lambda: self._set_branch_check_state(item, Qt.CheckState.Checked))
        action_none.triggered.connect(lambda: self._set_branch_check_state(item, Qt.CheckState.Unchecked))
        menu.addAction(action_all)
        menu.addAction(action_none)
        menu.exec(self.treeView.viewport().mapToGlobal(pos))

    def _set_branch_check_state(self, item, check_state):
        """Bulk-sets check state (and the underlying attribute) for every
        checkable leaf under `item`.

        `item` may be a top-level data branch (applies across all its sample
        sub-branches) or a single sample's sub-branch (applies to that sample
        only).
        """
        branch_name = self.treeView.get_item_path(item)[0]
        attr = self._CHECKABLE_BRANCH_ATTR.get(branch_name)
        if attr is None:
            return

        top_level = item.parent() is None
        sample_branches = [item.child(r) for r in range(item.rowCount())] if top_level else [item]

        self.treeView.treeModel.blockSignals(True)
        try:
            for sample_branch in sample_branches:
                data = self.ui.app_data.data.get(sample_branch.text())
                for leaf_row in range(sample_branch.rowCount()):
                    leaf = sample_branch.child(leaf_row)
                    if not leaf.isCheckable() or not leaf.isEnabled():
                        continue
                    leaf.setCheckState(check_state)
                    if data is not None:
                        data.processed.set_attribute(leaf.text(), attr, check_state == Qt.CheckState.Checked)
        finally:
            self.treeView.treeModel.blockSignals(False)

    def add_sample(self, sample_id):
        """Create plot selector tree

        Initializes ``MainWindow.treeView``.  The ``tree`` is intialized for each of the plot groups.
        ``Analyte`` its normalized counterpart are initialized with the full list of analytes.  Table
        data are stored in ``MainWindow.treeModel``.
        
        Parameters
        ----------
        sample_id : str
            Sample name, Defaults to None
        """
        if not sample_id:
            return

        # assign the two objects needed from self.ui
        data = self.ui.app_data.data[sample_id].processed
        treeView = self.treeView

        # add sample_id to analyte branch
        analyte_branch = treeView.branch_exists(self.tree['Analyte'], sample_id)
        if not analyte_branch:
            analyte_branch = treeView.add_branch(self.tree['Analyte'], sample_id)
        else:
            return

        # add sample_id to analyte (normalized) branch
        norm_analyte_branch = treeView.branch_exists(self.tree['Analyte (normalized)'], sample_id)
        if not norm_analyte_branch:
            norm_analyte_branch = treeView.add_branch(self.tree['Analyte (normalized)'], sample_id)
        else:
            return

        # block itemChanged while bulk-creating leaves so initial check-state
        # doesn't get written back into column_attributes as a user toggle
        treeView.treeModel.blockSignals(True)
        try:
            # add leaves for analytes
            for analyte in data.match_attribute('data_type','Analyte'):
                leaf = treeView.find_leaf(analyte_branch, analyte)
                if not leaf:
                    treeView.add_leaf(analyte_branch, analyte, checkable=True, checked=bool(data.get_attribute(analyte, 'use')))

                leaf = treeView.find_leaf(norm_analyte_branch, analyte)
                if not leaf:
                    treeView.add_leaf(norm_analyte_branch, analyte, checkable=True, checked=bool(data.get_attribute(analyte, 'use_normalized')))

            if not data.match_attribute('data_type','Ratio'):
                return

            # add sample_id to ratio branch
            ratio_branch = treeView.branch_exists(self.tree['Ratio'], sample_id)
            if not ratio_branch:
                ratio_branch = treeView.add_branch(self.tree['Ratio'], sample_id)
            else:
                return

            # add sample_id to ratio (normalized) branch
            norm_ratio_branch = treeView.branch_exists(self.tree['Ratio (normalized)'], sample_id)
            if not norm_ratio_branch:
                norm_ratio_branch = treeView.add_branch(self.tree['Ratio (normalized)'], sample_id)
            else:
                return

            # add leaves for ratios
            for ratio in data.match_attribute('data_type','Ratio'):
                leaf = treeView.find_leaf(ratio_branch, ratio)
                if not leaf:
                    treeView.add_leaf(ratio_branch, ratio, checkable=True, checked=bool(data.get_attribute(ratio, 'use')))

                leaf = treeView.find_leaf(norm_ratio_branch, ratio)
                if not leaf:
                    treeView.add_leaf(norm_ratio_branch, ratio, checkable=True, checked=bool(data.get_attribute(ratio, 'use_normalized')))
        finally:
            treeView.treeModel.blockSignals(False)

    def add_calculated_leaf(self, new_field):

        # assign the two objects needed from self.ui
        sample_id = self.ui.app_data.sample_id
        treeView = self.treeView

        calculated_branch = treeView.branch_exists(self.tree['Calculated'], sample_id)
        if not calculated_branch:
            sample_branch = treeView.add_branch(self.tree['Calculated'], sample_id)
        else:
            sample_branch = calculated_branch

        leaf = treeView.find_leaf(sample_branch, new_field)
        if not leaf:
            treeView.add_leaf(sample_branch, new_field)
    
    def sort_tree(self, method):
        """Sorts `MainWindow.treeView` and raw_data and processed_data according to one of several options.

        Parameters
        ----------
        method : str
            Method used for sorting the analytes.
        """        
        self.ui.app_data.sort_method = method

        treeView = self.treeView

        analyte_list, sorted_analyte_list = self.ui.data[self.ui.app_data.sample_id].sort_data(method)
         
        # Reorder tree items according to the new analyte list
        # Sort the tree branches associated with analytes
        for sample_id in self.ui.app_data.sample_list:
            sample_branch = treeView.find_leaf(self.tree['Analyte'], sample_id)
            if sample_branch:
                treeView.sort_branch(sample_branch, sorted_analyte_list)

            norm_sample_branch = treeView.find_leaf(self.tree['Analyte (normalized)'], sample_id)
            if sample_branch:
                treeView.sort_branch(norm_sample_branch, sorted_analyte_list)

        # Sort the tree branches associated with ratios
        # maybe later
        # sort by denominator and then numerator?

    def retrieve_plotinfo_from_tree(self, tree_index=None, tree=None, branch=None, leaf=None):
        """Gets the plot_info associated with a tree location using registry system
        
        Can recall the plot info given the index into the tree (top level group in ``Plot Selector``), or by the tree, branch, leaf location.
        
        Parameters
        ----------
        tree_index : QModelIndex
            Index into the ``Plot Selector`` tree items
        tree : str
            Top level of tree, categorized by the type of plots
        branch : str
            Associated with sample ID
        leaf : str
            Lowest level of tree, associated with an individual plot
        
        Returns
        -------
        dict, bool
            Plot_info dictionary with plot widget and information about the plot construction, 
            returns True if the branch exists
        """
        if not self.plot_registry:
            log("Plot registry not available", "WARNING")
            return None, False
            
        # Build tree key from parameters
        if tree_index is not None:
            tree_key = tree_index.data(Qt.ItemDataRole.UserRole)
        else:
            # Build tree key from individual parameters
            tree_key = f"{tree}:{branch}:{leaf}"

        if not tree_key:
            log("No tree key found", "WARNING")
            return None, False

        # Get plot info from registry using tree key
        plot_info = self.plot_registry.get_plot_by_tree_key(tree_key)
        
        if plot_info is None:
            # Check if the tree item exists but plot not registered
            item, item_flag = self.find_leaf(tree or tree_key.split(':')[0], 
                                           branch or tree_key.split(':')[1], 
                                           leaf or tree_key.split(':')[2])
            return None, item_flag
        
        return plot_info, True

    def _get_primary_axis(self, plot_type):
        """Return the app_data axis ('x' or 'c') that plot_info['field']/['field_type'] map to.

        Parameters
        ----------
        plot_type : str
            The plot type string (e.g. 'field map', 'histogram').

        Returns
        -------
        str
            'x' for histogram-style plots, 'c' for all map-style plots.
        """
        if plot_type in ['histogram']:
            return 'x'
        return 'c'

    def _sync_ui_to_plot(self, plot_type, field_type, field):
        """Synchronize all UI controls to match a selected plot.

        Switches the control dock toolbox tab, updates the plot-type combobox,
        style data, and field comboboxes to reflect the selected plot — all
        without triggering the signal chain that would schedule a redundant
        re-render.

        Parameters
        ----------
        plot_type : str
            The plot type (e.g. 'field map', 'histogram').
        field_type : str
            The field type of the primary axis (e.g. 'Analyte').
        field : str
            The field of the primary axis (e.g. 'Ca43').
        style : dict, optional
            Style dict to restore into style_data.style_dict. Defaults to None.
        """
        control_dock = self.ui.control_dock

        # Disable plot_flag for the entire sync so that any widget changes below
        # (e.g. X/Y/Z comboboxes that toggle_signals does NOT block) cannot
        # fire schedule_update and trigger an unwanted re-render mid-setup.
        old_plot_flag = self.ui.plot_flag
        self.ui.plot_flag = False

        try:
            # 1. Find the correct toolbox tab for this plot type
            target_tab = None
            for tab_id, settings in control_dock.field_control_settings.items():
                if tab_id == -1:
                    continue
                if plot_type in settings.plot_list:
                    target_tab = tab_id
                    break
            if target_tab is None:
                target_tab = control_dock.tab_dict.get('sample')

            # Block all style_data signals so that intermediate plot_type writes
            # don't fire update_plot_type before we've finished setting all state.
            self.ui.style_data.blockSignals(True)

            # 2. Switch toolbox tab without triggering toolbox_changed
            control_dock.toolbox.blockSignals(True)
            control_dock.toolbox.setCurrentIndex(target_tab)
            control_dock.toolbox.blockSignals(False)

            # 3. Repopulate comboBoxPlotType for this tab, then select the correct type.
            control_dock.update_plot_type_combobox_options()
            control_dock.comboBoxPlotType.blockSignals(True)
            control_dock.comboBoxPlotType.setCurrentText(plot_type)
            control_dock.comboBoxPlotType.blockSignals(False)

            # 4. Update style data to the correct plot type.
            #    NOTE: plot_info['style'] is a reference to style_dict, not a snapshot,
            #    so restoring it here is a no-op for same-type plots. Field values are
            #    written explicitly in step 5 to handle that case.
            self.ui.style_data.plot_type = plot_type

            # Re-enable style_data signals now that plot_type is correct
            self.ui.style_data.blockSignals(False)

            # 5. Write field_type/field directly into style_dict.
            #    • Bypasses property-setter side-effects (auto-reset via field_dict,
            #      which fails for tree names like 'Analyte (normalized)').
            #    • For multi-axis plots (scatter, heatmap, ternary) plot_info stores
            #      field_type/field as [x, y, z, c] lists — always write ALL axes,
            #      including empty ones, so residual values from a previously shown
            #      plot of the same type (e.g. 3-element → 2-element scatter) are
            #      cleared and don't cause a spurious re-render.
            style_entry = self.ui.style_data.style_dict.get(plot_type)
            if style_entry is not None:
                axes_upper = ['X', 'Y', 'Z', 'C']
                if isinstance(field_type, list) and isinstance(field, list):
                    for i, ax_upper in enumerate(axes_upper):
                        ft = field_type[i] if i < len(field_type) else ''
                        fv = field[i] if i < len(field) else ''
                        style_entry[f'{ax_upper}FieldType'] = ft if ft is not None else ''
                        style_entry[f'{ax_upper}Field'] = fv if fv is not None else ''
                else:
                    ax_upper = self._get_primary_axis(plot_type).upper()
                    style_entry[f'{ax_upper}FieldType'] = field_type
                    style_entry[f'{ax_upper}Field'] = field

            # 6. Update which axis rows are visible/enabled in the control dock
            control_dock.init_field_widgets(self.ui.style_data.axis_settings, plot_type)

            # 7. Initialize axis limits/labels using the primary (first non-empty) field
            primary_field_type = (field_type[0] if isinstance(field_type, list) else field_type) or ''
            primary_field = (field[0] if isinstance(field, list) else field) or ''
            if primary_field_type and primary_field:
                self.ui.style_data.initialize_axis_values(primary_field_type, primary_field)

            # 8. Sync all style dock widgets
            if hasattr(self.ui, 'style_dock'):
                self.ui.style_dock.set_style_widgets()

        finally:
            # Always restore plot_flag so the application remains responsive
            self.ui.plot_flag = old_plot_flag

    def tree_double_click(self, tree_index):
        """Double-click on plot selector.

        When the user double-clicks on the ``Plot Selector``, the stored plot
        is placed on the current canvas and the full UI (toolbox tab, plot-type
        combobox, field comboboxes, style dock) is updated to match.

        Parameters
        ----------
        tree_index : QModelIndex
            Item selected in the ``Plot Selector``.
        """
        if not self.plot_registry:
            log("Plot registry not available", "WARNING")
            return

        # Get tree key from clicked item
        tree_key = tree_index.data(Qt.ItemDataRole.UserRole)

        # Get plot info from registry using tree key (if it exists)
        if tree_key:
            self.plot_info = self.plot_registry.get_plot_by_tree_key(tree_key)
        else:
            # No tree_key means this is a persistent leaf item for quick map creation
            self.plot_info = None

        tree = tree_index.parent().parent().data()
        leaf = tree_index.data()

        # Set main UI plot_info for compatibility with other components
        self.ui.plot_info = self.plot_info

        if tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)', 'Calculated']:
            if self.plot_info:
                # Existing plot: restore full UI state then show cached canvas
                log("plot_info exists, showing from registry", "NOTE")
                self._sync_ui_to_plot(
                    self.plot_info.get('plot_type', 'field map'),
                    self.plot_info.get('field_type', tree),
                    self.plot_info.get('field', leaf),
                )
                self.ui.add_canvas_to_window(self.plot_info)
            else:
                # Persistent leaf item: sync UI for a new field map, then render
                log("Creating new field map plot for persistent item", "NOTE")
                self._sync_ui_to_plot('field map', tree, leaf)
                if hasattr(self.ui, 'update_SV'):
                    self.ui.update_SV()

        elif tree in ['Histogram', 'Correlation', 'Geochemistry', 'Multidimensional Analysis']:
            if self.plot_info:
                # Restore full UI state then show cached canvas
                self._sync_ui_to_plot(
                    self.plot_info.get('plot_type', ''),
                    self.plot_info.get('field_type', ''),
                    self.plot_info.get('field', ''),
                )
                self.ui.add_canvas_to_window(self.plot_info)

        else:
            raise ValueError(f"Unknown tree type {tree}.")

    def update_tree(self, norm_update=False):
        """Updates plot selector list and data

        Updates the tree with the list of analytes in ``MainWindow.data[sample_id]['norm']`` and background color
        to light yellow for analytes used in analyses.
        
        Parameters
        ----------
        analyte_df : pandas.DataFrame
            Data frame with information about analytes, scales, limits and use in analysis
        norm_update : bool
            Flag for updating norm list. Defaults to False
        """
        sample_id = self.ui.app_data.sample_id
        if sample_id == '':
            return

        if darkdetect.isDark():
            hexcolor = self.ui.theme_manager.highlight_color_dark
        else:
            hexcolor = self.ui.theme_manager.highlight_color_light

        data = self.ui.app_data.data[sample_id]
        ref_chem = self.ui.app_data.ref_chem
        analytes = data.processed.match_attribute('data_type','Analyte')
        ratios = data.processed.match_attribute('data_type','Ratio')

        treeView = self.treeView

        # 'use'/'use_normalized' are set authoritatively by AnalyteDialog, the
        # PlotTree checkboxes below, and their bulk select/none actions -- this
        # method only reflects that state (highlighting + checkbox sync), it
        # must not reset or overwrite it on every tree rebuild. Block signals
        # for the *whole* method, including unhighlight_tree() below: setting
        # an item's background also fires itemChanged (it's not exclusive to
        # checkState changes), which would otherwise write a leaf's current
        # (possibly stale) checkbox state back over a real 'use' value that
        # was just set elsewhere but not yet reflected in the checkbox.
        treeView.treeModel.blockSignals(True)
        try:
            # Un-highlight all leaf in the trees
            self.unhighlight_tree(self.tree['Ratio'])
            self.unhighlight_tree(self.tree['Analyte'])

            for analyte in analytes + ratios:
                norm = data.processed.get_attribute(analyte,'norm')
                if '/' in analyte:
                    analyte_1, analyte_2 = analyte.split(' / ')

                    # find sample_id (branch) in ratio (tree), if it does not exist, create it
                    sample_branch = treeView.branch_exists(self.tree['Ratio'],sample_id)
                    if not sample_branch:
                        sample_branch = self.treeView.add_branch(self.tree['Ratio'], sample_id)

                    # find sample_id (branch) in ratio normalized (tree), if it does not exist, create it
                    sample_branch_norm = treeView.branch_exists(self.tree['Ratio (normalized)'], sample_id)
                    if not sample_branch_norm:
                        sample_branch_norm = self.treeView.add_branch(self.tree['Ratio (normalized)'], sample_id)

                    # check if ratio (leaf) exists in sample_id (branch) and create if necessesary
                    leaf_item = treeView.find_leaf(sample_branch, analyte)
                    if not leaf_item:
                        # add ratio (leaf) item to sample_id (branch)
                        leaf_item = treeView.add_leaf(sample_branch, analyte, checkable=True,
                            checked=bool(data.processed.get_attribute(analyte, 'use')))

                        # add ratio normalized (leaf) item to sample_id (branch)
                        leaf_item_norm = treeView.add_leaf(sample_branch_norm, analyte, checkable=True,
                            checked=bool(data.processed.get_attribute(analyte, 'use_normalized')))
                    else:
                        leaf_item_norm = treeView.find_leaf(sample_branch_norm, analyte)
                        # keep checkbox state in sync in case 'use'/'use_normalized'
                        # changed elsewhere (e.g. InfoViewer) since the tree was built
                        leaf_item.setCheckState(Qt.CheckState.Checked if data.processed.get_attribute(analyte, 'use') else Qt.CheckState.Unchecked)
                        leaf_item_norm.setCheckState(Qt.CheckState.Checked if data.processed.get_attribute(analyte, 'use_normalized') else Qt.CheckState.Unchecked)

                    # check if ratio can be normalized (note: normalization is not handled here)
                    # .get(..., 0) treats an element missing from the reference table the same
                    # as a non-positive reference value below -- both mean "can't normalize",
                    # rather than crashing the whole tree update on one unnormalizable ratio.
                    refval_1 = ref_chem.get(re.sub(r'\d', '', analyte_1).lower(), 0)
                    refval_2 = ref_chem.get(re.sub(r'\d', '', analyte_2).lower(), 0)
                    ratio_flag = False
                    if (refval_1 > 0) and (refval_2 > 0):
                        ratio_flag = True
                    #print([analyte, refval_1, refval_2, ratio_flag])

                    # if normalization cannot be done, make text italic and disable item
                    leaf_item_norm.setEnabled(ratio_flag)
                    font = leaf_item_norm.font()
                    font.setItalic(not ratio_flag)
                    leaf_item_norm.setFont(font)
                    if not ratio_flag:
                        leaf_item_norm.setCheckState(Qt.CheckState.Unchecked)
                        data.processed.set_attribute(analyte, 'use_normalized', False)

                else: #single analyte

                    analyte_branch = treeView.find_leaf(self.tree['Analyte'], sample_id)
                    norm_analyte_branch = treeView.find_leaf(self.tree['Analyte (normalized)'], sample_id)
                    leaf_item = treeView.find_leaf(analyte_branch, analyte)
                    leaf_item_norm = treeView.find_leaf(norm_analyte_branch, analyte)

                    leaf_item.setBackground(QBrush(QColor(hexcolor)))

                    # keep checkbox state in sync in case 'use'/'use_normalized'
                    # changed elsewhere (e.g. InfoViewer) since the tree was built
                    if leaf_item.isCheckable():
                        leaf_item.setCheckState(Qt.CheckState.Checked if data.processed.get_attribute(analyte, 'use') else Qt.CheckState.Unchecked)
                    if leaf_item_norm is not None and leaf_item_norm.isCheckable():
                        leaf_item_norm.setCheckState(Qt.CheckState.Checked if data.processed.get_attribute(analyte, 'use_normalized') else Qt.CheckState.Unchecked)

                if norm_update: #update if analytes are returned from analyte selection window
                    data.update_norm(norm, analyte)
        finally:
            treeView.treeModel.blockSignals(False)

    def add_tree_item(self, plot_info=None):
        """Updates plot selector list and adds plot information data to tree item
        
        Parameters
        ----------
        plot_info : dict
            Plot related data (including plot widget) to tree item associated with the plot.
        """
        if plot_info is None or self.plot_registry is None:
            return

        #print('add_tree_item')
        sample_id = plot_info['sample_id']
        leaf = plot_info['plot_name']
        tree = plot_info['tree']
        if tree == 'Calculated':
            tree = 'Calculated Map'

        tree_items = self.get_tree_items(tree)
        
        # Register plot in registry first
        plot_id = self.plot_registry.register_plot(plot_info)
        
        # Create tree key for this location
        tree_key = f"{tree}:{sample_id}:{leaf}"
        
        # Link tree key to plot ID
        self.plot_registry.link_to_tree(tree_key, plot_id)
        
        #check if leaf is in tree
        item,check = self.find_leaf(tree=tree, branch=sample_id, leaf=leaf)
        # sample id item and plot item both dont exist
        if item is None and check is None:
            # create new branch for sample id
            sample_id_item = StandardItem(sample_id, 11)

            # create new leaf item
            plot_item = StandardItem(leaf)

            # store tree key instead of full plot_info
            plot_item.setData(tree_key, role=Qt.ItemDataRole.UserRole)

            sample_id_item.appendRow(plot_item)
            tree_items.appendRow(sample_id_item)
            
            # Store references
            # self.item_refs[(tree, sample_id)] = sample_id_item
            # self.item_refs[(tree, sample_id, leaf)] = plot_item
            
        # sample id item exists plot item doesnt exist
        elif item is not None and not check:
            # create new leaf item
            plot_item = StandardItem(leaf)

            # store tree key instead of full plot_info
            plot_item.setData(tree_key, role=Qt.ItemDataRole.UserRole)

            #item is sample id item (branch)
            item.appendRow(plot_item)

        # sample id item exists and plot item exists
        elif item is not None and check: 
            # Update existing item with tree key
            item.setData(tree_key, role=Qt.ItemDataRole.UserRole)
 
    def unhighlight_tree(self, tree):
        """Reset the highlight of all items in the tree.
        
        Parameters
        ----------
        tree : str
            Highest level of tree with branches to unhighlight
        """
        #bgcolor = tree.background().color()
        if darkdetect.isDark():
            bgcolor = '#1e1e1e'
        else:
            bgcolor = '#ffffff'

        for i in range(tree.rowCount()):
            branch_item = tree.child(i)
            # branch_item.setBackground(QBrush(QColor(bgcolor)))  # white or any default background color
            for j in range(branch_item.rowCount()):
                leaf_item = branch_item.child(j)
                leaf_item.setBackground(QBrush(QColor(bgcolor)))  # white or any default background color

    def get_tree_items(self, tree):
        """Returns items associated with the specified tree
        
        Parameters
        ----------
        tree : str
            Name of tree in ``MainWindow.treeView``

        Returns
        -------
        Qt.AbstractModelItem
            The set of items under *tree*
        """
        return self.tree[tree]

    def find_leaf(self, tree, branch, leaf):
        """Get a branch or leaf item from treeView
        
        Parameters
        ----------
        tree : str
            Highest level of tree, ``plot_info['tree']``
        branch : str
            Middle tree level, ``plot_info['sample_id']``
        leaf : str
            Lowest level of tree, ``plot_info['plot_name']``

        Returns
        -------
        tuple
            (item, flag), item is a branch (``flag==False``) or leaf (``flag==True``), if item neither return is ``(None, None)``.
        """
        #print('find_leaf')
        #print(f'{tree} : {branch} : {leaf}')
        tree_items = self.get_tree_items(tree)

        #Returns leaf_item & True if leaf exists, else returns branch_item, False
        if tree_items:
            for index in range(tree_items.rowCount()):
                branch_item = tree_items.child(index)
                if branch_item.text() == branch:
                    for index in range(branch_item.rowCount()):
                        leaf_item = branch_item.child(index)
                        if leaf_item.text() == leaf:
                            return (leaf_item, True)
                    return (branch_item,False)
        return (None,None)

    def clear_tree_data(self, tree):
        """Removes item data from all items in a given tree
        
        Parameters
        ----------
        tree : str
            Name of tree in ``MainWindow.treeView``
        """
        tree_items = self.get_tree_items(tree)

        def clear_item_data(item):
            """Recursively clear data from the item and its children"""
            item.setData(None, role=Qt.ItemDataRole.UserRole)
            for index in range(item.rowCount()):
                child_item = item.child(index)
                clear_item_data(child_item)
        
        for index in range(tree_items.rowCount()):
            branch_item = tree_items.child(index)
            clear_item_data(branch_item)

    def get_plot_info_from_tree(self, model):
        """
        Extract plot_info data from the root of QStandardItemModel as a flat list.
        """
        self.plot_info_list = []  # Reset the list each time this method is called
        root = model.invisibleRootItem()
        for i in range(root.rowCount()):
            self.extract_plot_info(root.child(i))
        return self.plot_info_list

    def extract_plot_info(self, item):
        """
        Recursively extract plot_info from QStandardItem and append to a flat list.
        """
        # Retrieve the plot_info from the UserRole data
        plot_info = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(plot_info, dict) and 'figure' in plot_info:
            # Check if it contains an mplc.MplCanvas object
            if isinstance(plot_info['figure'], mplc.MplCanvas):
                # Create a copy of plot_info and replace the mplc.MplCanvas object with its Figure
                plot_info_copy = plot_info.copy()
                plot_info_copy['figure'] = plot_info['figure'].fig
                self.plot_info_list.append(plot_info_copy)

        # Recursively process each child of this item
        for i in range(item.rowCount()):
            child = item.child(i)
            if child:
                self.extract_plot_info(child)  # Process child recursively

    def create_item_from_data(self, data):
        """Recursively create QStandardItem from data.
        
        Parameters
        ----------
        data : dict
            data dictionary
        """
        item = QStandardItem(data['text'])
        if 'plot_info' in data:
            #create new matplotlib canvas and save fig
            canvas = mplc.MplCanvas(fig=data['plot_info']['figure'])
            data['plot_info']['figure'] = canvas
            #store plot dictionary in tree
            item.setData(data['plot_info'], role=Qt.ItemDataRole.UserRole)
        for child_data in data['children']:
            child_item = self.create_item_from_data(child_data)
            item.appendRow(child_item)
        return item
