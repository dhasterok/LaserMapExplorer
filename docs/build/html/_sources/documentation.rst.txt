Documentation
*************

*LaME* is written in `Python <https://www.python.org>`_ with `Qt6 design tools <https://www.qt.io/product/ui-design-tools>`_ to develop the main graphical user interface (GUI).  The workflow design tools are constructed with `Blockly <https://developers.google.com/blockly>`_ and Javascript.



Module Documentation
====================

Below is the detailed documentation for the main modules of the Laser Map Explorer (*LaME*) application.  The main.py file contains the fcn.main used to start *LaME* and cls.MainWindow that builds the UI and connects all the functionality.  Additional packages are contained in app (*LaME* specific classes and methods), common (*LaME* independent classes and methods), and ui (UI classes built in QtCreator).  Well, at least that's the philosophy behind the divisions.  It doesn't quite work that way...yet.

If the UI is altered by QtCreator, then you will need to alter the UI files using `update_custom_widgets`.  This script:

- compiles resources.qrc file
- updates select widgets with custom versions (requires separate widget lists for each UI window)
- compiles UIs created by QtCreator
- compiles blockly workflow

.. toctree::
    :maxdepth: 2
    :caption: Shell Scripts:

    compile_ui

.. toctree::
    :maxdepth: 2
    :caption: Contents:

    modules

*LaME* (python) API
===================

.. autosummary::
   :toctree: generated/
   :caption: Modules Summary
   :recursive:

   main
   app
   ui
   common

Blockly Workflow (js) API
=========================

`Blockly JS API <_static/jsdoc/index.html>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`