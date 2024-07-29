from PyQt5.QtWidgets import QLineEdit

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None, value=0.0, precision=2):
        super().__init__(parent)
        self._value = value
        self._precision = precision
        self.textChanged.connect(self._update_value_from_text)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self._update_text_from_value()

    @property
    def precision(self):
        return self._precision 
    
    @precision.setter
    def precision(self, new_precision):
        self._precision = new_precision
        self._update_text_from_value

    def _update_text_from_value(self):
        self.setText(f"{self._value:.{self._precision}f}")

    def _update_value_from_text(self):
        try:
            self._value = float(self.text())
        except ValueError:
            pass