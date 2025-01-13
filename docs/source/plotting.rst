Plotting
********

There are a number of plots that are possible within *LaME*.  A list of plot types and where they are generated is given below.  If you would like a new type of plot or additional options, file a feature request on the GitHub page or contact us (:doc:`contact`).

.. table:: 
+---------------------------+---------------------------+
| Plot type                 | Tab                       |
+===========================+===========================+
| map                       |                           |
+---------------------------+---------------------------+
| - linear                  | *Samples and Fields*      |
| - log                     |                           |
| - normalized              |                           |
| - gradient map            | *Preprocess*              |
+---------------------------+---------------------------+
| correlation               |                           |
+---------------------------+---------------------------+
| - Pearson                 | *Preprocess*              |
| - Spearman                |                           |
| - Kendall                 |                           |
+---------------------------+---------------------------+
| histogram                 |                           |
+---------------------------+---------------------------+
| - normal                  | *Preprocessing*           |
| - KDE                     |                           |
+---------------------------+---------------------------+
| sctter and heatmaps       |                           |
+---------------------------+---------------------------+
| - scatter                 | *Scatter and Heatmaps*    |
| - heatmap                 |                           |
| - ternary colored map     |                           |
+---------------------------+---------------------------+
| multidimensional          |                           |
+---------------------------+---------------------------+
| - TEC (spider)            | *n-Dim*                   |
| - radar                   |                           |
+---------------------------+---------------------------+
| PCA                       |                           |
+---------------------------+---------------------------+
| - variance                | *PCA*                     |
| - vector                  |                           |
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

Map visualizations are the foundation of spatial analysis in *LaME*. These plots display the distribution of elemental concentrations across your sample, with options for:

- Linear or logarithmic scaling to highlight different concentration ranges
- Gradient mapping to emphasize compositional boundaries
- Normalization to reference values for comparative analysis
- Custom colormaps and scaling for optimal feature visibility

The map display automatically updates to reflect any active filters, masks, or preprocessing steps, making it easy to focus on regions of interest.

Correlation
===========

Correlation plots visualize relationships between analytes using different statistical methods (Pearson, Spearman, Kendall). The plots display correlation coefficients as a color-coded matrix, helping identify co-varying elements.

Histograms
==========

Histogram plots show the frequency distribution of concentration values (typically in ppm or wt%) for individual analytes within a sample. Available as standard histograms or kernel density estimation (KDE) plots for smoother distribution visualization.

`Scatter and Heatmaps <analysis_visualization.html#scatters-and-heatmaps>`_
===================

This category includes three visualization types:

- Scatter plots showing relationships between two variables
- Heatmaps displaying point density in variable space
- Ternary colored maps projecting three-component relationships onto the sample space

`Multidimensional <analysis_visualization.html#n-dim-analysis>`_
================================================================

Trace element compatibility (TEC)
---------------------------------
TEC diagrams (spider plots) display multiple elements normalized to a reference composition, arranged by geochemical compatibility.

Radar
-----
Radar plots display multiple variables on radial axes, offering an alternative view of multidimensional relationships.

`PCA <multidimensional.html#principal-component-analysis>`_
===========================================================

Principal Component Analysis visualizations include:

- Explained variance plots showing component significance
- Vector heatmaps displaying element contributions
- PCA scatter plots showing sample relationships in PC space
- PCA score maps showing spatial distribution of components
- PCA heatmaps displaying density in PC space

`Clustering <multidimensional.html#clustering>`_
================================================

Three main clustering visualizations:

- Cluster maps showing spatial distribution of groups
- Cluster scores showing degree of group membership
- Cluster performance plots for optimizing cluster numbers

`Profile <profiles.html>`_
=======
Profile plots display variations in analyte concentrations along user-defined transects across the sample.
