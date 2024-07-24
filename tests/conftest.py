import pytest
from pytestqt.qtbot import QtBot
from PyQt5.QtWidgets import QFileDialog, QAction,QComboBox, QComboBox
from PyQt5.QtCore import Qt
from main import MainWindow,create_app  # Import the create_app function

@pytest.fixture(scope='module')
def app():
    global app
    """Fixture for creating the QApplication."""
    app = create_app()
    return app

@pytest.fixture
def main_window(qtbot,app):
    """Fixture for creating the MainWindow."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    return main_window

def import_sample(qtbot, main_window, mocker):
    # Mock the file dialog to return the desired directory
    mocker.patch.object(QFileDialog, 'getExistingDirectory', return_value='maps/Alex_garnet_maps/processed data')
    

    # Mock the exec_ method of QFileDialog to simulate the dialog being accepted
    mocker.patch.object(QFileDialog, 'exec_', return_value=QFileDialog.Accepted)
    mocker.patch.object(QFileDialog, 'selectedFiles', return_value=['maps/Alex_garnet_maps/processed data/RM02.lame.csv'])

    # Find the action and trigger it
    action_open_sample = main_window.findChild(QAction, 'actionOpenSample')
    
    
    # Manually trigger the QAction
    action_open_sample.trigger()

    # Allow any processing to complete
    qtbot.wait(100)

    # Allow any processing to complete
    #qtbot.mouseClick(main_window.menuBar().actionOpenDirectory, Qt.LeftButton)

    # Check if the comboBoxSampleId has the expected value
    combo_box_sample_id = main_window.findChild(QComboBox, 'comboBoxSampleId')
    
    assert combo_box_sample_id.currentText() == 'RM02'


