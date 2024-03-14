#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 16:29:10 2023

@author: Shavin Kaluthantri
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.interpolate import LinearNDInterpolator
from scipy.special import erfinv,erf
from gausscensor import gausscensor

def adjby_quantile2(x_v, y_v, xref=None, x=None, y=None):
    """
    
    :param x_v:
    :type x_v:
    :param y_v:
    :type y_v:
    :param xref: Defaults to None
    :type xref: optional
    :param x: Defaults to None
    :type y: optional
    :param y: Defaults to None
    :type x: optional
    """
    # Step 1 - create x bins
    min_x = np.min(x_v)
    max_x = np.max(x_v)
    x_edges = np.linspace(min_x, max_x, 21)
    x_mid = (x_edges[:-1] + x_edges[1:]) / 2

    # Step 2 & 3 - determine empirical CDF for each bin and estimate scale parameters
    Q = np.array([0.0001, 0.5, 2.5] + list(range(10, 91, 10)) + [97.5, 99.5, 99.999]) / 100
    F = np.sqrt(2) * erfinv(2 * Q - 1)

    x_q = np.tile(x_mid, (len(Q), 1))
    y_q = np.zeros((len(Q), len(x_edges) - 1))
    
    model = []
    for i in range(len(x_edges) - 1):
        ind = (x_edges[i] <= x_v) & (x_v <= x_edges[i + 1])
        
        # Assuming gausscensor function is defined as provided earlier
        tmp, y_qtmp = gausscensor(y_v[ind], scale='log', quantiles=Q)
        
        model.append({
            'x': x_mid[i],
            'mu': tmp['mu'],
            'sigma': tmp['sigma'],
            'sigma_mu': tmp.get('sigma_mu', np.nan),
            'rms': tmp['rms'],
            'N': np.sum(ind)
        })
        
        y_q[:, i] = y_qtmp

    # Convert model list to a structured array or DataFrame for easier handling
    model = np.array(model)
    
    # Polynomial fitting for smooth model
    mind = ~np.isnan(model['mu'])
    W = np.diag(np.sqrt(model['N'][mind]))
    Aw2 = np.dot(W, np.column_stack((np.ones(np.sum(mind)), x_mid[mind], x_mid[mind]**2)))
    Cw2 = np.linalg.inv(np.dot(Aw2.T, Aw2))
    mm = np.dot(Cw2, np.dot(Aw2.T, np.dot(W, model['mu'][mind])))
    
    Aw = np.dot(W, np.column_stack((np.ones(np.sum(mind)), x_mid[mind])))
    Cw = np.linalg.inv(np.dot(Aw.T, Aw))
    ms = np.dot(Cw, np.dot(Aw.T, np.dot(W, model['sigma'][mind])))

    # Interpolating y_q quantiles to reference xref value
    y_q_smooth = np.zeros_like(y_q)
    for i in range(len(x_edges) - 1):
        y_q_smooth[:, i] = mm[0] + mm[1] * x_mid[i] + mm[2] * x_mid[i]**2 + (ms[0] + ms[1] * x_mid[i]) * F

    if xref is not None:
        yref = np.array([np.interp(xref, x_q[i, :], y_q[i, :]) for i in range(len(Q))])
        Yref = np.array([np.interp(xref, x_q[i, :], y_q_smooth[i, :]) for i in range(len(Q))])

        # Interpolate y quantile to xref along a quantile
        F_interp = LinearNDInterpolator(np.column_stack((x_q.flatten(), y_q_smooth.flatten())), np.tile(Q, len(x_edges) - 1))
        Qy = F_interp(x, np.log10(y))

        y_at_ref = 10**np.interp(Qy, Q, Yref)

        return y_at_ref, Qy  # Add other outputs as necessary

    return model, x_q, y_q, y_q_smooth  # Add other outputs as necessary

# Example usage - assuming x_v, y_v, etc. are defined
model, x_q, y_q, y_q_smooth = adjby_quantile2(x_v, y_v)