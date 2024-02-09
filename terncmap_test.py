import numpy as np
from ternary_plot import ternary
labels =['a', 'b', 'c']
t = ternary(labels)

a = []
hbin = t.hexagon(5)
xc = np.array([v['xc'] for v in hbin])
yc = np.array([v['yc'] for v in hbin])
a,b,c = t.xy2tern(xc,yc)
cv = t.terncolor(a,b,c)
for i, hb in enumerate(hbin):
    t.axs[0].fill(hb['xv'], hb['yv'], color=cv[i], edgecolor='none')