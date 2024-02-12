import numpy as np
from ternary_plot import ternary
labels =['a', 'b', 'c']
t = ternary(labels)

a = []
hbin = t.hexagon(10)
xc = np.array([v['xc'] for v in hbin])
yc = np.array([v['yc'] for v in hbin])
a,b,c = t.xy2tern(xc,yc)
cv = t.terncolor(a,b,c, ca = [1,1,0],cb = [0,1,1],cc=[1,0,1], cp = [1, 1, 1])
for i, hb in enumerate(hbin):
    t.axs[0].fill(hb['xv'], hb['yv'], color=cv[i], edgecolor='none')
t.fig