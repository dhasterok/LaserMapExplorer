"""LA-ICP-MS raw-data calibration backend: background subtraction, instrument
drift correction, and standard-based calibration to ppm for raw line-scan
data files.

Pure Python, no PyQt imports anywhere in this package except ``app.py`` and
``dock_widgets.py``. Reference-material compositions are external YAML config
files (see ``reflib.py`` and ``resources/calibration/reference_materials/*.yaml``)
-- no standard-specific assumptions are hardcoded outside those configs.
"""
