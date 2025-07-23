#!/bin/bash

# -----------------------------------------------------------------------------
# Script Name: update_blockly.sh
#
# Description:
#   Bundles blockly workflow tool for use with Laser Map Explorer (LaME) using
#   Webpack.  The blockly/src/*.js files are documented using JSDoc for
#   incorporation into the LaME Sphinx web-based documentation.
#
# Dependencies
#   - npx (for blockly build)
#
# Author: D. Hasterok (derrick.hasterok@adelaide.edu.au)
# -----------------------------------------------------------------------------

# Auto document JS files for sphinx
npx jsdoc blockly/src -r -d docs/_build/jsdoc
cp -r docs/_build/jsdoc docs/source/_static

# Rebuild blockly workflow
cd blockly
npx webpack --config webpack.config.js
cd ..