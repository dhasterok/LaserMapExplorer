Control (Left) Toolbox
**********************

The control toolbox includes the controls for changing and processing samples, producing plots, and performing analyses.  

Samples and Fields
==================

.. figure:: _static/screenshots/LaME_Samples_and_Fields.png
    :align: center
    :alt: LaME interface: left toolbox, samples and fields tab
    :width: 315

    The *Samples and Fields* tab contains tools for choosing analytes and plotting correlations.

Change sample:

* prompt to save analysis - saves to disk
* clears polygons, profiles, delete filters in table

Crop or reset map extent:

* resets data
* recompute clipped and analysis data
* deletes all figures
* clears masks, polygons, profiles and special function calculations
* refilters the data based on existing filters
* recomputes calculated fields

Swap X-Y:

* swaps x-y coordinates on maps, polygons and profiles
* recomputes maps

Change Analytes:

* updates *Plot Selector*
* clear clusters, pca, removes masks
* recompute correlations

Change ref value:

* update anything with norm data (plots, calculated fields, n-Dim plots, clustering?, filters?)

Change data scaling:

* same as crop and clears filters

Change Correlation Method:

* update correlation plots


.. _preprocessing
Preprocess
==========

Preprocessing, alters the data to improve performance, stability and visual characteristics.  

These changes can have an impact on certain statistical calculations, such as mean values and standard deviations.  

.. figure:: _static/screenshots/LaME_Preprocess.png
    :align: center
    :alt: LaME interface: left toolbox, preprocessing tab
    :width: 315

    The *Preprocessing* tab contains tools for autoscaling histograms, equalization, and noise reduction.

Autoscaling |icon-autoscale|
----------------------------

One common calibration issue is the conversion of low counts to negative concentrations after calibration.  These are almost certainly due to difference between the ablation properties of the mineral used to calibrate the map applied and another mineral.  Negative values are particularly an issue when the data are log-scaled.  To reduce the effect of negatives, we rescale the data by bringing applying a linear compression of the data, fixing the upper end and moving the lower end to a small positive value.  While this does change the concentration, it has a small affect on large concentrations.  We also perform an autoscaling, performed by default, to clip the high and low ends of the concentrations.  These values are not removed, rather set to the top or bottom of the scale.  Autoscaling can skew statistics as a result; however, it generally improves estimates of the mean as values that are several orders of magnitude higher than reasonable no longer have a massive effect.  Autoscaling can be toggled on or off by pressing the |icon-autoscale| button. 

Histogram Equalization
----------------------

An alternative to auto scaling that does not alter the data, histogram equalization ( |icon-histeq| ) ensures that colors are assigned by equal quantiles.  This method is particularly useful when the histogram covers a relatively large range of values often bi- or multi-modal with large regions of few data between.  A potential disadvantage is an amplification of noise at the expense of real features.

Histograms
----------

Noise Reduction
---------------

Noise reduction ( |icon-noise-reduction| ) involves the smoothing of data.  It may be applied to maps only for viewing, or can be applied to *Analysis Data* before producing other plots and analyses (set from the *Apply to analysis* drop down).  There are four noise reduction methods available:

* median, smooths the data by computing the median value over a specified kernel (window) size, assigning the result to the center pixel. The results smooth across the entire image;
* Gaussian, smooths the data using a Gaussian weighting with a specified sigma computed over a specified kernel size, assigning the result to the center pixel. The results smooth across the entire image;
* Wiener, smooths the data using a Fourier domain low-pass filter;
* edge-preserving, smooths the data while preserving sharp edges, this is the suggested option for most cases, though it may oversmooth inside grains; and
* bilateral, Gaussian smoothing and edge-preserving, this filter differs from edge-preserving as it does not as strongly smooth the data.

Spot Data
=========

Spot data is not currently available.

.. figure:: _static/screenshots/LaME_Spot_Data.png
    :align: center
    :alt: LaME interface: left toolbox, preprocessing tab
    :width: 315

    The *Spot Data* tab contains tools for loading and displaying and analyzing spot data.


Scatter and Heatmaps
====================

The creation of 

.. figure:: _static/screenshots/LaME_Scatter_and_Heatmaps.png
    :align: center
    :alt: LaME interface: left toolbox, scatter and heatmaps tab
    :width: 315

    The *Scatter and Heatmaps* tab contains tools for plotting scatter maps and heat maps in 2 (biplots) and 3 (ternary) dimensions.  Scatter data may be colored by a field set in the *Styling* tab.  A map may also be produced with color defined by pixel position within a ternary diagram.


n-Dim
=====

.. figure:: _static/screenshots/LaME_n-Dim.png
    :align: center
    :alt: LaME interface: left toolbox, n-Dim tab
    :width: 315

    The *n-Dim* tab contains tools for plotting multidimensional data as either radar plots or trace element compatibility diagrams (a.k.a. spider diagrams).

This tab is used to produce trace element compatibility diagrams (spider plots) with data normalized to a set of reference concentrations.  This tab is also used to produce radar plots (that look more like spider webs).

Principal Component Analysis (PCA)
==================================

.. figure:: _static/screenshots/LaME_PCA.png
    :align: center
    :alt: LaME interface: left toolbox, pca tab
    :width: 315

    The *PCA* tab contains tools for displaying a variety of plots relevant to principal component analysis, inclucing maps of PCA dimension scores.

Select from a range of plots relevant to principal component analyses using the *Plot type* dropdown, including: 

* variance - individual and cumulative explained variance for the principal components
* vectors - a heatmap showing vector components, useful for observing the influence of input fields on the variance (spread) in the data along each principal component axis
* 2-D score plots - shows both the scores of individal data points along two principal component axes (*PC X* and *PC Y*) and the field components along each axis
* score maps - produces a score map for a single principal component, change the map by changing the value of *PC X* field.

2-D score plots can also be displayed as a scatter or heatmap by selecting the corresponding from the *Plot type* dropdown.  

To save to the plot tree by clicking the |icon-launch| button.

Clustering
==========

Clustering employs unsupervised machine learning to identify subsets of the data that contain similar characteristics in multidimensional space (i.e., similar geochemical characteristics).  It is often a more efficient way to filter data when the goal is to isolate or exclude specific minerals from analyses.  Two methods are currently implmented, *k-means* and *fuzzy c-means*, which are chosen from the *Method* dropdown.  K-means is the simpler of the two algorithms, which optimizes the centroids of clusters by minimizing the distance of points nearest to each respective centroid.  Fuzzy c-means differs in that it assumes that the clusters can overlap allowing for an additional score to be provided for each cluster in addition to map assigning each point to the cluster with the highest score.

.. figure:: _static/screenshots/LaME_Clustering.png
    :align: center
    :alt: LaME interface: left toolbox, clustering tab
    :width: 315

    The *Clustering* tab contains tools for calculating and displaying multianalyte data classified into clusters based on similarities in properties.  Clustering needs to be performed prior to creating a cluster mask.


Profiling
=========

Create profiles across the across the map.
.. figure:: _static/screenshots/LaME_Profiling.png
    :align: center
    :alt: LaME interface: left toolbox, profiling tab
    :width: 315

    The *Profiling* tab contains tools for creating cross sections of analytes across the maps.


Special Functions
=================

These are not yet implemented, but will include methods to compute thermometry, barometry, dating using various isotopic systems, and multicomponent diffusion.  If you have interest in applying a specific methods please contact us and we'll see what we can do.


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