import numpy as np
from ternary_plot import ternary
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

labels =['a', 'b', 'c']
fig = plt.figure()
ax = fig.add_subplot(111)

t = ternary(ax,labels)

a = []
hbin = t.hexagon(10)
xc = np.array([v['xc'] for v in hbin])
yc = np.array([v['yc'] for v in hbin])
a,b,c = t.xy2tern(xc,yc)
cv = t.terncolor(a,b,c, ca = [1,1,0],cb = [0,1,1],cc=[1,0,1], cp = [1, 1, 1])
for i, hb in enumerate(hbin):
    t.ax.fill(hb['xv'], hb['yv'], color=cv[i], edgecolor='none')

fig.show()
