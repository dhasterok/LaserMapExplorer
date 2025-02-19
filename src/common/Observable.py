class Observable:
    def __init__(self):
        self._observers = []

    def add_observer(self, callback):
        """Register a callback function to be called when a property changes.
        
        Properties
        ----------
        callback : method
            Callback method to be executed when a property changes.
        """
        self._observers.append(callback)

    def notify_observers(self, prop_name, value):
        """Notify all registered observers.
        
        Properties
        ----------
        prop_name : str
            Name of property to observe.
        value : any
            New value of property.
        """
        for callback in self._observers:
            callback(prop_name, value)
