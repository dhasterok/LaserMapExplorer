"""Standalone entry point for the LA-ICP-MS calibration GUI.

Boots its own ``QApplication`` -- independent of LaME's ``MainWindow``. Not
wired into the main app yet (per the "standalone for now" requirement). Run
with ``python -m src.calibration.app`` from the repo root, or just execute
this file directly (e.g. from an IDE) -- the sys.path bootstrap below makes
both work.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def create_app():
    """Return the process ``QApplication``, creating one if needed.

    Returns
    -------
    PyQt6.QtWidgets.QApplication
        The existing application instance if one is already running,
        otherwise a freshly constructed one built from ``sys.argv``.

    Notes
    -----
    Attempts to reuse LaME's light/dark stylesheet via ``darkdetect`` and
    ``lame_core.config.load_stylesheet``. Any failure there is swallowed --
    stylesheet reuse is cosmetic only and a standalone run should not fail
    without it.
    """
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    try:
        import darkdetect
        from lame_core.config import load_stylesheet
        app.setStyleSheet(load_stylesheet("dark.qss" if darkdetect.isDark() else "light.qss"))
    except Exception:
        pass  # stylesheet reuse is cosmetic only -- a standalone run shouldn't fail without it
    return app


def main() -> int:
    """Launch the standalone calibration GUI and block until it exits.

    Returns
    -------
    int
        The Qt event-loop exit code, suitable for passing to
        :func:`sys.exit`.
    """
    from src.calibration.dock_widgets import CalibrationMainWindow

    app = create_app()
    window = CalibrationMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
