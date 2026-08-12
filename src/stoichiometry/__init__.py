"""Mineral stoichiometry backend: ppm/wt% analyses -> cations per formula
unit (apfu), site allocation, redox estimation, and end-member calculation.

Pure Python, no PyQt imports anywhere in this package except ``dock.py``.
Mineral "recipes" are external YAML config files (see ``config.py`` and
``resources/minerals/*.yaml``) -- no mineral-specific assumptions (site
names, site counts, element lists) are hardcoded outside those configs.
"""
