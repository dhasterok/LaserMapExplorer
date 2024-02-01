import numpy as np
from scipy.stats import norm, mode
from scipy.special import erfinv,erf
from scipy.interpolate import interp1d
def gausscensor(x, scale='linear', q=None , a=3/8):
    if q is None:
        q=[0.05, 0.25, 0.5, 0.75, 0.95]
        
    x = np.array(x)
    x = x[~np.isnan(x)]
    c = -x[x <= 0]
    u = x[x > 0]

    if len(u) < 8:
        return {'mu': np.nan, 'sigma': np.nan, 'sigma_mu': np.nan, 'rms': np.nan}

    mode_c = mode(c)[0] if len(c) > 0 else 0
    c[c == 0] = mode_c if mode_c != 0 else 10 * min(u)

    if scale == 'log':
        u = np.log(u)
        c = np.log(c)
    elif scale == 'log10':
        u = np.log10(u)
        c = np.log10(c)

    c = np.sort(c)
    u = np.sort(u)

    # Handling censored and uncensored data
    nc = len(c)
    nu = len(u)
    N = len(x)
    ind = np.zeros_like(u, dtype=int)
    j = k = 0
    if len(c)>0:
        while k < nc and j < nu:
            if c[k] <= u[j]:
                k += 1
            else:
                ind[j] = j + k
                j += 1
        if j < nu:
            ind[j:nu] = np.arange(j, nu) + k

    # Creating empirical CDF
    y = (N - a + 1) / (N - 2 * a + 1) * np.cumprod(((ind+1 - a) / (ind+2 - a))[::-1], axis=0)[::-1]
    
    # Unique values for u and y
    uu, indices = np.unique(u, return_index=True)
    yy = y[indices]

    # Calculating mean and sigma
    dy = np.diff(np.insert(yy, 0, 0))
    mu = np.sum(uu * dy)
    sigma = np.sqrt(N/(N - 1) * np.sum((uu - mu)**2 * dy))

    # RMS misfit
    rms = np.sqrt(np.sum((yy - 0.5 * (1 + erf((uu - mu) / (np.sqrt(2) * sigma))))**2) / N)

    model = {'mu': mu, 'sigma': sigma, 'rms': rms}
    
    
    quantile_values = np.zeros((len(q), 2))  # Initialize quantile_values with two columns
    quantile_values[:, 0] = mu + sigma * np.sqrt(2) * erfinv(2 * np.array(q) - 1)
    
    # Try to interpolate uu at points Q based on yy, and handle exceptions
    try:
        interp_func = interp1d(yy, uu)  # will raise an error if Q is out of bounds
        quantile_values[:, 1] = interp_func(q)
    except Exception as e:
        print(f"Interpolation failed: {e}")
        quantile_values[:, 1] = quantile_values[:, 0]

    return model, quantile_values

# # Example usage
# data = [-1, 0.5, 1, 1.5, -2, -3, 4, 5, 6, 7, 8]  # Example dataset
# q =  np.array([0.025, 0.25, 0.5, 0.75, 0.975])
# model,q = gausscensor(data,q)
# print(model)
