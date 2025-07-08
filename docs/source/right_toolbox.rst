Plot and Property Toolbox (Right)
*********************************

The *Plot and Property Toolbox* consists of three major components: the Plot Selector, the Styling Pane, and the Calculator. These tools work together to provide comprehensive control over plot creation, customization, and data manipulation.

Plot Selector
=============

The `plot type <plotting.html#plot-types>`_ dropdown list sits above the *Plot Selector*.  It updates the types of plots available to each of the *Control Toolbox* tabs.  In case the plot does not update automatically, the |icon-launch| button can be clicked.

The *Plot Selector* lists the available plots for display.  By default, it includes all analytes and their normalized versions.  Ratios can be added by selecting them from the *Analyte Selector* in the *Main Toolbar*.  Other plots will also appear in the list once they've been created or explicitly saved.

.. figure:: _static/screenshots/LaME_Plot_Selector.png
    :align: center
    :alt: LaME interface: right toolbox, plot selector tab
    :width: 232

    The *Plot Selector* organizes plots in a tree structure by type and sample.


Analytes and their normalized equivalents can be sorted alphabetically, by mass, or compatibility using the |icon-sort| button.  To remove plots, use the |icon-trash| button.  

Styling Pane
============

The Styling Pane controls the appearance of plots generated from functions in the *Control Toolbox*.  A complete list is given in the table below along with each of the properties that can be changed.  Not all properties are available for each type of plot.  Styles can be customized and saved using the save (|icon-save|) button and the saved themes can be recalled in future sessions.

.. table:: 

+------------------------+------------------------------------+
| tab                    | plot types                         |
+========================+====================================+
|| Preprocess            || field map                         |
||                       || gradient map                      |
+------------------------+------------------------------------+
|| Field Viewer          || field map                         |
||                       || histogram                         |
||                       || correlation                       |
+------------------------+------------------------------------+
|| Scatter \& Heatmaps   || scatter plot                      |
||                       || ternary scatter plot              |
||                       || heatmap                           |
||                       || ternary heatmap                   |
||                       || ternary map                       |
+------------------------+------------------------------------+
|| n-Dim                 || trace element compatibility (TEC) |
||                       || radar/spider web plot             |
+------------------------+------------------------------------+
|| Dimensional Reduction || variance                          |
||                       || basis vectors                     |
||                       || scatter                           |
||                       || heatmap                           |
||                       || score map                         |
+------------------------+------------------------------------+
|| Clustering            || clusters                          |
||                       || score map                         |
||                       || performance                       |
+------------------------+------------------------------------+
| P-T-t Functions        | TBD                                |
+------------------------+------------------------------------+


Axes and Labels
---------------

The axes and labels are initially filled with default values but can be edited to update the plot.

.. figure:: _static/screenshots/LaME_Styling_Axes_Labels.png
    :align: center
    :alt: LaME interface: right toolbox, styling-axes-and-labels tab
    :width: 232

    The Styling > Axes and Labels contains general settings applied to all plots.

Annotations and Scales
----------------------

The Annotations and Scales tab provides settings to add a scale bar to the plot and adjust the legend bar on the side of the plot.

.. figure:: _static/screenshots/LaME_Styling_Annotations.png
    :align: center
    :alt: LaME interface: right toolbox, styling-annotations tab
    :width: 232

    The Styling \> Annotations contains font type and font size settings.

Markers and Lines
-----------------

The Markers tab contains settings for markers and lines used in scatter, ternary, and PCA plots. For other plot types, these settings are grayed out. Symbol options, symbol size, and transparency can be modified in this tab.

.. figure:: _static/screenshots/LaME_Styling_Markers.png
    :align: center
    :alt: LaME interface: right toolbox, Styling-markers tab
    :width: 232

    The Styling \> Markers and Lines tab contains settings for markers and lines used in various plots.

Coloring
--------

The Coloring tab provides a range of options for customizing the color representation of data in plots and maps.  

.. figure:: _static/screenshots/LaME_Styling_Colors.png
    :align: center
    :alt: LaME interface: right toolbox, Styling-colors tab
    :width: 232

    The Styling \> Colors contains settings for changing color options.

Regression
----------

*Regression* is currently under development and not available.

.. |icon-sort| image:: _static/icons/icon-sort-64.png
    :height: 2ex

.. |icon-launch| image:: _static/icons/icon-launch-64.png
    :height: 2ex

.. |icon-save| image:: _static/icons/icon-save-file-64.png
    :height: 2ex

.. |icon-trash| image:: _static/icons/icon-delete-64.png
    :height: 2ex

.. |icon-calculator| image:: _static/icons/icon-calculator-64.png
    :height: 2ex

.. |icon-link| image:: _static/icons/icon-link-64.png
    :height: 2ex

.. |icon-unlink| image:: _static/icons/icon-unlink-64.png
    :height: 2ex

.. |icon-mask-light| image:: _static/icons/icon-mask-light-64.png
    :height: 2ex

.. |icon-mask-dark| image:: _static/icons/icon-mask-dark-64.png
    :height: 2ex