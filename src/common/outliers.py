#!/usr/bin/env python3
import numpy as np
import scipy.special

def chauvenet_criterion(array, threshold=1):
    """Apply Chauvenet's criterion for outlier detection.
    
    Parameters
    ----------
    array : numpy.ndarray
        The dataset to analyze.
    threshold : float
        The probability threshold multiplier for rejecting outliers (default is 1, stricter is higher).
        
    Returns
    -------
    numpy.ndarray
        Boolean mask, with outliers identified as false.
        

    Source: https://en.wikipedia.org/wiki/Chauvenet%27s_criterion
    """
    # Convert the input array to a numpy array
    array = np.array(array)
    
    # Calculate the mean and standard deviation of the array
    mean = np.mean(array, axis=0)
    std_dev = np.std(array, axis=0)
    
    # Calculate the deviation of each array point from the mean in terms of standard deviations
    z_scores = np.abs(array - mean) / std_dev
    
    # Determine the probability of observing each z-score or higher in a standard normal distribution
    probabilities = 2 * (1 - 0.5 * (1 + scipy.special.erf(z_scores / np.sqrt(2))))
    
    # Calculate the minimum acceptable probability based on Chauvenet's criterion
    n = len(array)
    min_prob = threshold / (2 * n)
    
    # Identify array points that meet the criterion
    mask = probabilities >= min_prob
    
    return mask


def peirce_dev(N, n, m) -> float:
    """Peirce's criterion
    
    Returns the squared threshold error deviation for outlier identification
    using Peirce's criterion based on Gould's methodology.
    
    Parameters
    ----------
    N : int
        Total number of observations
    n : int
        number of outliers to be removed
    m : int
        number of model unknowns

    Returns
    -------
    float
        squared error threshold

    Source: Wikipedia https://en.wikipedia.org/wiki/Peirce%27s_criterion
    """
    # Assign floats to input variables:
    N = float(N)
    n = float(n)
    m = float(m)

    # Check number of observations:
    if N > 1:
        # Calculate Q (Nth root of Gould's equation B):
        Q = (n ** (n / N) * (N - n) ** ((N - n) / N)) / N
        
        # Initialize R values (as floats)
        r_new = 1.0
        r_old = 0.0  # <- Necessary to prompt while loop
        
        # Start iteration to converge on R:
        while abs(r_new - r_old) > (N * 2.0e-16):
            # Calculate Lamda
            # (1/(N-n)th root of Gould's equation A'):
            ldiv = r_new ** n
            if ldiv == 0:
                ldiv = 1.0e-6
            Lamda = ((Q ** N) / (ldiv)) ** (1.0 / (N - n))
            # Calculate x-squared (Gould's equation C):
            x2 = 1.0 + (N - m - n) / n * (1.0 - Lamda ** 2.0)
            # If x2 goes negative, return 0:
            if x2 < 0:
                x2 = 0.0
                r_old = r_new
            else:
                # Use x-squared to update R (Gould's equation D):
                r_old = r_new
                r_new = np.exp((x2 - 1) / 2.0) * scipy.special.erfc( np.sqrt(x2) / np.sqrt(2.0))
    else:
        x2 = 0.0
    return x2

    
def quantile_and_difference(array, pl, pu, dpl, dpu, compositional, max_val):
    """Outlier detection with cluster-based correction for negatives and compositional constraints, using percentile-based shifting.

    Parameters
    ----------
    array : numpy.ndarray
        Data to detect outliers
    pl : float
        lower percentile bound
    pu : float
        upper percentile bound
    dpl : float
        _description_
    dpu : float
        _description_
    compositional : bool
        _description_
    max_val : float
        _description_

    Returns
    -------
    numpy.ndarray
        array with outliers removed
    """

    # Set a small epsilon to handle zeros (if compositional data)
    epsilon = 1e-10 if compositional else 0

    # Shift data to handle zeros and negative values for log transformations
    v0 = np.nanmin(array, axis=0) - epsilon
    data_shifted = np.log10(array - v0 + epsilon)

    # Quantile-based clipping (detect outliers)
    ql_val = np.nanpercentile(data_shifted, pl, axis=0)
    qu_val = np.nanpercentile(data_shifted, pu, axis=0)

    # Sort data and calculate differences between adjacent points
    sorted_indices = np.argsort(data_shifted, axis=0)
    sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)
    diff_sorted_data = np.diff(sorted_data, axis=0)

    # Account for the size reduction in np.diff by adding a zero row at the beginning
    diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
    diff_array_qu_val = np.nanpercentile(diff_sorted_data, dpu, axis=0)
    diff_array_ql_val = np.nanpercentile(diff_sorted_data, dpl, axis=0)

    # Initialize array for results
    clipped_data = np.copy(sorted_data)

    # Apply upper bound clipping based on quantiles and differences
    upper_cond = (sorted_data > qu_val) & (diff_sorted_data > diff_array_qu_val)
    for col in range(sorted_data.shape[1]):
        up_indices = np.where(upper_cond[:, col])[0]
        if len(up_indices) > 0:
            qu_outlier_index = up_indices[0]
            clipped_data[qu_outlier_index:, col] = clipped_data[qu_outlier_index - 1, col]

    # Apply lower bound clipping similarly based on lower quantile and difference
    lower_cond = (sorted_data < ql_val) & (diff_sorted_data > diff_array_ql_val)
    for col in range(sorted_data.shape[1]):
        low_indices = np.where(lower_cond[:, col])[0]
        if len(low_indices) > 0:
            ql_outlier_index = low_indices[-1]
            clipped_data[:ql_outlier_index + 1, col] = clipped_data[ql_outlier_index + 1, col]

    # Restore original data order and undo the log transformation
    clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
    clipped_data = 10**clipped_data + v0 - epsilon

    # Enforce upper bound (compositional constraint) to ensure data <= max_val
    clipped_data = np.where(clipped_data > max_val, max_val, clipped_data)

    # Ensure non-negative values and avoid exact zeros by shifting slightly if needed
    clipped_data = np.maximum(clipped_data, epsilon)

    return clipped_data