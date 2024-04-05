Right Toolbox
=============

Plot Selector
-------------

.. figure:: _static/screenshots/LaME_Plot_Selector.png
    :align: center
    :alt: LaME interface: right toolbox, plot selector tab
    :width: 232

    The *Plot Selector* is similar to a file tree.  It lists types of fields, samples and the plots available beneath each.

The *Plot Selector* lists the available plots for display.  The default list includes all isotopes and their normalized versions.  Ratios can be added by selecting them from *Isotope Selector*.  All other plots in the list are generated once they have been created and/or explicitly stored.

Isotopes and their normalized equivalents can be sorted alphabetically, by mass, or compatibility.  To change the sorting method, click the |icon-sort| button.

Styling Pane
------------

The properties in the styling pane control the look and feel of plots generated from functions in the left toolbox.  In some cases they also control the type of plot that is generated (e.g., scatter plot or heatmap).

General
+++++++

.. figure:: _static/screenshots/LaME_Styling_General.png
    :align: center
    :alt: LaME interface: right toolbox, styling-general tab
    :width: 232

    The *Styling \> General* contains general settings applied to all plots.

Maps
++++

.. figure:: _static/screenshots/LaME_Styling_Maps.png
    :align: center
    :alt: LaME interface: right toolbox, styling-maps tab
    :width: 232

    The *Styling \> Maps* contains settings exclusive to maps.

Scatter and Heatmap
+++++++++++++++++++

.. figure:: _static/screenshots/LaME_Styling_Scatter_and_Heatmap.png
    :align: center
    :alt: LaME interface: right toolbox, styling-scatter-and-heatmaps tab
    :width: 232

    The *Styling \> Scatter and Heatmap* contains settings for scatter plots and heatmaps including correlations.

+----------------+---------------------------+-----------------------+-----------------------------+------+-------+--------------------------------------------------+----------+-------+----------+
| tab            | Samples                   | Preprocess            | Scatter & Heatmap           | n-Dim        | PCA                                              | Clusters         | Profiles |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| plot type      | map         | correlation | histogram  | gradient | biplot & ternary  | ternary | TEC    radar | variance | vectors   | x vs. y | x vs. y | score | clusters | score | profiles |
+================+=============+=============+============+==========+=========+=========+=========+======+=======+==========+===========+=========+=========+=======+==========+=======+==========+
| axes & labels  |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| x label        | N           | N           | Y          | N        | Y       | Y       | N       | N    | N     | N        | N         | N       | N       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| y label        | N           | N           | Y          | N        | Y       | Y       | N       | Y    | N     | N        | N         | N       | N       | N     | N        | N     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| z label        | N           | N           | N          | N        | N       | Y       | N       | N    | N     | N        | N         | N       | N       | N     | N        | N     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| x limits       | Y           | N           | Y          | Y        | Y       | Y       | Y       | N    | N     | N        | N         | Y       | Y       | Y     | Y        | Y     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| y limits       | Y           | N           | N          | Y        | Y       | Y       | Y       | Y    | N     | N        | N         | Y       | Y       | Y     | Y        | Y     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| aspect ratio   | N           | 1 (fixed)   | Y          | N        | Y       | Y       | N       | Y    | N     | Y        | 1 (fixed) | Y       | Y       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| tick direction | N           | Y           | Y          | N        | Y       | Y       | N       | Y    | N     | Y        | Y         | Y       | Y       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| annotations    |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| font           | Y           | Y           | Y          | Y        | Y       | Y       | Y       | Y    | Y     | Y        | Y         | Y       | Y       | Y     | Y        | Y     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| font size      | Y           | Y           | Y          | Y        | Y       | Y       | Y       | Y    | Y     | Y        | Y         | Y       | Y       | Y     | Y        | Y     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| scales         |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| scale direct.  | Y           | N           | N          | Y        | N       | N       | Y       | N    | N     | N        | N         | N       | N       | Y     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| scale location | Y           | N           | N          | Y        | N       | N       | Y       | N    | N     | N        | N         | N       | N       | Y     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| overlay color  | Y           | N           | N          | Y        | N       | N       | Y       | N    | N     | N        | N         | N       | N       | Y     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| markers        |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| symbol         | N           | N           | N          | N        | Y       | N       | N       | N    | N     | N        | N         | Y       | N       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| size           | N           | N           | N          | N        | Y       | N       | N       | N    | N     | Y        | N         | Y       | N       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| transparency   | N           | N           | Y          | N        | Y       | N       | N       | Y    | Y     | N        | N         | Y       | N       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| lines          |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| line width     | Y (polygon) | N           | N          | N        | Y (fit) | N       | Y       | Y    | Y     | Y        | N         | Y       | Y       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| colors         |                                                                                                                                                                                 |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| color          | Y (spots)   | N           | Y          | N        | Y       | N       | N       | Y    | Y     | Y        | N         | Y       | N       | N     | N        | N     | Y        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| color by field | Y           | N           | N          | Y        | Y       | N       | N       | N    | N     | N        | N         | Y       | N       | N     | N        | N     | Y?       |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| field          | Y           | N           | N          | Y        | Y       | N       | N       | N    | N     | N        | N         | Y       | N       | N     | N        | Y     | Y?       |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| colormap       | Y           | Y           | N          | Y        | Y       | Y       | custom  | Y    | Y     | N        | Y         | Y       | Y       | Y     | N        | N     | Y?       |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| color limits   | Y           | [-1, 1]     | N          | Y        | Y       | Y       | Y       | N    | N     | N        | Y         | Y       | Y       | Y     | N        | N     | Y?       |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| c.bar direct.  | N           | N           | N          | N        | N       | Y       | N       | N    | N     | N        | N         | N       | Y       | N     | N        | N     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| c.bar label    | N           | N           | N          | N        | N       | Y       | N       | N    | N     | N        | N         | N       | Y       | N     | N        | N     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+
| resolution     | N           | N           | N          | N        | N       | Y       | N       | N    | N     | N        | N         | N       | Y       | N     | N        | N     | N        |
+----------------+-------------+-------------+------------+----------+---------+---------+---------+------+-------+----------+-----------+---------+---------+-------+----------+-------+----------+

| tab            | Samples and Fields        | Preprocessing                | Scatter & Heatmap |  |  | n-Dim |  | PCA |  |  |  |  | Clustering |  | Propfiling |
|                | analyte     | correlation | histogram      | gradient    | scatter       | heatmap | ternary | TEC | radar | variance | vectors | PCx vs PCy | PCx vs PCy | PCA | clusters | cluster | profiles |
| plot type      | map         |             |                |             |               |  | map |  |  |  |  | scatter | heatmap | score |  | score |  |
| axes & labels  |                                                                   |
| x label        | N           | N           | Y              | N           | Y             | Y | N | N | N | N | N | Y | Y | N | N | N | Y |
| y label        | N           | N           | Y              | N           | Y             | Y | N | Y | N | N | N | Y | Y | N | N | N | N |
| z label        | N           | N           | N              | N           | N/Y (ternary) | N/Y (ternary) | N | N | N | N | N | N | N | N | N | N | N |
| x limits       | Y           | N           | Y              | Y           | Y             | Y | Y | N | N | N | N | Y | Y | Y | Y | Y | Y |
| y limits       | Y           | N           | Y              | Y           | Y             | Y | Y | Y | N | N | N | Y | Y | Y | Y | Y | N |
| aspect ratio   | N           | N 1 (fixed) | Y              | N           | Y             | Y | N | Y | N | Y | N 1 (fixed) | Y | Y | N | N | N | Y |
| tick direction | N           | Y           | Y              | N           | Y             | Y | N | Y | N | Y | Y | Y | Y | N | N | N | Y |
| annotations    |    |
| font           | Y           | Y           | Y              | Y           | Y             | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| font size      | Y           | Y           | Y              | Y           | Y             | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| scales         |  |
| scale direct.  | Y           | N           | N              | Y           | N             | N | Y | N | N | N | N | N | N | Y | Y | Y | Y |
| scale location | Y           | N           | N              | Y           | N             | N | Y | N | N | N | N | N | N | Y | Y | Y | Y |
| overlay color  | Y           | N           | N              | Y           | N             | N | Y | N | N | N | N | N | N | Y | Y | Y | Y |
| markers        |  |
| symbol         | N/Y (spots) | N           | N              | N/Y (spots) | Y             | N | N | N | N | Y | N | Y | N | N/Y (spots) | N/Y (spots) | N/Y (spots) | Y |
| size           | N/Y (spots) | N           | N              | N/Y (spots) | Y             | N | N | N | N | Y | N | Y | N | N/Y (spots) | N/Y (spots) | N/Y (spots) | Y |
| transparency   | N/Y (spots) | N           | Y              | N/Y (spots) | Y             | N | N | Y | Y | N | N | Y | N | N/Y (spots) | N/Y (spots) | N/Y (spots) | N |
| lines          |  |
| line width     | N/Y (poly)  | N           | N              | N/Y (poly)  | Y (fit)/ N (tern) | Y (fit)/ N (ternary) | N | Y | Y | Y | N | Y (vectors) | Y | N/Y (poly) | N/Y (poly) | N/Y (poly) | Y (error bars) |
| colors         |  |
| color          | N           | N           | Y/N (clusters) | N           | Y/N (not none) | N | N | Y (1)/N (clusters) | Y (1)/N (clusters) | Y | N | Y/N (not none) | N | N | N | N | Y |
| color by field | Y           | N           | Y              | Y           | Y             | N | N | Y | Y | N | N | N/Y (not none) | N | N | N | N | N |
| field          | Y           | N           | Y              | Y           | Y             | N | N | N | N | N | N | Y | N | Y (score) | N | Y (score) | N |
| colormap       | Y           | Y           | N/Y (clusters) | Y           | N/Y (not none) | Y | custom | Y (clusters) | Y (clusters) | N | Y | N/Y (not none) | Y | Y | Y | Y | Y |
| color limits   | Y           | Y [-1, 1]   | N/Y (clusters) | Y           | N/Y (not none) | Y | N | N | N | N | Y | N/Y (not none) | Y | Y | N | Y | N |
| c.bar direct.  | Y           | Y           | N              | Y           | N/Y (not none) | Y | N | N | N | N | Y | N/Y (not none) | Y | Y | N | Y | N |
| c.bar label    | Y           | N           | N              | Y           | N/Y (not none) | Y | N | N | N | N | N | N/Y (not none) | Y | Y | N | Y | N |
| resolution     | N           | N           | N              | N           | N             | Y | N | N | N | N | N | N | Y | N | N | N | N |

spots use overlay color for outline and color by field, field value for fill color

Clusters
++++++++

.. figure:: _static/screenshots/LaME_Styling_Clusters.png
    :align: center
    :alt: LaME interface: right toolbox, styling-clustering tab
    :width: 232

    The *Styling \> Clustering* contains settings for scatter plots and heatmaps including correlations.

Calculator
----------

.. figure:: _static/screenshots/LaME_Calculator.png
    :align: center
    :alt: LaME interface: right toolbox, calculator tab
    :width: 232

    The *Calculator* can be used to compute custom fields.  Expressions can be typed directly into the edit box, by clicking the buttons.

Use the calculator ( |icon-calculator| ) to create custom fields.  These custom fields can be used to as dimensions on plots or to set marker color values.  Once created, custom fields will be added to associated drop downs.

.. |icon-sort| image:: _static/icons/icon-sort-64.png
    :height: 2ex

.. |icon-calculator| image:: _static/icons/icon-calculator-64.png
    :height: 2ex