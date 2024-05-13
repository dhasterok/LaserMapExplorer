import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0,5,6)
y = x

X, Y = np.meshgrid(x,y)

Z = (X**2+Y-11)**2

ax = plt.subplot(1,3,1)
plt.imshow(Z,cmap='jet')

layer = np.zeros((6,6))
layer[3,3] = 1
layer[2,4] = 1

masked = np.ma.masked_where(layer == 0, layer)
ax.imshow(masked,alpha=1,cmap = 'Reds')
plt.show()