"""LA-ICP-MS along-line map-artifact correction: dwell-offset shift and
washout-tailing deconvolution.

Pure Python, no PyQt -- mirrors ``src/calibration/``'s package shape.
Implements Stages 0/1/3 of ``plans/laicpms_map_correction_spec.md`` (the
matrix-free forward operator and the two "exact/fast" corrections); the
Poisson Richardson-Lucy solver, kernel estimation from real edge/pulse data,
and the 2D spot-mixing kernel are a later pass -- see that spec's staged
plan for the full scope.
"""
