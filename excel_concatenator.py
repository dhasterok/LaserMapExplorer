#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 14:14:26 2024

@author: a1904121
"""

import os
import pandas as pd
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt



def read_raw_folder(file_name,file_path, delimiter, delimiter_position):
    if delimiter_position == 'first':
        scan_num = file_name.split(delimiter)[0].strip()
    elif delimiter_position == 'last':
        scan_num = file_name.split(delimiter)[-1].split('.')[0].strip()

    df = pd.read_csv(file_path, skiprows=3)
    df['ScanNum'] = int(scan_num)
    df['SpotNum'] = range(1, len(df) + 1)
    return df

def read_ppm_folder(file_path, spot_size, line_sep, line_dir):
    df = pd.read_csv(file_path)
    df['ScanNum'] = range(1, len(df) + 1)
    df['SpotNum'] = range(1, len(df) + 1)

    if line_dir == 'x':
        df['X'] = df['SpotNum'] * spot_size
        df['Y'] = df['ScanNum'] * line_sep
    else:
        df['X'] = df['ScanNum'] * line_sep
        df['Y'] = df['SpotNum'] * spot_size
    return df

def read_ladr_ppm_folder(file_path):
    df = pd.read_csv(file_path)
    df['ScanNum'] = range(1, len(df) + 1)
    df['SpotNum'] = range(1, len(df) + 1)
    # LADR ppm processing might need specific manipulations, adjust as necessary
    return df


def excel_concatenator(type='raw', batch=False, overwrite=False, delimiter='-', delimiter_position='first',
                       standard_list=None, spot_size=20, line_sep=20, line_dir='x'):
    if standard_list is None:
        standard_list = ['STDGL', 'NiS', 'NIST610']

    app = QApplication([])
    root_path = QFileDialog.getExistingDirectory(None, "Select a folder", options=QFileDialog.ShowDirsOnly)
    if not root_path:
        return

    if batch:
        file_type_filter = "CSV files (*.csv);;Excel files (*.xls *.xlsx)"
        meta_path, _ = QFileDialog.getOpenFileName(None, "Select metadata file", filter=file_type_filter)
        if not meta_path:
            return
        metadata = pd.read_csv(meta_path)

    data_frames = []
    for subdir, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith('.csv') or file.endswith('.xls') or file.endswith('.xlsx'):
                file_path = os.path.join(subdir, file)
                save_prefix = os.path.basename(subdir)
                if any(std in file for std in standard_list):
                    continue  # skip standard files
                
                if type == 'raw':
                    df = read_raw_folder(file,file_path, delimiter, delimiter_position)
                elif type == 'ppm':
                    df = read_ppm_folder(file,file_path, spot_size, line_sep, line_dir)
                elif type == 'ladr ppm':
                    df = read_ladr_ppm_folder(file_path)
                else:
                    QMessageBox.warning(None, "Error", "Unknown Type specified.")
                    return

                data_frames.append(df)

    final_data = pd.concat(data_frames, ignore_index=True)
    if not final_data.empty:
        output_file = os.path.join(root_path, save_prefix + '.csv')
        if not overwrite and os.path.exists(output_file):
            response = QMessageBox.question(None, 'Confirm Overwrite',
                                            "File exists. Overwrite?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.Yes:
                final_data.to_csv(output_file, index=False)
        else:
            final_data.to_csv(output_file, index=False)

    QApplication.quit()

if __name__ == "__main__":
    excel_concatenator(type='raw', batch=False, overwrite=True, delimiter_position='last')
