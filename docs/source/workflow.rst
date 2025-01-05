Workflow Method Design (WMD)
****************************

*LaME* makes it simple to develop processing and analysis workflows for running on multiple samples.  Workflows can be designed directly with the Workflow Design Tool, or your actions on a sample can be recorded to produce a workflow that can then be applied to other samples.  The workflows can be shared between users, making it an easy way to share methods and develop best practices.  This set of design tools can save time when working with many samples and be a convenient way to document processing and analysis methods for publication.

Installation
============

The WMD tool requires Google's Blockly javascript library. Follow these steps to set up the workflow functionality:

1. Clone the latest version of LaME::

    git clone https://github.com/dhasterok/LaserMapExplorer/

2. Navigate to the blockly directory::

    cd LaserMapExplorer/blockly

3. Remove the existing node_modules folder if present

4. Install dependencies::

    npm install

5. Build the blockly bundle::

    npx webpack --config webpack.config.js

A successful build will show output listing various modules and assets.

Getting Started
===============

Basic Workflow Creation:

1. Open the Workflow tab in Lower Tabs
2. Use the Block Palette to find analysis functions
3. Drag blocks to the Workspace
4. Connect blocks to create processing sequences
5. Test your workflow on a small dataset
6. Save and share successful workflows

Interface Overview
------------------
- Block Palette: Contains available analytical blocks
- Workspace: Area for assembling workflow blocks
- Preview Panel: Shows real-time execution results