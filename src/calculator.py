#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 14:24:35 2024

@author: a1904121
"""

from pyqtgraph.Qt import QtWidgets
from src.ui.CalculatorWindow import Ui_CalWindow
import numexpr as ne
from PyQt5.Qt import QStandardItemModel,QStandardItem
## !pyuic5 CalculatorWindow.ui -o CalculatorWindow.py
class CalWindow(QtWidgets.QMainWindow, Ui_CalWindow):

    def __init__(self, isotopes,isotope_df, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        
        self.isotopes = list(isotopes)
        self.isotope_df = isotope_df
        
        self.model = QStandardItemModel(self.listViewIsotopes)
        self.listViewIsotopes.setModel(self.model)
        self.update_isotope_list()

        # Connect signals for add/remove buttons
        self.pushButtonAddElement.clicked.connect(self.add_element)
        self.pushButtonRemoveElement.clicked.connect(self.remove_element)
    
    
    def update_isotope_list(self):
        self.model.clear()
        for element in self.isotopes:
            item = QStandardItem(element)
            self.model.appendRow(item)
            
    def add_element(self):
        selected = self.listViewIsotopes.selectedIndexes()
        if selected:
            element = selected[0].data()  # Get the name of the selected element
            current_text = self.textEditScreen.toPlainText()
            self.textEditScreen.setText(current_text + " " + element + " ")

    def remove_element(self):
        # Implement logic to remove the last added element from textEditScreen
        current_text = self.textEditScreen.toPlainText()
        # Assume elements are separated by spaces or implement your own logic
        elements = current_text.split()
        if elements:
            elements.pop()  # Remove the last element
            new_text = ' '.join(elements)
            self.textEditScreen.setText(new_text)
            
    def calculate_result(self):
        expression = self.textEditScreen.toPlainText()
        # Create a dictionary of variables where keys are element names
        variables = {element: self.isotope_df[element].values for element in self.isotopes}
        try:
            result = ne.evaluate(expression, local_dict=variables)
            self.textEditScreen.setText(str(result))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid Expression: {e}")
            self.textEditScreen.setText("Error: Invalid Expression")