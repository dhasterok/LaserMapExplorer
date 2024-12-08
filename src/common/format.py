import numpy as np

def oround(val, order=2, toward=None):
    """Rounds a single of value to n digits

    Round a single number to the first n digits.

    Parameters
    ----------
    val : float
        number to round
    order : int, optional
        number of orders to retain, by default 2
    toward : int, optional
        direction for rounding, ``0`` for down, ``1`` for up, and ``None`` for nearest, by default None

    Returns
    -------
    float
        rounded matrix values
    """        
    if not isinstance(val, (float, int)):
        raise TypeError("val must be of type float or int")
    elif val == 0:
        return 0

    if not isinstance(order, (int)):
        raise TypeError("order must be of type float or int")

    if not (isinstance(toward, (float, int)) or toward is None):
        raise TypeError("toward order must be of type float, int or None")

    power = np.floor(np.log10(abs(val)))
    if toward == 0:
        return np.floor(val / 10**(power-order)) * 10**(power - order)
    elif toward == 1:
        return np.ceil(val / 10**(power-order)) * 10**(power - order)
    elif toward is None:
        return np.round(val / 10**(power-order)) * 10**(power - order)
    else:
        raise ValueError("Valid values of toward may be 0, 1, or None.")

def oround_matrix(val, order=2, toward=None):
    """Rounds a matrix of values to n digits

    Rounds all numbers in a matrix to the first n digits.

    Parameters
    ----------
    val : float
        number to round
    order : int, optional
        number of orders to retain, by default 2
    toward : int, optional
        direction for rounding, ``0`` for down, ``1`` for up, and ``None`` for nearest, by default None

    Returns
    -------
    float
        rounded matrix values
    """        
    newval = np.zeros(np.shape(val))

    idx = (val != 0)
    power = np.floor(np.log10(abs(val[idx])))
    if toward == 0:
        newval[idx] = np.floor(val[idx] / 10**(power-order)) * 10**(power - order)
    elif toward == 1:
        newval[idx] = np.ceil(val[idx] / 10**(power-order)) * 10**(power - order)
    else:
        newval[idx] = np.round(val[idx] / 10**(power-order)) * 10**(power - order)

    return newval

def dynamic_format(value, threshold=1e4, order=4, toward=None):
    """Prepares number for display as *str*

    Formats a number of display as a *str*, typically in a *lineEdit* widget.

    Parameters
    ----------
    value : float
        number to round
    threshold : float, optional
        order of magnitude for determining display as floating point or expressing in engineering notation, by default 1e4
    order : int, optional
        number of orders to keep, by default 4
    toward : int, optional
        direction for rounding, ``0`` for down, ``1`` for up, and ``None`` for nearest, by default None

    Returns
    -------
    str
        number formatted as a string
    """        
    if toward is not None:
        value = oround(value, order=order, toward=toward)

    if abs(value) > threshold:
        return f'{{:.{order-1}e}}'.format(value)  # Scientific notation with order decimal places
    else:
        return f'{{:.{order}g}}'.format(value)