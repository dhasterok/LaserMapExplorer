import sys, os, argparse, darkdetect
from pathlib import Path
from PyQt6.QtCore import QEvent, QTimer
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QIcon
import src.app.config  # noqa: F401 — runs lame_core.config.setup()
from lame_core.config import BASEDIR, ICONPATH, load_stylesheet
from lame_core.wheel_scroll import install_wheel_scrolling
from src.control.Logger import LoggerConfig, install_qt_message_handler
from src.app.MainWindow import MainWindow

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


def selftest(app):
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

    Returns
    -------
    int :
        0 if every check passed, 1 otherwise. Failures are reported to stderr.
    """
    from lame_core.config import APPDATA_PATH, STYLE_PATH, USERDATA_PATH, user_data_dir

    # A windowed (console=False) build has no attached console, and on Windows the
    # bootloader can leave sys.stderr as None -- writing to it would crash the very
    # check that is meant to report failures. Fall back to a file the CI step can read.
    stream = sys.stderr
    fallback = None
    if stream is None:
        fallback = open(USERDATA_PATH / 'selftest.log', 'w', encoding='utf-8')
        stream = fallback

    def report(message):
        print(f"selftest: {message}", file=stream)

    failures = []

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
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        view = QWebEngineView()
        view.setHtml('<html><body>selftest</body></html>')
        app.processEvents()
        view.deleteLater()
    except Exception as e:
        failures.append(f"QWebEngineView failed to initialise: {e}")

    window = None
    try:
        window = MainWindow(app)
    except Exception as e:
        import traceback
        traceback.print_exc()
        failures.append(f"MainWindow construction failed: {e}")

    for failure in failures:
        report(failure)

    if window is not None:
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()

    report(f"{'FAILED' if failures else 'passed'} ({len(failures)} problem(s))")

    if fallback is not None:
        fallback.close()

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
    configure_logging(args)
    install_qt_message_handler()

    app = create_app()

    if args.selftest:
        exit_code = selftest(app)
        for stream in (sys.stdout, sys.stderr):
            if stream is not None:
                stream.flush()
        os._exit(exit_code)

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