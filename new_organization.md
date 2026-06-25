# LaME-core
core tools that are common to LaME and other application

*Dependencies*: none

*Libraries*:
- format.py
- CustomWidgets.py (moving ColorButton to the color map tool)
- UITheme.py
- icons


# siesta-editor
reST editor

*Dependencies*:
lame-core (format.py, some CustomWidgets and icons, could make dependent on UI Theme)

*Libraries*:
- CodingWidgets.py
- reSTEdit.py
- reSTNotes.py
- reSTRules.py
- SearchTool.py


# blueberry-colortools
color map editor and color dropper/selector tools

*Dependencies*:
lame-core (format.py, some CustomWidgets and icons, could make dependent on UI Theme),
global-geochemistry (ternary_plot.py)

*Libraries*:
- ColorManager.py 
- ColormapEditor.py
- ColorPicker.py
- ColorSelector.py
- ColorButton.py (for use in other programs, not natively needed)


# global-geochemistry
geochemical plotting and analysis (at present no GUI)

*Dependencies*: None
ternary_plot.py
spider.py
radar.py
radar_factory.py
geochronology.py
geothermobarometry.py (to be created)


# LaME
Main GUI and everything else that is specific to it

*Dependencies*:
- lame-core
- siesta-editor (+SearchTool.py)
- blueberry-colortools (+ColorButton.py)
- global_geochemistry

Other tools that could be separated for more generic use, though I would probably put them all under one umbrella.
- Calculator.py
- CustomMplCanvas.py
- CustomTableWidget.py
- CropImage.py
- Logger.py
- ExtendedDF.py
- PolygonManager.py (renamed)