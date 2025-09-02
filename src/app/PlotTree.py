import re, darkdetect

from PyQt6.QtCore import ( Qt, QSize )
from PyQt6.QtGui import ( QColor, QBrush, QStandardItemModel, QStandardItem )
from PyQt6.QtWidgets import ( QWidget, QVBoxLayout, QSizePolicy, QDockWidget, QWidget, QToolBar ) 
from src.common.CustomWidgets import StandardItem, CustomTreeView, CustomDockWidget, CustomAction, CustomActionMenu
from src.app.UITheme import default_font

import src.common.CustomMplCanvas as mplc
from src.common.Logger import LoggerConfig, auto_log_methods, log
from src.app.PlotRegistry import PlotRegistry

from src.app.config import ICONPATH

# -------------------------------
# Plot Selector (tree) functions
# -------------------------------
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
        self.treeView = CustomTreeView(parent=self)
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

        # add leaves for analytes
        for analyte in data.match_attribute('data_type','Analyte'):
            leaf = treeView.find_leaf(analyte_branch, analyte)
            if not leaf:
                treeView.add_leaf(analyte_branch, analyte)

            leaf = treeView.find_leaf(norm_analyte_branch, analyte)
            if not leaf:
                treeView.add_leaf(norm_analyte_branch, analyte)

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
                treeView.add_leaf(ratio_branch, ratio)

            leaf = treeView.find_leaf(norm_ratio_branch, ratio)
            if not leaf:
                treeView.add_leaf(norm_ratio_branch, ratio)

    def add_calculated_leaf(self, new_field):

        # assign the two objects needed from self.ui
        sample_id = self.ui.app_data.sample_id
        treeView = self.treeView

        calculated_branch = treeView.branch_exists(self.tree['Calculated'], sample_id)
        if not calculated_branch:
            sample_branch = treeView.add_branch(self.tree['Calculated'], sample_id)
        else:
            return

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

    def tree_double_click(self,tree_index):
        """Double-click on plot selector
        
        When the user double-clicks on the ``Plot Selector``, the stored plot is placed on the current canvas.

        Parameters
        ----------
        val : PyQt5.QtCore.QModelIndex
            Item selected in ``Plot Selector``
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
        
        flag = self.plot_info is not None

        tree = tree_index.parent().parent().data()
        branch = tree_index.parent().data()
        leaf = tree_index.data()

        # Set main UI plot_info for compatibility with other components
        self.ui.plot_info = self.plot_info
        
        if tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)', 'Calculated']:
            if self.plot_info:
                # Existing plot: regenerate from registry data
                log("plot_info exists, regenerating from registry", "NOTE")
                
                # Initialize axis values with the plot's field data
                field_type = self.plot_info.get('field_type', tree)
                field = self.plot_info.get('field', leaf)
                self.ui.style_data.initialize_axis_values(field_type, field)
                self.ui.style_data.set_style_widgets()
                
                # Add to canvas using registry
                self.ui.add_plotwidget_to_canvas(self.plot_info)
                
                # Update UI fields to match the plot
                self.ui.update_fields(self.plot_info['sample_id'], self.plot_info['plot_type'], field_type, field)
                self.ui.update_spinboxes(field=field, field_type=field_type)
            else:
                # Persistent leaf item: create new field map plot
                log("Creating new field map plot for persistent item", "NOTE")

                # Set correct toolbox tab
                if self.ui.control_dock.toolbox.currentIndex() not in [self.ui.control_dock.tab_dict['sample'], self.ui.control_dock.tab_dict['process']]:
                    self.ui.control_dock.toolbox.setCurrentIndex(self.ui.control_dock.tab_dict['sample'])

                # First update UI fields to set correct field/field_type in widgets
                # This must happen BEFORE setting style data
                self.ui.update_fields(branch, 'field map', tree, leaf, plot=False)
                
                # Now initialize style data for the specific field AFTER widgets are set
                self.ui.style_data.initialize_axis_values(tree, leaf)
                self.ui.style_data.plot_type = 'field map'
                self.ui.style_data.set_style_widgets()

                # Update spinboxes to match the field
                self.ui.update_spinboxes(field=leaf, field_type=tree)
                
                # Finally create the plot - this should use the correct field now
                # Since widgets are already set, we can trigger plot creation
                if hasattr(self.ui, 'plot_map_mpl'):
                    self.ui.plot_map_mpl()
                elif hasattr(self.ui, 'update_SV'):
                    self.ui.update_SV()

        elif tree in ['Histogram', 'Correlation', 'Geochemistry', 'Multidimensional Analysis']:

            if self.plot_info:
                self.ui.add_plotwidget_to_canvas(self.plot_info)
                # Handle style updates safely
                plot_type = self.plot_info.get('plot_type')
                style = self.plot_info.get('style')
                if plot_type and style:
                    self.ui.style_data.style_dict[plot_type] = style
                    self.ui.style_data.plot_type = plot_type
                # updates comboBoxColorByField and comboBoxColorField comboboxes 
                #self.ui.update_fields(self.plot_info['sample_id'], self.plot_info['plot_type'],self.plot_info['field_type'], self.plot_info['field'])

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

        # Un-highlight all leaf in the trees
        self.unhighlight_tree(self.tree['Ratio'])
        self.unhighlight_tree(self.tree['Analyte'])

        analytes = data.processed.match_attribute('data_type','Analyte')
        ratios = data.processed.match_attribute('data_type','Ratio')

        data.processed.set_attribute(analytes,'use',False)
        treeView = self.treeView

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
                leaf_item_norm = None
                if not treeView.find_leaf(sample_branch, analyte):
                    # add ratio (leaf) item to sample_id (branch)
                    treeView.add_leaf(sample_branch, analyte)

                    # add ratio normalized (leaf) item to sample_id (branch)
                    leaf_item_norm = treeView.add_leaf(sample_branch_norm, analyte)
                else:
                    leaf_item_norm = treeView.find_leaf(sample_branch_norm, analyte)

                # check if ratio can be normalized (note: normalization is not handled here)
                refval_1 = ref_chem[re.sub(r'\d', '', analyte_1).lower()]
                refval_2 = ref_chem[re.sub(r'\d', '', analyte_2).lower()]
                ratio_flag = False
                if (refval_1 > 0) and (refval_2 > 0):
                    ratio_flag = True
                #print([analyte, refval_1, refval_2, ratio_flag])

                # if normalization cannot be done, make text italic and disable item
                if not ratio_flag:
                    font = leaf_item_norm.font()
                    font.setItalic(True)
                    leaf_item_norm.setFont(font)
                    leaf_item_norm.setEnabled(False)
                    data.processed.set_attribute(analyte, 'use', False)

            else: #single analyte

                leaf_item = treeView.find_leaf(treeView.find_leaf(self.tree['Analyte'], sample_id), analyte)
                # if norm_update:
                #     item,check = self.find_leaf('Analyte (normalized)', branch = sample_id, leaf = analyte)
                # else:
                #     item,check = self.find_leaf('Analyte', branch = sample_id, leaf = analyte)

                leaf_item.setBackground(QBrush(QColor(hexcolor)))

                data.processed.set_attribute(analytes,'use',True)

            if norm_update: #update if analytes are returned from analyte selection window
                data.update_norm(norm, analyte)

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
