from PyQt5.QtWidgets import ( QDialog, QHeaderView, QTableWidget, QTableWidgetItem, QCheckBox, QMenu, QMessageBox )
from PyQt5.QtGui import ( QIcon )
from src.ui.QuickViewDialog import Ui_QuickViewDialog
import src.CustomTableWidget as TW
import os, darkdetect
import src.csvdict as csvdict
import lame_helper as lamepath
from src.SortAnalytes import sort_analytes

# QuickViewDialog gui
# -------------------------------
class QuickView(QDialog, Ui_QuickViewDialog):
    """Creates a dialog for the user to select and order analytes for Quick View

    Opens an instance of QuickViewDialog for the user to select and order analytes for Quick View.
    The lists are automatically saved for future use.

    Parameters
    ----------
    QDialog : QDialog
        
    Ui_QuickViewDialog : QuickViewDialog
        User interface design.
    """    
    def __init__(self, parent=None):
        """Initializes quickView

        Parameters
        ----------
        analyte_list : list
            List of analytes to populate column 0 of  ``quickView.tableWidget``.
        quickview_list : dict
            Dictionary to be updated with an ordered list of analytes to be added to the ``MainWindow.layoutQuickView``.
        parent : None, optional
            Parent UI, by default None
        """        
        super().__init__(parent)
        self.setupUi(self)
        self.main_window = parent

        self.analyte_list = self.main_window.data[self.main_window.sample_id]['analyte_info']['analytes']

        if darkdetect.isDark():
            self.toolButtonSort.setIcon(QIcon(os.path.join(lamepath.ICONPATH,'icon-sort-dark-64.svg')))
            self.toolButtonSave.setIcon(QIcon(os.path.join(lamepath.ICONPATH,'icon-save-dark-64.svg')))

        self.tableWidget = TW.TableWidgetDragRows()  # Assuming TableWidgetDragRows is defined elsewhere
        self.setup_table()
        
        # Setup sort menu and associated toolButton
        self.setup_sort_menu()
        
        # Save functionality
        self.toolButtonSave.clicked.connect(self.save_selected_analytes)
        # Close dialog signal
        self.pushButtonClose.clicked.connect(lambda: self.done(0))
        self.layout().insertWidget(0, self.tableWidget)
        self.show()

    def setup_table(self):
        """Sets up analyte selection table in dialog"""
        self.tableWidget.setRowCount(len(self.analyte_list))
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Analyte', 'Show'])
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.populate_table()

    def populate_table(self):
        """Populates dialog table with analytes"""
        # Before repopulating, save the current state of checkboxes
        checkbox_states = {}
        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox:
                analyte = self.tableWidget.item(row, 0).text()
                checkbox_states[analyte] = checkbox.isChecked()

        # Clear the table and repopulate
        self.tableWidget.setRowCount(len(self.analyte_list))
        for row, analyte in enumerate(self.analyte_list):
            item = QTableWidgetItem(analyte)
            self.tableWidget.setItem(row, 0, item)
            checkbox = QCheckBox()
            # Restore the checkbox state based on the previous state if available
            checkbox.setChecked(checkbox_states.get(analyte, True))
            self.tableWidget.setCellWidget(row, 1, checkbox)

    def setup_sort_menu(self):
        """Adds options to sort menu"""
        sortmenu_items = ['alphabetical', 'atomic number', 'mass', 'compatibility', 'radius']
        SortMenu = QMenu()
        SortMenu.triggered.connect(self.apply_sort)
        self.toolButtonSort.setMenu(SortMenu)
        for item in sortmenu_items:
            SortMenu.addAction(item)

    def apply_sort(self, action):
        """Sorts analyte table in dialog"""        
        method = action.text()
        self.analyte_list = sort_analytes(method, self.analyte_list)
        self.populate_table()  # Refresh table with sorted data

    def save_selected_analytes(self):
        """Gets list of analytes and group name when Save button is clicked

        #     Retrieves the user defined name from ``quickView.lineEditViewName`` and list of analytes using ``quickView.column_to_list()``
        #     and adds them to a dictionary item with the name defined as the key.

        #     Raises
        #     ------
        #         A warning is raised if the user does not provide a name.  The list is not added to the dictionary in this case.
        #     """        
        self.view_name = self.lineEditViewName.text().strip()
        if not self.view_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid view name.")
            return

        selected_analytes = [self.tableWidget.item(row, 0).text() for row in range(self.tableWidget.rowCount()) if self.tableWidget.cellWidget(row, 1).isChecked()]
        self.analyte_list[self.view_name] = selected_analytes

        # update self.main_window.comboBoxQVList combo box with view_name
        self.main_window.comboBoxQVList.addItem(self.view_name)
        
        # Save to CSV
        self.save_to_csv()

    def save_to_csv(self):
        """Opens a message box, prompting user to in put a file to save the table list"""
        file_path = os.path.join(lamepath.BASEDIR,'resources', 'styles', 'qv_lists.csv')
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # append dictionary to file of saved qv_lists
        csvdict.export_dict_to_csv(self.analyte_list, file_path)
        

        QMessageBox.information(self, "Save Successful", f"Analytes view saved under '{self.view_name}' successfully.")