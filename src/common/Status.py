
class StatusMessageManager:
    """A class to manage status messages in a GUI application."""
    def __init__(self, parent):
        self.parent = parent # Parent is typically a main window or application instance
    
    def show_message(self,message: str):
        """Adds a status message to the status bar."""
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(message)
        else:
            self.parent.statusLabel.setText(message)
    
    def clear_message(self):
        """Clears the status message."""
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().clearMessage()
        else:
            self.parent.statusLabel.setText("")
