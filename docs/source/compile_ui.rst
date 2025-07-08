.. _compile_ui_script:

UI Compilation Scripts
**********************

These scripts automates the build process for Qt Designer `.ui` files, custom widget integration, package blockly functions and build the blockly API documentation.

update_custom_widgets
=====================

- Converts `.ui` files to `.py`
- Replaces standard Qt widgets with custom ones
- Converts `.qrc` resources

**Location**: ``scripts/update_custom_widgets.sh``

**Usage**:

.. code-block:: bash

   ./update_custom_widgets.sh

Dependencies
------------

- `pyrcc6` (from PyQt6)
- `pyuic6`
- `sed`

Widget Replacement
------------------

For some `.ui` files, the generated `.py` is automatically updated to use custom widgets defined in:

.. code-block:: python

   import src.common.CustomWidgets as cw

Custom replacements are based on object name patterns like:

- `self.tableWidget*` → `cw.CustomTableWidget`
- `self.lineEdit*` → `cw.CustomLineEdit`

update_blockly
==============

- Builds web-based documentation for Blockly Workflow assets
- Rebuilds (bundles) Blockly Workflow assets for use in Workflow Dock

**Location**: ``scripts/update_blockly.sh``

**Usage**:

.. code-block:: bash

   ./update_blockly.sh

After compiling, there should be html documentation in docs/source/_static/jsdoc.

Dependencies
------------

From Node.js:

- `npx`
- `webpack`

See also
--------

- :mod:`src.common.CustomWidgets`
- :ref:`ui-guidelines`

