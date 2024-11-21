#!/usr/bin/env python3
import numpy as np
import scipy.special

def chauvenet_criterion(data, threshold=1):
    """Apply Chauvenet's criterion for outlier detection.
    
    Parameters
    ----------
    data : numpy.ndarray
        The dataset to analyze.
    threshold : float
        The probability threshold multiplier for rejecting outliers (default is 1, stricter is higher).
        
    Returns
    -------
    numpy.ndarray
        Boolean mask, with outliers identified as false.
        

    Source: https://en.wikipedia.org/wiki/Chauvenet%27s_criterion
    """
    # Convert the input data to a numpy array
    data = np.array(data)
    
    # Calculate the mean and standard deviation of the data
    mean = np.mean(data)
    std_dev = np.std(data)
    
    # Calculate the deviation of each data point from the mean in terms of standard deviations
    z_scores = np.abs(data - mean) / std_dev
    
    # Determine the probability of observing each z-score or higher in a standard normal distribution
    probabilities = 2 * (1 - 0.5 * (1 + np.erf(z_scores / np.sqrt(2))))
    
    # Calculate the minimum acceptable probability based on Chauvenet's criterion
    n = len(data)
    min_prob = threshold / (2 * n)
    
    # Identify data points that meet the criterion
    mask = probabilities >= min_prob
    
    return mask


def peirce_dev(N: int, n: int, m: int) -> float:
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
        #
        # Initialize R values (as floats)
        r_new = 1.0
        r_old = 0.0  # <- Necessary to prompt while loop
        #
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
                r_new = np.exp((x2 - 1) / 2.0) * scipy.special.erfc(
                    numpy.sqrt(x2) / np.sqrt(2.0)
                )
    else:
        x2 = 0.0
    return x2