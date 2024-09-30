The Basics
**********

GUI Layout
==========
The *LaME* user interface is organized into five main panels:

* Main Toolbar (Top) : File menu and main toolbar with frequently used functions
* Control Toolbox (Left) : Functions for plotting and analysis
* Plot and Property (Right) Toolbox: Plot selection, plot styling, and calculator for custom fields
* Plot Window (Center): Plot viewer tabs for single plots, multiple plots, and quick view of all fields
* Lower Tabs: Tabs for notes, filters by value, profile plots and user manual. 

.. figure:: _static/screenshots/LaME_Initial_Window.png
    :align: center
    :alt: LaME interface

    The *LaME* interface on start-up and labeled panels.

Getting Started
===============

To begin using *LaME*, first load a directory using either the *File Menu* or the *Main Toolbar* (|icon-add-directory|).  If you haven't loaded a sample previously, the imported sample will be automatically added to the sample list dropdown in the *Main Toolbar*.  If you have previously loaded the data, you can load a saved session, a single sample, or a directory of samples. See :doc:`import` for file specifications that LaME can handle.

Once a directory is loaded, select a sample using the sample list dropdown in the Main Toolbar.  To choose the fields for analysis, use *Analyte Selector* ( |icon-atom| ) to choose the fields for analysis, including ratios between elements/analytes.  More details on this process can be found in the :doc:`top_toolbar` section.  

With data loaded and fields selected, various tools in the Control Toolbox and Plot and Property Toolbox can be used to analyze and visualize the data. All work on previous samples will be stored, and any images can be recalled from the Plot Selector in the Plot and Property Toolbox.

For a detailed explanation of the Control Toolbox and its features, refer to the :doc:`left_toolbox` section. Similarly, for information about the Plot and Property Toolbox and its capabilities, see the :doc:`right_toolbox` section.

These toolboxes provide essential functions for data analysis, visualization, and customization in *LaME*. Familiarizing yourself with their features will greatly enhance your ability to explore and analyze your data effectively.

Structure of Stored Data
========================

It is useful to know how data are stored within the program, as some operations will clear analyses and associated figures when the underlying data are changed.  *LaME* keeps three versions of the data: *raw data* (original data), *clipped data* (preprocessed data), and *analysis data* (filtered and/or masked).

Raw data
--------

*Raw data* refers to the data read directly from a file.  It may be uncalibrated (e.g., cps) or calibrated (e.g., ppm).  Currently, *LaME* does not calibrate LA-ICP-MS data, so any calibrated data should be calibrated in Iolite or XMapTools first.

Cropping ( |icon-crop| ) can be applied to the *raw data*, reducing the area analyzed by the code.  The original extent can be restored by clicking the |icon-fit-to-width| button.  If the *raw data* is cropped or restored to the original extent, these operations result in clearing any figures or analyses.  A dialog will appear prompting the user if they wish to proceed before clearing the memory.

Clipped data
------------

*Clipped data* refers to preprocessed data.  The preprocessing steps include several potential operations to reduce issues with analyses such as autoscaling ( |icon-autoscale| ) and rescaling to remove negative values.  While it may alter the values of some data points, it does so by improving stability of some processing methods (e.g., PCA and clustering) that are otherwise skewed by extreme outliers or cannot handle negative values.  These outliers often result from point measurement errors or incorrect calibrations related to differences in mineral ablation properties.  These preprocessing data steps are described in greater detail in the preprocessing subsection of the :doc:`left_toolbox`.

Analysis data
-------------

There are three types of :doc:`filters <filtering>` that can be applied to exclude data from analyses and geochemical plots: elemental filters (on = |icon-filter2|, off = |icon-filter| ), polygon masking (on = |icon-polygon-new|, off = |icon-polygon-off| ), and cluster masking (on = |icon-mask-dark|, off = |icon-mask-light| ).  These filters can be used in any combination and toggled on or off as required.  Each is implemented as a simple pixel-by-pixel mask. Filters can be toggled using the corresponding icons in the *Main Toolbar*. All filters/masks can be disabled by clicking the |icon-map| button.

The *analysis data* are used to produce plots and compute analyses; turning filters and masks on or off results in their recomputation of the analysis data. 

.. |icon-add-directory| image:: _static/icons/icon-add-directory-64.png
    :height: 2ex

.. |icon-atom| image:: _static/icons/icon-atom-64.png
    :height: 2ex

.. |icon-crop| image:: _static/icons/icon-crop-64.png
    :height: 2ex

.. |icon-fit-to-width| image:: _static/icons/icon-fit-to-width-64.png
    :height: 2ex

.. |icon-autoscale| image:: _static/icons/icon-autoscale-64.png
    :height: 2ex

.. |icon-map| image:: _static/icons/icon-map-64.png
    :height: 2ex

.. |icon-filter| image:: _static/icons/icon-filter-64.png
    :height: 2ex

.. |icon-filter2| image:: _static/icons/icon-filter2-64.png
    :height: 2ex

.. |icon-mask-light| image:: _static/icons/icon-mask-light-64.png
    :height: 2ex

.. |icon-mask-dark| image:: _static/icons/icon-mask-dark-64.png
    :height: 2ex

.. |icon-polygon-new| image:: _static/icons/icon-polygon-new-64.png
    :height: 2ex

.. |icon-polygon-off| image:: _static/icons/icon-polygon-off-64.png
    :height: 2ex