# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../src'))
sys.path.insert(0, os.path.abspath('../../src/ui'))

project = 'Laser Map Explorer'
copyright = '2024, Shavin Kaluthantri and Derrick Hasterok'
author = 'Shavin Kaluthantri and Derrick Hasterok'

print(sys.executable)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_theme_options = {"navbar_start": ["navbar-logo"],
                      "navbar_center": ["navbar-nav"],
                      "navbar_end": ["navbar-icon-links"]}

html_static_path = ['_static']

html_logo = "_static/LaME_logo-64.png"
html_title = "LaME"

html_theme_options = {
    "icon_links": [
        {
            # Label for this link
            "name": "GitHub",
            # URL where the link will redirect
            "url": "https://github.com/shavinkalu23/LaserMapExplorer",  # required
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fa-brands fa-square-github",
            # The type of image to be used (see below for details)
            "type": "fontawesome",
        },
        {
            "name": "MinEx CRC",
            "url": "https://minexcrc.com.au/",
            "icon": "_static/minex_crc_logo.svg",
            "type": "local"
        }
   ]
}

autoclass_content = 'both'
