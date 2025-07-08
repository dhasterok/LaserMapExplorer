# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../src/'))
sys.path.insert(0, os.path.abspath('../../src/app/'))
sys.path.insert(0, os.path.abspath('../../src/common/'))
sys.path.insert(0, os.path.abspath('../../src/ui/'))

print("sys.path:", sys.path)

project = 'Laser Map Explorer'
copyright = '2025, Shavin Kaluthantri, Derrick Hasterok, and Maggie Li'
author = 'Shavin Kaluthantri,  Derrick Hasterok and Maggie Li'
release = '0.1'

print(sys.executable)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
        'sphinx.ext.autodoc',
        'sphinx.ext.autosummary',
        'sphinx.ext.napoleon',
        'sphinx.ext.inheritance_diagram',
        'sphinx.ext.intersphinx',
        'sphinx.ext.autosectionlabel',
        'sphinx.ext.viewcode',
        'numpydoc'
    ]

napoleon_custom_sections = [('Signals', 'params_style')]

autosummary_generate = True
autosummary_imported_members = False  # Include members imported in modules
templates_path = ['_templates']
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints", "**/__pycache__/**", "**/.venv/**", "**/venv/**"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
import pydata_sphinx_theme
#import mpl_sphinx_theme

html_theme = 'pydata_sphinx_theme'
#html_theme = 'mpl_sphinx_theme'

html_css_files = [
    "mpl.css",
    "custom.css",
]
#html_theme = "mpl_sphinx_theme"

html_static_path = ['_static']

#html_logo = "_static/LaME-wide-64.svg"

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'dateutil': ('https://dateutil.readthedocs.io/en/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'pyqtgraph': ('http://pyqtgraph.org/documentation/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'python': ('https://docs.python.org/3/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'scikit-learn': ('https://scikit-learn.org/stable/api/', None),
    'pyqt5': ('https://www.riverbankcomputing.com/static/Docs/PyQt5', None),
    'darkdetect': ('https://pypi.org/project/darkdetect/', None),
    'rst2pdf': ('https://github.com/rst2pdf/rst2pdf/tree/main/doc', None)
}

html_theme_options = {
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["navbar-icon-links"],
    "logo": {
        "text": "LaME v.0.0 beta",
        "image_light": "_static/LaME-wide-64.svg",
        "image_dark": "_static/LaME-wide-green-64.svg",
    },
    "icon_links": [
        {
            # Label for this link
            "name": "GitHub",
            # URL where the link will redirect
            "url": "https://github.com/dhasterok/LaserMapExplorer",  # required
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fa-brands fa-github",
            # The type of image to be used (see below for details)
            "type": "fontawesome",
        },
        {
            "name": "MinEx CRC",
            "url": "https://minexcrc.com.au/",
            "icon": "_static/minex_crc_logo.svg",
            "type": "local",
        }
   ]
}

# link to github
html_context = {
    "display_github": True, # Integrate GitHub
    "github_user": "dhasterok", # Username
    "github_repo": "LaserMapExplorer", # Repo name
    "github_version": "master", # Version
    "conf_py_path": "/doc/", # Path in the checkout to the docs root
}

# Add member-wise documentation
autodoc_default_options = {
    'members': True,
    'undoc-members': True,  # Include members without docstrings
    'inherited-members': False,
    'show-inheritance': True,
}

# ------
# fixes issues with js and fontawsome loading issues

def setup(app):
    app.add_js_file('custom.js')
# ------

autoclass_content = 'both'