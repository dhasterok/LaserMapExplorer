import sys, os, threading, traceback
from pathlib import Path


class SelftestReport:
    """
    Progress log for ``--selftest`` that cannot itself hang or crash the check.

    A windowed (``console=False``) Windows build has ``sys.stderr`` set to None, and
    PyInstaller's bootloader answers any unhandled exception with a modal
    "Unhandled exception in script" message box. Headless on CI nobody dismisses it,
    so a single uncaught error stalls the job until GitHub's 6 h limit. Hence:

    * every line goes to ``<user data dir>/selftest.log`` (directory created first,
      flushed per line) as well as to stderr when there is one, so the CI step can
      show how far the check got even if the process has to be killed;
    * a watchdog thread ends the process with exit code 3 after ``timeout`` seconds,
      naming the stage it was stuck in -- this also covers a modal dialog or a hung
      WebEngine initialisation, which block the main thread.

    Built only from the standard library so it works before any LaME, lame_core or
    Qt import has been attempted.

    Parameters
    ----------
    timeout : float
        Seconds before the watchdog gives up on the whole check.
    """

    def __init__(self, timeout=120):
        self.stage = 'starting'
        self.file = None
        try:
            if sys.platform == 'win32':
                base = os.environ.get('APPDATA') or (Path.home() / 'AppData' / 'Roaming')
            elif sys.platform == 'darwin':
                base = Path.home() / 'Library' / 'Application Support'
            else:
                base = os.environ.get('XDG_DATA_HOME') or (Path.home() / '.local' / 'share')
            # Must match lame_core.config.default_user_data_dir('LaME'); duplicated
            # because lame_core may be the very import that is broken.
            log_dir = Path(base) / 'LaME'
            log_dir.mkdir(parents=True, exist_ok=True)
            self.file = open(log_dir / 'selftest.log', 'w', encoding='utf-8')
        except Exception:
            pass

        watchdog = threading.Timer(timeout, self._expire)
        watchdog.daemon = True
        watchdog.start()

    def write(self, message):
        """Write one line to every available sink, flushing immediately."""
        line = f"selftest: {message}\n"
        for stream in (self.file, sys.stderr):
            if stream is None:
                continue
            try:
                stream.write(line)
                stream.flush()
            except Exception:
                pass

    def begin(self, stage):
        """Record the stage about to run, so a hang can be attributed to it."""
        self.stage = stage
        self.write(f"stage: {stage}")

    def fail(self, context):
        """Log the active exception's traceback and exit immediately with code 1."""
        self.write(f"FAILED during {self.stage}: {context}")
        self.write(traceback.format_exc().rstrip())
        self.exit(1)

    def exit(self, code):
        """End the process without interpreter finalisation (see :func:`shutdown`)."""
        for stream in (self.file, sys.stdout, sys.stderr):
            try:
                if stream is not None:
                    stream.flush()
            except Exception:
                pass
        os._exit(code)

    def _expire(self):
        self.write(f"FAILED: timed out during stage '{self.stage}' (hung)")
        self.exit(3)


# Decided from the raw argv because the imports below can fail before argparse runs.
_selftest_report = SelftestReport() if '--selftest' in sys.argv[1:] else None
if _selftest_report is not None:
    _selftest_report.begin('importing modules')

try:
    import argparse, darkdetect
    from PyQt6.QtCore import QEvent, QTimer
    from PyQt6.QtWidgets import QSplashScreen, QApplication
    from PyQt6.QtGui import QPixmap, QIcon
    import src.app.config  # noqa: F401 — runs lame_core.config.setup()
    from lame_core.config import BASEDIR, ICONPATH, load_stylesheet
    from lame_core.wheel_scroll import install_wheel_scrolling
    from src.control.Logger import LoggerConfig, install_qt_message_handler
    from src.app.MainWindow import MainWindow
except BaseException:
    if _selftest_report is None:
        raise
    _selftest_report.fail('import failed (a module missing from the frozen build?)')

# -------------------------------
# MAIN FUNCTION!!!
# Sure doesn't look like much
# -------------------------------
app = None

def create_app():
    """
    Initializes and configures the QApplication instance for the application.

    This function creates a global QApplication object, applies a high-DPI scaling setting
    (default in PyQt6), and sets the application's stylesheet based on the current system
    theme (dark or light mode).  The stylesheet is loaded from either 'dark.qss' or
    'light.qss' using the `load_stylesheet` function.  If the system is in dark mode, it
    applies the dark stylesheet; otherwise, it applies the light stylesheet.

    The function also sets the global `app` variable to the created QApplication instance.

    This function should be called before creating any GUI elements to ensure that the
    application is properly initialized.

    Returns
    -------
    QApplication :
        The initialized and configured QApplication instance.
    """

    global app
    app = QApplication(sys.argv)

    # Enable high-DPI scaling (enabled by default in PyQt6)

    if darkdetect.isDark():
        ss = load_stylesheet('dark.qss')
        app.setStyleSheet(ss)
    else:
        ss = load_stylesheet('light.qss')
        app.setStyleSheet(ss)

    # Panels whose body is covered by a table, a log pane or a grid of plots
    # would otherwise only scroll when the pointer is over their scrollbar --
    # those widgets accept the wheel even with nothing to scroll.
    install_wheel_scrolling(app)

    return app

def show_splash():
    """
    Displays a splash screen for the application using a QPixmap image.

    The splash screen shows an image for 3 seconds before closing automatically.
    """
    pixmap = QPixmap(str(BASEDIR / "lame_splash.png"))
    splash = QSplashScreen(pixmap)
    splash.setMask(pixmap.mask())
    splash.show()
    QTimer.singleShot(3000, splash.close)

def parse_args(argv=None):
    """
    Parse LaME's command-line options.

    Unrecognised arguments are left in ``sys.argv`` so Qt can still consume its own
    platform flags (e.g. ``-platform``, ``-style``).

    Returns
    -------
    argparse.Namespace :
        Parsed options. ``verbose`` is None when the flag was absent, the string
        'ALL' when given without a value, or a comma-separated category list.
    """
    parser = argparse.ArgumentParser(
        prog='LaME',
        description='Laser Map Explorer -- processing and visualisation of multi-analyte maps.',
    )
    parser.add_argument(
        '-v', '--verbose',
        nargs='?', const='ALL', default=None, metavar='CATEGORIES',
        help=(
            'Stream diagnostic logging to the terminal. Without a value all categories '
            'are enabled; pass a comma-separated list (e.g. --verbose Data,Plot) to '
            'restrict output. Errors and warnings are always shown regardless.'
        ),
    )
    parser.add_argument(
        '--log-args', dest='log_args', action='store_true', default=None,
        help='Include function arguments in verbose output (default: on).',
    )
    parser.add_argument(
        '--no-log-args', dest='log_args', action='store_false',
        help='Omit function arguments from verbose output.',
    )
    parser.add_argument(
        '--log-call-chain', action='store_true',
        help='Include an abbreviated call chain in verbose output.',
    )
    parser.add_argument(
        '--selftest', action='store_true',
        help=(
            'Build the main window, verify the bundled resources load, then exit '
            'without showing a UI. Used to smoke-test a packaged build.'
        ),
    )

    args, remaining = parser.parse_known_args(argv)
    sys.argv = [sys.argv[0]] + remaining
    return args


def configure_logging(args):
    """
    Apply command-line logging options to the global :class:`LoggerConfig`.

    Logging is quiet unless ``--verbose`` was supplied; opening the Logger dock at
    runtime enables capture independently of this setting.
    """
    if args.verbose is None:
        return

    LoggerConfig.set_verbose(True)

    if args.verbose != 'ALL':
        categories = [c for c in (c.strip() for c in args.verbose.split(',')) if c]
        LoggerConfig.set_category_filter(categories)

    if args.log_args is not None:
        LoggerConfig.set_show_args(args.log_args)

    if args.log_call_chain:
        LoggerConfig.set_show_call_chain(True)


def shutdown(app, window, exit_code):
    """
    Tear the application down deterministically, then end the process.

    PyQt registers an ``atexit`` handler (``cleanup_on_exit``) that walks every
    surviving sip wrapper at interpreter finalisation and destroys the C++
    ``QObject`` behind each one. By then Qt's own static destructors are already
    in flight, so a wrapper whose C++ side is gone -- or whose destruction order
    matters -- gets touched after free. On macOS that surfaces as an intermittent
    (~1 launch in 12) crash on quit::

        Fatal Python error: Segmentation fault
        Current thread 0x... (most recent call first):
          <no Python frame>

    "No Python frame" precisely because the interpreter has stopped running
    Python code by then; the faulting frames are
    ``Py_FinalizeEx`` -> ``atexit_callfuncs`` -> ``cleanup_on_exit`` ->
    ``cleanup_qobject``.

    Two steps prevent it:

    1. Destroy the widget tree *here*, while the ``QApplication`` is still alive
       and can flush deferred-delete events -- the order Qt expects.
    2. End the process with ``os._exit``, which skips interpreter finalisation
       and so never runs PyQt's cleanup walk. Step 1 alone cannot guarantee this:
       the walk visits every remaining wrapper (matplotlib canvases, QSettings,
       the app object itself), not just the window.

    Step 2 is safe here only because nothing in LaME depends on finalisation --
    no ``atexit`` handlers, no ``__del__`` cleanup, and every ``QSettings`` write
    goes through a short-lived local that has already synced. ``os._exit`` does
    not flush Python's streams, so this does it explicitly first.

    Parameters
    ----------
    app : QApplication
        The running application instance, still alive.
    window : MainWindow
        The main window to destroy before exiting.
    exit_code : int
        Return value of ``app.exec()``, used as the process exit status.
    """
    window.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)


def selftest(app, report):
    """
    Construct the main window and confirm the bundled resources are reachable.

    A frozen build fails in a characteristic way -- a data file the spec forgot, or a
    module PyInstaller's static analysis never saw -- and the failure surfaces only
    when a user clicks the affected feature. This exercises the load-bearing paths in
    one headless pass so a packaging regression fails the build instead.

    Parameters
    ----------
    app : QApplication
        A live application instance; the stylesheet has already been applied by
        :func:`create_app`.
    report : SelftestReport
        Sink for progress and failures (stderr when present, plus selftest.log).

    Returns
    -------
    int :
        0 if every check passed, 1 otherwise.
    """
    from lame_core.config import APPDATA_PATH, STYLE_PATH, USERDATA_PATH, user_data_dir

    failures = []

    report.begin('checking bundled resources')

    def check(description, path):
        if not Path(path).exists():
            failures.append(f"missing: {description} -> {path}")

    check('application icon', ICONPATH / 'LaME-64.svg')
    check('dark stylesheet', STYLE_PATH / 'dark.qss')
    check('light stylesheet', STYLE_PATH / 'light.qss')
    check('splash image', BASEDIR / 'lame_splash.png')
    check('reference data', APPDATA_PATH / 'earthref.xlsx')
    check('isotope table', APPDATA_PATH / 'isotope_info.csv')
    check('calibration defaults', BASEDIR / 'resources' / 'calibration' / 'defaults.yaml')
    check('blockly workspace', BASEDIR / 'blockly' / 'index.html')
    check('blockly bundle', BASEDIR / 'blockly' / 'dist' / 'bundle.js')
    check('user guide', BASEDIR / 'docs' / 'build' / 'html' / 'index.html')

    # The user data directory has to be creatable and writable, or every save fails.
    try:
        probe = user_data_dir() / '.selftest'
        probe.write_text('ok')
        probe.unlink()
    except Exception as e:
        failures.append(f"user data directory not writable ({USERDATA_PATH}): {e}")

    # WebEngine is the component most likely to be broken by freezing: it needs the
    # QtWebEngineProcess helper, icudtl.dat and the .pak resources alongside the app.
    # Instantiating a view forces Chromium to initialise, which fails loudly if any of
    # that is missing.
    report.begin('initialising QWebEngineView')
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        view = QWebEngineView()
        view.setHtml('<html><body>selftest</body></html>')
        app.processEvents()
        view.deleteLater()
    except Exception as e:
        failures.append(f"QWebEngineView failed to initialise: {e}")

    report.begin('constructing MainWindow')
    window = None
    try:
        window = MainWindow(app)
    except Exception as e:
        report.write(traceback.format_exc().rstrip())
        failures.append(f"MainWindow construction failed: {e}")

    for failure in failures:
        report.write(failure)

    if window is not None:
        report.begin('destroying MainWindow')
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()

    report.write(f"{'FAILED' if failures else 'passed'} ({len(failures)} problem(s))")

    return 1 if failures else 0



def main():
    """
    Main entry point for the application.

    This function initializes the application, displays a splash screen,
    and creates the main window of the application.  It sets the
    application icon and starts the event loop.

    It also ensures that the application exits cleanly when the main window is closed.
    """
    args = parse_args()

    if _selftest_report is not None:
        # Any exception escaping here would reach PyInstaller's modal error box on a
        # windowed Windows build and hang CI; report it and exit instead.
        report = _selftest_report
        try:
            configure_logging(args)
            install_qt_message_handler()
            report.begin('creating QApplication')
            app = create_app()
            exit_code = selftest(app, report)
        except BaseException:
            report.fail('unhandled exception')
        report.exit(exit_code)

    configure_logging(args)
    install_qt_message_handler()

    app = create_app()

    show_splash()

    # Uncomment this line to set icon to App
    app.setWindowIcon(QIcon(str(ICONPATH / 'LaME-64.svg')))

    # create application data properties with notifiable observers that can be used to
    # update widgets in the UI
    window = MainWindow(app)

    # Set the main window to fullscreen
    #window.showFullScreen()
    window.show()

    shutdown(app, window, app.exec())


if __name__ == '__main__':
    main()