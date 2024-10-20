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

Step 1: Install Anaconda
------------------------
1. Download Anaconda from https://www.anaconda.com/download
2. Install Anaconda following the official installation guide for your operating system

Step 2: Install Git or Visual Studio Code
-----------------------------------------
Choose the option that best suits your needs:

Option A: Install Git
^^^^^^^^^^^^^^^^^^^^^
* Windows: Open Anaconda Prompt
* Mac/Linux: Open Terminal

Run the following command:

.. code-block:: bash

   conda install git

Option B: Install Visual Studio Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
1. Download and install Visual Studio Code from https://code.visualstudio.com/
2. Install the Python extension in Visual Studio Code
3. Run the following command in Anaconda Prompt or Terminal:

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
Using Terminal Prompt or Anaconda Prompt:

.. code-block:: bash

   python3 main.py

Updating *LaME*
---------------
To update *LaME* in the future, navigate to the LaserMapExplorer directory and run:

.. code-block:: bash

   git pull origin main

Then, activate your virtual environment and update dependencies if necessary:

.. code-block:: bash

   conda activate pyqt
   conda update --all

It's recommended to check the project's documentation for any additional steps that might be required after updating.

Troubleshooting
---------------
If you encounter any issues during the installation process, please :doc:`contact us <contact>` for further assistance.