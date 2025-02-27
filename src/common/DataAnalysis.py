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

        # Clustering Tab
        #-------------------------
        # cluster dictionary
        # number of clusters
        parent.spinBoxNClusters.valueChanged.connect(self.number_of_clusters_callback)

        # Populate the comboBoxClusterDistance with distance metrics
        # euclidean (a.k.a. L2-norm) = euclidean
        # manhattan (a.k.a. L1-norm and cityblock)= manhattan
        # mahalanobis = mahalanobis(n_components=n_pca_basis)
        # cosine = cosine_distances
        distance_metrics = ['euclidean', 'manhattan', 'mahalanobis', 'cosine']

        parent.comboBoxClusterDistance.clear()
        parent.comboBoxClusterDistance.addItems(distance_metrics)
        parent.comboBoxClusterDistance.setCurrentIndex(0)
        parent.comboBoxClusterDistance.activated.connect(self.cluster_distance_callback)

        # cluster exponent
        parent.horizontalSliderClusterExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        parent.horizontalSliderClusterExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        parent.horizontalSliderClusterExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        parent.horizontalSliderClusterExponent.setTickInterval(1)
        parent.horizontalSliderClusterExponent.valueChanged.connect(lambda value: self.labelClusterExponent.setText(str(value/10)))
        parent.horizontalSliderClusterExponent.sliderReleased.connect(self.cluster_exponent_callback)

        # starting seed
        parent.lineEditSeed.setValidator(QIntValidator(0,1000000000))
        parent.lineEditSeed.editingFinished.connect(self.cluster_seed_callback)
        parent.toolButtonRandomSeed.clicked.connect(self.generate_random_seed)

        # cluster method
        parent.comboBoxClusterMethod.activated.connect(self.cluster_method_callback)
        self.cluster_method_callback()

        # Connect cluster method comboBox to slot
        parent.comboBoxClusterMethod.currentIndexChanged.connect(self.group_changed)

    # -------------------------------------
    # Cluster functions
    # -------------------------------------
    def plot_cluster_map(self):
        """Produces a map of cluster categories
        
        Creates the map on an ``mplc.MplCanvas``.  Each cluster category is assigned a unique color.
        """
        print('plot_cluster_map')
        canvas = mplc.MplCanvas(parent=self)

        plot_type = self.plot_style.plot_type
        method = self.comboBoxClusterMethod.currentText()

        # data frame for plotting
        #groups = self.data[self.app_data.sample_id][plot_type][method].values
        groups = self.data[self.app_data.sample_id].processed_data[method].values

        reshaped_array = np.reshape(groups, self.data[self.app_data.sample_id].array_size, order=self.data[self.app_data.sample_id].order)

        n_clusters = len(np.unique(groups))

        cluster_color, cluster_label, cmap = self.plot_style.get_cluster_colormap(self.app_data.cluster_dict[method], alpha=self.plot_style.marker_alpha)

        #boundaries = np.arange(-0.5, n_clusters, 1)
        #norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)
        norm = self.plot_style.color_norm(n_clusters)

        #cax = canvas.axes.imshow(self.array.astype('float'), cmap=self.plot_style.cmap, norm=norm, aspect = self.data[self.app_data.sample_id].aspect_ratio)
        cax = canvas.axes.imshow(reshaped_array.astype('float'), cmap=cmap, norm=norm, aspect=self.data[self.app_data.sample_id].aspect_ratio)
        canvas.array = reshaped_array
        #cax.cmap.set_under(style['Scale']['OverlayColor'])

        self.add_colorbar(canvas, cax, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)

        canvas.fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
        canvas.fig.tight_layout()

        canvas.axes.set_title(f'Clustering ({method})')
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        #canvas.axes.set_axis_off()

        # add scalebar
        self.add_scalebar(canvas.axes)

        return canvas, self.data[self.app_data.sample_id].processed_data[method]

    def cluster_performance_plot(self):
        """Plots used to estimate the optimal number of clusters

        1. Elbow Method
        The elbow method looks at the variance (or inertia) within clusters as the number
        of clusters increases. The idea is to plot the sum of squared distances between
        each point and its assigned cluster's centroid, known as the within-cluster sum
        of squares (WCSS) or inertia, for different values of k (number of clusters).

        Process:
        * Run KMeans for a range of cluster numbers (k).
        * Plot the inertia (WCSS) vs. the number of clusters.
        * Look for the "elbow" point, where the rate of decrease sharply slows down,
        indicating that adding more clusters does not significantly reduce the inertia.


        2. Silhouette Score
        The silhouette score measures how similar an object is to its own cluster compared
        to other clusters. The score ranges from -1 to 1, where:

        * A score close to 1 means the sample is well clustered.
        * A score close to 0 means the sample lies on the boundary between clusters.
        * A score close to -1 means the sample is assigned to the wrong cluster.

        In cases where clusters have widely varying sizes or densities, Silhouette Score may provide the best result.

        Process:
        * Run KMeans for a range of cluster numbers (k).
        * Calculate the silhouette score for each k.
        * Choose the k with the highest silhouette score.
        """        
        if self.app_data.sample_id == '':
            return

        method = self.comboBoxClusterMethod.currentText()

        # maximum clusters for producing an cluster performance
        max_clusters = self.spinBoxClusterMax.value() 

        # compute cluster results
        inertia, silhouette_scores = self.compute_clusters(max_clusters)

        second_derivative = np.diff(np.diff(inertia))

        #optimal_k = np.argmax(second_derivative) + 2  # Example heuristic

        # Plot inertia
        canvas = mplc.MplCanvas(parent=self)

        canvas.axes.plot(range(1, max_clusters+1), inertia, linestyle='-', linewidth=self.plot_style.line_width,
            marker=self.plot_style.marker_dict[self.plot_style.marker], markeredgecolor=self.plot_style.marker_color, markerfacecolor='none', markersize=self.plot_style.marker_size,
            color=self.plot_style.marker_color, label='Inertia')

        # Plotting the cumulative explained variance

        canvas.axes.set_xlabel('Number of clusters')
        canvas.axes.set_ylabel('Inertia', color=self.plot_style.marker_color)
        canvas.axes.tick_params(axis='y', labelcolor=self.plot_style.marker_color)
        canvas.axes.set_title(f'Cluster performance: {method}')
        #canvas.axes.axvline(x=optimal_k, linestyle='--', color='m', label=f'Elbow at k={optimal_k}')

        # aspect ratio
        canvas.axes.set_box_aspect(self.plot_style.aspect_ratio)

        # Create a secondary y-axis to plot the second derivative
        canvas.axes2 = canvas.axes.twinx()
        canvas.axes2.plot(range(2, max_clusters), second_derivative, linestyle='-', linewidth=self.plot_style.line_width,
            marker=self.plot_style.marker_dict[self.plot_style.marker], markersize=self.plot_style.marker_size,
            color='r', label='3nd Derivative')

        canvas.axes2.set_ylabel('2nd Derivative', color='r')
        canvas.axes2.tick_params(axis='y', labelcolor='r')

        # aspect ratio
        canvas.axes2.set_box_aspect(self.plot_style.aspect_ratio)

        canvas.axes3 = canvas.axes.twinx()
        canvas.axes3.plot(range(1, max_clusters+1), silhouette_scores, linestyle='-', linewidth=self.plot_style.line_width,
            marker=self.plot_style.marker_dict[self.plot_style.marker], markeredgecolor='orange', markerfacecolor='none', markersize=self.plot_style.marker_size,
            color='orange', label='Silhouette Scores')

        canvas.axes3.spines['right'].set_position(('outward', 60))  # Move it outward by 60 points
        canvas.axes3.set_ylabel('Silhouette score', color='orange')
        canvas.axes3.tick_params(axis='y', labelcolor='orange')

        canvas.axes3.set_box_aspect(self.plot_style.aspect_ratio)


        #print(f"Second derivative of inertia: {second_derivative}")
        #print(f"Optimal number of clusters: {optimal_k}")

        plot_type = self.plot_style.plot_type
        plot_name = f"{plot_type}_{method}"
        plot_data = {'inertia': inertia, '2nd derivative': second_derivative}

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.app_data.sample_id,
            'plot_name': plot_name,
            'plot_type': self.plot_style.plot_type,
            'field_type':self.field_type,
            'field':  self.field,
            'figure': canvas,
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': self.app_data.cluster_dict[method],
            'view': [True,False],
            'position': [],
            'data': plot_data
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

    def compute_clusters(self, max_clusters=None):
        """Computes cluster results
        
        Cluster properties are defined in the ``MainWindow.toolBox.ClusterPage``."""
        #print('\n===compute_clusters===')
        if self.app_data.sample_id == '':
            return

        df_filtered, isotopes = self.data[self.app_data.sample_id].get_processed_data()
        filtered_array = df_filtered.values
        array = filtered_array[self.data[self.app_data.sample_id].mask]

        # get clustering options
        if max_clusters is None:
            n_clusters = [self.spinBoxNClusters.value()]
        else:
            n_clusters = np.arange(1,max_clusters+1).astype(int)
            cluster_results = []
            silhouette_scores = []

        seed = int(self.lineEditSeed.text())
        method = self.comboBoxClusterMethod.currentText()
        exponent = float(self.horizontalSliderClusterExponent.value()) / 10

        if exponent == 1:
            exponent = 1.0001
        distance_type = self.comboBoxClusterDistance.currentText()

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


        # set all masked data to cluster id -1
        if max_clusters is None:
            self.data[self.app_data.sample_id].processed_data[method] = 99

            # Create labels array filled with -1
            #groups = np.full(filtered_array.shape[0], -1, dtype=int)
            self.toolButtonGroupMask.blockSignals(True)
            self.toolButtonGroupMaskInverse.blockSignals(True)
            self.toolButtonGroupMask.setChecked(False)
            self.toolButtonGroupMaskInverse.setChecked(False)
            self.toolButtonGroupMask.blockSignals(False)
            self.toolButtonGroupMaskInverse.blockSignals(False)

        self.statusbar.showMessage('Computing clusters...')
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
                        self.data[self.app_data.sample_id].add_columns('cluster', method, model.predict(array), self.data[self.app_data.sample_id].mask)
                    else:
                        kmeans.fit(array)
                        cluster_results.append(kmeans.inertia_)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, kmeans.labels_, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")

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
                            #self.data[self.app_data.sample_id]['computed_data']['cluster score'].loc[:,str(n)] = pd.NA
                            self.data[self.app_data.sample_id].add_columns('cluster score', 'cluster' + str(n), u[n-1,:], self.data[self.app_data.sample_id].mask)

                        #add cluster results to self.data
                        self.data[self.app_data.sample_id].add_columns('cluster', method, labels, self.data[self.app_data.sample_id].mask)
                    else:
                        # weighted sum of squared errors (WSSE)
                        wsse = np.sum((u ** exponent) * (dist ** 2))
                        cluster_results.append(wsse)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, labels, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")
            
        if max_clusters is None:
            # make sure the column is all integer values
            self.data[self.app_data.sample_id].processed_data[method] = self.data[self.app_data.sample_id].processed_data[method].astype(int)  

            # update cluster table in style menu
            self.group_changed()

            self.statusbar.showMessage('Clustering successful')

            self.update_all_field_comboboxes()
            self.update_blockly_field_types()
            self.update_cluster_flag = False
        else:
            return cluster_results, silhouette_scores

    def plot_clusters(self):
        """Plot maps associated with clustering

        Will produce plots of Clusters or Cluster Scores and computes clusters if necesseary.
        """        
        print('plot_clusters')
        if self.app_data.sample_id == '':
            return

        method = self.comboBoxClusterMethod.currentText()
        if self.update_cluster_flag or \
                self.data[self.app_data.sample_id].processed_data[method].empty or \
                (method not in list(self.data[self.app_data.sample_id].processed_data.columns)):
            self.compute_clusters()


        self.app_data.cluster_dict['active method'] = method

        plot_type = self.plot_style.plot_type

        match plot_type:
            case 'cluster':
                self.comboBoxColorField.setCurrentText(method)
                plot_name = f"{plot_type}_{method}_map"
                canvas, plot_data = self.plot_cluster_map()
            case 'cluster score':
                plot_name = f"{plot_type}_{method}_{self.field}_score_map"
                canvas, plot_data = self.plot_score_map()
            case _:
                print(f'Unknown PCA plot type: {plot_type}')
                return

        self.plot_style.update_figure_font(canvas, self.plot_style.font)

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.app_data.sample_id,
            'plot_name': plot_name,
            'plot_type': self.plot_style.plot_type,
            'field_type':self.field_type,
            'field':  self.field,
            'figure': canvas,
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': self.app_data.cluster_dict[method],
            'view': [True,False],
            'position': [],
            'data': plot_data
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

class DimensionalReduction():
    def __init__(self, parent):
        self.parent = parent

        parent.comboBoxDimRedMethod.clear()
        parent.comboBoxDimRedMethod.addItems(['PCA: Principal component analysis', 'MDS: Multidimensional scaling', 'LDA: Linear discriminant analysis', 'FA: Factor analysis'])
        parent.comboBoxDimRedMethod.activated.connect()

        self.pca_results = []
        parent.spinBoxPCX.valueChanged.connect(self.plot_pca)
        parent.spinBoxPCY.valueChanged.connect(self.plot_pca)

    def compute_pca(self, update_ui=True):
        #print('compute_pca')
        self.pca_results = {}

        data = self.parent.data[self.parent.app_data.sample_id]

        df_filtered, analytes = data.get_processed_data()

        # Preprocess the data
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_filtered)

        # Perform PCA
        self.pca_results = PCA(n_components=min(len(df_filtered.columns), len(df_filtered)))  # Adjust n_components as needed

        # compute pca scores
        pca_scores = pd.DataFrame(self.pca_results.fit_transform(df_scaled), columns=[f'PC{i+1}' for i in range(self.pca_results.n_components_)])
        self.plot_style.clim = [np.amin(self.pca_results.components_), np.amax(self.pca_results.components_)]

        # Add PCA scores to DataFrame for easier plotting
        data.add_columns('pca score',pca_scores.columns,pca_scores.values,data.mask)

        if update_ui:
                #update min and max of PCA spinboxes
            if self.pca_results.n_components_ > 0:
                self.spinBoxPCX.setMinimum(1)
                self.spinBoxPCY.setMinimum(1)
                self.spinBoxPCX.setMaximum(self.pca_results.n_components_+1)
                self.spinBoxPCY.setMaximum(self.pca_results.n_components_+1)
                if self.spinBoxPCY.value() == 1:
                    self.spinBoxPCY.setValue(int(2))

            self.update_all_field_comboboxes()
        else:
            self.update_blockly_field_types()

        self.update_pca_flag = False