from typing import Callable
from collections import defaultdict

class Observable():
    """Class for observing changes to properties or other events and notifying the observers.

    Methods
    -------
    add_observer : 
        add an observer to a property or event
    remove_observer: 
        remove a property or event from the observer dictionary
    notify_observers: 
        inform observers of an event or change in a property

    """
    def __init__(self, *args, **kwargs):
        self._observers = defaultdict(list)

    def add_observer(self, event_name: str, callback: Callable):
        """Register a callback function to be called when a property changes.
        
        Properties
        ----------
        event_name : str
            String used to identify an event.
        callback : Callable
            Callback method to be executed when a property changes.
        """
        self._observers[event_name].append(callback)

    def remove_observer(self, event_name: str, callback: Callable):
        """Deregister a callback function from an event.
        
        Properties
        ----------
        event_name : str
            String used to identify an event.
        callback : Callable
            Callback method to be executed when a property changes.
        """
        if event_name in self._observers:
            self._observers[event_name].remove(callback)
            if not self._observers[event_name]:
                del self._observers[event_name]


    def notify_observers(self, event_name: str, *args, **kwargs):
        """Notify all registered observers of an event or property change.
        
        Properties
        ----------
        event_name : str
            Name of event or property to observe.
        """
        for callback in self._observers[event_name]:
            callback(*args, **kwargs)
