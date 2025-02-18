from PyQt6.QtCore import QTimer, QObject, pyqtSignal

class Scheduler(QObject):
    """Scheduler sets a timer once an action is triggered and can be use to delay actions until all desired actions are complete.

    Parameters
    ----------
    QObject : QObject
        _description_

    Attributes
    ----------
        timeout : pyqtSignal
            Signals when timer has expired.
    
    Examples
    --------
    1. Scheduler for plot updates

    self.scheduler = Scheduler(callback=self.*method*)

    self.*widget1*.*signal*.connect(self.scheduler.schedule_update)
    self.*widget2*.*signal*.connect(self.scheduler.schedule_update)

    2. Scheduler with signal

    self.scheduler = Scheduler()
    self.scheduler.timeout.connect(self.on_timeout)

    self.*widget*.*signal*.connect(self.scheduler.schedule_update)

    """    
    # Signal emitted when the timer triggers
    timeout = pyqtSignal()

    def __init__(self, parent=None, callback=None, delay=300):
        """Initializes Scheduler.

        Use a scheduler to delay updates when multiple actions are performed.

        Parameters
        ----------
        parent : QObject, optional
            UI window, by default None
        callback : Callable[[], None], optional
            Method executed when timer expires, by default None
        delay : int, optional
            Scheduler delay, by default 300
        """        
        super().__init__(parent)

        self.callback = callback
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(delay)  # Default delay in milliseconds
        self.update_timer.setSingleShot(True)  # Only fire once after inactivity

        # Connect the timer to the provided callback or emit the timeout signal
        if callback:
            self.update_timer.timeout.connect(callback)
        else:
            self.update_timer.timeout.connect(self.timeout.emit)

    def set_delay(self, delay):
        """Set the debounce delay dynamically.
        
        Parameters
        ----------
        delay : int
            Delay, by default 300
        """
        self.update_timer.setInterval(delay)

    def schedule_update(self):
        """Start or restart the timer."""
        self.update_timer.start()

    def stop(self):
        """Stop the timer if it's running."""
        self.update_timer.stop()

    def is_active(self):
        """Check if the timer is currently running."""
        return self.update_timer.isActive()

    def reset_timer(self):
        """Restart timer with same delay."""
        self.stop()
        self.schedule_update()