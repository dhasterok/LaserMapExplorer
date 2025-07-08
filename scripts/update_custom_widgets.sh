#!/bin/bash

# -----------------------------------------------------------------------------
# Script Name: update_custom_widgets.sh
# Description:
#   This script automates the conversion of Qt Designer `.ui` and `.qrc` files
#   into Python files, and post-processes certain files to replace base Qt 
#   widgets with custom widget implementations.

#
# Usage:
#   ./update_custom_widgets.sh
#
# Dependencies:
#   - pyrcc6
#   - pyuic6
#   - sed (BSD-style on macOS, GNU-style on Linux)
#   - npx (for blockly build)
#
# Author: D. Hasterok (derrick.hasterok@adelaide.edu.au)
# -----------------------------------------------------------------------------

# Convert Qt .qrc resource file to Python module
pyside6-rcc resources.qrc -o src/ui/resources_rc.py

# -------------------------------------------------------------------------
# STEP 1: Convert simple .ui files to .py using pyuic6
# These files do not require widget replacement
# -------------------------------------------------------------------------
names=("AnalyteSelectionDialog" "FieldSelectionDialog" "IsotopeSelectionDialog" "PlotViewer" "PreferencesWindow" "QuickViewDialog" "SpotImportDialog")

for name in "${names[@]}"; do
  file="src/ui/$name.py"
  pyuic6 -x designer/$name.ui -o $file
  echo "Processing completed for $name."
done

# -------------------------------------------------------------------------
# STEP 2: Convert and modify .ui files that require CustomWidgets
# -------------------------------------------------------------------------
names=("MainWindow" "FileSelectorDialog" "MapImportDialog")

# Helper: infer Qt widget type from object name prefix
get_widget_type() {
  local object_name=$1
  case "$object_name" in
    self.tableWidget*) echo "TableWidget" ;;
    self.lineEdit*) echo "LineEdit" ;;
    self.treeView*) echo "TreeView" ;;
    self.dockWidget*) echo "DockWidget" ;;
    self.comboBox*) echo "ComboBox" ;;
    *) echo "Unknown" ;;
  esac
}

for name in "${names[@]}"; do
  file="src/ui/$name.py"

  pyuic6 -x designer/$name.ui -o $file

  object_names_file="src/widget_list_$name.txt"

  if [[ ! -f "$file" ]]; then
    echo "File $file not found for $name!"
    continue
  fi

  if [[ ! -f "$object_names_file" ]]; then
    echo "File $object_names_file not found for $name!"
    continue
  fi

  # Ensure CustomWidgets import is added
  if ! grep -q "import src.common.CustomWidgets as cw" "$file"; then
    echo "Adding import for src.common.CustomWidgets as cw to $file..."
    sed -i '' "1i\\
import src.common.CustomWidgets as cw
" "$file"
  fi

  # Replace widget declarations with custom equivalents
  echo "Replacing QtWidgets widgets with custom widgets in $file..."
  while IFS= read -r object_name; do
    widget_type=$(get_widget_type "$object_name")
    echo "    object name: $object_name, widget type: $widget_type"
    sed -i '' "s/${object_name} = QtWidgets.Q${widget_type}/${object_name} = cw.Custom${widget_type}/g" "$file"
  done < "$object_names_file"

  # Special case for MainWindow
  if [ "$name" = "mainwindow" ]; then
    echo "Replacing 'import resources_rc' with 'import src.ui.resources_rc'..."
    sed -i '' "s/import resources_rc/import src.ui.resources_rc/g" "$file"
  fi

  echo "Processing completed for $name."
  echo
done
