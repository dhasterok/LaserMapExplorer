def partial_match(array: list[str], string: str) -> list[bool]:
    """Checks whether values in a list partially match a string

    Parameters
    ----------
    array: list[str]
        List of partial strings to find in ``string``
    string: str
        Text to test.

    Returns
    -------
    list[bool]
        ``True`` for strings that match the input string.
    """
    matches = [False]*len(array)
    for i, val in enumerate(array):
        if isinstance(val,str) and val in string:
            matches[i] = True

    return matches

class ObservableDict(dict):
    def __init__(self, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def _trigger_change(self):
        if self._callback:
            self._callback(self)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._trigger_change()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._trigger_change()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._trigger_change()