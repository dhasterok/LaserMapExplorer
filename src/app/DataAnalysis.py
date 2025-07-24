from PyQt6.QtCore import ( Qt, QSize, QRect )
from PyQt6.QtWidgets import (
    QScrollArea, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QToolButton, QWidget,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QSlider, QSpacerItem, QComboBox,
    QCheckBox, QSizePolicy
)
from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon, )
from src.common.CustomWidgets import ( CustomLineEdit, CustomSlider )
from src.app.UITheme import default_font
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
    def __init__(self):
        self.logger_key = "Analysis"

        self._distance_metrics = ['euclidean', 'manhattan', 'mahalanobis', 'cosine']
        self._cluster_methods = ['k-means', 'fuzzy c-means']

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
class ClusterPage(QWidget, Clustering):
    """
    Manages the clustering interface and links app_data updates to the MainWindow UI.

    The `ClusteringUI` class connects UI elements in the application's "Clustering" tab
    to corresponding app_data-handling logic. It listens for changes in style, and applies those
    settings to the active dataset.

    The class also ensures that the UI is updated dynamically when the underlying data
    model changes, and that scheduled plot updates are triggered when required.

    Methods
    -------
    """
    def __init__(self, parent=None, page_index=None):
        super().__init__()

        if parent is None:
            return

        self.ui = parent
        self.logger_key = "Analysis"
        self.update_cluster_flag = True

        self.setupUI(page_index)
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self, page_index):
        self.setGeometry(QRect(0, 0, 300, 506))
        self.setObjectName("ClusteringPage")

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setObjectName("verticalLayout_83")

        self.scrollAreaClustering = QScrollArea(parent=self)
        self.scrollAreaClustering.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollAreaClustering.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollAreaClustering.setWidgetResizable(True)
        self.scrollAreaClustering.setObjectName("scrollAreaClustering")

        self.scrollAreaWidgetContentsClustering = QWidget()
        self.scrollAreaWidgetContentsClustering.setGeometry(QRect(0, 0, 300, 506))
        self.scrollAreaWidgetContentsClustering.setObjectName("scrollAreaWidgetContentsClustering")
        scroll_layout = QVBoxLayout(self.scrollAreaWidgetContentsClustering)
        scroll_layout.setContentsMargins(6, 6, 6, 6)
        scroll_layout.setObjectName("scroll_layout")


        self.groupBoxClustering = QGroupBox(parent=self.scrollAreaWidgetContentsClustering)
        self.groupBoxClustering.setTitle("")
        self.groupBoxClustering.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.groupBoxClustering.setObjectName("groupBoxClustering")

        self.cluster_form_layout = QFormLayout(self.groupBoxClustering)
        self.cluster_form_layout.setObjectName("cluster_form_layout")

        self.comboBoxClusterMethod = QComboBox(parent=self.groupBoxClustering)
        self.comboBoxClusterMethod.setMaximumSize(QSize(150, 16777215))
        self.comboBoxClusterMethod.setFont(default_font())
        self.comboBoxClusterMethod.setObjectName("comboBoxClusterMethod")
        self.cluster_form_layout.addRow("Method", self.comboBoxClusterMethod)

        self.spinBoxClusterMax = QSpinBox(parent=self.groupBoxClustering)
        self.spinBoxClusterMax.setMaximumSize(QSize(150, 16777215))
        self.spinBoxClusterMax.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spinBoxClusterMax.setMinimum(3)
        self.spinBoxClusterMax.setMaximum(98)
        self.spinBoxClusterMax.setProperty("value", 10)
        self.spinBoxClusterMax.setObjectName("spinBoxClusterMax")
        self.cluster_form_layout.addRow("Max. clusters", self.spinBoxClusterMax)

        self.spinBoxNClusters = QSpinBox(parent=self.groupBoxClustering)
        self.spinBoxNClusters.setMaximumSize(QSize(150, 16777215))
        self.spinBoxNClusters.setFont(default_font())
        self.spinBoxNClusters.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spinBoxNClusters.setKeyboardTracking(False)
        self.spinBoxNClusters.setMinimum(1)
        self.spinBoxNClusters.setMaximum(98)
        self.spinBoxNClusters.setProperty("value", 5)
        self.spinBoxNClusters.setObjectName("spinBoxNClusters")
        self.cluster_form_layout.addRow("No. clusters", self.spinBoxNClusters)

        self.sliderClusterExponent = CustomSlider(parent=self.groupBoxClustering, orientation="horizontal", label_position="low")
        self.sliderClusterExponent.label.setFont(default_font())
        self.sliderClusterExponent.slider.setFont(default_font())
        self.sliderClusterExponent.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.sliderClusterExponent.min_value = 1.0
        self.sliderClusterExponent.max_value = 3.0
        self.sliderClusterExponent.step = 0.1 
        self.sliderClusterExponent.setTickInterval(1)
        self.sliderClusterExponent.setObjectName("sliderClusterExponent")
        self.cluster_form_layout.addRow("Exponent", self.sliderClusterExponent)
        self.cluster_form_layout.labelForField(self.sliderClusterExponent).setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        self.comboBoxClusterDistance = QComboBox(parent=self.groupBoxClustering)
        self.comboBoxClusterDistance.setMaximumSize(QSize(150, 16777215))
        self.comboBoxClusterDistance.setFont(default_font())
        self.comboBoxClusterDistance.setObjectName("comboBoxClusterDistance")
        self.cluster_form_layout.addRow("Distance", self.comboBoxClusterDistance)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.toolButtonRandomSeed = QToolButton(parent=self.groupBoxClustering)
        self.toolButtonRandomSeed.setMinimumSize(QSize(32, 32))
        self.toolButtonRandomSeed.setMaximumSize(QSize(32, 32))
        self.toolButtonRandomSeed.setFont(default_font())
        seed_icon = QIcon(":/resources/icons/icon-randomize-64.svg")
        self.toolButtonRandomSeed.setIcon(seed_icon)
        self.toolButtonRandomSeed.setIconSize(QSize(24, 24))
        self.toolButtonRandomSeed.setObjectName("toolButtonRandomSeed")
        self.horizontalLayout.addWidget(self.toolButtonRandomSeed)

        self.lineEditSeed = CustomLineEdit(parent=self.groupBoxClustering)
        self.lineEditSeed.setMaximumSize(QSize(150, 16777215))
        self.lineEditSeed.setFont(default_font())
        self.lineEditSeed.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditSeed.setObjectName("lineEditSeed")
        self.lineEditSeed.setValidator(QIntValidator(0,1000000000))
        self.horizontalLayout.addWidget(self.lineEditSeed)
        self.cluster_form_layout.addRow("Seed", self.horizontalLayout)

        self.checkBoxWithPCA = QCheckBox(parent=self.groupBoxClustering)
        self.checkBoxWithPCA.setFont(default_font())
        self.checkBoxWithPCA.setText("")
        self.checkBoxWithPCA.setObjectName("checkBoxWithPCA")
        self.cluster_form_layout.addRow("PCA", self.checkBoxWithPCA)

        self.spinBoxPCANumBasis = QSpinBox(parent=self.groupBoxClustering)
        self.spinBoxPCANumBasis.setMaximumSize(QSize(150, 16777215))
        self.spinBoxPCANumBasis.setFont(default_font())
        self.spinBoxPCANumBasis.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spinBoxPCANumBasis.setKeyboardTracking(False)
        self.spinBoxPCANumBasis.setObjectName("spinBoxPCANumBasis")
        self.cluster_form_layout.addRow("No. basis", self.spinBoxPCANumBasis)

        scroll_layout.addWidget(self.groupBoxClustering)
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        scroll_layout.addItem(spacer)
        self.scrollAreaClustering.setWidget(self.scrollAreaWidgetContentsClustering)

        page_layout.addWidget(self.scrollAreaClustering)

        cluster_icon = QIcon(":/resources/icons/icon-cluster-64.svg")
        if not page_index:
            self.ui.toolBox.addItem(self, cluster_icon, "Clustering")
        else:
            self.ui.toolBox.insertItem(page_index, self, cluster_icon, "Clustering")

    def connect_widgets(self):
        """Connect clustering widgets to UI."""
        # Clustering ui widgets
        self.spinBoxClusterMax.valueChanged.connect(lambda _: self.update_max_clusters())
        self.spinBoxNClusters.valueChanged.connect(lambda _: self.update_num_clusters())

        self.comboBoxClusterDistance.clear()
        self.comboBoxClusterDistance.addItems(self._distance_metrics)
        self.ui.app_data.cluster_distance = self._distance_metrics[0]
        self.comboBoxClusterDistance.activated.connect(lambda _: self.update_cluster_distance())

        # cluster exponent
        self.sliderClusterExponent.sliderReleased.connect(lambda _: self.update_cluster_exponent())

        # starting seed
        self.lineEditSeed.editingFinished.connect(lambda _: self.update_cluster_seed())
        self.toolButtonRandomSeed.clicked.connect(lambda _: self.ui.app_data.generate_random_seed())

        # cluster method
        self.comboBoxClusterMethod.clear()
        self.comboBoxClusterMethod.addItems(self.ui.app_data.cluster_method_options)
        self.ui.app_data.cluster_method = self.ui.app_data.cluster_method_options[0]
        self.comboBoxClusterMethod.activated.connect(lambda _: self.update_cluster_method())

        self.checkBoxWithPCA.setChecked(self.ui.app_data.dim_red_precondition)
        self.checkBoxWithPCA.setToolTip("Use dimensional reduction scores for clustering.")
        self.checkBoxWithPCA.stateChanged.connect(lambda _: self.update_dim_red_precondition())

        self.spinBoxPCANumBasis.setMinimum(1)
        self.spinBoxPCANumBasis.setMaximum(1)
        self.spinBoxPCANumBasis.setValue(self.ui.app_data.num_basis_for_precondition)
        self.spinBoxPCANumBasis.valueChanged.connect(lambda _: self.update_num_basis_for_precondition())

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("cluster_method", self.update_cluster_method)
        self.ui.app_data.add_observer("max_clusters", self.update_max_clusters)
        self.ui.app_data.add_observer("num_clusters", self.update_num_clusters)
        self.ui.app_data.add_observer("cluster_seed", self.update_cluster_seed)
        self.ui.app_data.add_observer("cluster_exponent", self.update_cluster_exponent)
        self.ui.app_data.add_observer("cluster_distance", self.update_cluster_distance)
        self.ui.app_data.add_observer("dim_red_precondition", self.update_dim_red_precondition)
        self.ui.app_data.add_observer("num_basis_for_precondition", self.update_num_basis_for_precondition)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxClusterMethod.activated.connect(lambda: log(f"comboBoxClusterMethod value=[{self.comboBoxClusterMethod.currentText()}]", prefix="UI"))
        self.spinBoxNClusters.valueChanged.connect(lambda: log(f"spinBoxNClusters value=[{self.spinBoxNClusters.value()}]", prefix="UI"))
        self.sliderClusterExponent.valueChanged.connect(lambda: log(f"horizontalSliderClusterExponent value=[{self.sliderClusterExponent.value()}]", prefix="UI"))
        self.comboBoxClusterDistance.activated.connect(lambda: log(f"comboBoxClusterDistance value=[{self.comboBoxClusterDistance.currentText()}]", prefix="UI"))
        self.lineEditSeed.editingFinished.connect(lambda: log(f"lineEditSeed value=[{self.lineEditSeed.value}]", prefix="UI"))
        self.toolButtonRandomSeed.clicked.connect(lambda: log("toolButtonRandomSeed", prefix="UI"))
        self.checkBoxWithPCA.checkStateChanged.connect(lambda: log(f"checkBoxWithPCA value=[{self.checkBoxWithPCA.isChecked()}]", prefix="UI"))
        self.spinBoxPCANumBasis.valueChanged.connect(lambda: log(f"spinBoxPCANumBasis value=[{self.spinBoxPCANumBasis.value()}]", prefix="UI"))

    def toggle_cluster_widgets(self):
        """Toggle visibility of cluster widgets based on the current clustering method.
        
        This method updates the visibility of various widgets in the clustering tab based on the current plot type and clustering method.
        It ensures that the appropriate widgets are shown or hidden based on the selected clustering method and plot type.
        It also enables or disables widgets based on the current clustering method and whether PCA is used for clustering.
        """
        # toggle visibility of widgets based on the current plot type
        match self.ui.plot_style.plot_type:
            case 'cluster map' | 'cluster score map':
                self.cluster_form_layout.labelForField(self.spinBoxClusterMax).hide()
                self.spinBoxClusterMax.hide()
                self.cluster_form_layout.labelForField(self.spinBoxNClusters).hide()
                self.spinBoxNClusters.show()
            case 'cluster performance':
                self.cluster_form_layout.labelForField(self.spinBoxClusterMax).show()
                self.spinBoxClusterMax.show()
                self.cluster_form_layout.labelForField(self.spinBoxNClusters).show()
                self.spinBoxNClusters.hide()

        # enable/disable widgets based on the current clustering method
        match self.ui.app_data.cluster_method:
            case 'k-means':
                self.spinBoxNClusters.setEnabled(True)
                self.spinBoxClusterMax.setEnabled(True)
                self.comboBoxClusterDistance.setEnabled(True)
                self.sliderClusterExponent.setEnabled(False)
            case 'fuzzy c-means':
                self.spinBoxNClusters.setEnabled(True)
                self.spinBoxClusterMax.setEnabled(True)
                self.comboBoxClusterDistance.setEnabled(False)
                self.sliderClusterExponent.setEnabled(True)
            case _:
                ValueError(f"Unknown clustering method {self.ui.app_data.cluster_method}")
        
        if 'PCA score' in self.ui.app_data.field_dict:
            self.checkBoxWithPCA.setEnabled(True)
            #self.labelClusterWithPCA.setEnabled(True)
        else:
            self.checkBoxWithPCA.setEnabled(False)
            #self.labelClusterWithPCA.setEnabled(False)

        # enable/disable widgets based on the current clustering method
        # self.labelNClusters.setEnabled(self.spinBoxNClusters.isEnabled())
        # self.labelClusterMax.setEnabled(self.spinBoxClusterMax.isEnabled())
        # self.labelClusterDistance.setEnabled(self.comboBoxClusterDistance.isEnabled())
        # self.labelClusterExponent.setEnabled(self.sliderClusterExponent.isEnabled())
        # self.labelExponent.setEnabled(self.sliderClusterExponent.isEnabled())

        # if PCA is not used for clustering, disable the PCA widgets
        if self.checkBoxWithPCA.isChecked() and self.checkBoxWithPCA.isEnabled():
            self.spinBoxPCANumBasis.setMaximum(self.ui.data[self.ui.app_data.sample_id].processed_data.get_attribute('PCA score').shape[1])
            self.spinBoxPCANumBasis.setEnabled(True)
            #self.labelPCANumBasis.setEnabled(True)
        else:
            self.spinBoxPCANumBasis.setEnabled(False)
            #self.labelPCANumBasis.setEnabled(False)


    def update_cluster_method(self, new_method=None):
        """Updates unsupervised clustering method.

        This method updates the clustering method used in the application. If a new method is provided,
        it sets the current text of the combo box to that method. If no new method is provided,
        it retrieves the current text from the combo box and updates the application data accordingly.

        Parameters
        ----------
        new_method : str or None, optional
            New clustering method.
        """
        if not new_method:
            self.ui.app_data.cluster_method = self.comboBoxClusterMethod.currentText()
        else:
            self.comboBoxClusterMethod.setCurrentText(new_method)

        self.toggle_cluster_widgets()

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.toggle_cluster_widgets()
            self.ui.plot_style.schedule_update()

    def update_max_clusters(self, max_clusters=None):
        """Update the maximum number of clusters for computing cluster performance plots.

        This method updates the maximum number of clusters used in clustering analysis. If a new maximum number of clusters is provided,
        it sets the spin box value to that number. If no new maximum number is provided,
        it retrieves the current value from the spin box and updates the application data accordingly.

        Parameters
        ----------
        max_clusters : int or None, optional
            The maximum number of clusters that will be used to produce a cluster performance plot.
        """
        if not max_clusters:
            self.ui.app_data.max_clusters = self.spinBoxClusterMax.value()
        else:
            self.spinBoxClusterMax.setValue(int(max_clusters))
            if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
                self.ui.plot_style.schedule_update()

    def update_num_clusters(self, num_clusters=None):
        """Update the number of clusters.
        
        This method updates the number of clusters used in clustering analysis. If a new number of clusters is provided,
        it sets the spin box value to that number. If no new number is provided, it retrieves the current value from the spin box
        and updates the application data accordingly.

        Parameters
        ----------
        num_clusters : int or None, optional
            The number of clusters for clustering analysis.
        """
        if not num_clusters:
            self.ui.app_data.num_clusters = self.spinBoxNClusters.value()
        else:
            self.spinBoxNClusters.setValue(int(num_clusters))

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def update_cluster_seed(self, new_seed=None):
        """Change the random seed for clustering.

        The seed for clustering may have an impact on the results, though generally there are
        few variations in the results.  To ensure that the results are meaningful you may wish
        to try a few random seeds.  However, fixing the seed ensures that the result can be
        replicated and the numbers assigned to each cluster are fixed.

        Parameters
        ----------
        new_seed : int or None, optional
            The random seed for clustering. If not provided, the current value of the line edit is used.
            If provided, the line edit is updated with the new seed value.
        """
        if new_seed is None:
            self.ui.app_data.cluster_seed = self.lineEditSeed.value
        else:
            if new_seed == int(self.ui.lineEditSeed.text()):
                return

            self.lineEditSeed.blockSignals(True)
            self.lineEditSeed.setText(str(new_seed))
            self.lineEditSeed.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def update_cluster_exponent(self, new_value=None):
        if new_value is None:
            self.ui.app_data.cluster_exponent = self.sliderClusterExponent.value()
        else:
            if new_value == self.sliderClusterExponent.value():
                return
        
            # this may cause a problem with the internal changing of the exponent label.
            self.sliderClusterExponent.blockSignals(True)
            self.sliderClusterExponent.setValue(new_value)
            self.sliderClusterExponent.blockSignals(False)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def update_cluster_distance(self, new_distance=None):
        """ Update the distance metric used for clustering.

        This method updates the distance metric used for clustering. If a new distance is provided,
        it sets the current text of the combo box to that distance. If no new distance is provided,
        it retrieves the current text from the combo box and updates the application data accordingly.

        Parameters
        ----------
        new_distance : str or None, optional
            The new distance metric used for clustering. If not provided, the current text of the combo box is used.
        """
        if not new_distance:
            self.ui.app_data.cluster_distance = self.comboBoxClusterDistance.currentText()
        else:
            self.comboBoxClusterDistance.setCurrentText(new_distance)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_precondition(self, new_value=None):
        """Update the preconditioning for PCA in clustering.

        This method updates the preconditioning for PCA in clustering. If a new value is provided,
        it sets the checkbox state to that value. If no new value is provided,
        it retrieves the current state of the checkbox and updates the application data accordingly.

        Parameters
        ----------
        new_value : bool or None, optional
            The new state of the checkbox for PCA preconditioning. If not provided, the current state
            of the checkbox is used. If provided, the checkbox state is updated with the new value
        """
        if new_value is None:
            self.ui.app_data.dim_red_precondition = self.checkBoxWithPCA.isChecked()
        else:
            self.checkBoxWithPCA.setChecked(new_value)

        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def update_num_basis_for_precondition(self, new_value=None):
        """Update the number of basis vectors for PCA preconditioning.

        This method updates the number of basis vectors used for PCA preconditioning in clustering.
        If a new value is provided, it sets the spin box value to that number. If no new value is provided,
        it retrieves the current value from the spin box and updates the application data accordingly.

        Parameters
        ----------
        new_value : int or None, optional
            The number of basis vectors for PCA preconditioning. If not provided, the current value of the spin box is used.
            If provided, the spin box is updated with the new value.
        """
        if not new_value:
            self.ui.app_data.num_basis_for_precondition = self.spinBoxPCANumBasis.value()
        else:
            self.spinBoxPCANumBasis.setValue(int(new_value))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['cluster']:
            self.ui.plot_style.schedule_update()

    def compute_clusters_update_groups(self):
        """
        Computes clusters and updates cluster groups.

        This method:
        1. Checks if clustering needs to be updated based on the application data flags.
        2. Invokes the clustering computation if necessary.
        3. Applies updated cluster colors and refreshes the cluster tab in the Mask Dock.
        """
        data = self.ui.data[self.ui.app_data.sample_id]
        method = self.ui.app_data.cluster_method
        if self.ui.app_data.update_cluster_flag or \
                data.processed_data[method].empty or \
                (method not in list(data.processed_data.columns)):
            # compute clusters
            self.ui.statusbar.showMessage('Computing clusters')
            self.compute_clusters(data, self.ui.app_data, max_clusters = None)
            # update cluster colors
            self.ui.app_data.cluster_group_changed(data, self.ui.plot_style)
            # enable cluster tab actions and update group table
            if hasattr(self, 'mask_dock'):
                self.ui.mask_dock.cluster_tab.toggle_cluster_actions()
                self.ui.mask_dock.cluster_tab.update_table_widget()

            self.ui.statusbar.showMessage('Clustering successful')


@auto_log_methods(logger_key="Analysis")
class DimensionalReduction():
    def __init__(self):
        self.logger_key = "Analysis"

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
class DimensionalReductionPage(QWidget, DimensionalReduction):
    def __init__(self, parent=None, page_index=None):
        super().__init__()

        if parent is None:
            return

        self.ui = parent
        self.logger_key = "Analysis"

        self.setupUI(page_index)
        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def setupUI(self, page_index):
        self.setGeometry(QRect(0, 0, 300, 506))
        self.setObjectName("MultidimensionalPage")

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        self.scrollAreaMultiDim = QScrollArea(parent=self)
        self.scrollAreaMultiDim.setFont(default_font())
        self.scrollAreaMultiDim.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollAreaMultiDim.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollAreaMultiDim.setWidgetResizable(True)
        self.scrollAreaMultiDim.setObjectName("scrollAreaMultiDim")

        self.scrollAreaWidgetContentsMultiDim = QWidget()
        self.scrollAreaWidgetContentsMultiDim.setGeometry(QRect(0, 0, 300, 506))
        self.scrollAreaWidgetContentsMultiDim.setObjectName("scrollAreaWidgetContentsMultiDim")

        scroll_area_layout = QVBoxLayout(self.scrollAreaWidgetContentsMultiDim)
        scroll_area_layout.setContentsMargins(6, 6, 6, 6)
        scroll_area_layout.setObjectName("verticalLayout_82")
        self.groupBoxMultidim = QGroupBox(parent=self.scrollAreaWidgetContentsMultiDim)
        self.groupBoxMultidim.setTitle("")
        self.groupBoxMultidim.setObjectName("groupBoxMultidim")

        self.multidim_form_layout = QFormLayout(self.groupBoxMultidim)
        self.multidim_form_layout.setContentsMargins(3, 3, 3, 3)
        self.multidim_form_layout.setObjectName("multidim_form_layout")

        self.comboBoxDimRedTechnique = QComboBox(parent=self.groupBoxMultidim)
        self.comboBoxDimRedTechnique.setFont(default_font())
        self.comboBoxDimRedTechnique.setObjectName("comboBoxDimRedTechnique")
        self.multidim_form_layout.addRow("Method", self.comboBoxDimRedTechnique)

        self.spinBoxPCX = QSpinBox(parent=self.groupBoxMultidim)
        self.spinBoxPCX.setFont(default_font())
        self.spinBoxPCX.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spinBoxPCX.setKeyboardTracking(False)
        self.spinBoxPCX.setObjectName("spinBoxPCX")
        self.multidim_form_layout.addRow("PC X", self.spinBoxPCX)

        self.spinBoxPCY = QSpinBox(parent=self.groupBoxMultidim)
        self.spinBoxPCY.setFont(default_font())
        self.spinBoxPCY.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spinBoxPCY.setKeyboardTracking(False)
        self.spinBoxPCY.setObjectName("spinBoxPCY")
        self.multidim_form_layout.addRow("PC Y", self.spinBoxPCY)

        scroll_area_layout.addWidget(self.groupBoxMultidim)
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        scroll_area_layout.addItem(spacer)
        self.scrollAreaMultiDim.setWidget(self.scrollAreaWidgetContentsMultiDim)
        page_layout.addWidget(self.scrollAreaMultiDim)

        multidim_icon = QIcon(":/resources/icons/icon-dimensional-analysis-64.svg")
        if not page_index:
            self.ui.toolBox.addItem(self, multidim_icon, "Dimensional Reduction")
        else:
            self.ui.toolBox.insertItem(page_index, self, multidim_icon, "Dimensional Reduction")

    def connect_widgets(self):
        # Dimensional reduction ui widgets
        self.comboBoxDimRedTechnique.clear()
        self.comboBoxDimRedTechnique.addItems(self.dim_red_methods)
        self.ui.app_data.dim_red_method = self.dim_red_methods[0]

        self.spinBoxPCX.valueChanged.connect(lambda: setattr(self.ui.app_data, "dim_red_x",self.spinBoxPCX.value()))
        self.spinBoxPCY.valueChanged.connect(lambda: setattr(self.ui.app_data, "dim_red_y",self.spinBoxPCY.value()))

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.app_data.add_observer("dim_red_method", self.update_dim_red_method_combobox)
        self.ui.app_data.add_observer("dim_red_x", self.update_dim_red_x_spinbox)
        self.ui.app_data.add_observer("dim_red_y", self.update_dim_red_y_spinbox)
        self.ui.app_data.add_observer("dim_red_x_max", self.update_dim_red_x_max_spinbox)
        self.ui.app_data.add_observer("dim_red_y_max", self.update_dim_red_y_max_spinbox)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxDimRedTechnique.currentTextChanged.connect(lambda: log(f"comboBoxDimRedTechnique, value=[{self.comboBoxDimRedTechnique.currentText()}]",prefix="UI"))
        self.spinBoxPCX.valueChanged.connect(lambda: log(f"spinBoxPCX value=[{self.spinBoxPCX.value()}]", prefix="UI"))
        self.spinBoxPCY.valueChanged.connect(lambda: log(f"spinBoxPCY value=[{self.spinBoxPCY.value()}]", prefix="UI"))

    def update_dim_red_method_combobox(self, new_method):
        self.comboBoxDimRedTechnique.setCurrentText(new_method)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_x_spinbox(self, new_value):
        self.spinBoxPCX.setValue(int(new_value))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_y_spinbox(self, new_value):
        self.spinBoxPCY.setValue(int(new_value))
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['multidim']:
            self.ui.plot_style.schedule_update()

    def update_dim_red_x_max_spinbox(self, new_value):
        self.spinBoxPCX.setMaximum(int(new_value))

    def update_dim_red_y_max_spinbox(self, new_value):
        self.spinBoxPCY.setMaximum(int(new_value))