Installation
************

Using a Precompiled Executable
==============================

Using the Source Code
=====================

This method always provides you with the most up-to-date version of *LaME*. However, please note that this method may occasionally encounter issues as we improve the code, implement new features, or experiment with new tools.

Step 1: Install Anaconda
------------------------

Download and install Anaconda from https://www.anaconda.com/download

Step 2: Install Git or Visual Studio Code
-----------------------------------------

You have two options for managing the *LaME* repository: Git or Visual Studio Code (VSC). Choose the option that best suits your needs.

Option A: Install Git
^^^^^^^^^^^^^^^^^^^^^

* Windows: Open Anaconda Prompt
* Mac/Linux: Open Terminal
 
Run the following command:

.. code-block:: bash

   conda install git

Option B: Install Visual Studio Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download and install Visual Studio Code from https://code.visualstudio.com/
Install the following extensions in VSC:

* Python

Run the following command:

.. code-block:: bash

   conda install git

Step 3: Clone Repository
------------------------

Clone the *LaME* repository to your local directory:

.. code-block:: bash

   git clone https://github.com/dhasterok/LaserMapExplorer.git
   cd LaserMapExplorer

Step 4: Create and Activate Virtual Environment
-----------------------------------------------

Create a new Anaconda virtual environment:

.. code-block:: bash

   conda create --name pyqt python=3.11 --file req.txt
   conda activate pyqt

If the above step fails, try the following alternative:

.. code-block:: bash

   conda create --name pyqt python=3.11
   conda activate pyqt
   conda install python=3.11 pyqt pyqtgraph PyQtWebEngine pandas matplotlib scikit-learn scikit-learn-extra opencv openpyxl numexpr
   conda install conda-forge/label/cf201901::scikit-fuzzy
   pip install darkdetect cmcrameri rst2pdf

Step 5: Run *LaME*
------------------

Using Terminal Prompt:

.. code-block:: bash
    
    python3 main.py

Troubleshooting
---------------

If you encounter any issues during the installation process, please refer to the project's documentation or :doc:`contact us <contact>`.

Updating *LaME*
---------------

To update *LaME* in the future, navigate to the LaserMapExplorer directory and run:

.. code-block:: bash

   git pull origin main

Then, activate your virtual environment and update dependencies if necessary:

.. code-block:: bash

   conda activate pyqt
   conda update --all

Remember to check the project's documentation for any additional steps that might be required after updating.