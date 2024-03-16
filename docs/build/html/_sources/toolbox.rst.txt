The Toolbox
===========

.. _preprocessing
Preprocessing Pane
==================

Autoscaling |icon-autoscale|
----------------------------

One common calibration issue is the conversion of low counts to negative concentrations after calibration.  These are almost certainly due to difference between the ablation properties of the mineral used to calibrate the map applied and another mineral.  Negative values are particularly an issue when the data are log-scaled.  To reduce the effect of negatives, we rescale the data by bringing applying a linear compression of the data, fixing the upper end and moving the lower end to a small positive value.  While this does change the concentration, it has a small affect on large concentrations.  We also perform an autoscaling, performed by default, to clip the high and low ends of the concentrations.  These values are not removed, rather set to the top or bottom of the scale.  Autoscaling can skew statistics as a result; however, it generally improves estimates of the mean as values that are several orders of magnitude higher than reasonable no longer have a massive effect.  Autoscaling can be toggled on or off by pressing the |icon-autoscale| button. 

Spot Data Pane
==============


Filter Pane
===========

There are three types of filters than can be applied to exclude data from analyses and geochemical plots.  These include elemental filters ( |icon-filter2| ), polygon masking ( |icon-polygon-new| ), and cluster masking ( |icon-mask-dark| ).  Elemental filters and polygon masking are both It is possible to use any combination of these and turn them on or off as required.

Elemental Filters |icon-filter2|
--------------------------------

One can filter by element/isotope values, ratios of elements/isotopes, principal component score, or cluster score.  Multiple filters may be combined to produce more complex filters.  The filters include a boolean operations (*and* and *or*) to assist with precisely defining filters to capture the desired regions for analysis and plotting.  In many cases, the overlap between values may make it difficult to separate phases.  In these cases, we suggest targeting specific regions with a polygon or cluster mask.

Polygon Masking |icon-polygon-new|
----------------------------------

Cluster Masking |icon-mask-dark|
--------------------------------

Cluster masks 

Scatter and Heatmaps Pane
=========================

n-Dim Pane
==========


PCA Pane
========

Clustering Pane
===============

Profiling Pane
==============

Special Functions Pane
======================