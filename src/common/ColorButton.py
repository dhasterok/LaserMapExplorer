
class ColorButton(QPushButton):
    """
    A QPushButton subclass that allows the user to select a background color
    via a QColorDialog. The widget tracks a history of recently selected colors
    and emits a signal whenever the color changes.

    Features:
    - Emits `colorChanged(str)` with hex color when the button's color is updated.
    - Maintains a history of recently used colors for quick access.
    - Displays the selected color as the button background.

    Attributes
    ----------
    permanent_text : str or None
        Fixed text displayed on the button. If None, the button text shows
        the selected color's hex code.
    ui : QWidget or None
        Reference to the parent UI component, used as the parent for the color dialog.
    _color_history : list of QColor
        Internal list tracking recently selected colors.
    _max_history : int
        Maximum number of colors to keep in the history (default = 16).
    
    Signals
    -------
    colorChanged(str)
        Emitted when the button's background color changes. Emits hex string.

    Parameters
    ----------
    permanent_text : str or None
        Fixed text to display on the button. If None, the button text
        will display the color's hex code.
    ui : QWidget or None
        Parent UI component, used as the parent for the color dialog.
    parent : QWidget or None
        Parent widget in the Qt hierarchy.

    Example
    -------

    btn = ColorButton("Pick Color")
    btn.colorChanged.connect(lambda hex_color: print("New color:", hex_color))

    """

    # Signal that emits the new color as hex string
    colorChanged = pyqtSignal(str)

    def __init__(self, permanent_text=None, ui=None, parent=None, initial_color=None):
        super().__init__(parent=parent)

        self.setContentsMargins(3, 3, 3, 3)
        self.permanent_text = permanent_text
        self.setText(self.permanent_text if permanent_text else "")

        self._color_history = []  # Track recently selected colors
        self._max_history = 16    # QColorDialog supports 16 custom slots (0-15)

        self.clicked.connect(self.select_color)

        # Apply initial color if given
        self.styles = { "border": "1px solid black",
            "border-radius": "4px",
            "background-color": "none;"
        }
        self.ui = ui
        if initial_color is None:
            initial_color = None
        if initial_color and not isinstance(initial_color, QColor):
            initial_color = QColor(initial_color)
        self._apply_color(initial_color)
        self._update_history(initial_color)

    @property
    def color(self):
        """QColor : Return the current background color of the button."""
        return self.palette().color(self.backgroundRole())

    @color.setter
    def color(self, value):
        """Allow setting via ColorButton.color = QColor(...) or a string."""
        if not value:
            value = None
            self._apply_color(value)
            self.colorChanged.emit(value)
        else:
            if not isinstance(value, QColor):
                value = QColor(value)

            if value.isValid():
                self._apply_color(value)
                self._update_history(value)
                # Emit hex string instead of QColor
                self.colorChanged.emit(value.name())

    def select_color(self):
        """
        Open a ColorSelector to allow the user to select a color.

        - Initializes the dialog with the current color.
        - Updates the button background and text when a new color is selected.
        - Emits `colorChanged(str)` with hex string if the color changes.
        """
        old_color = self.color
        initial_hex = old_color.name() if old_color.isValid() else None
        
        # Use ColorSelector.select_color function
        selected_hex = select_color(initial_color=initial_hex, parent=self)

        if selected_hex and selected_hex != initial_hex:
            new_color = QColor(selected_hex)
            if new_color.isValid():
                self.color = new_color


    def _apply_color(self, color: QColor | None):
        """
        Apply the given color to the button's background and update its text.

        Parameters
        ----------
        color : QColor | None
            The new color to apply.
        """
        if color is None:
            self.styles["background-color"] = "none"
            text_color = "black"
        else:
            self.styles["background-color"] = color.name()

            # Compute relative luminance to decide text color
            r, g, b = color.redF(), color.greenF(), color.blueF()
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            text_color = "#414042" if luminance > 0.5 else "#ffffff"

        # apply both bg and fg
        self.styles["color"] = text_color

        self.setStyleSheet(
            "QPushButton {" + "; ".join(f"{k}: {v}" for k, v in self.styles.items()) + "; }"
        )

        if self.permanent_text is None:
            if color is None:
                self.setText("None")
            else:
                self.setText(color.name())

    def _update_history(self, color: QColor):
        """
        Add the given color to the recent history, keeping it unique
        and limited to the maximum history size.

        Parameters
        ----------
        color : QColor
            The color to add to the history.
        """
        # Add new color at front, keep unique, maintain max length
        if color in self._color_history:
            self._color_history.remove(color)
        self._color_history.insert(0, color)
        self._color_history = self._color_history[:self._max_history]