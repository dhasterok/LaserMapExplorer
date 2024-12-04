Control Toolbox (Left)
**********************

The *Control Toolbox* provides essential functions for data management, analysis, and visualization. 

Samples and Fields
==================

The *Samples and Fields* tab offers crucial functions for data management.  Here, reference values can be changed, which updates normalized data across plots and calculated fields.  Additionally, the correlation method can be adjusted, which automatically updates all correlation plots to reflect the chosen approach.  The tab also allows switching between linear and logarithmic scales, and setting units for display.

.. figure:: _static/screenshots/LaME_Samples_and_Fields.png
    :align: center
    :alt: LaME interface: left toolbox, samples and fields tab
    :width: 315

    *Samples and Fields* tab with options for data manipulation and correlation visualization.

Autoscaling (|icon-autoscale|) addresses a common calibration issue where low counts convert to negative concentrations after calibration.  This often results from differences in ablation properties between calibration and sample minerals, causing particular problems with log-scaled data.  To mitigate this, *LaME* applies a linear compression to the data, fixing the upper end and shifting the lower end to a small positive value.  While this alters concentrations slightly, it minimally affects larger values.  The autoscaling process, performed by default, clips extreme high and low concentrations to the scale's limits.  Although autoscaling can influence statistics, it generally improves mean estimates by reducing the impact of unreasonably high values.

Histogram equalization (|icon-histeq|) offers an alternative to autoscaling that preserves the original data.  This method assigns colors based on equal quantiles, proving particularly useful for datasets with wide value ranges or multi-modal distributions.  While effective for visualizing complex distributions, be aware that it may amplify noise at the expense of real features.

Modifying data scaling is similar to cropping and clears existing filters, so these options should be used judiciously.

Preprocess
==========

The *Preprocessing* tab provides tools for data enhancement and noise reduction.  These modifications can improve performance, stability, and visual characteristics.  Note that these changes may impact certain statistical calculations, such as mean values and standard deviations.

.. figure:: _static/screenshots/LaME_Preprocess.png
    :align: center
    :alt: LaME interface: left toolbox, preprocessing tab
    :width: 315

    *Preprocessing* tab with tools for data enhancement and noise reduction.

Noise Reduction
---------------

Noise reduction (|icon-noise-reduction|) smooths data to enhance clarity.  It can be applied solely to maps for viewing or to Analysis Data before generating plots and analyses.  The application method can be selected from the Method dropdown. *LaME* offers five noise reduction methods:

* Median: Computes the median value over a specified kernel size, smoothing across the entire image
* Gaussian: Applies Gaussian weighting over a specified kernel size, smoothing across the entire image
* Wiener: Utilizes a Fourier domain low-pass filter for smoothing
* Edge-preserving: Smooths data while maintaining sharp edges, recommended for most cases but may over-smooth within grains
* Bilateral: Combines Gaussian smoothing with edge preservation, offering less aggressive smoothing than the edge-preserving method

Additionally, the Gradient checkbox converts the regular analyte map into a gradient map, highlighting areas of rapid change in analyte concentration.  This can be particularly useful for identifying mineral boundaries or compositional zoning.

Histogram
---------

The Histogram tool produces visualizations of data distribution.  The presentation of the histogram can be adjusted by modifying either the bin width or the number of bins. Changing the number of bins automatically updates the bin width.  This flexibility enables fine-tuning of the histogram to best represent the data distribution. See :doc:`plotting` for examples of different histogram visualizations.

Spot Data
=========

*Spot data* functionality is currently under development and not available.

Polygons
========

The Polygons tab enables creation and management of polygon masks for data filtering.  Polygon masks are a powerful tool for isolating specific regions in your maps, such as individual minerals or zones of interest.  You can create multiple polygons and link them together for complex region selection.  For detailed instructions on creating and using polygon masks, see the Polygon Masking section in `Filtering <filtering.html#polygon-masking>`_.

.. figure:: _static/screenshots/LaME_Polygons.png
    :align: center
    :alt: LaME interface: left toolbox, profiling tab
    :width: 315

    *Polygons* tab with tools for creating and editing polygons.

Profiling
=========

The *Profiling* tab provides tools for analyzing compositional variations along user-defined paths across your sample.  This functionality is particularly valuable for examining mineral zoning, reaction boundaries, and diffusion profiles.  When a profile is created, it appears in the *Profile* tab in *Lower Tabs* for detailed analysis. See :doc:`profiles` for comprehensive information about creating and analyzing compositional profiles.

.. figure:: _static/screenshots/LaME_Profiling.png
    :align: center
    :alt: LaME interface: left toolbox, profiling tab
    :width: 315

    *Profiling* tab with tools for creating cross-sections.

Scatter and Heatmaps
====================

The *Scatter and Heatmaps* tab provides tools for creating scatter plots and heatmaps in both 2D (biplots) and 3D (ternary) dimensions.  See `Scatter and Heatmaps <analysis_visualization.html#scatter-and-heatmaps>`_ for comprehensive details about different visualization methods and their applications.  Scatter data can be colored by a field set in the Colormap dropdown list, allowing for multi-variable visualization.  Additionally, maps can be generated with colors defined by pixel positions within a ternary diagram, offering a unique perspective on three-component systems.

.. figure:: _static/screenshots/LaME_Scatter_and_Heatmaps.png
    :align: center
    :alt: LaME interface: left toolbox, scatter and heatmaps tab
    :width: 315

    *Scatter and Heatmaps* tab for creating various 2D and 3D visualizations.

n-Dim
=====

The *n-Dim* tab enables visualization of multidimensional data through radar plots and trace element compatibility (spider) diagrams. Users can select reference values for normalization, build custom analyte sets or use predefined groups (majors, full trace, REE, metals), and control data representation through quantile selection.  For detailed information about these visualization techniques, see `n-Dim Analysis <analysis_visualization.html#n-dim-analysis>`_.

.. figure:: _static/screenshots/LaME_n-Dim.png
    :align: center
    :alt: LaME interface: left toolbox, n-Dim tab
    :width: 315

    *n-Dim* tab for creating multidimensional plots like spider diagrams and radar plots.

Dimensional Reduction
=====================

The *Dimensional Reduction* tab offers tools for principal component analysis (PCA) visualization, a key technique for reducing the dimensionality of complex datasets.  See `Principal Component Analysis <multidimensional.html#principal-component-analysis>`_ for comprehensive details about PCA methodology and interpretation.

.. figure:: _static/screenshots/LaME_PCA.png
    :align: center
    :alt: LaME interface: left toolbox, PCA tab
    :width: 315

    *Dimensional Reduction* tab with tools for principal component analysis visualization.

Clustering
==========

The *Clustering* tab identifies data subsets with similar multidimensional characteristics.  This functionality is often used to isolate or exclude specific minerals from analyses.  *LaME* implements two clustering methods: K-means and Fuzzy c-means.  For detailed information about clustering methods and applications, see `Clustering <multidimensional.html#clustering>`_.

The interface provides essential controls for cluster number, distance metrics, and initialization parameters, with options to incorporate dimensional reduction through PCA.  Once clusters are computed, they can be used to create masks for subsequent analyses.

.. figure:: _static/screenshots/LaME_Clustering.png
    :align: center
    :alt: LaME interface: left toolbox, clustering tab
    :width: 315

    *Clustering* tab for multivariate data classification and analysis.

P-T-t Functions
===============

P-T-t Functions for computing thermometry, barometry, isotopic dating, and multicomponent diffusion are planned for future implementation. 

.. |icon-atom| image:: _static/icons/icon-atom-64.png
    :height: 2.5ex

.. |icon-crop| image:: _static/icons/icon-crop-64.png
    :height: 2.5ex

.. |icon-fit-to-width| image:: _static/icons/icon-fit-to-width-64.png
    :height: 2.5ex

.. |icon-autoscale| image:: _static/icons/icon-autoscale-64.png
    :height: 2.5ex

.. |icon-histeq| image:: _static/icons/icon-histeq-64.png
    :height: 2.5ex

.. |icon-noise-reduction| image:: _static/icons/icon-noise-reduction-64.png
    :height: 2.5ex

.. |icon-map| image:: _static/icons/icon-map-64.png
    :height: 2.5ex

.. |icon-edge-detection| image:: _static/icons/icon-spotlight-64.png
    :height: 2.5ex

.. |icon-move-point| image:: _static/icons/icon-move-point-64.png
    :height: 2.5ex

.. |icon-add-point| image:: _static/icons/icon-add-point-64.png
    :height: 2.5ex

.. |icon-remove-point| image:: _static/icons/icon-remove-point-64.png
    :height: 2.5ex

.. |icon-filter| image:: _static/icons/icon-filter-64.png
    :height: 2.5ex

.. |icon-filter2| image:: _static/icons/icon-filter2-64.png
    :height: 2.5ex

.. |icon-link| image:: _static/icons/icon-link-64.png
    :height: 2.5ex

.. |icon-unlink| image:: _static/icons/icon-unlink-64.png
    :height: 2.5ex

.. |icon-mask-light| image:: _static/icons/icon-mask-light-64.png
    :height: 2.5ex

.. |icon-mask-dark| image:: _static/icons/icon-mask-dark-64.png
    :height: 2.5ex

.. |icon-polygon-new| image:: _static/icons/icon-polygon-new-64.png
    :height: 2.5ex

.. |icon-polygon-off| image:: _static/icons/icon-polygon-off-64.png
    :height: 2.5ex

.. |icon-launch| image:: _static/icons/icon-launch-64.png
    :height: 2.5ex

.. |icon-profile| image:: _static/icons/icon-profile-64.png
    :height: 2.5ex
