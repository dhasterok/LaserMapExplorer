from PyQt5.QtWidgets import QLineEdit
import src.format as fmt

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None, value=0.0, precision=4, threshold=1e4, toward=None):
        super().__init__(parent)
        self._value = value
        self._precision = precision
        self._threshold = threshold
        self._toward = toward
        self.textChanged.connect(self._update_value_from_text)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        # ensure value is a float rather than integer
        self._value = new_value
        self._update_text_from_value()

    @property
    def precision(self):
        return self._precision 

    @precision.setter
    def precision(self, new_precision):
        self._precision = new_precision
        self._update_text_from_value
    
    @property
    def threshold(self):
        return self._threshold
    
    @threshold.setter
    def threshold(self, new_threshold):
        self._threshold = new_threshold
        self._update_text_from_value

    @property
    def toward(self):
        return self._toward
    
    @toward.setter
    def toward(self, new_toward):
        self._toward = new_toward
        self._update_text_from_value

    def _update_text_from_value(self):
        if self._value is None:
            self.setText('')
        elif self._precision is None:
            self.setText(str(self._value))
        else:
            self.setText(fmt.dynamic_format(self._value, threshold=self._threshold, order=self._precision, toward=self._toward))
            #self.setText(f"{self._value:.{self._precision}f}")

    def _update_value_from_text(self):
        try:
            self._value = float(self.text())
        except ValueError:
            pass