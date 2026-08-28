# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
from datetime import datetime
from pathlib import Path

# Project root only -- every module in this codebase is imported as
# src.app.X / src.common.X / src.ui.X (matching how the app itself imports
# internally, e.g. main.py's `from src.app.MainWindow import MainWindow`),
# so that's all autodoc/autosummary need on the path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

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
        'sphinx.ext.mathjax',
        'numpydoc',
    ]
    #    'sphinx_js'
    #]

napoleon_custom_sections = [('Signals', 'params_style')]

# numpydoc auto-inserts a "Methods" autosummary table into every class
# docstring, including every inherited member -- for PyQt6-derived classes
# that's hundreds of stdlib Qt methods (accept, acceptDrops, ...) per class,
# each linked to a stub page that autosummary_generate never creates (it only
# generates stubs for what documentation.rst's autosummary directive actually
# lists: modules, not every individual inherited method). That mismatch is
# what produced ~24k "stub file not found" warnings. Disabling the toctree
# links keeps the summary table but stops it trying to link to pages that
# were never going to exist.
numpydoc_class_members_toctree = False

autosummary_generate = True
autosummary_imported_members = False  # Include members imported in modules
templates_path = ['_templates']
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints", "**/__pycache__/**", "**/.venv/**", "**/venv/**"]

#js_source_path = '../../blockly/src'


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

# Stamps a "Last updated on <date>" line at the bottom of every page, using
# *that page's own* .rst source file's last-modified-on-disk date -- not a
# single build timestamp shared by every page (Sphinx's own html_last_
# updated_fmt only does the latter; see the html-page-context hook in
# setup() below, which overrides it per page instead). Rendered via
# pydata_sphinx_theme's built-in `last-updated` footer component, enabled
# below in html_theme_options's footer_start. This value just needs to be
# non-None to turn the feature on -- setup()'s hook overwrites it per page.
html_last_updated_fmt = ''

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'dateutil': ('https://dateutil.readthedocs.io/en/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'scikit-learn': ('https://scikit-learn.org/stable/', None),
    'pyqt5': ('https://www.riverbankcomputing.com/static/Docs/PyQt5', None),
    # darkdetect and rst2pdf removed: neither actually publishes a Sphinx
    # inventory. darkdetect's PyPI project page returns its HTML page (not a
    # real objects.inv) for any URL ending in objects.inv, which crashes the
    # build with "invalid inventory header: <!DOCTYPE html>" -- confirmed via
    # `curl https://pypi.org/project/darkdetect/objects.inv`, real content is
    # an HTML page, not the "# Sphinx inventory version" file PyQt5 returns.
    # rst2pdf's repo doc path 404s (no Sphinx docs at that path either).
    # local sibling repos, checked out alongside this one (../../../lame-core,
    # ../../../siesta-rest-editor, ../../../blueberry-colortools) -- relative
    # paths so they stay valid regardless of the absolute checkout location, as
    # long as the sibling repos stay siblings. Each requires that sibling's own
    # docs to have been built first (its docs/build/html/objects.inv).
    # NOTE: the two elements are relative to *different* directories -- the
    # inventory location (2nd element) is resolved relative to confdir
    # (docs/source/), while the link target (1st element) is what actually
    # gets written into built page hrefs, which live one level deeper
    # (docs/build/html/) than confdir. Using the same relative string for both
    # (as intersphinx normally expects when they're both `None`-derived from
    # one URL) produces correct inventory loading but a broken href, off by
    # exactly the docs/source vs docs/build/html depth difference -- verified
    # empirically against the actual built output.
    'lame_core': ('../../../../lame-core/docs/build/html', '../../../lame-core/docs/build/html/objects.inv'),
    'siesta': ('../../../../siesta-rest-editor/docs/build/html', '../../../siesta-rest-editor/docs/build/html/objects.inv'),
    'blueberry': ('../../../../blueberry-colortools/docs/build/html', '../../../blueberry-colortools/docs/build/html/objects.inv'),
    'global_geochemistry': ('../../../../global_geochemistry/docs/build/html', '../../../global_geochemistry/docs/build/html/objects.inv'),
}

html_theme_options = {
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["navbar-icon-links"],
    # Site-wide footer (every page, not just the article content) -- shows
    # the "Last updated on <date>" line from html_last_updated_fmt above.
    "footer_start": ["last-updated"],
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
            "icon": "_static/minex_crc_logo_black.svg",
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

mathjax3_config = {
    "tex": {
        "packages": ["base", "ams"],
    }
}

# ------
# fixes issues with js and fontawsome loading issues

def _stamp_page_with_source_mtime(app, pagename, templatename, context, doctree):
    """Overrides the 'last_updated' template variable (normally one
    build-wide timestamp -- see html_last_updated_fmt above) with *this
    page's own* source .rst file's last-modified-on-disk date, so the
    footer answers "was this specific page's content touched recently"
    rather than "when did someone last run sphinx-build".

    doctree is None for pages not built from a source file (search,
    genindex, ...) -- nothing to stamp there.
    """
    if doctree is None:
        return
    try:
        src_path = Path(app.env.doc2path(pagename))
        mtime = datetime.fromtimestamp(src_path.stat().st_mtime)
    except OSError:
        return
    context['last_updated'] = mtime.strftime('%Y-%m-%d')


def setup(app):
    app.add_js_file('custom.js')
    app.connect('html-page-context', _stamp_page_with_source_mtime)
# ------

autoclass_content = 'both'