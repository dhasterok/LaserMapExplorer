from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QCheckBox,QComboBox,  QTableWidgetItem, QHBoxLayout,QVBoxLayout, QGridLayout, QFileDialog,QProgressDialog, QWidget, QTabWidget, QDialog, QLabel, QListWidgetItem
from PyQt5.Qt import QStandardItemModel,QStandardItem
from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen, AxisItem
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.GraphicsScene import exportDialog
from PyQt5.QtGui import QIntValidator, QColor, QImage, QPainter, QPixmap
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os
import numpy as np
import pandas as pd
from MainWindow import Ui_MainWindow
from PyQt5.QtGui import QTransform, QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from IsotopeSelectionDialog import Ui_Dialog
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtCore import pyqtSignal
from rotated import RotatedHeaderView
import cmcrameri.cm as cmc
from ternary_plot import ternary
from sklearn.cluster import KMeans
from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
from matplotlib.colors import Normalize
import matplotlib.patches as mpatches
from matplotlib.colors import BoundaryNorm
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from plot_spider import plot_spider_norm
import re
import matplotlib.ticker as ticker
from radar import Radar
from calculator import CalWindow
import scipy.stats
## !pyrcc5 resources.qrc -o resources_rc.py
## pyuic5 mainwindow.ui -o MainWindow.py
## !pyuic5 -x IsotopeSelectionDialog.ui -o IsotopeSelectionDialog.py
# pylint: disable=fixme, line-too-long, no-name-in-module, trailing-whitespace
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        # Add this line to set the size policy
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.buttons_layout = None  # create a reference to your layout
        self.isotopes_df = pd.DataFrame(columns = ['sample_id', 'isotopes', 'norm', 'x_max','x_min','y_min','y_max','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use'])
        self.ratios_df = pd.DataFrame(columns = ['sample_id', 'isotope_1','isotope_2', 'norm', 'x_max','x_min','y_min','y_max','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use', 'auto_scale'])
        self.filter_df = pd.DataFrame(columns = ['sample_id', 'isotope_1', 'isotope_2', 'ratio','norm','f_min','f_max', 'use'])
        self.cluster_results=pd.DataFrame(columns = ['Fuzzy', 'KMeans', 'KMediods'])
        self.clipped_ratio_data = pd.DataFrame()
        self.clipped_isotope_data = {}
        self.sample_data_dict = {}
        self.plot_widget_dict ={'lasermap':{},'histogram':{},'lasermap_norm':{},'clustering':{},'scatter':{},'n-dim':{}}
        self.multi_view_index = []
        self.laser_map_dict = {}
        self.multiview_info_label = {}
        self.selected_isotopes = []
        self.n_dim_list = []
        self.group_cmap = {}
        self.lasermaps = {}
        self.proxies = []
        self.prev_plot = ''
        self.pop_plot = ''
        self.plot_id = {'clustering':{},'scatter':{},'n-dim':{}}
        self.fuzzy_results={}
        self.matplotlib_canvas = None
        self.pyqtgraph_widget = None
        self.isUpdatingTable = False
        colormaps = pg.colormap.listMaps('matplotlib')
        self.comboBoxCM.clear()
        self.comboBoxCM.addItems(colormaps)
        self.comboBoxCMG.clear()
        self.comboBoxCMG.addItems(colormaps)
        self.cursor = False
        self.comboBoxCM.activated.connect(self.update_all_plots)
        layout_single_view = QtWidgets.QVBoxLayout()
        layout_single_view.setSpacing(0)
        self.widgetSingleView.setLayout(layout_single_view)
        self.widgetSingleView.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout_multi_view = QtWidgets.QHBoxLayout()
        layout_multi_view.setSpacing(0)# Set margins to 0 if you want to remove margins as well
        layout_multi_view.setContentsMargins(0, 0, 0, 0)

        self.widgetMultiView.setLayout(layout_multi_view)
        self.widgetMultiView.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout_profile_view = QtWidgets.QVBoxLayout()
        layout_profile_view.setSpacing(0)
        self.widgetProfilePlot.setLayout(layout_profile_view)
        # Connect the "Open" action to a function
        self.actionOpen.triggered.connect(self.open_directory)

        #Selecting isotopes
        # Connect the currentIndexChanged signal of comboBoxSampleId to load_data method
        self.comboBoxSampleId.activated.connect(
            lambda: self.change_sample(self.comboBoxSampleId.currentIndex()))

        # self.toolButtonAddRatio.clicked.connect(lambda: self.ratios_items.appendRow(StandardItem(self.ratio_name)))


        # self.comboBoxFIsotope.activated.connect(
        #     lambda: self.get_map_data(self.sample_id,isotope_1=self.comboBoxFIsotope_1.currentText(),
        #                           isotope_2=self.comboBoxFIsotope_2.currentText(),view = 1))
        #

        self.toolButtonLoadIsotopes.clicked.connect(self.open_select_isotope_dialog)



        #self.comboBoxPlots.activated.connect(lambda: self.add_remove(self.comboBoxPlots.currentText()))
        #self.toolButtonAddPlots.clicked.connect(lambda: self.add_multi_plot(self.comboBoxPlots.currentText()))
        self.toolButtonRemovePlots.clicked.connect(lambda: self.remove_multi_plot(self.comboBoxPlots.currentText()))
        #add ratio item to tree view

        #tabs = self.canvasWindow
        #tabs.tabCloseRequested.connect(lambda index: tabs.removeTab(index))
        #self.canvasWindow.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        #create plot tree

        self.create_tree()
        self.open_directory()

        #load ref table
        self.ref_data = pd.read_excel('earthref.xlsx')
        ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']
        self.comboBoxRefMaterial.addItems(ref_list.values)
        self.comboBoxRefMaterial.activated.connect(self.update_all_plots)

        #normalising
        self.comboBoxNorm.clear()
        self.comboBoxNorm.addItems(['linear','log','logit'])
        self.comboBoxNorm.activated.connect(lambda: self.update_norm(self.sample_id, self.comboBoxNorm.currentText(), update = True))

        #preprocess
        self.doubleSpinBoxUB.setMaximum(100)
        self.doubleSpinBoxUB.setMinimum(0)
        self.doubleSpinBoxLB.setMaximum(100)
        self.doubleSpinBoxLB.setMinimum(0)
        self.doubleSpinBoxDUB.setMaximum(100)
        self.doubleSpinBoxDUB.setMinimum(0)
        self.doubleSpinBoxDLB.setMaximum(100)
        self.doubleSpinBoxDLB.setMinimum(0)

        self.doubleSpinBoxLB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxUB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxDUB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxDUB.valueChanged.connect(lambda: self.auto_scale(True))

        self.spinBoxX.valueChanged.connect(lambda:self.update_plot(axis = True))
        self.spinBoxY.valueChanged.connect(lambda:self.update_plot(axis = True))
        self.spinBox_X.valueChanged.connect(lambda:self.update_plot(axis = True))
        self.spinBox_Y.valueChanged.connect(lambda:self.update_plot(axis = True))
        self.spinBoxNBins.valueChanged.connect(self.update_plot)
        self.spinBoxBinWidth.valueChanged.connect(lambda: self.update_plot(bin_s=False))
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(0))
        #auto scale
        self.checkBoxAutoScale.clicked.connect( self.auto_scale )


        ###Filter
        self.pushButtonAddFilter.clicked.connect(self.update_filter_table)
        self.pushButtonFilterSelectAll.clicked.connect(self.select_all_rows)
        self.toolButtonFilterRemove.clicked.connect(self.remove_selected_rows)
        self.comboBoxFSelect.activated.connect(lambda: self.update_combo_boxes('f'))
        self.comboBoxFIsotope.activated.connect(self.update_filter_values)
        #     lambda: self.get_map_data(self.sample_id,isotope_1=self.comboBoxFIsotope_1.currentText(),
        #                           isotope_2=self.comboBoxFIsotope_2.currentText(),view = 1))

        #scatterplot
        self.pushButtonPlotScatter.clicked.connect(self.plot_scatter)


        self.comboBoxScatterSelectX.activated.connect(lambda: self.update_combo_boxes('x'))
        self.comboBoxScatterSelectY.activated.connect(lambda: self.update_combo_boxes('y'))
        self.comboBoxScatterSelectZ.activated.connect(lambda: self.update_combo_boxes('z'))
        self.comboBoxScatterSelectC.activated.connect(lambda: self.update_combo_boxes('c'))



        #Clustering
        # Populate the comboBoxCluster with distance metrics
        distance_metrics = ['cityblock', 'cosine', 'euclidean', 'l1', 'l2', 'manhattan']
        self.comboBoxClusterDistance.clear()
        self.comboBoxClusterDistance.addItems(distance_metrics)
        # Connect radio buttons to the slot function
        self.radioButtonKMeans.setChecked(True)
        self.radioButtonKMeans.clicked.connect(self.update_cluster_ui)
        self.radioButtonKMedoids.clicked.connect(self.update_cluster_ui)
        self.radioButtonFuzzy.clicked.connect(self.update_cluster_ui)
        self.radioButtonClusterAll.clicked.connect(self.update_cluster_ui)

        self.pushButtonRunClustering.clicked.connect(self.plot_clustering)

        # Connect slider's value changed signal to a function
        self.spinBoxNClusters.valueChanged.connect(lambda: self.spinBoxFCView.setMaximum(self.spinBoxNClusters.value()))

        self.horizontalSliderExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        self.horizontalSliderExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        self.horizontalSliderExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        self.horizontalSliderExponent.setTickInterval(1)


        self.horizontalSliderExponent.valueChanged.connect(lambda value: self.labelExponent.setText(str(value/10)))
        self.update_cluster_ui()

        # Connect color point radio button signals to a slot
        self.radioButtonCNone.toggled.connect(self.onRadioButtonToggled)
        self.radioButtonCFuzzy.toggled.connect(self.onRadioButtonToggled)
        self.radioButtonCKMediods.toggled.connect(self.onRadioButtonToggled)
        self.radioButtonCKMeans.toggled.connect(self.onRadioButtonToggled)

        # Connect the itemChanged signal to a slot
        self.tableWidgetViewGroups.itemChanged.connect(self.onClusterLabelChanged)


        self.radioButtonCNone.setChecked(True)
        # self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)


        # N-Dim Plot

        isotop_set = ['majors', 'full trace', 'REE', 'metals']
        self.comboBoxNDimIsotopeSet.addItems(isotop_set)
        self.comboBoxNDimRefMaterial.addItems(ref_list.values)
        self.pushButtonNDimAdd.clicked.connect(self.update_n_dim_table)
        self.pushButtonNDimPlot.clicked.connect(self.plot_n_dim)

        # plot profile
        self.lineEditPointRadius.setValidator(QIntValidator())
        self.lineEditYThresh.setValidator(QIntValidator())
        self.profiling = Profiling(self)
        # self.pushButtonPlotProfile.clicked.connect(lambda: self.plot_profiles(self.comboBoxProfile1.currentText(), self.comboBoxProfile2.currentText()))
        # self.comboBoxProfile1.activated.connect(lambda: self.update_profile_comboboxes(False) )
        self.pushButtonClearProfile.clicked.connect(self.profiling.on_clear_profile_clicked)
        # self.pushButtonStartProfile.clicked.connect(lambda :self.pushButtonStartProfile.setChecked(True))
        # self.pushButtonStartProfile.setCheckable(True)
        # self.comboBoxProfile2.activated.connect(self.update_profile_comboboxes)
        self.toolButtonPointUp.clicked.connect(self.profiling.move_point_up)
        self.toolButtonPointDown.clicked.connect(self.profiling.move_point_down)
        self.toolButtonPointDelete.clicked.connect(self.profiling.delete_point)
        self.comboBoxProfileSort.activated.connect(self.plot_profile_and_table)
        self.pushButtonIPProfile.clicked.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.lineEditIntDist.text()), radius= int(self.lineEditPointRadius.text())))
        self.comboBoxPointType.activated.connect(lambda:self.profiling.plot_profiles())
        self.pushButtonPlotProfile.clicked.connect(lambda:self.profiling.plot_profiles())

        #SV/MV tool box
        self.toolButtonPanSV.setCheckable(True)
        self.toolButtonPanMV.setCheckable(True)

        self.toolButtonZoomSV.setCheckable(True)
        self.toolButtonZoomMV.setCheckable(True)


        self.toolButtonHomeSV.clicked.connect(lambda: self.toolbar_plotting('home', 'SV', self.toolButtonHomeSV.isChecked()))
        # self.toolButtonHomeMV.clicked.connect

        self.toolButtonPanSV.clicked.connect(lambda: self.toolbar_plotting('pan', 'SV', self.toolButtonPanSV.isChecked()))
        # self.toolButtonPanMV.clicked.connect

        self.toolButtonZoomSV.clicked.connect(lambda: self.toolbar_plotting('zoom', 'SV', self.toolButtonZoomSV.isChecked()))
        # self.toolButtonZoomMV.clicked.connect

        self.toolButtonPreferencesSV.clicked.connect(lambda: self.toolbar_plotting('preference', 'SV', self.toolButtonPreferencesSV.isChecked()))
        # self.toolButtonPreferencesMV.clicked.connect

        self.toolButtonAxesSV.clicked.connect(lambda: self.toolbar_plotting('axes', 'SV', self.toolButtonAxesSV.isChecked()))
        # self.toolButtonAxesMV.clicked.connect

        self.toolButtonSaveSV.clicked.connect(lambda: self.toolbar_plotting('save', 'SV', self.toolButtonSaveSV.isChecked()))
        # self.toolButtonSaveMV.clicked.connect

        self.actionCalculator.triggered.connect(self.open_calculator)

    def open_calculator(self):
        isotopes_list = self.isotopes_df['isotopes'].values
        self.calWindow = CalWindow(isotopes_list,self.sample_data_dict[self.sample_id] )
        self.calWindow.show()

    def plot_profile_and_table(self):
        self.profiling.plot_profiles()
        self.profiling.update_table_widget()

    def update_clusters(self):
        selected_clusters = []
        for idx in self.tableWidgetViewGroups.selectionModel().selectedRows():
            selected_clusters.append(self.tableWidgetViewGroups.item(idx.row(), 0).text())

        if selected_clusters:
            self.current_group['clusters'] = selected_clusters
        else:
            self.current_group['clusters'] = None


    def update_color_bar_position(self):
        # Get the selected color bar position
        color_bar_position = self.comboBoxCBP.currentText().lower()

        # Iterate over your plots to update the color bar position
        for key, value in self.plot_widget_dict.items():
            # Assume each value has a 'fig' attribute representing the Figure
            fig = value['widget'][0].figure
            ax = fig.axes[0]  # Assuming the first axis is the one with the color bar

            # Remove existing color bars
            for cbar in fig.colorbar_artists:
                cbar.remove()

            # Add color bar with new orientation
            if color_bar_position == 'horizontal':
                orientation = 'horizontal'
            else:  # Default to vertical if not horizontal
                orientation = 'vertical'

            # Create a new color bar with the new orientation
            img = ax.images[0]  # Assuming the first image is the one to apply color bar
            fig.colorbar(img, ax=ax, orientation=orientation)

            # Redraw the figure to update the changes
            fig.canvas.draw_idle()


    def scale_plot(self, current_plot_df, lq, uq, d_lb,d_ub, x_range, y_range, norm='linear', outlier=False):
        # remove outliers, autoscale plots
        isotope_array = current_plot_df['array'].values

        if outlier: #run outlier detection algorithm
            isotope_array = self.outlier_detection(current_plot_df['array'].values.reshape(-1, 1), lq, uq, d_lb,d_ub)
        else:
            lq_val = np.nanpercentile(isotope_array, lq, axis=0)
            uq_val = np.nanpercentile(isotope_array, uq, axis=0)
            isotope_array = np.clip(isotope_array, lq_val, uq_val)
        isotope_array = self.transform_plots(isotope_array)


        if norm == 'log':
            # np.nanlog handles NaN values
            isotope_array = np.log10(isotope_array, where=~np.isnan(isotope_array))
        elif norm == 'logit':
            # Handle division by zero and NaN values
            with np.errstate(divide='ignore', invalid='ignore'):
                isotope_array = np.log10(isotope_array / (10**6 - isotope_array), where=~np.isnan(isotope_array))

        current_plot_df.loc[:, 'array'] = self.transform_plots(isotope_array)

        return current_plot_df


    def auto_scale(self,update = False):
        if self.update_spinboxes_bool: # spinboxes are not being updated
            sample_id = self.current_plot_information['sample_id']
            isotope_1 = self.current_plot_information['isotope_1']
            isotope_2 = self.current_plot_information['isotope_2']
            plot_type = self.current_plot_information['plot_type']
            auto_scale = True
            lb = self.doubleSpinBoxLB.value()
            ub = self.doubleSpinBoxUB.value()
            d_lb = self.doubleSpinBoxDLB.value()
            d_ub = self.doubleSpinBoxDUB.value()

            # if isotope_1 and not isotope_2:
            #     auto_scale_value = self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
            #                      & (self.isotopes_df['isotopes']==isotope_1),'auto_scale'].values[0]
            # else:
            #     auto_scale_value = self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
            #                              & (self.ratios_df['isotope_1']==isotope_1)
            #                              & (self.ratios_df['isotope_2']==isotope_2),'auto_scale'].values[0]




            # if auto_scale_value and not update: #user unticks auto_scale
            #     auto_scale = False



            if isotope_1 and not isotope_2:

                self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
                                  & (self.isotopes_df['isotopes']==isotope_1),'auto_scale']  = self.checkBoxAutoScale.isChecked()
                self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
                                         & (self.isotopes_df['isotopes']==isotope_1),
                                         ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]


            else:
                self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
                                         & (self.ratios_df['isotope_1']==isotope_1)
                                         & (self.ratios_df['isotope_2']==isotope_2),'auto_scale']  = self.checkBoxAutoScale.isChecked()
                self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
                                          & (self.ratios_df['isotope_1']==isotope_1)
                                          & (self.ratios_df['isotope_2']==isotope_2),
                                          ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
            self.get_map_data(self.sample_id, isotope_1 = isotope_1, isotope_2 = isotope_2, plot_type = plot_type, auto_scale = auto_scale, update = True)

            self.update_filter_values()



    def update_plot(self,bin_s = True, axis = False):
        if self.update_spinboxes_bool:
            self.canvasWindow.setCurrentIndex(0)
            lb = self.doubleSpinBoxLB.value()
            ub = self.doubleSpinBoxUB.value()
            d_lb = self.doubleSpinBoxDLB.value()
            d_ub = self.doubleSpinBoxDUB.value()

            x_range= [self.spinBox_X.value(),self.spinBoxX.value()]
            y_range = [self.spinBox_Y.value(),self.spinBoxY.value()]
            bins = self.spinBoxNBins.value()
            isotope_str = self.current_plot
            isotope_str_list = isotope_str.split('_')
            auto_scale = self.checkBoxAutoScale.isChecked()
            sample_id = self.current_plot_information['sample_id']
            isotope_1 = self.current_plot_information['isotope_1']
            isotope_2 = self.current_plot_information['isotope_2']
            plot_type = self.current_plot_information['plot_type']
            plot_name = self.current_plot_information['plot_name']
            current_plot_df = self.current_plot_df
            current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub, x_range = x_range, y_range = y_range)

            # Computing data range using the 'array' column
            data_range = current_plot_df['array'].max() - current_plot_df['array'].min()
            #change axis range for all plots in sample
            if axis:
                self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id), ['x_min','x_max','y_min','y_max']] = [x_range[0],x_range[1],y_range[0],y_range[1]]

                self.ratios_df.loc[(self.ratios_df['sample_id']==sample_id), ['x_min','x_max','y_min','y_max']] = [x_range[0],x_range[1],y_range[0],y_range[1]]
                # Filtering rows based on the conditions on 'X' and 'Y' columns
                self.axis_mask = ((current_plot_df['X'] >= x_range[0]) & (current_plot_df['X'] <= x_range[1]) &
                               (current_plot_df['Y'] <= current_plot_df['Y'].max() - y_range[0]) & (current_plot_df['Y'] >= current_plot_df['Y'].max() - y_range[1]))


            self.clipped_isotope_data[sample_id][isotope_1] = current_plot_df['array'].values
            self.update_norm(sample_id, isotope = isotope_1)
            current_plot_df = current_plot_df[self.axis_mask].reset_index(drop=True)
            if plot_type=='hist':
                # If bin_width is not specified, calculate it
                if bin_s:
                    bin_width = data_range / bins
                    self.spinBoxBinWidth.setValue(int(bin_width))
                else:
                    bin_width = self.spinBoxBinWidth.value()
                    bins = int(data_range / bin_width)
                    self.spinBoxNBins.setValue(bins)
                self.plot_histogram(current_plot_df,bins,bin_width ,self.current_plot_information)
            else:
                self.plot_laser_map(current_plot_df, self.current_plot_information)
            # self.add_plot(isotope_str,clipped_isotope_array)




    def remove_multi_plot(self, selected_plot_name):
        widget_index = self.multi_view_index.index(selected_plot_name)
        layout = self.widgetMultiView.layout()
        item = layout.itemAt(widget_index)  # Get the item at the specified index
        if item is not None:
            widget = item.widget()   # Get the widget from the item
            if widget is not None:
                layout.removeWidget(widget)  # Remove the widget from the layout
                widget.setParent(None)      # Set the widget's parent to None
        # if widget is not None:
        #     index = self.canvasWindow.addTab( widget, selected_plot_name)
        self.multi_view_index.pop(widget_index)
        for widget in self.multiview_info_label[selected_plot_name+'1']:
            widget.setParent(None)
            widget.deleteLater()
        del self.multiview_info_label[selected_plot_name+'1']
        del self.lasermaps[selected_plot_name+'1']
        #self.plot_widget_dict[selected_plot_name] = widget
        #self.add_remove(selected_plot_name)
        self.comboBoxPlots.clear()
        self.comboBoxPlots.addItems(self.multi_view_index)

    def add_plot(self, plot_information, current_plot_df = None):
        
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']
        

        #get plot widget and view from plot_widget_dict
        for widget, view in zip(self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'],self.plot_widget_dict[plot_type][sample_id][plot_name]['view']):
            if view == self.canvasWindow.currentIndex():
                selected_plot_widget = widget
                continue
            else:
                selected_plot_widget = widget
        if self.canvasWindow.currentIndex() and plot_name not in self.multi_view_index:
            #Multi view
            layout = self.widgetMultiView.layout()

            # Set the inner grid layout for the inner widget
            layout.addWidget(selected_plot_widget)

            # Set spacing to 0 to remove gaps between widgets
            layout.setSpacing(0)

            # Set margins to 0 if you want to remove margins as well
            layout.setContentsMargins(0, 0, 0, 0)
            # show plot sinc parent is visible
            selected_plot_widget.show()
            #remove tab
            #self.canvasWindow.removeTab(tab_index)
            #get the the index of plot on multiview
            self.multi_view_index.append(plot_name)
            #self.canvasWindow.setEnabled(index,False)
            #self.add_remove(plot_name)
            #reduce the index of widgets right hand side of index tab by one 
            self.comboBoxPlots.clear()
            self.comboBoxPlots.addItems(self.multi_view_index)
        elif self.canvasWindow.currentIndex()==0:
            #Single view 
            self.single_plot_name = plot_name

            #remove plot from multi view if the plot is already in multiview

            layout = self.widgetSingleView.layout()
            #remove current plot
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item is not None:
                    widget = item.widget()   # Get the widget from the item
                    if widget is not None:
                        layout.removeWidget(widget)  # Remove the widget from the layout
                        widget.setParent(None)      # Set the widget's parent to None
            # selected_plot_widget = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget']
            self.current_plot = plot_name
            self.current_plot_information = plot_information
            self.current_plot_df = current_plot_df
            layout.addWidget(selected_plot_widget)
            selected_plot_widget.show()

            # Assuming widgetClusterMap is a QWidget with a QVBoxLayout containing figure_canvas
            for i in range(selected_plot_widget.layout().count()):
                widget = selected_plot_widget.layout().itemAt(i).widget()
                if isinstance(widget, FigureCanvas):
                    self.matplotlib_canvas = widget
                    break
                elif isinstance(widget, pg.GraphicsLayoutWidget):
                    self.pyqtgraph_widget = widget
                    break

        # After adding the plots, refresh windows to fix toggle button issue
        self.hide()
        self.show()
    def clear_views(self):
        pass

    def activate_ratios(self, state):
        if state == 2:  # Qt.Checked
            # Call your method here when the checkbox is checked
            self.labelIsotope_2.setEnabled(True)
            self.comboBoxIsotope_2.setEnabled(True)
            self.get_map_data(self.sample_id,
                              isotope_1=self.comboBoxIsotope_1.currentText(),
                              isotope_2=self.comboBoxIsotope_2.currentText(),view = 1)
            self.toolButtonAddRatio.setEnabled(True)
        else:
            self.labelIsotope_2.setEnabled(False)
            self.comboBoxIsotope_2.setEnabled(False)
            self.get_map_data(self.sample_id,isotope_1=self.comboBoxIsotope_1.currentText())
            self.toolButtonAddRatio.setEnabled(False)

    def update_filter_values(self):
        isotope_1 = self.comboBoxFIsotope.currentText()
        isotope_2  = None
        isotope_select =self.comboBoxFSelect.currentText()

        if isotope_select == 'Isotope':
            f_val = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope_1)].iloc[0][['v_min', 'v_max']]
        else:
            if '/' in isotope_1:
                isotope_1, isotope_2 = isotope_1.split(' / ')
                f_val = self.ratios_df.loc[(self.ratios_df['sample_id'] == self.sample_id)
                                            & (self.ratios_df['isotope_1'] == isotope_1)& (self.ratios_df['isotope_2'] == isotope_2)].iloc[0][['v_min', 'v_max']]

        self.lineEditFMin.setText(str(self.dynamic_format(f_val['v_min'])))
        self.lineEditFMax.setText(str(self.dynamic_format(f_val['v_max'])))

    def update_filter_table(self):

        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.filter_df.at[row, 'use'] = state == QtCore.Qt.Checked



        isotope_1 = self.comboBoxFIsotope.currentText()
        isotope_2  = None
        isotope_select =self.comboBoxFSelect.currentText()
        f_min = float(self.lineEditFMin.text())
        f_max = float(self.lineEditFMax.text())
        # Add a new row at the end of the table
        row = self.tableWidgetFilterTable.rowCount()
        self.tableWidgetFilterTable.insertRow(row)

        # Create a QCheckBox for the 'use' column
        chkBoxItem_use = QtWidgets.QCheckBox()
        chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
        chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

        chkBoxItem_select = QTableWidgetItem()
        chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                            QtCore.Qt.ItemIsEnabled)
        ratio =False
        if isotope_select == 'Isotope':
            chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope_1)].iloc[0]['norm']
        else:
            if '/' in isotope_1:
                ratio = True
                isotope_1, isotope_2 = isotope_1.split(' / ')
                norm = self.ratios_df.loc[(self.ratios_df['sample_id'] == self.sample_id)
                                          & (self.ratios_df['isotope_1'] == isotope_1) & (self.ratios_df['isotope_2'] == isotope_2)].iloc[0]['norm']

        self.tableWidgetFilterTable.setCellWidget(row, 0, chkBoxItem_use)
        self.tableWidgetFilterTable.setItem(row, 1,
                                 QtWidgets.QTableWidgetItem(self.sample_id))
        self.tableWidgetFilterTable.setItem(row, 2,
                                 QtWidgets.QTableWidgetItem(isotope_1))
        self.tableWidgetFilterTable.setItem(row, 3,
                                 QtWidgets.QTableWidgetItem(isotope_2))

        self.tableWidgetFilterTable.setItem(row, 4,
                                 QtWidgets.QTableWidgetItem(ratio))

        self.tableWidgetFilterTable.setItem(row, 5,
                                 QtWidgets.QTableWidgetItem(self.dynamic_format(f_min)))
        self.tableWidgetFilterTable.setItem(row, 6,
                                 QtWidgets.QTableWidgetItem(self.dynamic_format(f_max)))


        self.tableWidgetFilterTable.setItem(row, 7,
                                 chkBoxItem_select)


        filter_info = {'sample_id': self.sample_id, 'isotope_1': isotope_1, 'isotope_2': isotope_2, 'ratio': ratio,'norm':norm ,'f_min': f_min,'f_max':f_max, 'use':True}
        self.filter_df.loc[len(self.filter_df)]=filter_info


        self.update_filter_mask(self.sample_id)


    def update_filter_mask(self,sample_id):
        # Check if rows in self.filter_df exist and filter array in current_plot_df
        # by creating a mask based on f_min and f_max of the corresponding filter isotopes
        self.filter_mask = np.ones_like(self.filter_mask, dtype=bool)
        for index, filter_row in self.filter_df.iterrows():
            if filter_row['use'] and filter_row['sample_id'] == sample_id:
                isotope_df = self.get_map_data(sample_id, filter_row['isotope_1'], filter_row['isotope_2'], plot_type = None,plot= False)
                self.filter_mask = self.filter_mask & (isotope_df['array'].values <= filter_row['f_min']) | (isotope_df['array'].values >= filter_row['f_max'])


    def select_all_rows(self):
        for row in range(self.tableWidgetFilterTable.rowCount()):
            # Assuming the checkbox is in the 0th column
            chkBoxItem = self.tableWidgetFilterTable.item(row, 7)
            chkBoxItem.setCheckState(QtCore.Qt.Checked)

    def remove_selected_rows(self,sample):
        # We loop in reverse to avoid issues when removing rows
        for row in range(self.tableWidgetFilterTable.rowCount()-1, -1, -1):
            chkBoxItem = self.tableWidgetFilterTable.item(row, 7)
            sample_id = self.tableWidgetFilterTable.item(row, 1).text()
            isotope_1 = self.tableWidgetFilterTable.item(row, 2).text()
            isotope_2 = self.tableWidgetFilterTable.item(row, 3).text()
            ratio = bool(self.tableWidgetFilterTable.item(row, 4).text())
            if chkBoxItem.checkState() == QtCore.Qt.Checked:
                self.tableWidgetFilterTable.removeRow(row)
                if not ratio:
                    self.filter_df.drop(self.filter_df[(self.filter_df['sample_id'] == sample_id)
                                           & (self.filter_df['isotope_1'] == isotope_1)& (self.filter_df['ratio'] == ratio)].index, inplace=True)
                else:
                # Remove corresponding row from filter_df
                    self.filter_df.drop(self.filter_df[(self.filter_df['sample_id'] == sample_id)
                                           & (self.filter_df['isotope_1'] == isotope_1)& (self.filter_df['isotope_2'] == isotope_2)].index, inplace=True)
        self.update_filter_mask(sample_id)


    def dynamic_format(self,value, threshold=1e3):
        if abs(value) > threshold:
            return "{:.4e}".format(value)  # Scientific notation with 2 decimal places
        else:
            return "{:.4f}".format(value)

    def update_norm(self,sample_id, norm = None, isotope=None, update = False):
        if not norm:
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                                 & (self.isotopes_df['isotopes']==isotope),'norm'][0]
        if isotope: #if normalising single isotope
            isotopes = [isotope]
            self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                                 & (self.isotopes_df['isotopes']==isotope),'norm'] = norm

        else: #if normalising all isotopes in sample
            self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id),'norm'] = norm
            isotopes = self.isotopes_df[self.isotopes_df['sample_id']==sample_id]['isotopes']



        isotope_array =  self.clipped_isotope_data[sample_id][isotopes].values
        if norm == 'log':
            # np.nanlog handles NaN value
            self.processed_isotope_data[sample_id].loc[:,isotopes] = np.log10(isotope_array, where=~np.isnan(isotope_array))
        elif norm == 'logit':
            # Handle division by zero and NaN values
            with np.errstate(divide='ignore', invalid='ignore'):
                isotope_array = np.log10(isotope_array / (10**6 - isotope_array), where=~np.isnan(isotope_array))
                self.processed_isotope_data[sample_id].loc[:,isotopes] = isotope_array
        else:
            # set to clipped data with original values if linear normalisation
            self.processed_isotope_data = self.clipped_isotope_data.copy()
        if update:
            self.update_all_plots()
        # self.update_plot()



    def update_all_plots(self):

        for plot_type in self.plot_widget_dict.keys():
            if plot_type == 'histogram' or plot_type == 'lasermap' or plot_type == 'lasernorm':
                for sample_id, plot in self.plot_widget_dict.items():
                    info = plot['info']
                    self.get_map_data(sample_id=info['sample_id'], isotope_1 =info['isotope_1'],isotope_2= info['isotope_2'],plot_type = info['plot_type'], plot =False )
            





    def open_directory(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        # Set the default directory to the current working directory
        # dialog.setDirectory(os.getcwd())
        dialog.setDirectory('/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/')
        if dialog.exec_():
            self.selected_directory = dialog.selectedFiles()[0]
            file_list = os.listdir(self.selected_directory)
            self.csv_files = [file for file in file_list if file.endswith('.csv')]
            self.comboBoxSampleId.clear()
            self.comboBoxSampleId.addItems([os.path.splitext(file)[0] for file in self.csv_files])
            # Populate the sampleidcomboBox with the file names
            self.canvasWindow.setCurrentIndex(0)
            self.change_sample(0, )
        # self.selected_directory='/Users/a1904121/LaserMapExplorer/laser_mapping/Alex_garnet_maps/processed data'
        # self.selected_directory='/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/processed data'
        # self.selected_directory=''
        file_list = os.listdir(self.selected_directory)
        self.csv_files = [file for file in file_list if file.endswith('.csv')]
        self.comboBoxSampleId.clear()
        self.comboBoxSampleId.addItems([os.path.splitext(file)[0] for file in self.csv_files])
        # Populate the sampleidcomboBox with the file names
        self.canvasWindow.setCurrentIndex(0)
        self.change_sample(0, )

    def remove_widgets_from_layout(self, layout, object_names_to_remove):
        """
        Remove widgets from the provided layout based on their objectName properties.
        """
        for i in reversed(range(layout.count())):  # Reverse to avoid skipping due to layout change
            item = layout.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() in object_names_to_remove:
                widget.setParent(None)
                widget.deleteLater()
            # Handle child layouts
            elif hasattr(item, 'layout') and item.layout():
                child_layout = item.layout()
                if child_layout.objectName() in object_names_to_remove:
                    # Remove all widgets from the child layout
                    while child_layout.count():
                        child_item = child_layout.takeAt(0)
                        if child_item.widget():
                            child_item.widget().setParent(None)
                            child_item.widget().deleteLater()
                    # Now remove the layout itself
                    layout.removeItem(child_layout)
                    del child_layout

        layout.update()

    def plot_laser_map(self, current_plot_df, plot_information):
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']
        

        array = np.reshape(current_plot_df['array'].values,
                                    (current_plot_df['Y'].nunique(),
                                     current_plot_df['X'].nunique()), order='F')[ ::-1, :] #reverse order of rows
        self.x_range = current_plot_df['X'].max() - current_plot_df['X'].min()
        self.y_range = current_plot_df['Y'].max() - current_plot_df['Y'].min()

        duplicate = False
        plot_exist = False
        if plot_name in self.plot_widget_dict[plot_type][sample_id]:
            plot_exist = True
            duplicate = len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view'])==1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()



        if plot_exist and not duplicate:
            widget_info = self.plot_widget_dict[plot_type][sample_id][plot_name]
            for widgetLaserMap, view in zip(widget_info['widget'],widget_info['view']):
                glw = widgetLaserMap.findChild(pg.GraphicsLayoutWidget, 'plotLaserMap')
                p1 = glw.getItem(0, 0)  # Assuming ImageItem is the first item in the plot
                img = p1.items[0]
                img.setImage(image=array.T)
                cm = pg.colormap.get(self.comboBoxCM.currentText(), source = 'matplotlib')
                img.setColorMap(cm)
                histogram = widgetLaserMap.findChild(pg.HistogramLUTWidget, 'histogram')
                if histogram:
                    histogram.gradient.setColorMap(cm)
                    histogram.setImageItem(img)
                for i in reversed(range(p1.layout.count())):  # Reverse to avoid skipping due to layout change
                    item = p1.layout.itemAt(i)
                    if isinstance(item, pg.ColorBarItem):#find colorbar
                        item.setColorMap(cm)
                        item.setLevels([array.min(), array.max()])
                layout = widgetLaserMap.layout()
                # self.plot_laser_map_cont(layout,array,img,p1,cm,view)
        else:

            widgetLaserMap = QtWidgets.QWidget()
            layoutLaserMap = QtWidgets.QGridLayout()
            widgetLaserMap.setLayout(layoutLaserMap)
            layoutLaserMap.setSpacing(0)
            view = self.canvasWindow.currentIndex()
            if duplicate: 
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetLaserMap)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)

            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget':[widgetLaserMap],
                                                      'info':plot_information, 'view':[view]}
            # self.array = array[:, ::-1]
            layout = widgetLaserMap.layout()
            glw = pg.GraphicsLayoutWidget(show=True)
            glw.setObjectName('plotLaserMap')
            # Create the ImageItem
            img = pg.ImageItem(image=array.T)

            #set aspect ratio of rectangle
            img.setRect(0,0,self.x_range,self.y_range)
            # img.setAs
            cm = pg.colormap.get(self.comboBoxCM.currentText(), source = 'matplotlib')
            img.setColorMap(cm)
            # img.setLookupTable(cm.getLookupTable())
            #--- add non-interactive image with integrated color ------------------
            p1 = glw.addPlot(0,0,title=plot_name.replace('_',' '))
            # p1.setRange(padding=0)
            p1.showAxes(False, showValues=(True,False,False,True) )




            p1.addItem(img)
            # print(p1.getAspectRatio())
            p1.setAspectLocked()


            # ... Inside your plotting function
            target = pg.TargetItem(symbol = '+')
            p1.addItem(target)

            # Optionally, configure the appearance
            # For example, set the size of the crosshair
            name = plot_name+str(view)
            self.lasermaps[name] = (target, p1, view, array)


            #hide pointer
            target.hide()


            p1.scene().sigMouseClicked.connect(lambda event,array=array, k=name, plot=p1: self.profiling.on_plot_clicked(event,array, k, p1, radius= int(self.lineEditPointRadius.text())))

            if view == 1:
                #create label with isotope name
                #create another label for value of the corresponding plot
                labelInfoVL = QtWidgets.QLabel(self.groupBoxInfoM)
                # labelInfoVL.setMaximumSize(QtCore.QSize(20, 16777215))
                labelInfoVL.setObjectName("labelInfoVL"+name)
                labelInfoVL.setText(plot_name)
                font = QtGui.QFont()
                font.setPointSize(9)
                labelInfoVL.setFont(font)
                verticalLayout = QtWidgets.QVBoxLayout()
                # Naming the verticalLayout
                verticalLayout.setObjectName(plot_name + str(view))
                verticalLayout.addWidget(labelInfoVL)

                labelInfoV = QtWidgets.QLabel(self.groupBoxInfoM)
                labelInfoV.setObjectName("labelInfoV"+name)
                labelInfoV.setFont(font)
                verticalLayout.addWidget(labelInfoV)
                self.gridLayoutInfoM.addLayout(verticalLayout, 0, self.gridLayoutInfoM.count()+1, 1, 1)
                # Store the reference to verticalLayout in a dictionary
                self.multiview_info_label[name] = (labelInfoVL, labelInfoV)
            else:
                #remove previous plot in single view
                if self.prev_plot:
                    del self.lasermaps[self.prev_plot]
                self.prev_plot = name



            # Create a SignalProxy to handle mouse movement events
            # self.proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
            # Create a SignalProxy for this plot and connect it to mouseMoved

            p1.scene().sigMouseMoved.connect(lambda event,plot=p1: self.mouse_moved(event,plot))
            # proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)
            # self.proxies.append(proxy)  # Assuming self.proxies is a list to store proxies

            # print(p1.getAspectRatio())
            # p1.autoRange()
            layout.addWidget(glw, 0, 0, 3, 2)
            glw.setBackground('w')
            self.plot_laser_map_cont(layout,array,img,p1,cm,view)

    def mouse_moved(self,event,plot):
        pos_view = plot.vb.mapSceneToView(event)  # This is in view coordinates
        pos_scene = plot.vb.mapViewToScene(pos_view)  # Map from view to scene coordinates
        any_plot_hovered = False
        for k, (_, p, v, array) in self.lasermaps.items():
            # print(p.sceneBoundingRect(), pos)
            if p.sceneBoundingRect().contains(pos_scene) and v == self.canvasWindow.currentIndex() and not self.toolButtonPanSV.isChecked() and not self.toolButtonZoomSV.isChecked() :

                # mouse_point = p.vb.mapSceneToView(pos)
                mouse_point = pos_view
                x, y = mouse_point.x(), mouse_point.y()

                # print(x,y)
                x_i = round(x*array.shape[1]/self.x_range)
                y_i = round(y*array.shape[0]/self.y_range)
                if 0 <= x_i < array.shape[1] and 0 <= y_i < array.shape[0] :
                    if not self.cursor:
                        QtWidgets.QApplication.setOverrideCursor(Qt.BlankCursor)
                        self.cursor = True
                    any_plot_hovered = True
                    value = array[y_i, x_i]  # assuming self.array is numpy self.array

                    if self.canvasWindow.currentIndex() == 0:

                        self.labelInfoX.setText('X: '+str(round(x)))
                        self.labelInfoY.setText('Y: '+str(round(y)))
                        self.labelInfoV.setText('V: '+str(round(value,2)))
                    else: #multi-view
                        self.labelInfoXM.setText('X: '+str(round(x)))
                        self.labelInfoYM.setText('Y: '+str(round(y)))

                    for k, (target, _, _,array) in self.lasermaps.items():
                        target.setPos(mouse_point)
                        target.show()
                        value = array[y_i, x_i]
                        if k in self.multiview_info_label:
                            self.multiview_info_label[k][1].setText('v: '+str(round(value,2)))
                # break
        if not any_plot_hovered:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.cursor = False
            for target,_, _, _ in self.lasermaps.values():
                target.hide() # Hide crosshairs if no plot is hovered


    def plot_laser_map_cont(self,layout,array,img,p1,cm, view):
        # Single views
        if self.canvasWindow.currentIndex()==0 and view==self.canvasWindow.currentIndex():
            # Try to remove the colorbar just in case it was added somehow
            # for i in reversed(range(p1.layout.count())):  # Reverse to avoid skipping due to layout change
            #     item = p1.layout.itemAt(i)
            #     if isinstance(item, pg.ColorBarItem):
            #         p1.layout.removeAt(i)
            # Create the histogram item


            histogram = pg.HistogramLUTWidget( orientation='horizontal')
            histogram.setObjectName('histogram')
            histogram.gradient.setColorMap(cm)
            histogram.setImageItem(img)
            histogram.setBackground('w')
            layout.addWidget(histogram, 3, 0,  1, 2)
            # Set the maximum length
            # max_length = 1.5 * p1.boundingRect().width()
            # histogram.setMaximumWidth(max_length)
            # Create a horizontal spacer to center the histogram
            # spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            # # Add a Reset Zoom button
            # reset_zoom_button = QtWidgets.QPushButton("Reset Zoom")
            # reset_zoom_button.setObjectName("pushButtonResetZoom")
            # # reset_button.setMaximumWidth(100)
            # reset_zoom_button.clicked.connect(lambda: self.reset_zoom(p1,histogram))
            # # layout.addWidget(reset_zoom_button, 4, 0, 1, 1)
            # reset_plot_button = QtWidgets.QPushButton("Reset Plot")
            # reset_plot_button.setObjectName("pushButtonResetPlot")
            # # reset_button.setMaximumWidth(100)
            # reset_plot_button.clicked.connect(lambda: print(histogram.getHistogramRange()))
            # # layout.addWidget(reset_plot_button, 4, 1, 1, 1)

            # hbox = QHBoxLayout()
            # hbox.addStretch(1)
            # hbox.addWidget(reset_zoom_button)
            # hbox.addWidget(reset_plot_button)
            # vbox = QVBoxLayout()
            # vbox.setObjectName('buttons')
            # vbox.addStretch(1)
            # vbox.addLayout(hbox)

            # layout.addLayout(vbox, 4, 0, 1, 2)
        else:
            # multi view
            object_names_to_remove = ['histogram', 'pushButtonResetZoom', 'pushButtonResetPlot', 'buttons']
            # self.remove_widgets_from_layout(layout, object_names_to_remove)
            # plot = glw.getItem(0, 0)
            cbar = pg.ColorBarItem(orientation = 'h',colorMap = cm)
            cbar.setObjectName('colorbar')
            cbar.setImageItem(img, insert_in=p1)
            cbar.setLevels([array.min(), array.max()])



        # distances, medians, lowers, uppers = process_points(profile1_points, sort_axis='x')
        # errors = [upper - lower for upper, lower in zip(uppers, lowers)]

        # fig = Figure()
        # ax1 = fig.add_subplot(111)
        # ax1.errorbar(distances, medians, yerr=errors, fmt='o', color='b', ecolor='lightgray', elinewidth=3, capsize=0)
        # ax1.set_xlabel('Distance')
        # ax1.set_ylabel('Profile 1 Values', color='b')

        # if profile2_key:
        #     profile2_points = self.profiles[profile2_key]
        #     distances2, medians2, lowers2, uppers2 = process_points(profile2_points, sort_axis='x')
        #     errors2 = [upper - lower for upper, lower in zip(uppers2, lowers2)]

        #     ax2 = ax1.twinx()
        #     ax2.errorbar(distances2, medians2, yerr=errors2, fmt='o', color='r', ecolor='lightgray', elinewidth=3, capsize=0)
        #     ax2.set_ylabel('Profile 2 Values', color='r')

        #     # Set window title for comparison
        #     fig.suptitle(f'Comparison: {profile1_key[:-1]} vs {profile2_key[:-1]}')
        # else:
        #     # Set window title for single profile
        #     fig.suptitle(f'Profile {profile1_key[:-1]}')

        # fig.tight_layout(pad=0, h_pad=None, w_pad=None, rect=None)

        # # Embed the matplotlib plot in a QWidget
        # canvas = FigureCanvas(fig)
        # widget = QtWidgets.QWidget()
        # layout = QVBoxLayout(widget)
        # layout.addWidget(canvas)
        # widget.setLayout(layout)

        # # Remove current plot from the layout and add the new one
        # for i in reversed(range(self.widgetProfilePlot.layout().count())):
        #     self.widgetProfilePlot.layout().itemAt(i).widget().setParent(None)

        # self.widgetProfilePlot.layout().addWidget(widget)
        # widget.show()

    def reset_zoom(self, vb,histogram):
        vb.enableAutoRange()
        histogram.autoHistogramRange()

    # def plot_histogram(self, current_plot_df, plot_information, bin_width):
    #     select_histogram = plot_information['plot_name']
    #     array = current_plot_df['array'].values
    #     edges = np.arange(array.min(), array.max() + bin_width, bin_width)

    #     plot_exist = select_histogram in self.plot_widget_dict
    #     duplicate = plot_exist and len(self.plot_widget_dict[select_histogram]['view']) == 1 and self.plot_widget_dict[select_histogram]['view'][0] != self.canvasWindow.currentIndex()

    #     if plot_exist and not duplicate:
    #         widgetHistogram = self.plot_widget_dict[select_histogram]['widget'][0]
    #         histogram_plot = widgetHistogram.findChild(pg.PlotWidget)
    #         histogram_plot.clear()
    #         self.update_histogram(array, edges, histogram_plot)
    #     else:
    #         layout = QtWidgets.QVBoxLayout()
    #         widgetHistogram = QtWidgets.QWidget()
    #         widgetHistogram.setLayout(layout)
    #         view = self.canvasWindow.currentIndex()
    #         if duplicate:
    #             self.plot_widget_dict[select_histogram]['widget'].append(widgetHistogram)
    #             self.plot_widget_dict[select_histogram]['view'].append(view)
    #         else:
    #             self.plot_widget_dict[select_histogram] = {'widget': [widgetHistogram], 'info': plot_information, 'view': [view]}
    #         histogram_plot = pg.PlotWidget(title=select_histogram)
    #         self.update_histogram(array, edges, histogram_plot)
    #         layout.addWidget(histogram_plot)
    #         histogram_plot.setBackground('w')

    # def update_histogram(self, array, edges, histogram_plot):
    #     # Create a legend
    #     legend = pg.LegendItem(offset=(70, 30))  # Adjust offset as needed
    #     legend.setParentItem(histogram_plot.graphicsItem())  # Add legend to the histogram plot


    #     if 'algorithm' in self.current_group and self.current_group['algorithm'] in self.cluster_results:
    #         # Color the histogram based on clusters
    #         for cluster in self.current_group['clusters']:
    #             cluster_num = int(cluster.split()[1])  # Assuming cluster name format is "Cluster X"
    #             cluster_indices = np.where(self.cluster_results[self.current_group['algorithm']] == cluster_num)[0]
    #             cluster_data = array[cluster_indices]
    #             hist, _ = np.histogram(cluster_data.flatten(), bins=edges)
    #             # Adjust color with transparency (alpha)
    #             color = pg.intColor(cluster_num, alpha=80)  # Adjust alpha value (0-255) for transparency
    #             bar_graph_item = pg.BarGraphItem(x0=edges[:-1], x1=edges[1:], height=hist, brush=color)
    #             histogram_plot.addItem(bar_graph_item)
    #             # Add item to legend
    #             legend.addItem(bar_graph_item, f'Cluster {cluster_num}')
    #     else:
    #         # Regular histogram
    #         hist, _ = np.histogram(array.flatten(), bins=edges)
    #         bar_graph_item = pg.BarGraphItem(x0=edges[:-1], x1=edges[1:], height=hist, brush='b')
    #         histogram_plot.addItem(bar_graph_item)
    #     histogram_plot.setLabel('left', 'Frequency')
    #     histogram_plot.setLabel('bottom', 'Value')

    def plot_histogram(self, current_plot_df, plot_information, bin_width):

        mask = self.filter_mask & self.polygon_mask & current_plot_df['array'].notna()

        
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']
        array = current_plot_df['array'][mask].values
        edges = np.arange(array.min(), array.max() + bin_width, bin_width)
    
        plot_exist = plot_name in self.plot_widget_dict[plot_type][sample_id]
        duplicate = plot_exist and len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view']) == 1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()
    

        if plot_exist and not duplicate:
            widgetHistogram = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'][0]
            figure_canvas = widgetHistogram.findChild(FigureCanvas)
            figure_canvas.figure.clear()
            ax = figure_canvas.figure.subplots()
            self.update_histogram(array, edges, ax)
            figure_canvas.draw()
        else:
            figure = Figure()
            ax = figure.add_subplot(111)
            self.update_histogram(array, edges, ax)
            widgetHistogram = QtWidgets.QWidget()
            widgetHistogram.setLayout(QtWidgets.QVBoxLayout())
            figure_canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(figure_canvas, widgetHistogram)  # Create the toolbar for the canvas
            widgetHistogram.layout().addWidget(toolbar)  # Add the toolbar to the widget
            widgetHistogram.layout().addWidget(figure_canvas)
            view = self.canvasWindow.currentIndex()

            if duplicate:
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetHistogram)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)
            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget': [widgetHistogram], 'info': plot_information, 'view': [view]}
            

            # self.canvasWindow.setCurrentIndex(view)
            # Assuming you have a method to add the widget to the tab
            # self.add_histogram_tab(widgetHistogram, plot_name)

    def update_histogram(self, array, edges, ax):
        # Clear previous histogram
        ax.clear()
        # Check if the algorithm is in the current group and if results are available
        if 'algorithm' in self.current_group and self.current_group['algorithm'] in self.cluster_results:
            # Get the cluster labels for the data
            cluster_labels = self.cluster_results[self.current_group['algorithm']]
            clusters = cluster_labels.dropna().unique()


            # Plot histogram for all clusters
            for i in clusters:
                cluster_data = array[cluster_labels == i]
                # Create RGBA color with transparency by directly indexing the colormap
                # color = cmap(i)[:-1]  # Create a new RGBA tuple with alpha value
                color = self.goup_cmap[i][:-1] + (0.6,)
                ax.hist(cluster_data, bins=edges, color=color,edgecolor='black', linewidth=1.5, label=f'Cluster {i}', alpha=0.6)
        else:
            # Regular histogram
            ax.hist(array, bins=edges, color='blue', edgecolor='black', linewidth=1.5, label='Data')
        # Add a legend
        ax.legend()

        # Set labels
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')

    def tern2xy(self, a, b, c):
        w = 0.5
        h = 0.5 / np.tan(np.pi/6)
        s = a + b + c
        a = a / s
        b = b / s
        c = c / s
        y = a * h
        x = (1 - b) * h / np.cos(np.pi/6) - y * np.tan(np.pi/6) - w
        return x, y


    def get_scatter_values(self):
        value_dict = {
            'x': {'elements': None, 'type': None, 'array': None},
            'y': {'elements': None, 'type': None, 'array': None},
            'z': {'elements': None, 'type': None, 'array': None},
            'c': {'elements': None, 'type': None, 'array': None}
        }
        value_dict['x']['elements'] = self.comboBoxScatterIsotopeX.currentText()
        value_dict['x']['type'] = self.comboBoxScatterSelectX.currentText().lower()
        value_dict['y']['elements'] = self.comboBoxScatterIsotopeY.currentText()
        value_dict['y']['type'] = self.comboBoxScatterSelectY.currentText().lower()
        value_dict['z']['elements'] = self.comboBoxScatterIsotopeZ.currentText()
        value_dict['z']['type'] = self.comboBoxScatterSelectZ.currentText().lower()
        value_dict['c']['elements'] = self.comboBoxScatterIsotopeC.currentText()
        value_dict['c']['type'] = self.comboBoxScatterSelectC.currentText().lower()

        for k, v in value_dict.items():
            if v['type'] == 'isotope' and v['elements']:
                df = self.get_map_data(self.sample_id, v['elements'], plot_type=None, plot=False)
            elif v['type'] == 'ratio' and '/' in v['elements']:
                isotope_1, isotope_2 = v['elements'].split('/')
                df = self.get_map_data(self.sample_id, isotope_1, isotope_2, plot_type=None, plot=False)
            else:
                df = pd.DataFrame({'array': []})  # Or however you want to handle this case

            value_dict[k]['array'] = df['array'][self.filter_mask].values if not df.empty else []

        return value_dict['x'], value_dict['y'], value_dict['z'], value_dict['c']





    def plot_scatter(self):

        x, y, z, c = self.get_scatter_values()
        df = pd.DataFrame({
            x['elements']: x['array'],
            y['elements']: y['array'],
            z['elements']: z['array']
        })
        el_list  = df.columns
        el_list_lower = [re.sub(r'\d', '', el).lower() for el in el_list]
        df.columns = el_list_lower



        ref_data_chem = self.ref_data.iloc[self.comboBoxNDimRefMaterial.currentIndex()]
        ref_data_chem.index = [col.replace('_ppm', '') for col in ref_data_chem.index]
        ref_series = ref_data_chem[el_list_lower].squeeze()
        df = df.div(ref_series, axis= 1)

        df = df.dropna(axis = 0).astype('int64')

        x['array'], y['array'], z['array'] = df.iloc[:, 0].values, df.iloc[:, 1].values, df.iloc[:, 2].values



        plot_type =  self.comboBoxScatterType.currentText().lower()
        cmap = matplotlib.colormaps.get_cmap(self.comboBoxCM.currentText())

        if len(z['array'])>0 and len(c['array'])>0:  # 3d scatter plot with color

            labels = [x['elements'], y['elements'], z['elements']]

            ternary_plot = ternary(labels,plot_type,mul_axis=True )
            fig = ternary_plot.fig



            if plot_type =='scatter':
                ternary_plot.ternscatter(x['array'], y['array'], z['array'], categories=  c['array'], cmap=cmap, orientation = self.comboBoxCBP.currentText().lower())

            else:
                ternary_plot.ternhex(x['array'], y['array'], z['array'], val= c['array'],n=int(self.spinBoxScatterN.value()), cmap = cmap, orientation = self.comboBoxCBP.currentText().lower())


            select_scatter = f"{x['elements']}_{y['elements']}_{z['elements']}_{c['elements']}_scatter"
        elif len(z['array'])>0:  # Ternary plot

            labels = [x['elements'], y['elements'], z['elements']]
            ternary_plot = ternary(labels,plot_type)
            fig = ternary_plot.fig
            if plot_type =='scatter':
                if self.current_group['algorithm'] in self.cluster_results:
                    cluster_labels = self.cluster_results[self.current_group['algorithm']]
                    ternary_plot.ternscatter(x['array'], y['array'], z['array'], categories=cluster_labels, cmap=self.group_cmap, labels = True, orientation = self.comboBoxCBP.currentText().lower())
                else:
                    ternary_plot.ternscatter(x['array'], y['array'], z['array'],cmap= cmap)
            else:
                ternary_plot.ternhex(x['array'], y['array'], z['array'],n=int(self.spinBoxScatterN.value()), color_map = cmap, orientation = self.comboBoxCBP.currentText().lower())
            fig.subplots_adjust(left=0.05, right=1)
            select_scatter = f"{x['elements']}_{y['elements']}_{z['elements']}_scatter"
            # fig.tight_layout()
        else:  # 2d scatter plot
            fig = Figure()
            ax = fig.add_subplot(111)
            ax.scatter(x['array'], y['array'], alpha=0.5)
            select_scatter = f"{x['elements']}_{y['elements']}_scatter"

        plot_information = {
            'plot_name': select_scatter,
            'sample_id': self.sample_id,
            'plot_type': 'scatter'
        }

        # Create a Matplotlib figure and axis

        widgetScatter = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widgetScatter.setLayout(layout)
        # scatter_plot = pg.PlotWidget(title=select_scatter)
        scatter_plot = FigureCanvas(fig)
        view = self.canvasWindow.currentIndex()
        # Add the plot widget to your layout
        layout.insertWidget(0,scatter_plot)
        toolbar = NavigationToolbar(scatter_plot)  # Create the toolbar for the canvas
        # widgetScatter.layout().addWidget(toolbar)

        self.plot_widget_dict['scatter'][self.sample_id][select_scatter] = {'widget':[widgetScatter],

                                               'info':plot_information, 'view':[view]}
        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'Scatter')
        self.add_plot(plot_information)




    def plot_clustering(self):
        df_filtered, mask, isotopes = self.get_processed_data()
        filtered_array =df_filtered.values
        # filtered_array = df_filtered.dropna(axis=0, how='any').values


        n_clusters = self.spinBoxNClusters.value()
        exponent = float(self.horizontalSliderExponent.value()) / 10
        if exponent == 1:
            exponent = 1.0001
        distance_type = self.comboBoxClusterDistance.currentText()
        fuzzy_cluster_number = self.spinBoxFCView.value()


        if self.radioButtonClusterAll.isChecked():
            # clustering_algorithms = {
            #     'KMeans': KMeans(n_clusters=n_clusters, init='k-means++'),
            #     'KMedoids': KMedoids(n_clusters=n_clusters, metric=distance_type),  # Assuming implementation
            #     'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            # }

            # Process for all clustering methods
            clustering_algorithms = {
                'KMeans': KMeans(n_clusters=n_clusters, init='k-means++'),
                'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            }
        elif self.radioButtonKMeans.isChecked():
            clustering_algorithms = {
                'KMeans': KMeans(n_clusters=n_clusters, init='k-means++')
                }
        elif self.radioButtonKMedoids.isChecked():
            clustering_algorithms = {
                'KMedoids': KMedoids(n_clusters=n_clusters, metric=distance_type)  # Placeholder for fuzzy
            }

        elif self.radioButtonFuzzy.isChecked():
            clustering_algorithms = {
                'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            }


        self.process_clustering_methods( n_clusters, exponent, distance_type,fuzzy_cluster_number,  filtered_array,clustering_algorithms, mask, )
 
    
    def process_clustering_methods(self, n_clusters, exponent, distance_type, fuzzy_cluster_number, filtered_array, clustering_algorithms, mask):
        #create unique id if new plot
        plot_type = 'clustering'
        if self.sample_id in self.plot_id[plot_type]:
            self.plot_id[plot_type][self.sample_id]  = self.plot_id[plot_type][self.sample_id]+1
        else:
            self.plot_id[plot_type][self.sample_id]  = 0
            
        plot_name =  plot_type+str(self.plot_id[plot_type][self.sample_id])
        
        # Create figure 

        fig = Figure(figsize=(6, 4))
        # Adjust subplot parameters here for better alignment

        for i, (name, clustering) in enumerate(clustering_algorithms.items()):
            subplot_num = int('1'+str(len(clustering_algorithms))+str(i+1))
            #if len(clustering_algorithms) ==1:
                # Adjust the left and right margins
                # fig.subplots_adjust(left=0, right=1)

            ax = fig.add_subplot(subplot_num)
            if name == 'Fuzzy':
                cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(filtered_array.T, n_clusters, exponent, error=0.00001, maxiter=1000,seed =23)
                # cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.005, maxiter=1000,seed =23)
                for n in range(n_clusters):
                    self.fuzzy_results[n] = u[n-1,:]
                    if fuzzy_cluster_number>0:
                        labels = self.fuzzy_results[fuzzy_cluster_number]
                    else:
                        labels = np.argmax(u, axis=0)
                        self.cluster_results[name][mask] = ['Cluster '+str(c) for c in labels]
            else:
                model = clustering.fit(filtered_array)
                labels = model.predict(filtered_array)
                self.cluster_results[name][mask] = ['Cluster '+str(c) for c in labels]
            # Plot each clustering result
            self.plot_clustering_result(ax, labels, name, fuzzy_cluster_number)
            
            
        # Create and add the widget to layout
        self.add_clustering_widget_to_layout(fig,plot_name, plot_type)
        

    def plot_clustering_result(self, ax, labels, method_name, fuzzy_cluster_number):
        reshaped_array = np.reshape(labels, (self.clipped_isotope_data[self.sample_id]['X'].nunique(), self.clipped_isotope_data[self.sample_id]['Y'].nunique()))

        x_range = self.clipped_isotope_data[self.sample_id]['X'].max() -  self.clipped_isotope_data[self.sample_id]['X'].min()
        y_range = self.clipped_isotope_data[self.sample_id]['Y'].max() -  self.clipped_isotope_data[self.sample_id]['Y'].min()
        aspect_ratio =  (y_range/self.clipped_isotope_data[self.sample_id]['Y'].nunique())/ (x_range/self.clipped_isotope_data[self.sample_id]['X'].nunique())
        # aspect_ratio  = 1
        # aspect_ratio = 0.617
        fig = ax.figure
        if method_name == 'Fuzzy' and fuzzy_cluster_number>0:
            cmap = plt.get_cmap(self.comboBoxCM.currentText())
            # img = ax.imshow(reshaped_array.T, cmap=cmap,  aspect=aspect_ratio)
            img = ax.imshow(reshaped_array.T, cmap=cmap,  aspect=aspect_ratio)
            fig.colorbar(img, ax=ax, orientation = self.comboBoxCBP.currentText().lower())
        else:
            unique_labels = np.unique(['Cluster '+str(c) for c in labels])
            unique_labels.sort()
            n_clusters = len(unique_labels)
            cmap = plt.get_cmap(self.comboBoxCMG.currentText(), n_clusters)
            # Extract colors from the colormap
            colors = [cmap(i) for i in range(cmap.N)]
            # Assign these colors to self.group_cmap
            for label, color in zip(unique_labels, colors):
                self.group_cmap[label] = color

            boundaries = np.arange(-0.5, n_clusters, 1)
            norm = BoundaryNorm(boundaries, cmap.N, clip=True)
            img = ax.imshow(reshaped_array.T.astype('float'), cmap=cmap, norm=norm, aspect = aspect_ratio)
            fig.colorbar(img, ax=ax, ticks=np.arange(0, n_clusters), orientation = self.comboBoxCBP.currentText().lower())

        fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
        fig.tight_layout()
        # fig.canvas.manager.window.move(0,0)
        ax.set_title(f'{method_name} Clustering')
        ax.set_axis_off()
 
    def add_clustering_widget_to_layout(self, fig,plot_name, plot_type):

        

        widgetClusterMap = QtWidgets.QWidget()
        widgetClusterMap.setLayout(QtWidgets.QVBoxLayout())
        figure_canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(figure_canvas)  # Create the toolbar for the canvas
        widgetClusterMap.setObjectName('plotClusterMap')
        widgetClusterMap.layout().addWidget(figure_canvas)
        # widgetClusterMap.layout().addWidget(toolbar)
        self.plot_widget_dict['clustering'][self.sample_id][plot_name] = {'widget': [widgetClusterMap],
                                                              'info': {'plot_type': plot_type, 'sample_id': self.sample_id},
                                                              'view': [self.canvasWindow.currentIndex()]}
        plot_information = {
            'plot_name': plot_name,
            'sample_id': self.sample_id,
            'plot_type': plot_type
        }
        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'Clustering')
        self.add_plot(plot_information)
        
    def update_plot_with_new_colormap(self):
        if self.fig and self.clustering_results:
            for name, results in self.clustering_results.items():
                labels = results['labels']
                method_name = results['method_name']
                fuzzy_cluster_number = results['fuzzy_cluster_number']
                # Find the corresponding axis to update
                ax_index = list(self.clustering_results.keys()).index(name)
                ax = self.axs[ax_index]
                # Redraw the plot with the new colormap on the existing axis
                self.plot_clustering_result(ax, labels, method_name, fuzzy_cluster_number)
            
            # Redraw the figure canvas to reflect the updates
            self.fig.canvas.draw_idle()
        

    def update_cluster_ui(self):
        if self.radioButtonKMeans.isChecked():
            # Enable parameters relevant to KMeans
            self.spinBoxNClusters.setEnabled(True)
            self.horizontalSliderExponent.setEnabled(False)  # Not used in KMeans
            self.comboBoxClusterDistance.setEnabled(False)  # Not used in KMeans
            self.spinBoxFCView.setEnabled(False)

            self.labelExponent.setEnabled(False)
            self.labelNClusters.setEnabled(True)
            self.labelExponen.setEnabled(False)
            self.labelClusterDistance.setEnabled(False)
            self.labelFCView.setEnabled(False)

        elif self.radioButtonKMedoids.isChecked():
            # Enable parameters relevant to KMedoids
            self.spinBoxNClusters.setEnabled(True)
            self.horizontalSliderExponent.setEnabled(False)  # Not used in KMedoids
            self.comboBoxClusterDistance.setEnabled(True)  # Distance metric is relevant
            self.spinBoxFCView.setEnabled(False)

            self.labelExponent.setEnabled(False)
            self.labelNClusters.setEnabled(True)
            self.labelExponen.setEnabled(False)
            self.labelClusterDistance.setEnabled(True)
            self.labelFCView.setEnabled(False)

        elif self.radioButtonFuzzy.isChecked():
            # Enable parameters relevant to Fuzzy Clustering
            self.spinBoxNClusters.setEnabled(True)
            self.horizontalSliderExponent.setEnabled(True)  # Exponent is relevant
            self.comboBoxClusterDistance.setEnabled(False)  # Distance metric may not be relevant, depending on implementation
            self.spinBoxFCView.setEnabled(True)

            self.labelNClusters.setEnabled(True)
            self.labelExponen.setEnabled(True)
            self.labelExponent.setEnabled(True)
            self.labelClusterDistance.setEnabled(False)
            self.labelFCView.setEnabled(True)


        elif self.radioButtonClusterAll.isChecked():
            # Enable parameters relevant to Fuzzy Clustering
            self.spinBoxNClusters.setEnabled(True)
            self.horizontalSliderExponent.setEnabled(True)  # Exponent is relevant
            self.comboBoxClusterDistance.setEnabled(True)  # Distance metric may not be relevant, depending on implementation
            self.spinBoxFCView.setEnabled(True)

            self.labelNClusters.setEnabled(True)
            self.labelExponen.setEnabled(True)
            self.labelExponent.setEnabled(True)
            self.labelClusterDistance.setEnabled(True)
            self.labelFCView.setEnabled(True)
        
    
    def get_processed_data(self):
        # return normalised, filtered data with that will be used for analysis
        use_isotopes = self.isotopes_df.loc[(self.isotopes_df['use']==True) & (self.isotopes_df['sample_id']==self.sample_id), 'isotopes'].values
        # Combine the two masks to create a final mask
        nan_mask = self.processed_isotope_data[self.sample_id][use_isotopes].notna().all(axis=1) 
        mask = self.filter_mask & self.polygon_mask  & nan_mask & self.axis_mask
        
        df_filtered = self.processed_isotope_data[self.sample_id][use_isotopes][mask]

        return df_filtered, mask, use_isotopes
        

    def plot_n_dim(self):

        
        df_filtered, mask,_  = self.get_processed_data()
        
        

        ref_i = self.comboBoxNDimRefMaterial.currentIndex()


        q = self.dialNDimQ.value()
        quantiles = [0.25, 0.5, 0.75]
        if q== '1':
            quantiles = 0.5
        elif q=='2':
            quantiles = [0.25, 0.75]
        elif q=='3':
            quantiles = [0.25, 0.5, 0.75]
        elif q=='4':
            quantiles = [0.05, 0.25, 0.5, 0.75, 0.95]



        if self.comboBoxNDimPlotType.currentText() == 'Radar':
            axes_interval = 5
            if self.current_group['algorithm'] in self.cluster_results:
                # Get the cluster labels for the data

                cluster_labels = self.cluster_results[self.current_group['algorithm']]
                df_filtered['clusters'] = cluster_labels[mask]

                radar = Radar(df_filtered, fields = self.n_dim_list, quantiles=quantiles, axes_interval = axes_interval, group_field ='clusters', groups = np.unique(cluster_labels.dropna()))

                fig,ax = radar.plot(cmap = self.group_cmap)
                ax.legend()
            else:
                radar = Radar(df_filtered, fields = self.n_dim_list, quantiles=quantiles, axes_interval = axes_interval, group_field ='', groups = None)

                fig,ax = radar.plot()
        else: #tec plot
            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            yl = [np.inf, -np.inf]
            if self.current_group['algorithm'] in self.cluster_results:
                # Get the cluster labels for the data
                cluster_labels = self.cluster_results[self.current_group['algorithm']]
                df_filtered['clusters'] = cluster_labels[mask]
                clusters = np.unique(cluster_labels)

                # Plot tec for all clusters
                for i in clusters:
                    # Create RGBA color
                    color = self.group_cmap[i][:-1]
                    ax,yl_tmp = plot_spider_norm(data = df_filtered.loc[df_filtered['clusters']==i,:],
                            ref_data = self.ref_data, norm_ref_data =  self.ref_data['model'][ref_i],
                            layer = self.ref_data['layer'][ref_i], el_list = self.n_dim_list ,
                            style = 'Quanta',quantiles = quantiles, ax = ax, c = color, label=f'{i}')
                    #store max y limit to convert the set y limit of axis
                    yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                ax.legend()
                self.logax(ax, yl, 'y')
                ax.set_ylim(yl)
            else:
                ax,yl = plot_spider_norm(data = df_filtered, ref_data = self.ref_data, norm_ref_data =  self.ref_data['model'][ref_i], layer = self.ref_data['layer'][ref_i], el_list = self.n_dim_list ,style = 'Quanta', ax = ax)
            ax.set_ylabel('Abundance / ['+self.ref_data['model'][ref_i]+', '+self.ref_data['layer'][ref_i]+']')
            fig.tight_layout()
        widgetNDim = QtWidgets.QWidget()
        widgetNDim.setLayout(QtWidgets.QVBoxLayout())
        figure_canvas = FigureCanvas(fig)

        widgetNDim.setObjectName('plotNDim')
        widgetNDim.layout().addWidget(figure_canvas)

        
        plot_type = 'n-dim'
        #create unique id if new plot
        if self.sample_id in self.plot_id[plot_type]:
            self.plot_id[plot_type][self.sample_id]  = self.plot_id[plot_type][self.sample_id]+1
        else:
            self.plot_id[plot_type][self.sample_id]  = 0  
        plot_name =  plot_type+str(self.plot_id[plot_type][self.sample_id])
        

        toolbar = NavigationToolbar(figure_canvas)  # Create the toolbar for the canvas
        # widgetNDim.layout().addWidget(toolbar)
        self.plot_widget_dict[plot_type][self.sample_id][plot_name] = {'widget': [widgetNDim],
                                                              'info': {'plot_type': plot_type, 'sample_id': self.sample_id},
                                                              'view': [self.canvasWindow.currentIndex()]}
        plot_information = {
            'plot_name': self.sample_id +f'_{plot_type}',
            'sample_id': self.sample_id,
            'plot_type': plot_type
        }
        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'n-Dim')
        self.add_plot(plot_information)

    def update_n_dim_table(self):

        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.filter_df.at[row, 'use'] = state == QtCore.Qt.Checked


        isotope_1 = self.comboBoxNDimIsotope.currentText()

        # isotope_select =self.comboBoxNDimSelect.currentText()

        isotope_set =self.comboBoxNDimIsotopeSet.currentText().lower()

        if isotope_set == 'user defined':
            el_list= [isotope_1]
        elif isotope_set == 'majors':
            el_list = ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P']
        elif isotope_set == 'full trace':
            el_list = ['Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb','Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li','Ti','Gd','Dy','Ho','Y','Er','Yb','Lu']
        elif isotope_set == 'ree':
            el_list = ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu']
        elif isotope_set == 'metals':
            el_list = ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr'];

        isotopes_list = self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id), 'isotopes'].values






        isotopes = [col for iso in el_list for col in isotopes_list if re.sub(r'\d', '', col).lower() == iso.lower()]

        self.n_dim_list.extend(isotopes)

        for isotope in isotopes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QtWidgets.QCheckBox()
            chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                QtCore.Qt.ItemIsEnabled)

            chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope)].iloc[0]['norm']



            self.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetNDim.setItem(row, 1,
                                     QtWidgets.QTableWidgetItem(self.sample_id))
            self.tableWidgetNDim.setItem(row, 2,
                                     QtWidgets.QTableWidgetItem(isotope))

            self.tableWidgetNDim.setItem(row, 3,
                                     QtWidgets.QTableWidgetItem(norm))
            self.tableWidgetNDim.setItem(row, 4,
                                     chkBoxItem_select)

    def logax(self,ax, lim, axis='y', label='', tick_label_rotation=0):
        """
        Produces log-axes limits and labels.

        Parameters:
        ax (matplotlib.axes.Axes): The axes to modify.
        lim (list): The log10 values of the axes limits.
        axis (str): 'x' or 'y' to add ticks to x- or y-axis, default is 'y'.
        label (str): Label for the axis.
        tick_label_rotation (float): Angle of text rotation, default is 0.
        """
        # Create tick marks and labels
        mt = np.log10(np.arange(1, 10))
        ticks = []
        tick_labels = []
        for i in range(int(lim[0]), int(lim[1]) + 1):
            ticks.extend([i + m for m in mt])
            tick_labels.extend([f'$10^{i}$'] + [''] * (len(mt) - 1))

        # Apply settings based on the axis
        if axis.lower() == 'x':
            ax.set_xticks(ticks)
            ax.set_xticklabels(tick_labels, rotation=tick_label_rotation)
            ax.set_xlim([10**lim[0], 10**lim[1]])
            if label:
                ax.set_xlabel(label)
        elif axis.lower() == 'y':
            ax.set_yticks(ticks)
            ax.set_yticklabels(tick_labels, rotation=tick_label_rotation)
            ax.set_ylim([10**lim[0], 10**lim[1]])
            if label:
                ax.set_ylabel(label)
        else:
            print('Incorrect axis argument. Please use "x" or "y".')



    def onRadioButtonToggled(self):
        # Clear the list widget
        self.tableWidgetViewGroups.clear()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Groups'])
        algorithm = ''
        # Check which radio button is checked and update the list widget
        if self.radioButtonCNone.isChecked():
            pass  # No clusters to display for 'None'
        elif self.radioButtonCFuzzy.isChecked():
            algorithm = 'Fuzzy'
        elif self.radioButtonCKMediods.isChecked():
            algorithm = 'KMediods'
        elif self.radioButtonCKMeans.isChecked():
            algorithm = 'KMeans'

        if algorithm in self.cluster_results:
            if not self.cluster_results[algorithm].empty:
                clusters = self.cluster_results[algorithm].dropna().unique()
                clusters.sort()
                self.tableWidgetViewGroups.setRowCount(len(clusters))

                for i, c in enumerate(clusters):
                    # item = QTableWidgetItem(str(c))
                    # Initialize the flag
                    self.isUpdatingTable = True
                    self.tableWidgetViewGroups.setItem(i, 0, QTableWidgetItem(c))
                    self.tableWidgetViewGroups.item(i, 0).setSelected(True)
                self.current_group = {'algorithm':algorithm,'clusters': clusters}


        else:
            self.current_group = {'algorithm':None,'clusters': None}
        self.isUpdatingTable = False

    def onClusterLabelChanged(self, item):
        # Initialize the flag
        if not self.isUpdatingTable: #change name only when cluster renamed
            # Get the new name and the row of the changed item
            new_name = item.text()
            row = item.row()
            print(new_name)
            # Extract the cluster id (assuming it's stored in the table)
            cluster_id = self.current_group['clusters'][row]

            # Check for duplicate names
            for i in range(self.tableWidgetViewGroups.rowCount()):
                if i != row and self.tableWidgetViewGroups.item(i, 0).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(cluster_id)
                    print("Duplicate name not allowed.")
                    return

            # Update self.cluster_results with the new name
            if self.current_group['algorithm'] in self.cluster_results:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.cluster_results[self.current_group['algorithm']] == cluster_id

                # Update these rows with the new name
                self.cluster_results.loc[rows_to_update, self.current_group['algorithm']] = new_name
                self.group_cmap[new_name] = self.group_cmap[cluster_id]
                del self.group_cmap[cluster_id]
            # Optionally, update current_group to reflect the new cluster name
            self.current_group['clusters'][row] = new_name

    def outlier_detection(self, data ,lq = 0.0005, uq = 99.5,d_lq =9.95 , d_uq = 99):
        # Ensure data is a numpy array
        data = np.array(data)

        # Shift values to positive concentrations
        v0 = np.nanmin(data, axis=0) - 0.001
        data_shifted = np.log10(data - v0)

        # Calculate required quantiles and differences
        lq_val = np.nanpercentile(data_shifted, lq, axis=0)
        uq_val = np.nanpercentile(data_shifted, uq, axis=0)
        sorted_indices = np.argsort(data_shifted, axis=0)
        sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)


        diff_sorted_data = np.diff(sorted_data, axis=0)
        # Adding a 0 to the beginning of each column to account for the reduction in size by np.diff
        diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
        diff_array_uq_val = np.nanpercentile(diff_sorted_data, d_uq, axis=0)
        diff_array_lq_val = np.nanpercentile(diff_sorted_data, d_lq, axis=0)
        upper_cond = (sorted_data > uq_val) & (diff_sorted_data > diff_array_uq_val)

        # Initialize arrays for results
        clipped_data = np.copy(sorted_data)

        # Upper bound outlier filter
        for col in range(sorted_data.shape[1]):
            up_indices = np.where(upper_cond[:, col])[0]
            if len(up_indices) > 0:
                uq_outlier_index = up_indices[0]
                clipped_data[uq_outlier_index:, col] = clipped_data[uq_outlier_index-1, col]

        lower_cond = (sorted_data < lq_val) & (diff_sorted_data > diff_array_lq_val)
        # Lower bound outlier filter
        for col in range(sorted_data.shape[1]):
            low_indices = np.where(lower_cond[:, col])[0]
            if len(low_indices) > 0:
                lq_outlier_index = low_indices[-1]
                clipped_data[:lq_outlier_index+1, col] = clipped_data[lq_outlier_index+1, col]

        clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
        # Unshift the data
        clipped_data = 10**clipped_data + v0

        return clipped_data

    def transform_plots(self, array):
        min_val = np.nanmin(array)-0.0001
        max_val = np.nanmax(array)

        if min_val < 0:
            t_array = (max_val * (array - min_val)) / (max_val - min_val)
        else:
            t_array = np.copy(array)
        return t_array


    def add_ree(self, sample_df):

        lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']
        hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']
        mree = ['sm', 'eu', 'gd']

        # Convert column names to lowercase and filter based on lree, hree, etc. lists
        lree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in lree])]
        hree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in hree])]
        mree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in mree])]
        ree_cols = lree_cols + hree_cols

        # Sum up the values for each row
        sample_df['LREE'] = sample_df[lree_cols].sum(axis=1)
        sample_df['HREE'] = sample_df[hree_cols].sum(axis=1)
        sample_df['MREE'] = sample_df[mree_cols].sum(axis=1)
        sample_df['REE'] = sample_df[ree_cols].sum(axis=1)

        return sample_df


    def change_sample(self, index):

        file_path = os.path.join(self.selected_directory, self.csv_files[index])
        self.sample_id = os.path.splitext(self.csv_files[index])[0]

        # print(self.self.sample_id)
        if self.sample_id == 'TR1-07':
            self.aspect_ratio = 0.976
        elif self.sample_id == 'TR3-06':
            self.aspect_ratio = 0.874
        elif self.sample_id == 'WOS-02':
            self.aspect_ratio = 0.873


        if self.sample_id not in self.sample_data_dict:
            self.update_spinboxes_bool = False #prevent update plot from runing
            sample_df = pd.read_csv(file_path, engine='c')
            sample_df  = sample_df.loc[:, ~sample_df .columns.str.contains('^Unnamed')]
            # self.sample_data_dict[self.sample_id] = pd.read_csv(file_path, engine='c')
            self.sample_data_dict[self.sample_id] = self.add_ree(sample_df)
            self.selected_isotopes = list(self.sample_data_dict[self.sample_id].columns[5:])
            isotopes = pd.DataFrame()
            isotopes['isotopes']=list(self.selected_isotopes)
            isotopes['sample_id'] = self.sample_id
            isotopes['norm'] = 'linear'
            x_max = self.sample_data_dict[self.sample_id]['X'].max()
            x_min = self.sample_data_dict[self.sample_id]['X'].min()
            y_max = self.sample_data_dict[self.sample_id]['Y'].max()
            y_min = self.sample_data_dict[self.sample_id]['Y'].min()
            isotopes['x_max'] = x_max
            isotopes['x_min'] = x_min
            isotopes['y_max'] = y_max
            isotopes['y_min'] = y_min
            isotopes['upper_bound'] = 99.5
            isotopes['lower_bound'] = 0.05
            isotopes['d_l_bound'] = 99
            isotopes['d_u_bound'] = 99
            isotope_data = self.sample_data_dict[self.sample_id][self.selected_isotopes].values
            clipped_data = self.outlier_detection(isotope_data)

            self.clipped_isotope_data[self.sample_id] = pd.DataFrame(clipped_data, columns = self.selected_isotopes).apply(self.transform_plots)
            self.clipped_isotope_data[self.sample_id]['X'] = self.sample_data_dict[self.sample_id]['X']
            self.clipped_isotope_data[self.sample_id]['Y'] = self.sample_data_dict[self.sample_id]['Y']
            self.cluster_results=pd.DataFrame(columns = ['Fuzzy', 'KMeans', 'KMediods'])
            self.cluster_results['X'] = self.sample_data_dict[self.sample_id]['X']
            self.cluster_results['Y'] = self.sample_data_dict[self.sample_id]['Y']
            self.processed_isotope_data = self.clipped_isotope_data.copy()
            isotopes['v_min'] = np.min(clipped_data, axis=0)
            isotopes['v_max'] = np.max(clipped_data, axis=0)
            isotopes['auto_scale'] = True
            isotopes['use'] = True
            # print(isotopes)
            # isotopes = add_ree(isotopes)
            self.isotopes_df = pd.concat([self.isotopes_df, isotopes])
            
            # add sample_id to self.plot_widget_dict
            for plot_type in self.plot_widget_dict.keys():
                if self.sample_id not in self.plot_widget_dict[plot_type]:
                    self.plot_widget_dict[plot_type][self.sample_id]={}

            # set mask of size of isotope array
            self.filter_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'].values, dtype=bool)
            self.polygon_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'], dtype=bool)
            self.axis_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'], dtype=bool)


            self.comboBoxFIsotope.clear()
            self.comboBoxNDimIsotope.clear()
            # self.comboBoxFIsotope_2.clear()
            self.comboBoxFIsotope.addItems(isotopes['isotopes'])
            self.update_filter_values()
            self.comboBoxScatterIsotopeX.clear()
            self.comboBoxScatterIsotopeX.addItems(isotopes['isotopes'])
            self.comboBoxScatterIsotopeY.clear()
            self.comboBoxScatterIsotopeY.addItems(isotopes['isotopes'])

            self.comboBoxNDimIsotope.addItems(isotopes['isotopes'])

            self.comboBoxScatterIsotopeZ.clear()
            self.comboBoxScatterIsotopeZ.addItem('')
            self.comboBoxScatterIsotopeZ.addItems(isotopes['isotopes'])
            self.comboBoxScatterIsotopeC.clear()
            self.comboBoxScatterIsotopeC.addItem('')
            self.comboBoxScatterIsotopeC.addItems(isotopes['isotopes'])

            self.spinBoxX.setMaximum(int(x_max))
            self.spinBoxX.setMinimum(int(x_min))
            self.spinBox_X.setMaximum(int(x_max))
            self.spinBox_X.setMinimum(int(x_min))
            self.spinBoxY.setMaximum(int(y_max))
            self.spinBoxY.setMinimum(int(y_min))
            self.spinBox_Y.setMaximum(int(y_max))
            self.spinBox_Y.setMinimum(int(y_min))

            # self.checkBoxViewRatio.setChecked(False)
            self.get_map_data(self.sample_id,isotope_1=None, isotope_2=None)
            self.create_tree(self.sample_id)
            self.clear_views()
            self.update_tree(self.selected_isotopes)

            self.update_spinboxes_bool = True  # Place this line at end of method



    def update_combo_boxes(self, axis):

        isotopes = self.isotopes_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotopes']
        ratios = self.ratios_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotope_1'] + ' / ' + self.ratios_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotope_2']


        if axis == 'x':
            if self.comboBoxScatterSelectX.currentText().lower() =='isotope':
                self.comboBoxScatterIsotopeX.clear()
                self.comboBoxScatterIsotopeX.addItems(isotopes)
            else:
                self.comboBoxScatterIsotopeX.clear()
                self.comboBoxScatterIsotopeX.addItems(ratios)
        elif axis == 'y':
            if self.comboBoxScatterSelectY.currentText().lower() =='isotope':
                self.comboBoxScatterIsotopeY.clear()
                self.comboBoxScatterIsotopeY.addItems(isotopes)
            else:
                self.comboBoxScatterIsotopeY.clear()
                self.comboBoxScatterIsotopeY.addItems(ratios)
        elif axis == 'z':
            if self.comboBoxScatterSelectZ.currentText().lower() =='isotope':
                self.comboBoxScatterIsotopeZ.clear()
                self.comboBoxScatterIsotopeZ.addItem('')
                self.comboBoxScatterIsotopeZ.addItems(isotopes)
            else:
                self.comboBoxScatterIsotopeZ.clear()
                self.comboBoxScatterIsotopeZ.addItem('')
                self.comboBoxScatterIsotopeZ.addItems(ratios)
        elif axis =='c':
            if self.comboBoxScatterSelectC.currentText().lower() =='isotope':
                self.comboBoxScatterIsotopeC.clear()
                self.comboBoxScatterIsotopeC.addItem('')
                self.comboBoxScatterIsotopeC.addItems(isotopes)
            else:
                self.comboBoxScatterIsotopeC.clear()
                self.comboBoxScatterIsotopeC.addItem('')
                self.comboBoxScatterIsotopeC.addItems(ratios)

        elif axis =='f':
            if self.comboBoxFSelect.currentText().lower() =='isotope':
                self.comboBoxFIsotope.clear()
                self.comboBoxFIsotope.addItems(isotopes)
            else:
                self.comboBoxFIsotope.clear()
                self.comboBoxFIsotope.addItems(ratios)



        # self.comboBoxIsotope_1.clear()
        # self.comboBoxIsotope_2.clear()
        # self.comboBoxFIsotope.clear()
        # # self.comboBoxFIsotope_2.clear()
        # self.comboBoxIsotope_1.addItems(isotopes['isotopes'])
        # self.comboBoxIsotope_2.addItems(isotopes['isotopes'])
        # self.comboBoxFIsotope.addItems(isotopes['isotopes'])
        # self.comboBoxFIsotope_2.addItem('')
        # self.comboBoxFIsotope_2.addItems(isotopes['isotopes'])


        # self.comboBoxScatterIsotopeX
        # comboBoxScatterSelectX

    def update_spinboxes(self,parameters,bins,bin_width, auto_scale):
        if self.canvasWindow.currentIndex()==0:
            self.update_spinboxes_bool = False

            self.spinBoxX.setValue(int(parameters['x_max']))

            self.checkBoxAutoScale.setChecked(auto_scale)
            if auto_scale:
                self.doubleSpinBoxDUB.setEnabled(True)
                self.doubleSpinBoxDLB.setEnabled(True)
            else:
                self.doubleSpinBoxDUB.setEnabled(False)
                self.doubleSpinBoxDLB.setEnabled(False)
            # self.spinBox_X.setMinimum(int(parameters['x_max']))
            # self.spinBox_X.setMaximum(int(parameters['x_min']))
            self.spinBox_X.setValue(int(parameters['x_min']))

            # self.spinBoxY.setMaximum(int(parameters['y_max']))
            # self.spinBoxY.setMinimum(int(parameters['y_min']))
            self.spinBoxY.setValue(int(parameters['y_max']))


            # self.spinBox_Y.setMaximum(int(parameters['y_max']))
            # self.spinBox_Y.setMinimum(int(parameters['y_min']))
            self.spinBox_Y.setValue(int(parameters['y_min']))

            self.doubleSpinBoxUB.setValue(parameters['upper_bound'])
            self.doubleSpinBoxLB.setValue(parameters['lower_bound'])
            self.doubleSpinBoxDLB.setValue(parameters['d_l_bound'])
            self.doubleSpinBoxDUB.setValue(parameters['d_u_bound'])
            # self.spinBoxNBins.setMaximum(int(max(isotope_array)))
            # self.spinBoxBinWidth.setMaximum(int(max(isotope_array)))
            self.spinBoxNBins.setValue(int(bins))
            self.spinBoxBinWidth.setValue(int(bin_width))

            self.lineEditFMin.setText(str(self.dynamic_format(parameters['v_min'])))
            self.lineEditFMax.setText(str(self.dynamic_format(parameters['v_max'])))

            self.update_spinboxes_bool = True
        
        
    def get_map_data(self,sample_id, isotope_1=None, isotope_2=None, plot_type = 'lasermap', plot= True,auto_scale = False, update = False):

        """
        Retrieves and processes the mapping data for the given sample and isotopes, then plots the result if required.

        Parameters:
        - self.sample_id (str): Identifier for the sample to be processed.
        - isotope_1 (str, optional): Primary isotope for plotting. If not provided, it's inferred from the isotope data frame.
        - isotope_2 (str, optional): Secondary isotope for ratio plotting. If not provided, only the primary isotope will be plotted.
        - plot_type (str, default='laser'): Specifies the type of plot. Accepts 'laser' or 'hist'.
        - plot (bool, default=True): Determines if the plot should be shown after processing.
        - auto_scale (bool, default=False): Determines if auto-scaling should be re-applied to the plot. if False use fmin and fmax and clip array

        Returns:
        - DataFrame: Processed data for plotting. This is only returned if plot_type is not 'laser' or 'hist'.

        Note:
        - The method also updates certain parameters in the isotope data frame related to scaling.
        - Based on the plot type, this method internally calls the appropriate plotting functions.
        """

        selected_sample = self.sample_data_dict[sample_id]



        if not isotope_1:
            isotope_1 = self.isotopes_df.loc[self.isotopes_df['sample_id']==sample_id,'isotopes'].iloc[0]


        parameters =  self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                              & (self.isotopes_df['isotopes']==isotope_1)].iloc[0]

        if not isotope_2:
            norm = parameters['norm']
            lb = parameters['lower_bound']
            ub = parameters['upper_bound']
            d_lb = parameters['d_l_bound']
            d_ub = parameters['d_u_bound']
            # if plot is None: #only update x and y for plotting for analysis use original x and y range
            #     x_range = [current_plot_df['X'].min(), current_plot_df['X'].max()]
            #     y_range = [current_plot_df['Y'].min(), current_plot_df['Y'].max()]
            # else:
            x_range= [parameters['x_min'],parameters['x_max']]
            y_range = [parameters['y_min'],parameters['y_max']]
            auto_scale_param = parameters['auto_scale']
            if update: #update clipped isotopes df and processed df

                current_plot_df = selected_sample[[isotope_1,'X','Y']].rename(columns = {isotope_1:'array'})


                #perform autoscaling only if scaling is performed if not get array
                if auto_scale_param:

                    current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub, x_range = x_range, y_range = y_range, norm=norm, outlier=auto_scale_param)

                else:

                    current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub, x_range = x_range, y_range = y_range, norm=norm)

                self.clipped_isotope_data[sample_id][isotope_1] = current_plot_df['array'].values
                self.update_norm(sample_id,norm, isotope = isotope_1)
            else:
                current_plot_df = self.processed_isotope_data[sample_id][[isotope_1,'X','Y']].rename(columns = {isotope_1:'array'})

            isotope_str =   isotope_1

        else:

            ratio_df = selected_sample[[isotope_1, isotope_2]] #consider original data for ratio

            current_plot_df = selected_sample[['X','Y']]

            mask = (ratio_df[isotope_1] > 0) & (ratio_df[isotope_2] > 0)

            current_plot_df.loc[:, 'array'] = np.where(mask, ratio_df[isotope_1] / ratio_df[isotope_2], np.nan)

            # Get the index of the row that matches the criteria
            index_to_update = self.ratios_df.loc[
                (self.ratios_df['sample_id'] == sample_id) &
                (self.ratios_df['isotope_1'] == isotope_1) &
                (self.ratios_df['isotope_2'] == isotope_2)
            ].index

            # Check if we found such a row
            if len(index_to_update) > 0:
                idx = index_to_update[0]

                if pd.isna(self.ratios_df.at[idx, 'lower_bound']):
                    norm = self.ratios_df.at[idx, 'norm']
                    self.ratios_df.at[idx, 'lower_bound'] = 0.05
                    self.ratios_df.at[idx, 'upper_bound'] = 99.5
                    self.ratios_df.at[idx, 'd_l_bound'] = 99
                    self.ratios_df.at[idx, 'd_u_bound'] = 99
                    self.ratios_df.at[idx, 'x_min'] = current_plot_df['X'].min()
                    self.ratios_df.at[idx, 'x_max'] = current_plot_df['X'].max()
                    self.ratios_df.at[idx, 'y_min'] = current_plot_df['Y'].min()
                    self.ratios_df.at[idx, 'y_max'] = current_plot_df['Y'].max()

                    x_range= [self.ratios_df.at[idx, 'x_min'], self.ratios_df.at[idx, 'x_max']]
                    y_range = [self.ratios_df.at[idx, 'y_min'], self.ratios_df.at[idx, 'y_max']]

                    auto_scale_param = self.ratios_df.at[idx, 'auto_scale']

                    current_plot_df = self.scale_plot(current_plot_df, lq=0.05, uq=99.5, d_lb=99, d_ub= 99, x_range=x_range, y_range=y_range, norm=norm, outlier=auto_scale_param)

                    self.ratios_df.at[idx, 'v_min'] = current_plot_df['array'].min()
                    self.ratios_df.at[idx, 'v_max'] = current_plot_df['array'].max()
                else:
                    norm = self.ratios_df.at[idx, 'norm']
                    lb = self.ratios_df.at[idx, 'lower_bound']
                    ub = self.ratios_df.at[idx, 'upper_bound']
                    d_lb = self.ratios_df.at[idx, 'd_l_bound']
                    d_ub = self.ratios_df.at[idx, 'd_u_bound']
                    x_range = [self.ratios_df.at[idx, 'x_min'], self.ratios_df.at[idx, 'x_max']]
                    y_range = [self.ratios_df.at[idx, 'y_min'], self.ratios_df.at[idx, 'y_max']]
                    auto_scale_param = self.ratios_df.at[idx, 'auto_scale']

                    current_plot_df = self.scale_plot(current_plot_df, lq=lb, uq=ub, d_lb=d_lb, d_ub=d_ub, x_range=x_range, y_range=y_range, norm=norm, outlier=auto_scale_param)


                    if auto_scale_param:

                        current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub, x_range = x_range, y_range = y_range, norm=norm, outlier=auto_scale)
                    else:

                        current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub, x_range = x_range, y_range = y_range, norm=norm)

                parameters  = self.ratios_df.iloc[idx]
            self.plot_type = plot_type
            isotope_str =   isotope_1 + '/' + isotope_2
            

            if update: #update clipped ratio df
                self.clipped_ratio_data[isotope_str] = current_plot_df['array'].values
        bins =100

        bin_width = (np.nanmax(current_plot_df['array']) - np.nanmin(current_plot_df['array'])) / bins

        # current_plot_df = current_plot_df[self.axis_mask].reset_index(drop=True)
        if plot_type=='lasermap':
            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_laser_map(current_plot_df,plot_information)
            self.update_spinboxes(parameters,bins, bin_width, auto_scale_param)

        elif plot_type=='historgram': 
            

            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_histogram(current_plot_df,plot_information,bin_width = bin_width)
            self.update_spinboxes(parameters,bins, bin_width, auto_scale_param)
        elif plot_type == 'lasermap_norm':
            ref_data_chem = self.ref_data.iloc[self.comboBoxRefMaterial.currentIndex()]
            ref_data_chem.index = [col.replace('_ppm', '') for col in ref_data_chem.index]
            ref_series =  ref_data_chem[re.sub(r'\d', '', isotope_1).lower()]
            current_plot_df['array']= current_plot_df['array'] / ref_series
            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_laser_map(current_plot_df,plot_information)
            self.update_spinboxes(parameters,bins, bin_width, auto_scale_param)
        else:
            # Return df for analysis
            ## filter current_plot_df based on active filters
            mask = self.filter_mask & self.polygon_mask & self.axis_mask
            current_plot_df['array'] = np.where(mask, current_plot_df['array'], np.nan)
            return current_plot_df
        if plot:
            self.add_plot(plot_information, current_plot_df)


    def toolbar_plotting(self,function,view,enable):
        if function == 'home':
            self.toolButtonPanSV.setChecked(False)
            self.toolButtonZoomSV.setChecked(False)
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.home()
            if self.pyqtgraph_widget:
                self.pyqtgraph_widget.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.toolButtonZoomSV.setChecked(False)
            if self.matplotlib_canvas:
                # Toggle pan mode in Matplotlib
                self.matplotlib_canvas.toolbar.pan()
            if self.pyqtgraph_widget:
                # Enable or disable panning
                self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.PanMode if enable else pg.ViewBox.RectMode)

        if function == 'zoom':
            self.toolButtonPanSV.setChecked(False)
            if self.matplotlib_canvas:
                # Toggle zoom mode in Matplotlib
                self.matplotlib_canvas.toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            if self.pyqtgraph_widget:
                # Assuming pyqtgraph_widget is a GraphicsLayoutWidget or similar
                if enable:

                    self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.RectMode)
                else:
                    self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.PanMode)

        if function == 'preference':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.edit_parameters()
            if self.pyqtgraph_widget:
                # Assuming it's about showing/hiding axes
                if enable:
                    self.pyqtgraph_widget.showAxis('left', True)
                    self.pyqtgraph_widget.showAxis('bottom', True)
                else:
                    self.pyqtgraph_widget.showAxis('left', False)
                    self.pyqtgraph_widget.showAxis('bottom', False)

        if function == 'axes':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.configure_subplots()
            if self.pyqtgraph_widget:
                # Assuming it's about showing/hiding axes
                if enable:
                    self.pyqtgraph_widget.showAxis('left', True)
                    self.pyqtgraph_widget.showAxis('bottom', True)
                else:
                    self.pyqtgraph_widget.showAxis('left', False)
                    self.pyqtgraph_widget.showAxis('bottom', False)

        if function == 'save':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.save_figure()
            if self.pyqtgraph_widget:
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(self.pyqtgraph_widget.getItem(0, 0).scene())
                export.show(self.pyqtgraph_widget.getItem(0, 0).getViewBox())
                export.exec_()
    def import_data(self, path):
        # Get a list of all files in the directory
        file_list = os.listdir(path)
        csv_files = [file for file in file_list if file.endswith('.csv')]
        csv_files = csv_files[0:2]
        # layout = self.widgetLaserMap.layout()
        # progressBar = QProgressDialog("Loading CSV files...", None, 0,
        #                               len(csv_files))
        # layout.addWidget(progressBar, 3, 0,  1, 2)
        # progressBar.setWindowTitle("Loading")
        # progressBar.setWindowModality(QtCore.Qt.WindowModal)
        # Loop through the CSV files and read them using pandas
        data_dict = {}
        i = 0
        for csv_file in csv_files:
            file_path = os.path.join(path, csv_file)
            df = pd.read_csv(file_path, engine='c')
            file_name = os.path.splitext(csv_file)[0]
            # Get the file name without extension
            data_dict[file_name] = df
            i += 1
            # progressBar.setValue(i)
        return data_dict

    def create_tree(self,sample_id = None):
        if self.isotopes_df.empty:
            treeView  = self.treeView
            treeView.setHeaderHidden(True)
            treeModel = QStandardItemModel()
            rootNode = treeModel.invisibleRootItem()
            self.isotopes_items = StandardItem('Isotope', 14, True)
            self.norm_isotopes_items = StandardItem('Normalised Isotope', 14, True)
            self.ratios_items = StandardItem('Ratio', 14, True)
            self.histogram_items = StandardItem('Histogram', 14, True)
            self.correlation_items = StandardItem('Correlation', 14, True)
            self.scatter_items = StandardItem('Scatter', 14, True)
            self.n_dim_items = StandardItem('n-Dim', 14, True)
            self.clustering_items = StandardItem('Clustering', 14, True)
            rootNode.appendRows([self.isotopes_items,self.norm_isotopes_items,self.ratios_items,self.histogram_items,self.correlation_items, self.scatter_items,
                                 self.n_dim_items,self.clustering_items])
            treeView.setModel(treeModel)
            treeView.expandAll()
            treeView.doubleClicked.connect(self.tree_double_click)
        elif sample_id:
            #self.isotopes_items.setRowCount(0)
            sample_id_item = StandardItem(sample_id, 13)
            histogram_sample_id_item = StandardItem(sample_id, 13)
            ratio_sampe_id_item = StandardItem(sample_id, 13)
            norm_sample_id_item = StandardItem(sample_id, 13)
            for isotope in self.isotopes_df.loc[self.isotopes_df['sample_id']==sample_id,'isotopes']:
                isotope_item = StandardItem(isotope)
                sample_id_item.appendRow(isotope_item)
                histogram_item = StandardItem(isotope)
                histogram_sample_id_item.appendRow(histogram_item)
                norm_item = StandardItem(isotope)
                norm_sample_id_item.appendRow(norm_item)
            self.isotopes_items.appendRow(sample_id_item)
            self.histogram_items.appendRow(histogram_sample_id_item)
            self.ratios_items.appendRow(ratio_sampe_id_item)
            self.norm_isotopes_items.appendRow(norm_sample_id_item)
    def tree_double_click(self,val):
        level_1_data = val.parent().parent().data()
        level_2_data =val.parent().data()
        level_3_data = val.data()
        # self.checkBoxViewRatio.setChecked(False)
        if level_1_data == 'Isotope' :
            self.get_map_data(level_2_data,level_3_data)
        if level_1_data == 'Normalised Isotope' :
            self.get_map_data(level_2_data,level_3_data, plot_type='lasermap_norm')
        elif level_1_data == 'Histogram' :
            self.get_map_data(level_2_data,level_3_data,plot_type='histogram')
        # self.add_plot(val.data())
        elif level_1_data == 'Ratio' :
            isotopes= level_3_data.split(' / ')
            self.get_map_data(level_2_data,isotopes[0],isotopes[1])

        elif ((level_1_data == 'Clustering') or (level_1_data=='Scatter')):
            plot_info ={'plot_name':level_3_data, 'plot_type':level_1_data.lower(),'sample_id':level_2_data }
            self.add_plot(plot_info)
                

    def open_select_isotope_dialog(self):
        isotopes_list = self.isotopes_df['isotopes'].values

        self.isotopeDialog = IsotopeSelectionWindow(isotopes_list,self.selected_isotopes, self.clipped_isotope_data[self.sample_id], self)
        self.isotopeDialog.show()
        self.isotopeDialog.listUpdated.connect(lambda: self.update_tree(self.isotopeDialog.selected_pairs))
        result = self.isotopeDialog.exec_()  # Store the result here
        if result == QDialog.Accepted:
            self.selected_isotopes = self.isotopeDialog.selected_pairs
        if result == QDialog.Rejected:
            self.update_tree(self.selected_isotopes)




    def update_tree(self,leaf,data = None,tree= 'Isotope'):
        if tree == 'Isotope':
            # Highlight isotopes in treeView
            # Un-highlight all leaf in the trees
            self.unhighlight_tree(self.ratios_items)
            self.unhighlight_tree(self.isotopes_items)
            self.isotopes_df.loc[self.isotopes_df['sample_id']==self.sample_id,'use'] = False
            if len(leaf)>0:
                for line in leaf:
                    if ',' in line:
                        isotope_pair, norm = line.strip().split(',') #get norm returned from load isotope
                    else:
                        isotope_pair = line.strip()
                        norm = 'linear'
                    if '/' in isotope_pair:
                        isotope_1, isotope_2 = isotope_pair.split(' / ')
                        self.update_ratio_df(self.sample_id,isotope_1, isotope_2, norm)
                        ratio_name = f"{isotope_1} / {isotope_2}"
                        # Populate ratios_items if the pair doesn't already exist
                        item,check = self.find_leaf(tree = self.ratios_items, branch = self.sample_id, leaf = ratio_name)

                        if not check: #if ratio doesnt exist
                            child_item = StandardItem(ratio_name)
                            child_item.setBackground(QBrush(QColor(255, 255, 0)))
                            item.appendRow(child_item)
                        else:
                            item.setBackground(QBrush(QColor(255, 255, 0)))
                    else: #single isotope
                        item,check = self.find_leaf(tree = self.isotopes_items, branch = self.sample_id, leaf = isotope_pair)
                        item.setBackground(QBrush(QColor(255, 255, 0)))
                        self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id) & (self.isotopes_df['isotopes']==isotope_pair),'use'] = True
                        self.update_norm(self.sample_id,norm,isotope_pair)

        elif tree=='Scatter':

            self.add_tree_item(self.sample_id,self.scatter_items,leaf,data)

        elif tree == 'Clustering':
            self.add_tree_item(self.sample_id,self.clustering_items,leaf,data)

        elif tree == 'n-Dim':
            self.add_tree_item(self.sample_id,self.n_dim_items,leaf,data)



    def add_tree_item(self,sample_id,tree, leaf, data):
        #check if leaf is in tree
        item,check = self.find_leaf(tree = tree, branch = sample_id, leaf = leaf)
        if item is None and check is None: #sample id item and plot item both dont exist
            cluster_sample_id_item = StandardItem(sample_id, 13)
            plot_item = StandardItem(leaf)
            if data is not None:
                # The role should be an integer, Qt.UserRole is the base value for custom roles
                custom_role = Qt.UserRole + 1

                # Store the dictionary in the item using a custom role
                plot_item.setData(data, custom_role)

            cluster_sample_id_item.appendRow(plot_item)
            tree.appendRow(cluster_sample_id_item)
        elif item is not None and check is False: #sample id item exists plot item doesnt exist
            plot_item = StandardItem(leaf)
            if data is not None:
                # The role should be an integer, Qt.UserRole is the base value for custom roles
                custom_role = Qt.UserRole + 1

                # Store the dictionary in the item using a custom role
                plot_item.setData(data, custom_role)
            #item is sample id item (branch)
            item.appendRow(plot_item)



    def unhighlight_tree(self, tree):
        """Reset the highlight of all items in the tree."""
        for i in range(tree.rowCount()):
            branch_item = tree.child(i)
            branch_item.setBackground(QBrush(QColor(255, 255, 255)))  # white or any default background color
            for j in range(branch_item.rowCount()):
                leaf_item = branch_item.child(j)
                leaf_item.setBackground(QBrush(QColor(255, 255, 255)))  # white or any default background color


    def find_leaf(self,tree, branch, leaf):
        #Returns leaf item,True  if leaf exists else returns branch item, False
            for index in range(tree.rowCount()):
                branch_item = tree.child(index)
                if branch_item.text() == branch:
                    for index in range(branch_item.rowCount()):
                        leaf_item = branch_item.child(index)
                        if leaf_item.text() == leaf:
                            return (leaf_item, True)
                    return (branch_item,False)
            return (None,None)



    def update_ratio_df(self,sample_id,isotope_1, isotope_2,norm):

        parameter= self.ratios_df.loc[(self.ratios_df['sample_id'] == sample_id) & (self.ratios_df['isotope_1'] == isotope_1) & (self.ratios_df['isotope_2'] == isotope_2)]
        if parameter.empty:
            ratio_info= {'sample_id': self.sample_id, 'isotope_1':isotope_1, 'isotope_2':isotope_2, 'norm': norm,
                            'x_min':np.nan,'x_max':np.nan,'y_min':np.nan,'y_max':np.nan,
                            'upper_bound':np.nan,'lower_bound':np.nan,'d_bound':np.nan,'use': True,'auto_scale': True}
            self.ratios_df.loc[len(self.ratios_df)] = ratio_info



            self.get_map_data(sample_id, isotope_1=isotope_1, isotope_2 = isotope_2, plot_type = None, plot = False)



class StandardItem(QStandardItem):
    def __init__(self, txt = '', font_size = 12, set_bold= False):
        super().__init__()

        fnt  = QFont()
        fnt.setBold(set_bold)
        self.setEditable(False)
        self.setText(txt)
        self.setFont(fnt)


class IsotopeSelectionWindow(QDialog, Ui_Dialog):
    listUpdated = pyqtSignal()
    def __init__(self, isotopes,selected_pairs, clipped_data, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.isotopes = list(isotopes)
        self.selected_pairs = selected_pairs
        self.clipped_data = clipped_data
        self.correlation_matrix = None
        self.tableWidgetIsotopes.setRowCount(len(isotopes))
        self.tableWidgetIsotopes.setColumnCount(len(isotopes))
        self.tableWidgetIsotopes.setHorizontalHeaderLabels(list(isotopes))
        self.tableWidgetIsotopes.setHorizontalHeader(RotatedHeaderView(self.tableWidgetIsotopes))
        self.tableWidgetIsotopes.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetIsotopes.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)


        self.tableWidgetIsotopes.setVerticalHeaderLabels(isotopes)
        self.correlation_methods = [
            "Pearson",
            "Spearman",
            "Kendall"
        ]

        for method in self.correlation_methods:
            self.comboBoxCorrelation.addItem(method)

        self.calculate_correlation()



        self.tableWidgetIsotopes.cellClicked.connect(self.toggle_cell_selection)

        self.tableWidgetSelected.setColumnCount(2)
        self.tableWidgetSelected.setHorizontalHeaderLabels(['Isotope Pair', 'normalisation'])

        self.pushButtonSaveSelection.clicked.connect(self.save_selection)

        self.pushButtonLoadSelection.clicked.connect(self.load_selection)

        self.pushButtonDone.clicked.connect(self.accept)

        self.pushButtonCancel.clicked.connect(self.reject)
        self.comboBoxCorrelation.activated.connect(self.calculate_correlation)

        if len(self.selected_pairs)>0:
            for line in self.selected_pairs:
                self.populate_isotope_list(line)
        else:
            # Select diagonal pairs by default
            for i in range(len(self.isotopes)):
                row=column = i
                item = self.tableWidgetIsotopes.item(row, column)

                # If the item doesn't exist, create it
                if not item:
                    item = QTableWidgetItem()
                    self.tableWidgetIsotopes.setItem(row, column, item)
                    self.add_isotope_to_list(row, column)
                # If the cell is already selected, deselect it
                elif not item.isSelected():
                    item.setSelected(True)
                    self.add_isotope_to_list(row, column)
                else:
                    item.setSelected(False)
                    self.remove_isotope_from_list(row, column)

    def calculate_correlation(self):
        selected_method = self.comboBoxCorrelation.currentText().lower()
        # Compute the correlation matrix
        self.correlation_matrix = self.clipped_data.corr(method=selected_method)
        for i, row_isotope in enumerate(self.isotopes):
            for j, col_isotope in enumerate(self.isotopes):

                correlation = self.correlation_matrix.loc[row_isotope, col_isotope]
                self.color_cell(i, j, correlation)
        self.create_colorbar()  # Call this to create and display the colorbar

    def color_cell(self, row, column, correlation):
        color = self.get_color_for_correlation(correlation)
        item = self.tableWidgetIsotopes.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetIsotopes.setItem(row, column, item)
        item.setBackground(color)

    def get_color_for_correlation(self, correlation):
            # Map correlation to RGB color
            r = 255 * (correlation > 0) * (abs(correlation))
            b = 0
            g = 255 * (correlation < 0) * ( abs(correlation))
            return QColor(int(r), int(g),int(b))

    def create_colorbar(self):
        colorbar_image = self.generate_colorbar_image(40, 200)  # Width, Height of colorbar
        colorbar_label = QLabel(self)
        colorbar_pixmap = QPixmap.fromImage(colorbar_image)
        self.labelColorbar.setPixmap(colorbar_pixmap)

    def generate_colorbar_image(self, width, height):
        image = QImage(width, height, QImage.Format_RGB32)
        painter = QPainter(image)
        painter.fillRect(0, 0, width, height, Qt.white)  # Fill background with white
        pad =20
        # Draw color gradient
        for i in range(pad,height-pad):
            correlation = 1 - (2 * i / height)  # Map pixel position to correlation value
            color = self.get_color_for_correlation(correlation)
            painter.setPen(color)
            painter.drawLine(10, i, width-20, i) # Leave space for ticks
        # Draw tick marks
        tick_positions = [pad, height // 2, height-pad - 1]  # Top, middle, bottom
        tick_labels = ['1', '0', '-1']
        painter.setPen(Qt.black)
        for pos, label in zip(tick_positions, tick_labels):
            painter.drawLine(width - 20, pos, width-18 , pos)  # Draw tick mark
            painter.drawText(width-15 , pos + 5, label)   # Draw tick label
        painter.end()
        return image
    def toggle_cell_selection(self, row, column):
        item = self.tableWidgetIsotopes.item(row, column)

        # If the item doesn't exist, create it
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetIsotopes.setItem(row, column, item)
            self.add_isotope_to_list(row, column)
        # If the cell is already selected, deselect it
        elif item.isSelected():
            item.setSelected(True)
            self.add_isotope_to_list(row, column)
        else:
            item.setSelected(False)
            self.remove_isotope_from_list(row, column)

    def add_isotope_to_list(self, row, column):
        row_header = self.tableWidgetIsotopes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetIsotopes.horizontalHeaderItem(column).text()

        newRow = self.tableWidgetSelected.rowCount()
        self.tableWidgetSelected.insertRow(newRow)
        if row == column:
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header}"))
        else:
            # Add isotope pair to the first column
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header} / {col_header}"))

        # Add dropdown to the second column
        combo = QComboBox()
        combo.addItems(['linear', 'log', 'logit'])
        self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
        self.update_list()

    def remove_isotope_from_list(self, row, column):
        row_header = self.tableWidgetIsotopes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetIsotopes.horizontalHeaderItem(column).text()
        if row == column:
            item_text = f"{row_header}"
        else:
            item_text = f"{row_header} / {col_header}"

        # Find the row with the corresponding text and remove it
        for i in range(self.tableWidgetSelected.rowCount()):
            if self.tableWidgetSelected.item(i, 0).text() == item_text:
                self.tableWidgetSelected.removeRow(i)
                self.update_list()
                break


    def get_selected_data(self):
        data = []
        for i in range(self.tableWidgetSelected.rowCount()):
            isotope_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            data.append((isotope_pair, selection))
        return data


    def save_selection(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    isotope_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{isotope_pair},{selection}\n")

    def load_selection(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r') as f:
                for line in f.readlines():
                    self.populate_isotope_list(line)
            self.update_list()
            self.raise_()
            self.activateWindow()

    def update_list(self):
        self.selected_pairs=[]
        for i in range(self.tableWidgetSelected.rowCount()):
            isotope_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            self.selected_pairs.append(f"{isotope_pair},{selection}")
        self.listUpdated.emit()

    def populate_isotope_list(self,line):
        if ',' in line: 
            isotope_pair, norm = line.strip().split(',') #get norm returned from load isotope
        else:
            isotope_pair = line
            norm = 'linear'
        if '/' in isotope_pair:
            row_header, col_header = isotope_pair.split(' / ')
        else:
            row_header = col_header = isotope_pair
        # Select the cell in tableWidgetIsotope
        if row_header in self.isotopes:
            row_index = self.isotopes.index(row_header)
            col_index = self.isotopes.index(col_header)

            item = self.tableWidgetIsotopes.item(row_index, col_index)
            if not item:
                item = QTableWidgetItem()
                self.tableWidgetIsotopes.setItem(row_index, col_index, item)
            item.setSelected(True)

            # Add the loaded data to tableWidgetSelected
            newRow = self.tableWidgetSelected.rowCount()
            self.tableWidgetSelected.insertRow(newRow)
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(isotope_pair))
            combo = QComboBox()
            combo.addItems(['linear', 'log', 'logit'])
            combo.setCurrentText(norm)
            self.tableWidgetSelected.setCellWidget(newRow, 1, combo)

class CustomAxis(AxisItem):
    def __init__(self, *args, **kwargs):
        AxisItem.__init__(self, *args, **kwargs)
        self.scale_factor = 1.0

    def setScaleFactor(self, scale_factor):
        self.scale_factor = scale_factor

    def tickStrings(self, values, scale, spacing):
        # Scale the values back to the original scale
        scaled_values = [v * self.scale_factor for v in values]
        print (scaled_values)
        # Format the tick strings as you want them to appear
        return ['{:.2f}'.format(v) for v in scaled_values]

class Profiling:
    def __init__(self,main_window):
        self.main_window = main_window
        # Initialize other necessary attributes
        # Initialize variables and states as needed
        self.profiles = {}
        self.i_profiles = {} #interpolated profiles
        self.array_x = None
        self.array_y = None
    def on_plot_clicked(self, event,array,k, plot,radius=5):
        # if event.button() == QtCore.Qt.LeftButton and self.main_window.pushButtonStartProfile.isChecked():
        if event.button() == QtCore.Qt.LeftButton and self.main_window.pushButtonPlotProfile.isChecked():
            # Convert the click position to plot coordinates
            click_pos = plot.vb.mapSceneToView(event.scenePos())
            x, y = click_pos.x(), click_pos.y()
            self.array_x = array.shape[1]
            self.array_y = array.shape[0]
            x_i = round(x*self.array_x /self.main_window.x_range)
            y_i = round(y*self.array_y/self.main_window.y_range)
            interpolate = False
            # Ensure indices are within bounds
            if 0 <= x_i < self.array_x  and 0 <= y_i < self.array_y:
                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                plot.addItem(scatter)
                # Find all points within the specified radius
                circ_val = []
                circ_cord = []
                for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                    for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                        if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                            value = array[i, j]
                            circ_cord.append([i, j])
                            circ_val.append( value)

                #add values within circle of radius in self.profiles
                if k in self.profiles:
                    self.profiles[k].append((x,y,circ_val,scatter, interpolate))
                else:
                    self.profiles[k] = [(x,y, circ_val,scatter, interpolate)]


                if self.main_window.canvasWindow.currentIndex() == 1:
                    # Add the scatter item to all other plots and save points in self.profiles
                    for k, (_, p, v, array) in self.main_window.lasermaps.items():
                        circ_val = []
                        if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                            p.addItem(scatter)
                            for c in circ_cord:
                                value = array[c[0], c[1]]
                                circ_val.append( value)
                            if k in self.profiles:
                                self.profiles[k].append((x,y,circ_val, scatter, interpolate))
                            else:
                                self.profiles[k] = [(x,y, circ_val,scatter, interpolate)]
            self.plot_profiles()
            self.update_table_widget()

    def interpolate_points(self, interpolation_distance,radius):
        """
        Interpolate linear points between each pair of points in the profiles.
        """
        if self.main_window.pushButtonIPProfile.isChecked():
            interpolate = True
            for k, points in self.profiles.items():
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    if i==0:
                        self.i_profiles[k] = [start_point]
                    else:
                        self.i_profiles[k].append(start_point)

                    # Calculate the distance between start and end points
                    dist = self.calculate_distance(start_point, end_point)

                    # Determine the number of interpolations based on the distance
                    num_interpolations = max(int(dist / interpolation_distance) - 1, 0)

                    # Generate linearly spaced points between start_point and end_point
                    for t in np.linspace(0, 1, num_interpolations + 2)[1:-1]:  # Exclude the endpoints
                        x = start_point[0] + t * (end_point[0] - start_point[0])
                        y = start_point[1] + t * (end_point[1] - start_point[1])

                        x_i = round(x*self.array_x /self.main_window.x_range) #index points
                        y_i = round(y*self.array_y/self.main_window.y_range)
                        # Add the scatter item to all other plots and save points in self.profiles
                        _, p, v, array= self.main_window.lasermaps[k]
                        if v==self.main_window.canvasWindow.currentIndex() and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=5)
                            p.addItem(scatter)
                            # Find all points within the specified radius
                            circ_val = []
                            for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                                for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                                    if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                                        value = array[i, j]
                                        circ_val.append(value)
                            if k in self.i_profiles:
                                self.i_profiles[k].append((x,y,circ_val, scatter, interpolate))

                    self.i_profiles[k].append(end_point)



            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate= interpolate)
        else:
            # remove interpolation
            for key, profile in self.i_profiles.items():
                for point in profile:
                    scatter_item = point[3]  # Access the scatter plot item
                    interpolate =point[4]
                    if interpolate:
                        _, plot, _, _ = self.main_window.lasermaps[key]
                        plot.removeItem(scatter_item)
            #plot original profile
            self.plot_profiles(interpolate= False)
        # self.update_table_widget(interpolate= True)


    def plot_profiles(self,interpolate= False):
        def process_points( points, sort_axis='x'):
            # Sort the points based on the user-specified axis
            if sort_axis == 'x':
                points.sort(key=lambda p: p[0])  # Sort by x-coordinate of median point
            elif sort_axis == 'y':
                points.sort(key=lambda p: p[1])  # Sort by y-coordinate of median point

            median_values = []
            lower_quantiles = []
            upper_quantiles = []
            mean_values = []
            standard_errors = []
            distances = [0]

            for i, group in enumerate(points):

                values = [p for p in group[2]] # Extract values
                median_values.append(np.median(values))
                lower_quantiles.append(np.quantile(values, 0.25))
                upper_quantiles.append(np.quantile(values, 0.75))
                mean_values.append(np.mean(values))
                standard_errors.append(np.std(values, ddof=1) / np.sqrt(len(values)))
                if i>0:
                    dist = self.calculate_distance(points[i - 1], points[i])
                    distances.append(distances[-1] + dist)

            return distances, median_values, lower_quantiles, upper_quantiles,mean_values,standard_errors

        def group_profiles_by_range(sort_axis, range_threshold,interpolate,point_type):
            if not interpolate:
                profiles = self.profiles
            else:
                profiles = self.i_profiles
            # Group profiles based on range similarity
            profile_groups = {}
            keys = []
            if self.main_window.canvasWindow.currentIndex(): #multiview
                keys= [k for k in profiles.keys() if k[-1]== '1']



            else: #singleview
                keys = [k for k in profiles.keys() if k[-1]== '0']

            colors = [cmap(i / len(keys)) for i in range(len(keys))]

            for k in keys:
                points =  profiles[k]
                distances, medians, lowers, uppers, mean,s_error  = process_points(points, sort_axis)
                if point_type == 'mean':
                    range_value = np.max(mean)- np.min(mean)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, mean, s_error))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, mean, s_error)]
                else:

                    range_value = np.max(medians)- np.min(medians)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, medians, lowers, uppers))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, medians, lowers, uppers)]

            return profile_groups, colors

        if not interpolate:
            profiles = self.profiles
        else:
            profiles = self.i_profiles

        if len(profiles)>0:
            self.main_window.tabWidget.setCurrentIndex(1) #show profile plot tab
            sort_axis=self.main_window.comboBoxProfileSort.currentText()
            range_threshold=int(self.main_window.lineEditYThresh.text())
            # Clear existing plot
            layout = self.main_window.widgetProfilePlot.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get the colormap specified by the user
            cmap = matplotlib.colormaps.get_cmap(self.main_window.comboBoxCM.currentText())
            # Determine point type from the pushButtonProfileType text
            if self.main_window.comboBoxPointType.currentText() == 'median':
                point_type = 'median'
            else:
                point_type ='mean'
            # Group profiles and set up the figure
            profile_groups,colors = group_profiles_by_range(sort_axis, range_threshold, interpolate, point_type)
            # Initialize the figure
            fig = Figure()
            num_groups = len(profile_groups)
            num_subplots = (num_groups + 1) // 2  # Two groups per subplot, rounding up
            subplot_idx = 1

            # Adjust subplot spacing
            # fig.subplots_adjust(hspace=0.1)  # Adjust vertical spacing
            ax = fig.add_subplot(num_subplots, 1, subplot_idx)
            for idx, (range_value, group_profiles) in enumerate(profile_groups.items()):
                if idx > 1 and idx % 2 == 0:  # Create a new subplot for every 2 groups after the first two
                    subplot_idx += 1
                    ax = fig.add_subplot(num_subplots, 1, subplot_idx)
                elif idx % 2 == 1:  # Create a new subplot for every 2 groups after the first two
                    ax = ax.twinx()
                el_labels = []
                # Plot each profile in the group
                if point_type == 'mean':
                    for g_idx,(profile_key, distances, means,s_errors) in enumerate(group_profiles):
                        ax.errorbar(distances, means, yerr=s_errors, fmt='o', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0, label=f'{profile_key[:-1]}')
                        el_labels.append(profile_key[:-1].split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        ax.set_ylabel(f'{y_axis_text}')
                else:
                    for g_idx,(profile_key, distances, medians, lowers, uppers) in enumerate(group_profiles):

                        # errors = [upper - lower for upper, lower in zip(uppers, lowers)]
                        #asymmetric error bars
                        errors = [[median - lower for median, lower in zip(medians, lowers)],
                            [upper - median for upper, median in zip(uppers, medians)]]
                        ax.errorbar(distances, medians, yerr=errors, fmt='o', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0, label=f'{profile_key[:-1]}')
                        el_labels.append(profile_key[:-1].split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        ax.set_ylabel(f'{y_axis_text}')
            # Set labels only for the bottom subplot
                if subplot_idx == num_subplots:
                    ax.set_xlabel('Distance')
                else:
                    # Remove the x-axis for the first subplot
                    ax.xaxis.set_visible(False)
                # ax.set_ylabel(f'Axis {idx}')
                # Adjust legend position based on the subplot index
                legend_loc = 'upper left' if idx % 2 == 0 else 'upper right'
                # ax.legend(title=f'Axis {idx}', loc=legend_loc, bbox_to_anchor=(1.05, 1))

            # fig.tight_layout(pad=3, h_pad=None, w_pad=None, rect=None)
            fig.tight_layout(pad=3,w_pad=0, h_pad=0)
            fig.subplots_adjust(wspace=0, hspace=0)
            fig.legend(loc='outside right upper')
            # Embed the matplotlib plot in a QWidget
            canvas = FigureCanvas(fig)
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(canvas)
            widget.setLayout(layout)

            # Add the new plot widget to the layout
            self.main_window.widgetProfilePlot.layout().addWidget(widget)
            widget.show()

    def on_clear_profile_clicked(self):
        # Clear all scatter plot items from the lasermaps
        for _, (_, plot, _, _) in self.main_window.lasermaps.items():
            items_to_remove = [item for item in plot.listDataItems() if isinstance(item, ScatterPlotItem)]
            for item in items_to_remove:
                plot.removeItem(item)

        # Clear the profiles data
        self.profiles.clear()

        # Clear all data from the table
        self.main_window.tableWidgetProfilePoints.clearContents()

        # Remove all rows
        self.main_window.tableWidgetProfilePoints.setRowCount(0)

        # Clear the profile plot widget
        layout = self.main_window.widgetProfilePlot.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def calculate_distance(self, point1, point2):
        # Simple Euclidean distance
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def update_table_widget(self):
        self.main_window.tableWidgetProfilePoints.setRowCount(0)  # Clear existing rows
        point_number = 0
        first_data_point = list(self.profiles.values())[0]
        for data_point in first_data_point:
            x, y, _,_,_ = data_point  # Assuming data_point structure
            row_position = self.main_window.tableWidgetProfilePoints.rowCount()
            self.main_window.tableWidgetProfilePoints.insertRow(row_position)

            # Fill in the data
            self.main_window.tableWidgetProfilePoints.setItem(row_position, 0, QTableWidgetItem(str(point_number)))
            self.main_window.tableWidgetProfilePoints.setItem(row_position, 1, QTableWidgetItem(str(round(x))))
            self.main_window.tableWidgetProfilePoints.setItem(row_position, 2, QTableWidgetItem(str(round(y))))
            point_number += 1

        # Enable or disable buttons based on the presence of points
        self.toggle_buttons(self.main_window.tableWidgetProfilePoints.rowCount() > 0)

    def move_point_up(self):
        self.main_window.comboBoxProfileSort.setCurrentIndex(0) #set dropdown sort to no
        # Get selected row
        row = self.main_window.tableWidgetProfilePoints.currentRow()

        if row > 0:
            self.main_window.tableWidgetProfilePoints.insertRow(row - 1)
            for i in range(self.main_window.tableWidgetProfilePoints.columnCount()):
                self.main_window.tableWidgetProfilePoints.setItem(row - 1, i, self.main_window.tableWidgetProfilePoints.takeItem(row + 1, i))
            self.main_window.tableWidgetProfilePoints.removeRow(row + 1)
            self.main_window.tableWidgetProfilePoints.setCurrentCell(row - 1, 0)
            # Update self.profiles here accordingly
            for key, profile in self.profiles.items():
                if row >0:
                    profile[row], profile[row -1 ] = profile[row - 1], profile[row]
            self.plot_profiles(sort_axis = False)
    def move_point_down(self):
        self.main_window.comboBoxProfileSort.setCurrentIndex(0) #set dropdown sort to no
        # Similar to move_point_up, but moving the row down
        row = self.main_window.tableWidgetProfilePoints.currentRow()
        max_row = self.main_window.tableWidgetProfilePoints.rowCount() - 1
        if row < max_row:
            self.main_window.tableWidgetProfilePoints.insertRow(row + 2)
            for i in range(self.main_window.tableWidgetProfilePoints.columnCount()):
                self.main_window.tableWidgetProfilePoints.setItem(row + 2, i, self.main_window.tableWidgetProfilePoints.takeItem(row, i))
            self.main_window.tableWidgetProfilePoints.removeRow(row)
            self.main_window.tableWidgetProfilePoints.setCurrentCell(row + 1, 0)
            # update point order of each profile
            for key, profile in self.profiles.items():
                if row < len(profile) - 1:
                    profile[row], profile[row + 1] = profile[row + 1], profile[row]
            self.plot_profiles(sort_axis = False)


    def delete_point(self):
        # Get selected row and delete it
        row = self.main_window.tableWidgetProfilePoints.currentRow()
        self.main_window.tableWidgetProfilePoints.removeRow(row)

        # remove point from each profile and its corresponding scatter plot item
        for key, profile in self.profiles.items():
            if row < len(profile):
                scatter_item = profile[row][3]  # Access the scatter plot item
                for _, (_, plot, _, _) in self.main_window.lasermaps.items():
                    plot.removeItem(scatter_item)
                profile.pop(row) #index starts at 0
        self.plot_profiles(sort_axis = False)



    def toggle_buttons(self, enable):
        self.main_window.toolButtonPointUp.setEnabled(enable)
        self.main_window.toolButtonPointDown.setEnabled(enable)
        self.main_window.toolButtonPointDelete.setEnabled(enable)




app = None
def main():
    global app

    app = QtWidgets.QApplication(sys.argv)

    main = MainWindow()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()