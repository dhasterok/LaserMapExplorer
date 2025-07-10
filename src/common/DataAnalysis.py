from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon )
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
#from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from src.common.Logger import log, auto_log_methods

@auto_log_methods(logger_key="Analysis")
class Clustering():
    def __init__(self, parent):
        self.logger_key = "Clustering"
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



@auto_log_methods(logger_key="Analysis")
class ClusteringUI(Clustering):
    """
    Manages the clustering interface and links app_data updates to the MainWindow UI.

    The `ClusteringUI` class connects UI elements in the application's "Clustering" tab
    to corresponding app_data-handling logic. It listens for changes in style, and applies those
    settings to the active dataset.

    The class also ensures that the UI is updated dynamically when the underlying data
    model changes, and that scheduled plot updates are triggered when required.
    """
    def __init__(self, parent):
        super().__init__(self)

        self.ui = parent
        self.schedule_update = self.ui.plot_style.schedule_update

        # Clustering ui widgets
        self.ui.spinBoxNClusters.valueChanged.connect(lambda: setattr(self.ui.app_data, "num_clusters",self.ui.spinBoxNClusters.value()))
        self.ui.comboBoxClusterDistance.clear()
        self.ui.comboBoxClusterDistance.addItems(self.distance_metrics)
        self.ui.app_data.cluster_distance = self.distance_metrics[0] 

        self.ui.comboBoxClusterDistance.activated.connect(lambda: setattr(self.ui.app_data, "cluster_distance",self.ui.comboBoxClusterDistance.currentText()))
        # cluster exponent
        self.ui.horizontalSliderClusterExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        self.ui.horizontalSliderClusterExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        self.ui.horizontalSliderClusterExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        self.ui.horizontalSliderClusterExponent.setTickInterval(1)
        self.ui.horizontalSliderClusterExponent.valueChanged.connect(lambda value: self.ui.labelClusterExponent.setText(str(value/10)))
        self.ui.horizontalSliderClusterExponent.sliderReleased.connect(lambda: setattr(self.ui.app_data, "cluster_exponent",float(self.ui.horizontalSliderClusterExponent.value()/10)))

        # starting seed
        self.ui.lineEditSeed.setValidator(QIntValidator(0,1000000000))
        self.ui.lineEditSeed.editingFinished.connect(lambda: setattr(self.ui.app_data, "cluster_seed",int(self.ui.lineEditSeed.text())))
        self.ui.toolButtonRandomSeed.clicked.connect(self.ui.app_data.generate_random_seed)

        # cluster method
        self.ui.comboBoxClusterMethod.addItems(self.cluster_methods)
        self.ui.app_data.cluster_method = self.cluster_methods[0]
        self.ui.toggle_cluster_parameters(self.cluster_methods[0]) 
        self.ui.comboBoxClusterMethod.activated.connect(lambda: setattr(self.ui.app_data, "cluster_method",self.ui.comboBoxClusterMethod.currentText()))

        self.connect_observer()
        self.connect_logger()

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("cluster_method", self.update_cluster_method_combobox)
        self.ui.app_data.add_observer("max_clusters", self.update_max_clusters_spinbox)
        self.ui.app_data.add_observer("num_clusters", self.update_num_clusters_spinbox)
        self.ui.app_data.add_observer("cluster_seed", self.update_cluster_seed_lineedit)
        self.ui.app_data.add_observer("cluster_exponent", self.update_cluster_exponent_slider)
        self.ui.app_data.add_observer("cluster_distance", self.update_cluster_distance_combobox)
        self.ui.app_data.add_observer("dim_red_precondition", self.update_dim_red_precondition_checkbox)
        self.ui.app_data.add_observer("num_basis_for_precondition", self.update_num_basis_for_precondition_spinbox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxClusterMethod.activated.connect(lambda: log(f"comboBoxClusterMethod value=[{self.ui.comboBoxClusterMethod.currentText()}]", prefix="UI"))
        self.ui.spinBoxNClusters.valueChanged.connect(lambda: log(f"spinBoxNClusters value=[{self.ui.spinBoxNClusters.value()}]", prefix="UI"))
        self.ui.horizontalSliderClusterExponent.valueChanged.connect(lambda: log(f"horizontalSliderClusterExponent value=[{self.ui.horizontalSliderClusterExponent.value()}]", prefix="UI"))
        self.ui.comboBoxClusterDistance.activated.connect(lambda: log(f"comboBoxClusterDistance value=[{self.ui.comboBoxClusterDistance.currentText()}]", prefix="UI"))
        self.ui.lineEditSeed.editingFinished.connect(lambda: log(f"lineEditSeed value=[{self.ui.lineEditSeed.value}]", prefix="UI"))
        self.ui.toolButtonRandomSeed.clicked.connect(lambda: log("toolButtonRandomSeed", prefix="UI"))
        self.ui.checkBoxWithPCA.checkStateChanged.connect(lambda: log(f"checkBoxWithPCA value=[{self.ui.checkBoxWithPCA.isChecked()}]", prefix="UI"))
        self.ui.spinBoxPCANumBasis.valueChanged.connect(lambda: log(f"spinBoxPCANumBasis value=[{self.ui.spinBoxPCANumBasis.value()}]", prefix="UI"))


    def update_cluster_method_combobox(self, new_cluster_method):
        self.ui.comboBoxClusterMethod.setCurrentText(new_cluster_method)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.toggle_cluster_parameters(new_cluster_method)
            self.ui.plot_style.schedule_update()

    def update_max_clusters_spinbox(self, new_max_clusters):
        self.ui.spinBoxClusterMax.setValue(int(new_max_clusters))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_num_clusters_spinbox(self, new_num_clusters):
        self.ui.spinBoxNClusters.setValue(int(new_num_clusters))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_cluster_seed_lineedit(self, new_cluster_seed):
        self.ui.lineEditSeed.setText(str(new_cluster_seed))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_cluster_exponent_slider(self, new_cluster_exponent):
        self.ui.horizontalSliderClusterExponent.setValue(int(new_cluster_exponent*10))
        self.ui.labelClusterExponent.setText(str(new_cluster_exponent))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_cluster_distance_combobox(self, new_cluster_distance):
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_dim_red_precondition_checkbox(self, new_pca_precondition):
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()

    def update_num_basis_for_precondition_spinbox(self, new_value):
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.schedule_update()


@auto_log_methods(logger_key="Analysis")
class DimensionalReduction():
    def __init__(self, parent):
        self.parent = parent

        self.dim_red_methods = ['PCA: Principal component analysis', 'MDS: Multidimensional scaling', 'LDA: Linear discriminant analysis', 'FA: Factor analysis']

    def compute_dim_red(self, data, app_data):
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
            app_data.dim_red_x_max = pca_results.n_components_+1
            app_data.dim_red_y_max = pca_results.n_components_+1
            if app_data.dim_red_y == 1:
                app_data.dim_red_y = int(2)


@auto_log_methods(logger_key="Analysis")
class DimensionalReductionUI(DimensionalReduction):
    def __init__(self, parent):
        super().__init__(self)

        self.ui = parent

        # Dimensional reduction ui widgets
        self.ui.comboBoxDimRedTechnique.clear()
        self.ui.comboBoxDimRedTechnique.addItems(self.dim_red_methods)
        self.ui.app_data.dim_red_method = self.dim_red_methods[0]
        self.ui.spinBoxPCX.valueChanged.connect(lambda: setattr(self.ui.app_data, "dim_red_x",self.ui.spinBoxPCX.value()))
        self.ui.spinBoxPCY.valueChanged.connect(lambda: setattr(self.ui.app_data, "dim_red_y",self.ui.spinBoxPCY.value()))

        self.ui.comboBoxDimRedTechnique.activated.connect(lambda: log(f"comboBoxDimRedTechnique value=[{self.ui.comboBoxDimRedTechnique.currentText()}]", prefix="UI"))
        self.ui.spinBoxPCX.valueChanged.connect(lambda: log(f"spinBoxPCX value=[{self.ui.spinBoxPCX.value()}]", prefix="UI"))
        self.ui.spinBoxPCY.valueChanged.connect(lambda: log(f"spinBoxPCY value=[{self.ui.spinBoxPCY.value()}]", prefix="UI"))

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        pass

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("dim_red_method", self.update_dim_red_method_combobox)
        self.ui.app_data.add_observer("dim_red_x", self.update_dim_red_x_spinbox)
        self.ui.app_data.add_observer("dim_red_y", self.update_dim_red_y_spinbox)
        self.ui.app_data.add_observer("dim_red_x_max", self.update_dim_red_x_max_spinbox)
        self.ui.app_data.add_observer("dim_red_y_max", self.update_dim_red_y_max_spinbox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxNDimRefMaterial.activated.connect(lambda: log(f"comboBoxNDimRefMaterial value=[{self.ui.comboBoxNDimRefMaterial.currentText()}]", prefix="UI"))
        self.ui.comboBoxNDimAnalyte.activated.connect(lambda: log(f"comboBoxNDimAnalyte value=[{self.ui.comboBoxNDimAnalyte.currentText()}]", prefix="UI"))
        self.ui.toolButtonNDimAnalyteAdd.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.comboBoxNDimAnalyteSet.activated.connect(lambda: log(f"comboBoxNDimAnalyteSet value=[{self.ui.comboBoxNDimAnalyteSet.currentText()}]", prefix="UI"))
        self.ui.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.comboBoxNDimQuantiles.activated.connect(lambda: log(f"comboBoxNDimQuantiles value=[{self.ui.comboBoxNDimQuantiles.currentText()}]", prefix="UI"))
        self.ui.toolButtonNDimSelectAll.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.toolButtonNDimUp.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.toolButtonNDimDown.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.toolButtonNDimSaveList.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))
        self.ui.toolButtonNDimRemove.clicked.connect(lambda: log("toolButtonNDimAnalyteAdd", prefix="UI"))

    def update_dim_red_method_combobox(self, new_method):
        self.ui.comboBoxNoiseReductionMethod.setCurrentText(new_method)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_x_spinbox(self, new_value):
        self.ui.spinBoxPCX.setValue(int(new_value))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_y_spinbox(self, new_value):
        self.ui.spinBoxPCY.setValue(int(new_value))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_x_max_spinbox(self, new_value):
        self.ui.spinBoxPCX.setMaximum(int(new_value))

    def update_dim_red_y_max_spinbox(self, new_value):
        self.ui.spinBoxPCY.setMaximum(int(new_value))