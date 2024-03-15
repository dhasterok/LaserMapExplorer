Users Guide
***********

Stucture of stored data
=======================

It is useful to know how data are stored within the program as some operations will clear analyses and associated figures when the underlying data are changed.  The figure below shows the progression of different data structures from the input data to the data used for analyses.

.. figure:: _static/LaME_data_progression.png
:align: center
The method of data stored within the program

Raw data frame
--------------

The *raw data frame* refers to the data read from a file.  The raw data may be uncalibrated (e.g., cps) or calibrated (e.g., ppm).  LaME does not calibrate LA-ICP-MS data at present, so the any calibrated data should be calibrated in Iolite or XMapTools first.

.. |icon-crop| image:: _static/icon-crop-64.png
    :height: 2ex

.. |icon-fit-to-width| image:: _static/icon-fit-to-width-64.png
    :height: 2ex

Cropping ( |icon-crop| ) is applied to the *raw data frame*, reducing the area analyzed by the code.  The original extent can be restored by clicking |icon-fit-to-width|.  The *clipped data frame* and *analysis data frame* must be recomputed from *raw data frame* if the *raw data frame* is cropped or restored to the original extent.

Clipped data frame
------------------

The *clipped data frame* refers to data that are preprocessed.  The preprocessing steps include several potential operations meant to reduce issues with analyses.  While it may alter the values of some data points, 

Analysis data frame
-------------------