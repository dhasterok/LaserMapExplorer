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
    if val == 0:
        return 0

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


def symlog(x, linear_threshold=1.0):
    """Transforms data from linear to symlog space

    The advantage of a symlog transformation is that produces a log-like distribution for most
    values, but can be used on negative and zero values as well as positive values,
    preserves symmetry about 0.

    A symlog transformation is symlog(x) = sign(x) * log_{10}(1 + |x / a|), where a is the 
    linear threshold, region where the transformation is approximately linear.

    Parameters
    ----------
    x : numpy.array
        the array of values to transform
    linear_threshold : float, optional
        linear threshold, often chosen as the mean, median, or standard deviation of the data
        or simply, by default 1.0

    Returns
    -------
    numpy.array
        _description_
    """    
    x = np.asarray(x)
    return np.sign(x) * np.log10(1 + np.abs(x / linear_threshold))

def invsymlog(y, linthresh=1.0):
    """Inverse symlog transform back to linear space

    Converts an array back to into linear space.

    Parameters
    ----------
    y : numpy.array
        the array of values to transform
    linear_threshold : float, optional
        linear threshold, often chosen as the mean, median, or standard deviation of the data
        or simply, by default 1.0

    Returns
    -------
    numpy.array
        
    :see also: symlog
    """    
    y = np.asarray(y)
    return np.sign(y) * linthresh * (10**np.abs(y) - 1)
