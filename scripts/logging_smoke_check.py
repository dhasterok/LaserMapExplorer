"""
Drive a real LaME session headlessly to check terminal output.

Loads the sample maps in a directory, switches samples and renders a few plot
types -- exercising the import, plot-tree, plotting and styling code paths where
most logging lives -- then reports what reached stdout/stderr.

Used to verify the quiet-by-default logging policy: this should print no tracing
without ``--verbose``, and a stream of categorised messages with it.

Usage
-----

.. code-block:: bash

    # should emit no tracing
    python scripts/logging_smoke_check.py "../LAME/processed data"

    # should emit categorised tracing
    python scripts/logging_smoke_check.py "../LAME/processed data" --verbose

Any options after the directory are handled exactly as ``main.py`` handles them,
so ``--verbose Data,Plot``, ``--no-log-args`` etc. all work here too.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
import main as lame_main
from src.control.Logger import LoggerConfig


def _step(label, fn):
    """Run one workflow step, reporting failures without aborting the run."""
    try:
        fn()
        print(f"[check] {label}: ok", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 -- diagnostic harness
        print(f"[check] {label}: FAILED ({type(e).__name__}: {e})", file=sys.stderr)


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1

    data_dir = Path(argv[0]).expanduser()
    sys.argv = [sys.argv[0]] + argv[1:]

    args = lame_main.parse_args()
    lame_main.configure_logging(args)
    lame_main.install_qt_message_handler()

    print(f"[check] verbose={LoggerConfig.is_verbose()} "
          f"active={LoggerConfig.is_active()} dir={data_dir}", file=sys.stderr)

    app = lame_main.create_app()
    from src.app.MainWindow import MainWindow
    ui = MainWindow(app)

    added = []

    def _open():
        added.extend(ui.io.open_directory(data_dir) or [])
    _step(f"open_directory -> {data_dir}", _open)
    print(f"[check] samples added: {added}", file=sys.stderr)

    if not added:
        print("[check] no samples loaded; aborting", file=sys.stderr)
        return 2

    for sample_id in added[:2]:
        _step(f"change_sample({sample_id})",
              lambda s=sample_id: setattr(ui.app_data, 'sample_id', s))
        app.processEvents()

        _step("update_SV", ui.update_SV)
        app.processEvents()

        for plot_type in ('field map', 'histogram', 'correlation'):
            def _plot(pt=plot_type):
                ui.control_dock.update_plot_type(pt, force=True)
                ui.update_SV()
            _step(f"plot_type={plot_type}", _plot)
            app.processEvents()

    print("[check] done", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
