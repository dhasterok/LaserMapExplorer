Documentation
*************

LaME is written in `Python <https://www.python.org>`_ with `Qt6 design tools <https://www.qt.io/product/ui-design-tools>`_ to develop the main graphical user interface (GUI).  The workflow design tools are constructed with `Blockly <https://developers.google.com/blockly>`_ and Javascript.

Module Documentation
====================

Below is the detailed documentation for the main modules of the Laser Map Explorer (LaME) application.  The main.py file contains the fcn.main used to start LaME and cls.MainWindow that builds the UI and connects all the functionality.  Additional packages are contained in app (LaME specific classes and methods), common (LaME independent classes and methods), and ui (UI classes built in QtCreator).  Well, at least that's the philosophy behind the divisions.  It doesn't quite work that way yet...

.. toctree::
    :maxdepth: 2
    :caption: Contents:

    modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

API Reference
=============

.. autosummary::
   :toctree: generated/
   :caption: Modules Summary
   :recursive:

   app
   ui
   common

