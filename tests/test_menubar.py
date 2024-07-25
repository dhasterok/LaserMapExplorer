import pytest
from pytestqt.qtbot import QtBot
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QAction, QDialog, QTableWidgetItem, QComboBox, QFileDialog
from tests.conftest import import_sample, MainWindow
from src.ui.AnalyteSelectionDialog import Ui_Dialog  # type: ignore # Import the UI class


def test_import_directory(qtbot, main_window, mocker):
    # Mock the file dialog to return the desired directory
    mocker.patch.object(QFileDialog, 'getExistingDirectory', return_value='maps/Alex_garnet_maps/processed data')

    # Mock the exec_ method of QFileDialog to simulate the dialog being accepted
    mocker.patch.object(QFileDialog, 'exec_', return_value=QFileDialog.Accepted)
    mocker.patch.object(QFileDialog, 'selectedFiles', return_value=['maps/Alex_garnet_maps/processed data'])

    # Find the action and trigger it
    action_open_sample = main_window.findChild(QAction, 'actionOpenDirectory')
    
    
    # Manually trigger the QAction
    action_open_sample.trigger()

    # Allow any processing to complete
    qtbot.wait(100)

    # Allow any processing to complete
    #qtbot.mouseClick(main_window.menuBar().actionOpenDirectory, Qt.LeftButton)

    # Check if the comboBoxSampleId has the expected value
    combo_box_sample_id = main_window.findChild(QComboBox, 'comboBoxSampleId')
    
    assert combo_box_sample_id.currentText() == 'RM02'
    

def test_select_analytes(qtbot, main_window, mocker):
    # ipdb.set_trace()  # Insert breakpoint here
    # First, import the sample
    import_sample(qtbot, main_window, mocker)

    # Mock the norm_dict to test against it
    # main_window.analyteDialog = QDialog()
    # ui = Ui_Dialog()
    # ui.setupUi(main_window.analyteDialog)
    
    # main_window.analyteDialog.norm_dict = {}
    items_to_select = [
        ('Li7', 'linear'),
        ('Mg24', 'log'),
    ]
    def on_timeout(items_to_select):
        # Iterate through all rows in tableWidgetSelected to update combo boxes
        assert main_window.analyteDialog.isVisible()
        if main_window.analyteDialog.isVisible():
            for row, (analyte, scale) in enumerate(items_to_select):
                for row in range(main_window.analyteDialog.tableWidgetSelected.rowCount()):
                    combo = main_window.analyteDialog.tableWidgetSelected.cellWidget(row, 1)
                    analyte_s = main_window.analyteDialog.tableWidgetSelected.item(row, 0).text()
                    print(analyte_s,analyte)
                    if combo is not None and analyte_s == analyte:  # Make sure there is a combo box in this cell
                        combo.setCurrentText(scale)  # Update the combo box value
                        break
            # Click Done to confirm selection
            done_button = main_window.analyteDialog.pushButtonDone
            qtbot.mouseClick(done_button, Qt.LeftButton)

    # Open the dialog using actionSelectAnalytes
    action_select_analytes = main_window.findChild(QAction, 'actionSelectAnalytes')
    
    # add delay to open Analyteselector and selectcomboboxes
    QTimer.singleShot(1, lambda: on_timeout(items_to_select))
    action_select_analytes.trigger()

    # Allow any processing to complete
    qtbot.wait(100)


    # Verify the values in tableWidgetSelected matches keys in norm_dict
    expected_norm_dict = {analyte: scale for analyte, scale in items_to_select}
    for k,v in expected_norm_dict.items():
        assert main_window.analyteDialog.norm_dict[k] == expected_norm_dict[k]

    