import pytest
from pytestqt.qtbot import QtBot
from PyQt5.QtWidgets import QFileDialog, QAction,QComboBox
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

def test_import_sample(qtbot, main_window, mocker):
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
    #qtbot.mouseClick(main_window.menuBar().actionOpenDirectory, Qt.LeftButton)

    # Check if the comboBoxSampleId has the expected value
    combo_box_sample_id = main_window.findChild(QComboBox, 'comboBoxSampleId')
    
    assert combo_box_sample_id.currentText() == 'RM02'
    
# @pytest.fixture
# def another_widget(qtbot):
#     widget = AnotherWidget()
#     qtbot.addWidget(widget)
#     return widget

# def test_another_widget_initial_state(another_widget):
#     assert another_widget.some_property == expected_initial_value  # Adjust the expected initial value

# def test_another_widget_interaction(qtbot, another_widget):
#     qtbot.keyClicks(another_widget.some_input, "text")
#     assert another_widget.some_output == expected_output  # Adjust the expected outcome