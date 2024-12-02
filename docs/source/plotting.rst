Plotting
********

There are a number of plots that are possible within *LaME*.  A list of plot types and where they are generated is given below.  If you would like a new type of plot or additional options, file a feature request on the GitHub page or contact us (:doc:`contact`).

.. table::
    +---------------------------+---------------------------+
    | Plot type                 | Tab                       |
    +===========================+===========================+
    | map                       |                           |
    +---------------------------+---------------------------+
    | - linear                  | *Plot selector*           |
    | - log                     |                           |
    | - normalized              |                           |
    | - gradient map            | *Preprocess*              |
    +---------------------------+---------------------------+
    | correlation               |                           |
    +---------------------------+---------------------------+
    | - Pearson                 | *Preprocess*              |
    | - Spearman                |                           |
    | - Kendall                 |                           |
    | - squared correlation     |                           |
    +---------------------------+---------------------------+
    | histogram                 |                           |
    +---------------------------+---------------------------+
    | - normal                  | *Preprocessing*           |
    | - KDE                     |                           |
    +---------------------------+---------------------------+
    | scatter and heatmaps      |                           |
    +---------------------------+---------------------------+
    | - scatter                 | *Scatter and Heatmaps*    |
    | - 2-D histogram (heatmap) |                           |
    | - ternary colored map     |                           |
    +---------------------------+---------------------------+
    | multidimensional          |                           |
    +---------------------------+---------------------------+
    | - TEC (spider)            | *n-Dim*                   |
    | - radar                   |                           |
    +---------------------------+---------------------------+
    | dimensional reduction     |                           |
    +---------------------------+---------------------------+
    | - explained variance      | *PCA*                     |
    | - vector heatmap          |                           |
    | - PCA scatter             |                           |
    | - PCA score               |                           |
    | - PCA heatmap             |                           |
    +---------------------------+---------------------------+
    | clustering                |                           |
    +---------------------------+---------------------------+
    | - cluster map             | *Clustering*              |
    | - cluster scores          |                           |
    | - cluster performance     |                           |
    +---------------------------+---------------------------+
    | profile                   |                           |
    +---------------------------+---------------------------+
    | geochemistry profile      | *Profiling*               |
    +---------------------------+---------------------------+

Map-form plots
==============

Map-form plots display elemental concentration distributions from LA-ICP-MS data as color-intensity maps, with all analytes sharing the same spatial dimensions from simultaneous measurement points.

Gradient Maps 
=============

Gradient maps highlight regions of rapid change in elemental concentrations, making them particularly useful for identifying mineral boundaries and compositional zoning. These maps calculate the rate of change between adjacent pixels, with brighter areas indicating steeper concentration gradients.

Correlation
===========

Correlation plots visualize relationships between analytes using different statistical methods (Pearson, Spearman, Kendall). The plots display correlation coefficients as a color-coded matrix, helping identify co-varying elements.

Histograms
==========

Histogram plots show the frequency distribution of concentration values (typically in ppm or wt%) for individual analytes within a sample. Available as standard histograms or kernel density estimation (KDE) plots for smoother distribution visualization.

Scatter and Heatmaps
====================

This category includes three visualization types:
- Scatter plots showing relationships between two variables
- 2-D histograms (heatmaps) displaying point density in variable space
- Ternary colored maps projecting three-component relationships onto the sample space

Multidimensional
================

Trace element compatibility (TEC)
---------------------------------
TEC diagrams (spider plots) display multiple elements normalized to a reference composition, arranged by geochemical compatibility.

Radar
-----
Radar plots display multiple variables on radial axes, offering an alternative view of multidimensional relationships.

Dimensional deduction methods
=============================

Principal Component Analysis visualizations include:
- Explained variance plots showing component significance
- Vector heatmaps displaying element contributions
- PCA scatter plots showing sample relationships in PC space
- PCA score maps showing spatial distribution of components
- PCA heatmaps displaying density in PC space

Clustering
==========

Three main clustering visualizations:
- Cluster maps showing spatial distribution of groups
- Cluster scores showing degree of group membership
- Cluster performance plots for optimizing cluster numbers

Profile
=======
Profile plots display variations in analyte concentrations along user-defined transects across the sample.
