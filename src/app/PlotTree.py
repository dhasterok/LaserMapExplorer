import re, darkdetect
from PyQt6.QtCore import ( Qt )
from PyQt6.QtGui import ( QColor, QBrush, QStandardItemModel, QStandardItem )
from PyQt6.QtWidgets import ( QMenu ) 
import src.common.CustomMplCanvas as mplc
from src.common.CustomWidgets import StandardItem, CustomTreeView
from src.common.SortAnalytes import sort_analytes

from src.common.Logger import LoggerConfig, auto_log_methods, log

# -------------------------------
# Plot Selector (tree) functions
# -------------------------------
@auto_log_methods(logger_key='Tree', prefix="TREE: ", show_args=True)
class PlotTree():
    def __init__(self, parent):
        self.logger_key = 'Tree'

        self.parent = parent

        #create plot tree
        self.initialize_tree()

        # create analyte sort menu
        sortmenu_items = ['alphabetical', 'atomic number', 'mass', 'compatibility', 'radius']
        SortMenu = QMenu()
        SortMenu.triggered.connect(self.sort_tree)
        self.parent.toolButtonSortAnalyte.setMenu(SortMenu)
        for item in sortmenu_items:
            SortMenu.addAction(item)

    def initialize_tree(self):
        """Initialize ``self.parent.treeView`` with the top level items."""        
        # create tree
        treeView = self.parent.treeView
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
        #self.parent.treeView.doubleClicked.connect(treeView.on_double_click)
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

        # assign the two objects needed from self.parent
        data = self.parent.app_data.data[sample_id].processed_data
        treeView = self.parent.treeView

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

        # assign the two objects needed from self.parent
        sample_id = self.parent.app_data.sample_id
        treeView = self.parent.treeView

        calculated_branch = treeView.branch_exists(self.tree['Calculated'], sample_id)
        if not calculated_branch:
            sample_branch = treeView.add_branch(self.tree['Calculated'], sample_id)
        else:
            return

        leaf = treeView.find_leaf(sample_branch, new_field)
        if not leaf:
            treeView.add_leaf(sample_branch, new_field)
    
    def sort_tree(self, action, method=None):
        """Sorts `MainWindow.treeView` and raw_data and processed_data according to one of several options.

        Parameters
        ----------
        action : QAction
            Menu selection defining sort type
        method : str, optional
            Method used for sorting the analytes. If `None`, defined by action, by default `None`
        """        
        if method is None:
            method = action.text()
            self.parent.app_data.sort_method = method

        treeView = self.parent.treeView

        analyte_list, sorted_analyte_list = self.parent.data[self.parent.app_data.sample_id].sort_data(method)
         
        # Reorder tree items according to the new analyte list
        # Sort the tree branches associated with analytes
        for sample_id in self.parent.app_data.sample_list:
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
        """Gets the plot_info associated with a tree location
        
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
        #print('retrieve_table_data')
        if tree_index is not None:
            tree = tree_index.parent().parent().data()
            branch = tree_index.parent().data()
            leaf = tree_index.data()

        item,item_flag = self.find_leaf(tree, branch, leaf)

        if not item_flag:
            return None, True

        if not item.isEnabled():
            return None, False

        # ----start debugging----
        # print(tree_index)
        # print('item')
        # print(tree+':'+branch+':'+leaf)
        # ----end debugging----

        plot_info = item.data(role=Qt.ItemDataRole.UserRole)

        # ----start debugging----
        # print(plot_info)
        # print('\nsuccessfully retrieved plot info\n')
        # ----end debugging----

        return plot_info, True

    def tree_double_click(self,tree_index):
        """Double-click on plot selector
        
        When the user double-clicks on the ``Plot Selector``, the stored plot is placed on the current canvas.

        Parameters
        ----------
        val : PyQt5.QtCore.QModelIndex
            Item selected in ``Plot Selector``
        """
        # get double-click result
        self.plot_info, flag = self.retrieve_plotinfo_from_tree(tree_index=tree_index)

        if not flag:
            return

        tree = tree_index.parent().parent().data()
        branch = tree_index.parent().data()
        leaf = tree_index.data()

        if tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)', 'Calculated']:
            self.parent.plot_style.initialize_axis_values(tree, leaf)
            self.parent.plot_style.set_style_widgets()
            if self.plot_info:
                log("plot_info exists, adding to canvas", "  NOTE: ")

                self.parent.add_plotwidget_to_canvas(self.plot_info)
                # updates comboBoxColorByField and comboBoxColorField comboboxes 
                self.parent.update_fields(self.parent.plot_info['sample_id'], self.parent.plot_info['plot_type'],self.parent.plot_info['field_type'], self.parent.plot_info['field'])
                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.parent.update_spinboxes(self.parent.plot_info['field'],self.parent.plot_info['field_type'])
            else:
                log("plot_info does not exist, creating map", "  NOTE: ")

                # print('tree_double_click: plot_map_pg')
                if self.parent.toolBox.currentIndex() not in [self.parent.left_tab['sample'], self.parent.left_tab['process']]:
                    self.parent.toolBox.setCurrentIndex(self.parent.left_tab['sample'])

                # updates comboBoxColorByField and comboBoxColorField comboboxes and creates new plot
                self.parent.update_fields(branch,'field map',tree, leaf, plot=True)

                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.parent.update_spinboxes(field=leaf, field_type=tree)

        elif tree in ['Histogram', 'Correlation', 'Geochemistry', 'Multidimensional Analysis']:

            if self.plot_info:
                self.parent.add_plotwidget_to_canvas(self.plot_info)
                self.parent.plot_style.style_dict[self.plot_info.plot_type] = self.plot_info.style
                self.parent.plot_style.plot_type = self.plot_info.plot_type
                # updates comboBoxColorByField and comboBoxColorField comboboxes 
                #self.parent.update_fields(self.parent.plot_info['sample_id'], self.parent.plot_info['plot_type'],self.parent.plot_info['field_type'], self.parent.plot_info['field'])

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
        sample_id = self.parent.app_data.sample_id
        if sample_id == '':
            return

        if darkdetect.isDark():
            hexcolor = self.parent.theme.highlight_color_dark
        else:
            hexcolor = self.parent.theme.highlight_color_light

        data = self.parent.app_data.data[sample_id]
        ref_chem = self.parent.app_data.ref_chem

        # Un-highlight all leaf in the trees
        self.unhighlight_tree(self.tree['Ratio'])
        self.unhighlight_tree(self.tree['Analyte'])

        analytes = data.processed_data.match_attribute('data_type','Analyte')
        ratios = data.processed_data.match_attribute('data_type','Ratio')

        data.processed_data.set_attribute(analytes,'use',False)
        treeView = self.parent.treeView

        for analyte in analytes + ratios:
            norm = data.processed_data.get_attribute(analyte,'norm')
            if '/' in analyte:
                analyte_1, analyte_2 = analyte.split(' / ')

                # find sample_id (branch) in ratio (tree), if it does not exist, create it
                sample_branch = treeView.branch_exists(self.tree['Ratio'],sample_id)
                if not sample_branch:
                    sample_branch = self.parent.treeView.add_branch(self.tree['Ratio'], sample_id)

                # find sample_id (branch) in ratio normalized (tree), if it does not exist, create it
                sample_branch_norm = treeView.branch_exists(self.tree['Ratio (normalized)'], sample_id)
                if not sample_branch_norm:
                    sample_branch_norm = self.parent.treeView.add_branch(self.tree['Ratio (normalized)'], sample_id)

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
                    data.processed_data.set_attribute(analyte, 'use', False)

            else: #single analyte

                leaf_item = treeView.find_leaf(treeView.find_leaf(self.tree['Analyte'], sample_id), analyte)
                # if norm_update:
                #     item,check = self.find_leaf('Analyte (normalized)', branch = sample_id, leaf = analyte)
                # else:
                #     item,check = self.find_leaf('Analyte', branch = sample_id, leaf = analyte)

                leaf_item.setBackground(QBrush(QColor(hexcolor)))

                data.processed_data.set_attribute(analytes,'use',True)

            if norm_update: #update if analytes are returned from analyte selection window
                data.update_norm(norm, analyte)

    def add_tree_item(self, plot_info=None):
        """Updates plot selector list and adds plot information data to tree item
        
        Parameters
        ----------
        plot_info : dict
            Plot related data (including plot widget) to tree item associated with the plot.
        """
        if plot_info is None:
            return

        #print('add_tree_item')
        sample_id = plot_info['sample_id']
        leaf = plot_info['plot_name']
        tree = plot_info['tree']
        if tree == 'Calculated':
            tree = 'Calculated Map'

        tree_items = self.get_tree_items(tree)
        
        
        # Ensure there's a persistent reference to items.
        # if not hasattr(self, 'item_refs'):
        #     self.item_refs = {}  # Initialize once
        
        #check if leaf is in tree
        item,check = self.find_leaf(tree=tree, branch=sample_id, leaf=leaf)
        # sample id item and plot item both dont exist
        if item is None and check is None:
            # create new branch for sample id
            sample_id_item = StandardItem(sample_id, 11)

            # create new leaf item
            plot_item = StandardItem(leaf)

            # store plot dictionary in leaf
            plot_item.setData(plot_info, role=Qt.ItemDataRole.UserRole)

            sample_id_item.appendRow(plot_item)
            tree_items.appendRow(sample_id_item)
            
            # Store references
            # self.item_refs[(tree, sample_id)] = sample_id_item
            # self.item_refs[(tree, sample_id, leaf)] = plot_item
            
        # sample id item exists plot item doesnt exist
        elif item is not None and not check:
            # create new leaf item
            plot_item = StandardItem(leaf)

            # store plot dictionary in leaf
            plot_item.setData(plot_info, role=Qt.ItemDataRole.UserRole)

            #item is sample id item (branch)
            item.appendRow(plot_item)
            
            # Update reference
            # self.item_refs[(tree, sample_id, leaf)] = plot_item

        # sample id item exists and plot item exists
        elif item is not None and check: 
            # store plot dictionary in tree
            item.setData(plot_info, role=Qt.ItemDataRole.UserRole)
            
            # self.item_refs[(tree, sample_id, leaf)] = item
 
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

    def create_item_from_data(self,data):
        """Recursively create QStandardItem from data."""
        item = QStandardItem(data['text'])
        if 'plot_info' in data.keys():
            #create new matplotlib canvas and save fig
            canvas = mplc.MplCanvas(fig=data['plot_info']['figure'])
            data['plot_info']['figure'] = canvas
            #store plot dictionary in tree
            item.setData(data['plot_info'], role=Qt.ItemDataRole.UserRole)
        for child_data in data['children']:
            child_item = self.create_item_from_data(child_data)
            item.appendRow(child_item)
        return item
