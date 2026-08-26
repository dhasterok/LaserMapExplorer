User Guide
**********

*LaME* is built in `Python3.12 <https://www.python.org/downloads/>`_ using `PyQt6 <https://pypi.org/project/PyQt6/>`_ for the user interface with plotting is handled by `matplotlib <https://matplotlib.org>`_. A workflow design tool is built with Javascript `Blockly <https://www.blockly.com>`_ to create a visual programming environment for batch processing.

There are two ways to use *LaME*, either as a precompiled executable (eventually) or using the source code.  The latter will always be up to date, but may occasionally break as we improve the code, implement new features, or experiment with new tools.  If you do use the source, we suggest you download a distribution manager such as `GitHub Desktop <https://docs.github.com/en/desktop/overview/about-github-desktop>`_ which can be used to monitor changes and easily download updates. 

.. toctree::
    :maxdepth: 2
    :caption: Getting Started

    installation
    basics
    import

.. toctree::
    :maxdepth: 2
    :caption: The Interface

    top_toolbar
    left_toolbox
    right_toolbox
    center_pane
    lower_tabs

.. toctree::
    :maxdepth: 2
    :caption: Figures & Analyses

    filtering
    plotting
    profiles
    visualization
    multidimensional
    additional_functions
    export

.. toctree::
    :maxdepth: 2
    :caption: Docks

    calculator
    stoichiometry
    geochronology
    diffusion
    cluster_dock
    notes
    logging_tool
    info_tool
    workflow
    workflow_reference