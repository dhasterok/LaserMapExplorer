import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# Generate sample data
np.random.seed(0)
X = np.random.rand(100, 2)  # 100 points in 2D

# Apply KMeans clustering
kmeans = KMeans(n_clusters=3, random_state=0)  # Change n_clusters as needed
kmeans.fit(X)
labels = kmeans.labels_

# Plotting the results
plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis')
centers = kmeans.cluster_centers_
plt.scatter(centers[:, 0], centers[:, 1], c='red', s=200, alpha=0.5)  # Mark the centroids
plt.title('KMeans Clustering')
plt.xlabel('Feature 1')
plt.ylabel('Feature 2')
plt.show()
