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
        
        
        # Adding a progress bar to the status bar
        self.progressBar = QProgressBar()
        self.statusBar.addPermanentWidget(self.progressBar)
        
        
        self.pushButtonSaveMetaData.setEnabled(False)
        self.pushButtonLoadMetaData.setEnabled(False)
        
        self.pushButtonSaveMetaData.clicked.connect(self.save_meta_data)
       
        self.pushButtonLoadMetaData.clicked.connect(self.load_meta_data)

        self.pushButtonOpenDirectory.clicked.connect(self.open_directory)
        

        # self.pushButtonDone.clicked.connect(self.accept)
        
        # self.pushButtonCancel.clicked.connect(self.reject)
        
        self.pushButtonImport.clicked.connect(self.import_data)
        
        
        self.tableWidgetMetaData.currentItemChanged.connect(self.on_item_changed)
        
        
        
        
    def load_meta_data(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;All Files (*)")
        status = True
        if file_name:
            data = pd.read_csv(file_name)
    
            # Assuming 'Sample ID' is the column to match sample IDs
            for index, row in data.iterrows():
                sample_id = row['Sample ID']
                if sample_id in self.sample_ids:
                    row_pos = self.sample_ids.index(sample_id)
                    self.update_table_row(row_pos, row)
                else:
                    status = False
              
            if status:
                self.statusBar.showMessage("Metadata loaded successfully")
            else:
                self.statusBar.showMessage("Some metadata sample IDs do not match sample IDs in directory")
    
    def update_table_row(self, row_pos, row_data):
        # Ensure the table has enough rows
        if self.tableWidgetMetaData.rowCount() <= row_pos:
            self.tableWidgetMetaData.insertRow(row_pos)
    
        for col_index, (col_name, value) in enumerate(row_data.items()):
            if col_name == 'Sample ID':
                continue  # Skip the sample ID since it's just a reference, not to be edited
    
            # Handling different widget types in the table
            cell_widget = self.tableWidgetMetaData.cellWidget(row_pos, col_index)
            if isinstance(cell_widget, QComboBox):
                # Set the current index for combo box if the value exists in its options
                index = cell_widget.findText(str(value), Qt.MatchFixedString)
                if index >= 0:
                    cell_widget.setCurrentIndex(index)
                else:
                    self.statusBar.showMessage(f"Value {value} not found in ComboBox options at column {col_index}")
            else:
                # For QTableWidgetItem, just set the text
                item = QTableWidgetItem(str(value))
                self.tableWidgetMetaData.setItem(row_pos, col_index, item)
    
        
            
                        
    def save_meta_data(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
        if file_name:
            # Collect data from QTableWidget
            data = []
            headers = []
            
            # Retrieve headers
            for column in range(self.tableWidgetMetaData.columnCount()):
                header = self.tableWidgetMetaData.horizontalHeaderItem(column)
                if header is not None:
                    headers.append(header.text())
                else:
                    headers.append(f"Column{column}")
            
            # Retrieve cell data
            for row in range(self.tableWidgetMetaData.rowCount()):
                row_data = []
                for column in range(self.tableWidgetMetaData.columnCount()):
                    item = self.tableWidgetMetaData.item(row, column)
                    if item:
                        row_data.append(item.text())
                    else:
                        # Try to fetch the QComboBox if QTableWidgetItem is not found
                        cell_widget = self.tableWidgetMetaData.cellWidget(row, column)
                        if isinstance(cell_widget, QComboBox):
                            row_data.append(cell_widget.currentText())
                        else:
                            row_data.append('')
                data.append(row_data)
            
            # Create a DataFrame and save to CSV
            df = pd.DataFrame(data, columns=headers)
            df.to_csv(file_name, index=False)  # Save DataFrame to CSV without the index
            self.statusBar.showMessage("Metadata saved successfully")

                    
        
        

    def open_directory(self):
        
        root_path = QFileDialog.getExistingDirectory(None, "Select a folder", options=QFileDialog.ShowDirsOnly)
        if not root_path:
            return
        
        self.root_path = root_path 
        self.lineEditRootDirectory.setText(root_path)  # Set the directory path in the QTextEdit
        
        #clear existing contents in tableWidgetMetaData
        self.tableWidgetMetaData.clearContents()
        self.tableWidgetMetaData.setRowCount(0)
        
        self.fill_sample_id_path(root_path)
        
        self.pushButtonSaveMetaData.setEnabled(True)
        self.pushButtonLoadMetaData.setEnabled(True)
        
        for sample_id in self.sample_ids:
            #fill column with column name 'Sample ID' of  self.tableMetaData with sample ids
            self.populate_table()
        
        self.raise_()
        self.activateWindow()
    
    def fill_sample_id_path(self,root_path):
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

            
        

         
    def populate_table(self):
        self.tableWidgetMetaData.setRowCount(len(self.sample_ids))
        for i, sample_id in enumerate(self.sample_ids):
            item = QTableWidgetItem(sample_id)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tableWidgetMetaData.setItem(i, 0, item)
            self.add_combobox(i, 1, ['XMap','Iolite','LADr'])
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
        if not self.checkBoxSaveAtRoot.isChecked():
            save_path = QFileDialog.getExistingDirectory(None, "Select a folder to Save imports", options=QFileDialog.ShowDirsOnly)
            if not save_path:
                return
        else:
            save_path = self.root_path
        total_files = sum(len(files) for path in self.paths for r, d, files in os.walk(path))
        current_progress = 0
        self.progressBar.setMaximum(total_files)
        
        final_data = pd.DataFrame([])
        try:
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
                            
                            if data_type == 'iolite':
                                df = self.read_raw_folder(file,file_path, delimiter, scan_no_pos)
                                data_frames.append(df)
                            elif data_type == 'xmap':
                                df,nr,nc = self.read_ppm_folder(file,file_path, spot_size, line_sep, line_dir)
                                
                                data_frames.append(df)
                            elif data_type == 'ladr':
                                df = self.read_ladr_ppm_folder(file_path)
                                data_frames.append(df)
                        current_progress += 1
                        self.progressBar.setValue(current_progress)
                        self.statusBar.showMessage(f" {current_progress}/{total_files} files imported.")
                        QtWidgets.QApplication.processEvents()  # Process GUI events to update the progress bar
                
                        
                        
                    if data_type == 'iolite':
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
                        
                        
                    elif data_type == 'xmap':
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
                        
                    else:
                        final_data = pd.concat(data_frames, ignore_index=True)
                    
                    file_name = os.path.join(save_path, self.sample_ids[i]+'.csv')
                    print(file_name)
                    print(final_data.head())
                    # final_data.to_csv(file_name, index= False)
                
        except Exception as e:
            self.statusBar.showMessage(f"Error during import: {str(e)}")
            return
        self.statusBar.showMessage("Import completed successfully!")
        self.progressBar.setValue(total_files)  # Ensure the progress bar reaches full upon completion
            
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
   
    def read_ladr_ppm_folder(self,file_name,file_path):
        match = re.search(r' (\w+)_ppm', file_name)
        if match:
            iolite_name =  match.group(1)  # Returns the captured group, which is the text of interest
        else:
            self.statusBar.showMessage('Iolite name not part of filename')
            return []
        data = pd.read_csv(file_path)
        
        # Rename the first two columns to X and Y
        data.columns = ['X', 'Y'] + list(data.columns[2:])
    
        # Calculate unique counts to define the grid
        nr = data['X'].nunique()
        nc = data['Y'].nunique()
    
        # Generate ScanNum and SpotNum
        ScanNum = pd.DataFrame((1 + i for i in range(nc)).repeat(nr)).reset_index(drop=True)
        SpotNum = pd.DataFrame((1 + i for i in range(nr)).repeat(nc)).reset_index(drop=True)
        
        # Insert ScanNum and SpotNum as the first columns
        data.insert(0, 'ScanNum', ScanNum)
        data.insert(1, 'SpotNum', SpotNum)
    
        # Insert a NaN column for Time_Sec_ after 'Y'
        data.insert(data.columns.get_loc('Y') + 1, 'Time_Sec_', pd.Series([float('nan')] * len(data)))
        return data
                    
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