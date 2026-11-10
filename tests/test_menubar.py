import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QComboBox, QFileDialog
from tests.conftest import import_sample, MainWindow
from src.data.AnalyteSelectionDialog import Ui_Dialog  # type: ignore # Import the UI class


def test_import_directory(qtbot, main_window, mocker, dialogs):
    # `dialogs` answers Discard to the unsaved-changes prompt. Adding a sample
    # dirties the project, and qtbot's teardown closes the window, so without it
    # closeEvent -> close_project -> _confirm_discard_if_dirty puts up a modal
    # QMessageBox that nothing can click and the run hangs rather than fails.
    # Mock the file dialog to return the desired directory
    mocker.patch.object(QFileDialog, 'getExistingDirectory', return_value='maps/Alex_garnet_maps/processed data')

    # Mock exec() to simulate the dialog being accepted. PyQt5's 'exec_' alias is
    # gone in PyQt6, and patching a name the class doesn't have is an AttributeError.
    mocker.patch.object(QFileDialog, 'exec', return_value=QFileDialog.DialogCode.Accepted)
    mocker.patch.object(QFileDialog, 'selectedFiles', return_value=['maps/Alex_garnet_maps/processed data'])

    # 'actionOpenDirectory' no longer exists: opening a directory is now
    # AddSampleDirectory, wired straight to ProjectManager (see MainToolBar).
    action_open_sample = main_window.findChild(QAction, 'actionAddSampleDirectory')
    assert action_open_sample is not None, "the add-sample-directory action was renamed again"

    # Manually trigger the QAction
    action_open_sample.trigger()

    # Allow any processing to complete
    qtbot.wait(100)

    # Allow any processing to complete
    #qtbot.mouseClick(main_window.menuBar().actionOpenDirectory, Qt.LeftButton)

    # Check if the comboBoxSampleId has the expected value
    combo_box_sample_id = main_window.findChild(QComboBox, 'comboBoxSampleId')
    
    assert combo_box_sample_id.currentText() == 'RM02'
    

@pytest.mark.skip(
    reason="Hangs rather than fails: AnalyteDialog.exec() starts a nested event loop "
           "and the QTimer callback meant to click Done never gets there, so the run "
           "blocks at MainWindow.open_select_analyte_dialog with nothing reported. "
           "Skipped so it cannot stall the suite -- driving this modal needs the "
           "dialog exercised directly rather than through the menu action."
)
def test_select_analytes(qtbot, main_window, mocker, dialogs):
    # `dialogs` as above: importing a sample dirties the project, so without it
    # qtbot's teardown blocks on the unsaved-changes prompt.
    # ipdb.set_trace()  # Insert breakpoint here
    # First, import the sample
    import_sample(qtbot, main_window, mocker)

    # Mock the norm_dict to test against it
    # main_window.analyte_dialog = QDialog()
    # ui = Ui_Dialog()
    # ui.setupUi(main_window.analyte_dialog)
    
    # main_window.analyte_dialog.norm_dict = {}
    items_to_select = [
        ('Li7', 'linear'),
        ('Mg24', 'log'),
    ]
    def on_timeout(items_to_select):
        # Iterate through all rows in tableWidgetSelected to update combo boxes
        assert main_window.analyte_dialog.isVisible()
        if main_window.analyte_dialog.isVisible():
            for row, (analyte, scale) in enumerate(items_to_select):
                for row in range(main_window.analyte_dialog.tableWidgetSelected.rowCount()):
                    combo = main_window.analyte_dialog.tableWidgetSelected.cellWidget(row, 1)
                    analyte_s = main_window.analyte_dialog.tableWidgetSelected.item(row, 0).text()
                    print(analyte_s,analyte)
                    if combo is not None and analyte_s == analyte:  # Make sure there is a combo box in this cell
                        combo.setCurrentText(scale)  # Update the combo box value
                        break
            # Click Done to confirm selection
            done_button = main_window.analyte_dialog.pushButtonDone
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
        assert main_window.analyte_dialog.norm_dict[k] == expected_norm_dict[k]

    