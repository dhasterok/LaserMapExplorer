Installation
************

There are two methods available for installing and using *LaME*:

* using precomplied executable (standalone application)
* using source code

Standalone Application
======================

This method provides a ready-to-run program that doesn't require any programming knowledge. While this method is the easiest to set up, it may not have the very latest features.

To install the standalone application:

1. Download the *LaME* installer from: [insert download link]
2. Run the installer and follow the on-screen instructions
3. Once installed, *LaME* can be launched from your applications menu or desktop shortcut

Source Code Installation
========================

This method always provides the most up-to-date version with the latest features and improvements. However, it may occasionally encounter issues as the code is improved and new features are implemented.

*LaME* is installed with Python's built-in ``venv`` -- no Anaconda required. If you prefer a conda-based environment, `miniforge <https://github.com/conda-forge/miniforge>`_ works too; see :ref:`installation-conda` below.

Prerequisites
-------------
* Python 3.11 or later
* git
* Node.js and npm (for the Blockly workflow editor)

Step 1: Clone the Repositories
-------------------------------
*LaME* depends on several sibling packages, which must be cloned into the same parent directory:

.. code-block:: bash

   git clone https://github.com/dhasterok/LaserMapExplorer.git
   git clone https://github.com/dhasterok/lame-core.git
   git clone https://github.com/dhasterok/blueberry-colortools.git
   git clone https://github.com/dhasterok/siesta-rest-editor.git
   git clone https://github.com/dhasterok/global_geochemistry.git

The result should look like:

.. code-block:: text

   GitHub/
   ├── LaserMapExplorer/
   ├── lame-core/
   ├── blueberry-colortools/
   ├── siesta-rest-editor/
   └── global_geochemistry/

Step 2: Create a Virtual Environment
-------------------------------------
.. code-block:: bash

   cd LaserMapExplorer
   python3 -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\activate         # Windows

Step 3: Install Python Dependencies
-------------------------------------
.. code-block:: bash

   pip install -r requirements.txt

This installs the sibling packages cloned in Step 1 in editable mode, along with every other dependency *LaME* needs.

Step 4: Build the Blockly Workflow Editor
-------------------------------------------
.. code-block:: bash

   cd blockly
   npm install
   npx webpack --config webpack.config.js
   cd ..

Step 5: Run *LaME*
--------------------
.. code-block:: bash

   python3 main.py

Updating *LaME*
---------------
To update *LaME* in the future, navigate to the LaserMapExplorer directory, pull the latest changes, activate your virtual environment, and reinstall dependencies:

.. code-block:: bash

   git pull origin main
   source .venv/bin/activate      # macOS / Linux, or .venv\Scripts\activate on Windows
   pip install -r requirements.txt

It's recommended to check the project's documentation for any additional steps that might be required after updating.

.. _installation-conda:

Using conda/miniforge instead
------------------------------
If you prefer a conda-based environment over ``venv``, install `miniforge <https://github.com/conda-forge/miniforge>`_ and substitute Step 2 above with:

.. code-block:: bash

   conda create --name lame python=3.11
   conda activate lame

Steps 1 and 3-5 are otherwise unchanged; when updating, run ``conda activate lame`` in place of activating the ``venv``.

Troubleshooting
---------------
If you encounter any issues during the installation process, please :doc:`contact us <contact>` for further assistance.