import pandas as pd
import numpy as np
from scipy.stats import yeojohnson, percentileofscore
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
#from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

class Clustering():
    def __init__(self, parent):

        self.parent = parent

        self.distance_metrics = ['euclidean', 'manhattan', 'mahalanobis', 'cosine']

        self.cluster_methods = ['k-means', 'fuzzy c-means']

    def compute_clusters(self,data, app_data, max_clusters = None):
        """Computes cluster results

        When clustering is run once with a specified value of app_data.n_clusters, compute_cluster is run with max_cluster = None. Else clustering is run 
        n_cluster fro 1 to app_data.max_clusters"""
        #print('\n===compute_clusters===')
        if app_data.sample_id == '':
            return

        df_filtered, isotopes = data.get_processed_data()
        filtered_array = df_filtered.values
        array = filtered_array[data.mask]


        seed = app_data.cluster_seed
        method = app_data.cluster_method
        exponent = app_data.cluster_exponent

        # get clustering options
        if max_clusters is None: 
            # set all masked data to cluster id 99
            n_clusters = [app_data.num_clusters]
            data.processed_data[method] = 99
        else:
            n_clusters = np.arange(1,app_data.max_clusters+1).astype(int)
            cluster_results = []
            silhouette_scores = []

        if exponent == 1:
            exponent = 1.0001
        distance_type = app_data.cluster_distance

        #self.statusbar.showMessage('Precomputing distance for clustering...')
        # match distance_type:
        #     # euclidean (a.k.a. L2-norm)
        #     case 'euclidean':
        #         distance = euclidean(array)

        #     # manhattan (a.k.a. L1-norm and cityblock)
        #     case 'manhattan':
        #         distance = manhattan(array)

        #     # mahalanobis = MahalanobisDistance(n_components=n_pca_basis)
        #     case 'mahalanobis':
        #         inv_cov_matrix = np.linalg.inv(np.cov(array))

        #         distance = np.array([mahalanobis(x, np.mean(array, axis=0), inv_cov_matrix) for x in array])

        #     # fisher-rao (a.k.a. cosine?) = FisherRaoDistance()
        #     case 'cosine':
        #         distance = cosine_distances(array)

        match method:
            # k-means
            case 'k-means':
                # setup k-means
                for nc in n_clusters:
                    kmeans = KMeans(n_clusters=nc, init='k-means++', random_state=seed)

                    # produce k-means model from data
                    model = kmeans.fit(array)

                    #add k-means results to self.data
                    if max_clusters is None:
                        data.add_columns('Cluster', method, model.predict(array), data.mask)
                    else:
                        kmeans.fit(array)
                        cluster_results.append(kmeans.inertia_)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, kmeans.labels_, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")
                        data.cluster_results[method] =cluster_results
                        data.silhouette_scores[method] = silhouette_scores

            # fuzzy c-means
            case 'fuzzy c-means':
                for nc in n_clusters:
                    # compute cluster scores
                    cntr, u, _, dist, _, _, _ = fuzz.cluster.cmeans(array.T, nc, exponent, error=0.00001, maxiter=1000, seed=seed)
                    #cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, metric='precomputed', error=0.00001, maxiter=1000, seed=seed)
                    # cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.005, maxiter=1000,seed =23)

                    labels = np.argmax(u, axis=0)

                    if max_clusters is None:
                        # assign cluster scores to self.data
                        for n in range(nc):
                            #data['computed_data']['cluster score'].loc[:,str(n)] = pd.NA
                            data.add_columns('Cluster score', 'cluster' + str(n), u[n-1,:], data.mask)

                        #add cluster results to self.data
                        data.add_columns('Cluster', method, labels, data.mask)
                    else:
                        # weighted sum of squared errors (WSSE)
                        wsse = np.sum((u ** exponent) * (dist ** 2))
                        cluster_results.append(wsse)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, labels, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")
            
                        data.cluster_results[method] =cluster_results
                        data.silhouette_scores[method] = silhouette_scores




class DimensionalReduction():
    def __init__(self, parent):
        self.parent = parent

        self.dim_red_methods = ['PCA: Principal component analysis', 'MDS: Multidimensional scaling', 'LDA: Linear discriminant analysis', 'FA: Factor analysis']

    def compute_dim_red(self ,data, app_data):
        match app_data.dim_red_method:
            case 'PCA: Principal component analysis':
                self.compute_pca(data, app_data)
    
    def compute_pca(self,data, app_data):
        #print('compute_pca')
        df_filtered, _ = data.get_processed_data()

        # Preprocess the data
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_filtered)

        # Perform PCA
        pca_results = PCA(n_components=min(len
                                           (df_filtered.columns), len(df_filtered)))  # Adjust n_components as needed
        
        # store PCA results in data
        data.dim_red_results[app_data.dim_red_method] = pca_results

        # compute pca scores
        pca_scores = pd.DataFrame(pca_results.fit_transform(df_scaled), columns=[f'PC{i+1}' for i in range(pca_results.n_components_)])
        

        # Add PCA scores to DataFrame for easier plotting
        data.add_columns('PCA score',pca_scores.columns,pca_scores.values,data.mask)
        
        # update_pca_flag to prevent PCA running during when app_data.dim_red_y is being set
        app_data.update_pca_flag = False
        #update min and max of PCA spinboxes
        if pca_results.n_components_ > 0:
            app_data.dim_red_x_min = 1
            app_data.dim_red_y_min = 1
            app_data.dim_red_x_max =  pca_results.n_components_+1
            app_data.dim_red_y_max =  pca_results.n_components_+1
            if app_data.dim_red_y == 1:
                app_data.dim_red_y = int(2)