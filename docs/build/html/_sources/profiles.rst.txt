Profiles
********

The Profiling functionality in *LaME* enables quantitative analysis of compositional variations across samples. This tool is particularly valuable for examining mineral zoning, reaction boundaries, and diffusion profiles.

.. figure:: _static/screenshots/LaME_Profile_Plot2.png
    :align: center
    :alt: Profile tab interface
    :width: 600

    The *Profiles* tab displaying compositional profiles.

Creating Profiles
=================

To create a profile:

1. select your desired analyte map in the Plot Selector
2. Click the profile button (|icon-profile|) in the *Control Toolbox* Profiling tab 
3. Give your profiles a name and left-click on the plot to set your points4. 
4. The profile will automatically appear in the *Profile* tab of the *Lower Tabs*.

Profile Controls
================

The *Profile* tab provides several options for data extraction and visualization:

Point Settings
--------------

- Point sort: Choose between sorting points by X or Y coordinates, useful for different profile orientations
- Point radius: Set the perpendicular sampling width (in pixels) for data collection along the profile
- Y-axis threshold: Set the threshold for the y-axis to determine the profile direction
- Interpolation distance: Set the distance between points for interpolation, controlling profile resolution
- Point & error type: Select error representation method:

  - IQR (Interquartile Range): Shows data spread using 25th and 75th percentiles
  - Standard Deviation: Displays variation around the mean
  - Standard Error: Indicates uncertainty in the mean value

Display Options
---------------
The *Profile* tab offers flexible visualization controls:

Subplot Configuration
^^^^^^^^^^^^^^^^^^^^^
- Use the "Number of Subplots" spinbox to set how many profiles to display simultaneously
- Arrange profiles vertically for easy comparison
- Each subplot maintains independent y-axis scaling for optimal visibility

Adding Analytes
^^^^^^^^^^^^^^^
- Click the "Add Analyte" button to include additional elements in your profile
- Select analytes from the dropdown menu
- Each new analyte appears in a different color for clear distinction

.. |icon-profile| image:: _static/icons/icon-profile-64.png
    :height: 2ex

.. |icon-save| image:: _static/icons/icon-save-file-64.png
    :height: 2ex