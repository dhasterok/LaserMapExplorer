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
