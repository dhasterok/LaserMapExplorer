# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Laser Map Explorer (LaME) is a PyQt6-based desktop application for processing and visualizing multi-analyte maps of minerals (LA-ICP-MS, XRF, etc.). The software features geochemical plotting, multidimensional analysis, and an integrated Blockly-based workflow editor.

## Development Environment Setup

### Python Environment
```bash
# Create conda environment with dependencies
conda create --name pyqt python=3.11 --file req.txt
conda activate pyqt

# If the above fails, use manual installation:
conda create --name pyqt python=3.11
conda activate pyqt
conda install python=3.11 pyqt pyqtgraph PyQtWebEngine pandas matplotlib scikit-learn openpyxl numexpr
conda install conda-forge/label/cf201901::scikit-fuzzy
pip install darkdetect cmcrameri rst2pdf opencv-python-headless
pip install -U scikit-fuzzy
```

### JavaScript/Blockly Dependencies
```bash
cd blockly
rm -rf node_modules
npm install
npx webpack --config webpack.config.js
```

## Common Development Commands

### Running the Application
```bash
python main.py
```

### Testing
```bash
# Run tests with pytest (configured for PyQt5 compatibility)
pytest

# Test configuration is in pytest.ini with qt_api=pyqt5 and testpaths=tests
```

### Code Quality
```bash
# Lint with pylint (configured to ignore trailing-whitespace and line-too-long)
pylint src/

# Configuration in .pylintrc
```

### Blockly Development
```bash
# Rebuild Blockly workflow and documentation
./scripts/update_blockly.sh

# This script:
# - Generates JSDoc documentation for blockly/src/*.js files
# - Bundles blockly using webpack
# - Copies documentation to docs/source/_static
```

## Architecture Overview

### Core Structure
- `main.py`: Application entry point with splash screen and theme detection
- `src/app/`: Main application modules
  - `MainWindow.py`: Primary application window and UI orchestration
  - `AppData.py`: Central data management and observable properties
  - `LamePlotUI.py`: Plotting interface and visualization components
  - `DataAnalysis.py`: Data processing and analysis algorithms
  - `StyleToolbox.py`: UI styling and theming components
  - `FieldLogic.py`: Field selection and analyte management logic

### Key Components
- **Data Management**: Centralized through `AppData.py` with observable pattern for UI updates
- **Plotting System**: Multi-plot canvas with support for biplots, ternary plots, radar plots, and trace element compatibility diagrams
- **Blockly Integration**: Visual workflow editor (`src/blockly/`) with custom blocks for geochemical analysis
- **Theme System**: Dark/light mode detection with dynamic stylesheet loading
- **Import/Export**: Support for various data formats through `MapImporter.py` and `LameIO.py`

### UI Architecture
- PyQt6-based with custom widgets in `src/ui/`
- Modular dialog system (`AnalyteDialog.py`, `FieldDialog.py`)
- Canvas-based plotting with `CanvasWidget.py`
- Status bar integration through `LameStatusBar.py`

### Data Flow
1. Data import through `MapImporter.py` or `SpotImporter.py`
2. Processing via `Preprocessing.py` and `DataAnalysis.py`
3. Field logic management through `FieldLogic.py`
4. Visualization through `LamePlotUI.py` and plotting components
5. Results export via `LameIO.py`

## Development Notes

- Uses PyQt6 with high-DPI scaling enabled by default
- Requires both Python and JavaScript/Node.js environments
- Blockly workflows are bundled using webpack and documented with JSDoc
- Theme detection uses `darkdetect` for automatic light/dark mode switching
- Tests use PyQt5 API compatibility layer (qt_api=pyqt5 in pytest.ini)