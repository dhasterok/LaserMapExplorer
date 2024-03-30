Export Formats
==============

The data used to produce a plot can be exported by clicking the save button (|icon-save|) from the central plot viewer.  The exported file ...

Polygon Data
------------
Polygon locations are exported by clicking the save button (|icon-save|) below the *Polygon table* from the left toolbox *Filter* tab.  The exported file ...


Profile Data
------------
Profile data are exported by clicking the save button (|icon-save|) on the *Profile* tab in the lower pane.  The exported file will be a csv file with the following format:

Line 1 - Averaging radius (set by ``Point radius``)

Line 2 - Header:

X, Y, Distance, Analyte1 average, Analyte1 uncertainty, ..., AnalyteN average, AnalyteN, uncertainty

The value for the average and uncertainty are determined by the ``Point & error type`` dropdown.

.. |icon-save| image:: _static/icons/icon-save-64.png
    :height: 2ex