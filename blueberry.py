"""
Blüberry - Colormap Editor

A simple dialog to create and edit colormaps.

Author: Derrick Hasterok
Date: 2024-06-20
"""
import sys
from PyQt6.QtWidgets import QDialog, QApplication
from src.common.ColormapEditor import ColormapEditorDialog

# Example usage and test
def main():
    app = QApplication(sys.argv)
    
    # Sample existing colormaps
    existing_maps = { }
    
    dialog = ColormapEditorDialog(existing_maps, title="Blüberry")
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        model = dialog.get_colormodel()
        print(f"Colormap saved: {len(model.color_points)} {'discrete' if model.is_discrete else 'continuous'} colors")
        
        for i, point in enumerate(model.color_points):
            print(f"  Point {i}: {point.color.name()} at position {point.position:.3f}")
    
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())