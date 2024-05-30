.. Laser Map Explorer documentation master file, created by
   sphinx-quickstart on Tue Mar 12 12:36:10 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
.. sphinx-build -b html docs/source/ docs/build/html
.. raw:: html

   <script type="text/javascript" src="_static/custom.js"></script>

Welcome to Laser Map Explorer (LaME)!
*************************************

LaME is a graphical user interface for rapidly diplaying and analyzing data generated from LA-ICP-MS.  The app allows users to simply and quickly filter data, produce standard geochemical plots, perform multi-dimensional analyses, and computations relevant to geoscientific interpretation.

The penultimate goal is to allow users to intuitively analyze multi-analyte data, and produce publication ready figures with minimal effort.  The program is currently in beta release.  There are plenty of bugs and some features that have yet to be partially or fully implemented.  Release notes below detail the progress and future plans.

.. figure:: _static/screenshots/LaME_quickview.png
    :align: center
    :alt: LaME interface

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   userguide
   tutorials
   documentation
   contact

Release notes:
==============

As this program is currently in beta, there are still some features that need to be completed/fixed.  Most plot functions are working.  Analyte maps, noise reduction, scatter and heatmaps, PCA and clustering are all working properly.  Histograms and correlation plots are also working.  Most plot types can be customized by selecting/filtering the data.  Masking and filtering are functional, but have not been extensively tested.  Profiling works, but is not yet displayed in an easy to customize format.  There are a few buttons that have planned functionality, but have yet to be implemented wholly or in part.  Note taking functions, figure saving, spot data, and the custom field calculator are places where fuctionality are not at 100%.  

We can use your help to identify bugs, places where the program is not intuitive, and/or layout can be improved.  We would also like to know what features you would like to see.  For instance, are there types of analyses, plots, or auto-generated note capabilites that you might like to see?

The documentation can be accessed through the help browser in the bottom dock.  Since the documentation is integrated with the program it should be viewable when offline.  The documentation is not yet complete.

Know issues:
============

- Ratios are not currently being added to the plot selector, but are at the top of the list to correct.
- Log scaling may not be implemented properly in all cases yet (e.g., maps, PCA, Clustering).
- Not all buttons are set up yet.
- Crop tool does not allow adjustment.

If you would like to contribute in any way to the improvement of the program, have feature requests or would like to help with documentation, please contact us via the GitHub project page or using the email link on the :doc:`contact` page.

Funding for this app has been provided by the `MinEx CRC <https://minexcrc.com.au/>`_ by developers at
the `University of Adelaide <https://www.adelaide.edu.au/>`_.