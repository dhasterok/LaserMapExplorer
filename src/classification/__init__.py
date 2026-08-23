"""Mineral classification by cosine-distance matching against a reference
composition library (Stage 3 of the six-stage LA-ICP-MS calibration
scheme -- see plans/mineral_classification_calibration_spec.md).

Pure Python core (``reference.py``, ``cosine.py``); ``dock.py`` is the only
PyQt file, following ``src/stoichiometry/``'s established package shape.
"""
