#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 26 01:02:07 2024

@author: shavinkalu
"""
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidgetItem, QComboBox,  QProgressBar
import os
import re
import sys
import pandas as pd
from src.ui.ExcelConcatenator import Ui_ExelConcatenator
import numpy as np
# Excel concatenator gui
# -------------------------------
class excelConcatenator(QtWidgets.QMainWindow, Ui_ExelConcatenator):       
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        
        self.standard_list = ['STDGL', 'NiS', 'NIST610']
        self.sample_ids = []
        self.paths = []
        
        self.statusBar = self.statusBar()
        # Set a message that will be displayed in the status bar
        self.statusBar.showMessage('Ready')
        # Adding a progress bar to the status bar
        self.progressBar = QProgressBar()
        self.statusBar.addPermanentWidget(self.progressBar)
        
        self.pushButtonSaveSelection.clicked.connect(self.save_selection)

        self.pushButtonLoadSelection.clicked.connect(self.load_selection)

        # self.pushButtonDone.clicked.connect(self.accept)
        
        # self.pushButtonCancel.clicked.connect(self.reject)
        
        self.pushButtonImport.clicked.connect(self.import_data)
        
        
        self.tableWidgetMetaData.currentItemChanged.connect(self.on_item_changed)
        
        
        
        
    def save_selection(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    analyte_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{analyte_pair},{selection}\n")

    def load_selection(self):
        
        root_path = QFileDialog.getExistingDirectory(None, "Select a folder", options=QFileDialog.ShowDirsOnly)
        if not root_path:
            return
        
        # List all entries in the directory given by root_path
        entries = os.listdir(root_path)
        subdirectories = [name for name in entries if os.path.isdir(os.path.join(root_path, name))]
        
        
        if subdirectories:
            # If there are subdirectories, use them as sample IDs
            self.sample_ids = subdirectories
            self.paths = [os.path.join(root_path, name) for name in subdirectories]
        else:
            # If no subdirectories, use the directory name itself as the sample ID
            self.sample_ids = [os.path.basename(root_path)]
            self.paths = [root_path]
        for sample_id in self.sample_ids:
            #fill column with column name 'Sample ID' of  self.tableMetaData with sample ids
            self.populate_table()
        
        self.raise_()
        self.activateWindow()
         
    def populate_table(self):
        self.tableWidgetMetaData.setRowCount(len(self.sample_ids))
        for i, sample_id in enumerate(self.sample_ids):
            item = QTableWidgetItem(sample_id)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tableWidgetMetaData.setItem(i, 0, item)
            self.add_combobox(i, 1, ['raw','ppm','LADr ppm'])
            self.add_combobox(i, 2, ['left to right', 'right to left', 'bottom to top', 'top to bottom'])
            self.add_combobox(i, 3, ['left to right', 'right to left', 'bottom to top', 'top to bottom'])
            self.add_combobox(i, 5, ['first','last'])
            
        self.table_update = True

    def add_combobox(self, row, column, items):
        combo = QComboBox()
        combo.addItems(items)
        combo.currentIndexChanged.connect(lambda _, r=row, c=column: self.on_combobox_changed(r, c))
        self.tableWidgetMetaData.setCellWidget(row, column, combo)

    def on_item_changed(self , curr_item, prev_item):
        if prev_item:
            if self.checkBoxApplyAll.isChecked() and prev_item.column() != 0:
                column = prev_item.column()
                for row in range(self.tableWidgetMetaData.rowCount()):
                    if row != prev_item.row():
                        new_item = QTableWidgetItem(prev_item.text())
                        self.tableWidgetMetaData.setItem(row, column, new_item)
            
            # Always check and compute intraline distance when columns 7 or 8 change
            row = prev_item.row()
            sweep_time_item = self.tableWidgetMetaData.item(row, 8)
            sweep_speed_item = self.tableWidgetMetaData.item(row, 9)
        
            if sweep_time_item and sweep_speed_item and sweep_time_item.text().isdigit() and sweep_speed_item.text().isdigit():
                sweep_time = float(sweep_time_item.text())
                sweep_speed = float(sweep_speed_item.text())
                if sweep_time > 0 and sweep_speed > 0:
                    intraline_dist = sweep_time * sweep_speed
                    if self.checkBoxApplyAll.isChecked():
                        for row in range(self.tableWidgetMetaData.rowCount()):
                                self.tableWidgetMetaData.setItem(row, 10, QTableWidgetItem(str(intraline_dist)))
                    else:
                        self.tableWidgetMetaData.setItem(row, 10, QTableWidgetItem(str(intraline_dist)))
            elif sweep_time_item and sweep_speed_item:
                self.statusBar.showMessage('Sweep time and sweep speed should be postive')

    def on_combobox_changed(self, row, column):
        if self.checkBoxApplyAll.isChecked():
            combo = self.tableWidgetMetaData.cellWidget(row, column)
            selected_text = combo.currentText()
            for r in range(self.tableWidgetMetaData.rowCount()):
                if r != row:
                    self.tableWidgetMetaData.cellWidget(r, column).setCurrentText(selected_text)
            
            
    def import_data(self): 
        
        for i,path in enumerate(self.paths):
            data_type = self.tableWidgetMetaData.cellWidget(i,1).currentText().lower()
            file_direction   = self.tableWidgetMetaData.cellWidget(i,2).currentText().lower()
            scan_direction   = self.tableWidgetMetaData.cellWidget(i,3).currentText().lower()
            
            delimiter   = self.tableWidgetMetaData.item(i,4)
            if delimiter:
                delimiter = delimiter.text().strip().lower()
            scan_no_pos   = self.tableWidgetMetaData.cellWidget(i,5).currentText().lower()
            spot_size = float(self.tableWidgetMetaData.item(i,6).text().lower())
            interline_dist = float(self.tableWidgetMetaData.item(i,7).text().lower())

            intraline_dist = float(self.tableWidgetMetaData.item(i,10).text().lower())
            line_sep =20
            line_dir = 'x'
            
            
            for subdir, dirs, files in os.walk(path):
                data_frames = []
                for file in files:
                    if file.endswith('.csv') or file.endswith('.xls') or file.endswith('.xlsx'):
                        file_path = os.path.join(subdir, file)
                        save_prefix = os.path.basename(subdir)
                        if any(std in file for std in self.standard_list):
                            continue  # skip standard files
                        
                        if data_type == 'raw':
                            df = self.read_raw_folder(file,file_path, delimiter, scan_no_pos)
                            data_frames.append(df)
                        elif data_type == 'ppm':
                            df,nr,nc = self.read_ppm_folder(file,file_path, spot_size, line_sep, line_dir)
                            
                            data_frames.append(df)
                        elif data_type == 'ladr ppm':
                            df = self.read_ladr_ppm_folder(file_path)
                        else:
                            QMessageBox.error(self.main_window,"Error", "Unknown Type specified.")
                            return
        
                if data_type == 'raw':
                    final_data = pd.concat(data_frames, ignore_index=True)
                    final_data.insert(2,'X',final_data['ScanNum'] * float(interline_dist))
                    final_data.insert(3,'Y',final_data['SpotNum'] * float(intraline_dist))
                    
                    
                    #determine read direction
                    x_dir = self.orientation(file_direction)
                    y_dir = self.orientation(scan_direction)
                    
                    # Adjust coordinates based on the reading direction and make upper left corner as (0,0)
                    
                    final_data['X'] = final_data['X'] * x_dir
                    final_data['X'] = final_data['X'] - final_data['X'].min()
            
                    final_data['Y'] = final_data['Y'] * y_dir
                    final_data['Y'] = final_data['Y'] - final_data['Y'].min()
                    
                    match file_direction:
                        case 'top to bottom'| 'bottom to top':
                            pass
                        case 'left to right' | 'right to left':
                            Xtmp = final_data['X'];
                            final_data['X'] =final_data['Y'];
                            final_data['Y'] = Xtmp;
                    
                    
                elif data_type == 'ppm':
                    final_data = pd.concat(data_frames, axis = 1)
                    
                    # Create scanNum array
                    scanNum = np.tile(np.arange(1, nc + 1), (nr, 1))  # Tile the sequence horizontally
                    
                    # Create spotNum array
                    spotNum = np.tile(np.arange(1, nr + 1).reshape(nr, 1), (1, nc))  # Tile the sequence vertically
                   
                    final_data.insert(0,'ScanNum',scanNum.flatten('F'))
                    final_data.insert(1,'SpotNum', spotNum.flatten('F'))
                    
                    
                    final_data.insert(2,'X',final_data['SpotNum'] * line_sep)
                    final_data.insert(3,'Y',final_data['SpotNum'] * spot_size)
                    
                    final_data.insert(3,'Time_Sec_',np.nan)
                    
                    print(final_data.head())
                    
            
    def orientation(self,readdir):
   
        match readdir:
            case 'top to bottom'|'left to right' :
                direction = 1
            case 'bottom to top'| 'right to left':
                direction = -1
            case _:
                print('Unknown read direction.')
        
        return direction
        
    def read_raw_folder(self,file_name,file_path, delimiter, delimiter_position):
        if delimiter_position == 'first':
            scan_num = file_name.split(delimiter)[0].strip()
        elif delimiter_position == 'last':
            scan_num = file_name.split(delimiter)[-1].split('.')[0].strip()
   
        df = pd.read_csv(file_path, skiprows=3)
        df.insert(0,'ScanNum',int(scan_num))
        df.insert(1,'SpotNum',range(1, len(df) + 1))
        return df
   
    def read_ppm_folder(self,file_name, file_path, spot_size, line_sep, line_dir):
        
        match = re.search(r' (\w+)_ppm', file_name)
        
        match2 = re.search(r'(\D+)(\d+).csv', file_name) or re.search(r'(\d+)(\D+).csv', file_name)
        
        if match:
            iolite_name =  match.group(1)  # Returns the captured group, which is the text of interest
        elif  match2:
            name = match2.group(2)  # First group: iolite name
            number = match2.group(1)  # Second group: iolite number
            # Create the variable combining name and number
            iolite_name = f"{name}{number}"
        else:
            self.statusBar.showMessage('Iolite name not part of filename')
            return []
        
        # drop rows and columns with all nans 
        df = pd.read_csv(file_path, header=None).dropna(how='all', axis=0).dropna(how='all', axis=1)
       
        print(df.shape)
        if line_dir =='x':
            new_df= pd.DataFrame(df.values.flatten(), columns = [iolite_name])
        elif line_dir =='y':
            new_df= pd(df.values.T.flatten(), columns = [iolite_name])
        r,c = df.shape
        return new_df, r,c
   
    def read_ladr_ppm_folder(self,file_path):
        df = pd.read_csv(file_path)
        df['ScanNum'] = range(1, len(df) + 1)
        df['SpotNum'] = range(1, len(df) + 1)
        # LADR ppm processing might need specific manipulations, adjust as necessary
        return df
        # X = ScanNum*sampleTable.InterlineDistance(i);
        # Y = data.SpotNum*sampleTable.IntralineDistance(i);
    
        # % determine read direction
        # xdir = orientation(sampleTable.FileDirection{i});
        # ydir = orientation(sampleTable.ScanDirection{i});
    
        # % make upper left corner (0,0), i.e., image coordinates
        # X = X*xdir; X = X - min(X);
        # Y = Y*ydir; Y = Y - min(Y);
            
        # file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        # if file_name:
        #     with open(file_name, 'r') as f:
        #         for line in f.readlines():
        #             self.populate_analyte_list(line)
        #     self.update_list()
        #     self.raise_()
        #     self.activateWindow()
                    
app = None
def main():
    global app

    app = QtWidgets.QApplication(sys.argv)

    main = excelConcatenator()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()                 