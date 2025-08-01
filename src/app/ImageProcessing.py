import numpy as np
import pandas as pd
import matplotlib.colors as colors
import src.common.CustomMplCanvas as mplc
from scipy import ndimage
from scipy.signal import convolve2d, wiener, decimate
from pyqtgraph import ( ImageItem )
import cv2
from src.common.Logger import log, auto_log_methods

# -------------------------------------
# Image processing functions
# -------------------------------------
@auto_log_methods(logger_key='Image')
class ImageProcessing():
    """Image processing methods for use in LaME.

    Methods
    -------

    add_edge_detection :
        Add edge detection to the current laser map plot.
    remove_edge_detection:
        Removes edge detection from the current map.
    zero_crossing_lapalcian :
        Apply zero-crossing on the Laplacian of the image.
    noise_reduction_method_callback :
        Sets up noise reduction controls when noise reduction method is changed.
    gaussian_sigma :
        Sets default Gaussian sigma for Gaussian blur.
    run_noise_reduction :
        Gets parameters and runs noise reduction
    noise_reduction_option1_callback :
        Callback executed when the first noise reduction option is changed
    noise_reduction_option2_callback :
        Callback executed when the second noise reduction option is changed
    noise_reduction :
        Add noise reduction to the current laser map plot.
    plot_gradient : 
        Produces a gradient map with arrows showing gradient direction and colors indicating magnitude
    """
    def __init__(self, parent):
        self.logger_key = 'Image'

        self.parent = parent

        self.noise_red_img = None
        self.grad_img = None
        self.noise_red_options = {'median':{'label1':'Kernel size', 'value1':5, 'label2':None},
            'gaussian':{'label1':'Kernel size', 'value1':5, 'label2':'Sigma', 'value2':self.gaussian_sigma(5)},
            'wiener':{'label1':'Kernel size', 'value1':5, 'label2':None},
            'edge-preserving':{'label1':'Sigma S', 'value1':5, 'label2':'Sigma R', 'value2': 0.2},
            'bilateral':{'label1':'Diameter', 'value1':9, 'label2':'Sigma', 'value2':75}}

        self.noise_red_array = pd.DataFrame()

        self.update_noise1_flag = False
        self.update_noise2_flag = False

        # add edge detection algorithm to aid in creating polygons
        self.edge_img = None

        self._noise_reduction_methods = ['none','median','Gaussian','Wiener','edge-preserving','bilateral']
        self._edge_detection_methods = ['Sobel','Canny','zero cross']


    def add_edge_detection(self):
        """Add edge detection to the current laser map plot.

        Executes on change of ``MainWindow.comboBoxEdgeDetectMethod`` when ``MainWindow.toolButtonEdgeDetect`` is checked.
        Options include 'sobel', 'canny', and 'zero_cross'.
        """
        if self.edge_img:
            # remove existing filters
            self.remove_edge_detection()

        algorithm = self.parent.app_data.edge_detection_method.lower()
        if algorithm == 'sobel':
            # Apply Sobel edge detection
            sobelx = cv2.Sobel(self.array, cv2.CV_64F, 1, 0, ksize=5)
            sobely = cv2.Sobel(self.array, cv2.CV_64F, 0, 1, ksize=5)
            edge_detected_image = np.sqrt(sobelx**2 + sobely**2)
        elif algorithm == 'canny':

            # Normalize the array to [0, 1]
            normalized_array = (self.array - np.nanmin(self.array)) / (np.nanmax(self.array) - np.nanmin(self.array))

            # Scale to [0, 255] and convert to uint8
            scaled_array = (normalized_array * 255).astype(np.uint8)

            # Apply Canny edge detection
            edge_detected_image = cv2.Canny(scaled_array, 100, 200)
        elif algorithm == 'zero cross':
            # Apply Zero Crossing edge detection (This is a placeholder as OpenCV does not have a direct function)
            # You might need to implement a custom function or find a library that supports Zero Crossing
            edge_detected_image = self.zero_crossing_laplacian(self.array)  # Placeholder, replace with actual Zero Crossing implementation
        else:
            raise ValueError("Unsupported algorithm. Choose 'sobel', 'canny', or 'zero cross'.")

        # Assuming you have a way to display this edge_detected_image on your plot.
        # This could be an update to an existing ImageItem or creating a new one if necessary.
        self.edge_array = edge_detected_image
        if (np.nanmin(self.edge_array) < 0) or (np.nanmax(self.edge_array) > 255):
            self.edge_array = (self.edge_array - np.nanmin(self.edge_array)) / (np.nanmax(self.edge_array) - np.nanmin(self.edge_array))

            # Scale to [0, 255] and convert to uint8
            self.edge_array = (self.edge_array * 255).astype(np.uint8)

        self.edge_img = ImageItem(image=self.edge_array)
        #set aspect ratio of rectangle
        #self.edge_img.setRect(0,0,self.x_range,self.y_range)
        # edge_img.setAs
        #cm = colormap.get(style['Colors']['Colormap'], source = 'matplotlib')
        #self.edge_img.setColorMap(cm)
        #self.plot.addItem(self.edge_img)

        overlay_image = np.zeros(self.edge_array.shape+(4,), dtype=np.uint8)
        colorlist = self.parent.get_rgb_color(self.parent.plot_style.overlay_color)
        overlay_image[..., 0] = colorlist[0]  # Red channel
        overlay_image[..., 1] = colorlist[1]  # Green channel
        overlay_image[..., 2] = colorlist[2]  # Blue channel
        overlay_image[..., 3] = 0.9*self.edge_array

        self.edge_img = ImageItem(image=overlay_image)

        #set aspect ratio of rectangle
        x_range = self.parent.data[self.parent.sample_id].x_range
        y_range = self.parent.data[self.parent.sample_id].y_range
        self.edge_img.setRect(0,0,x_range,y_range)
        self.parent.plot.addItem(self.edge_img)

    def remove_edge_detection(self):
        """Removes edge detection from the current map."""
        if self.edge_img:
            self.parent.plot.removeItem(self.edge_img)

    def zero_crossing_laplacian(self,array):
        """Apply Zero Crossing on the Laplacian of the image.

        Parameters
        ----------
        array : numpy.ndarray
            Image data
        
        Returns
        -------
        numpy.ndarray
            Edge-detected image using the zero crossing method.
        """
        # Normalize the array to [0, 1]
        normalized_array = (array - np.nanmin(array)) / (np.nanmax(array) - np.nanmin(array))

        # Scale to [0, 255] and convert to uint8
        image = (normalized_array * 255).astype(np.uint8)


        # Apply Gaussian filter for noise reduction
        blurred_image = ndimage.gaussian_filter(image, sigma=6)

        # Apply Laplacian operator
        # laplacian_image = ndimage.laplace(blurred_image)

        LoG_kernel = np.array([
                                [0, 0,  1, 0, 0],
                                [0, 1,  2, 1, 0],
                                [1, 2,-16, 2, 1],
                                [0, 1,  2, 1, 0],
                                [0, 0,  1, 0, 0]
                            ])


        laplacian_image = convolve2d(blurred_image,LoG_kernel)

        # Find zero crossings
        zero_crossings = np.zeros_like(laplacian_image)
        # Shift the image by one pixel in all directions
        for shift in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            shifted = np.roll(np.roll(laplacian_image, shift[0], axis=0), shift[1], axis=1)
            # A zero crossing occurs where the product of the original and the shifted image is less than zero (sign change)
            zero_mask = (laplacian_image * shifted) < 0
            zero_crossings[zero_mask] = 1
        return zero_crossings

    def gaussian_sigma(self, ksize):
        """Sets default Gaussian sigma for Gaussian blur.

        Same as default in OpenCV, i.e., 0.3 ((ksize-1)/2 - 1) + 0.8. This functions sets the sigma
        value for ``cv2.GaussianBlur`` only when ``MainWindow.comboBoxNoiseReductionMethod`` is 'Gaussian' and new kernel
        value is set by the user via ``MainWindow.spinBoxNoiseReductionOption1.value()``.
        """
        return 0.3*((ksize-1)*0.5 - 1) + 0.8


    def noise_reduction(self, algorithm, val1=None, val2=None):
        """
        Add noise reduction to the current laser map plot.

        Executes on change of ``MainWindow.comboBoxNoiseReductionMethod``, ``MainWindow.spinBoxNoiseOption1`` and
        ``MainWindow.doubleSpinBoxOption2``. Updates map(s).

        Reduces noise by smoothing via one of several algorithms chosen from
        ``MainWindow.comboBoxNoiseReductionMethod``.

        Parameters
        ----------
        algorithm : str
            Options include:
            | 'None' - no smoothing
            | 'Median' - simple blur that computes each pixel from the median of a window including surrounding points
            | 'Gaussian' - a simple Gaussian blur
            | 'Weiner' - a Fourier domain filtering method that low pass filters to smooth the map
            | 'Edge-preserving' - filter that does an excellent job of preserving edges when smoothing
            | 'Bilateral' - an edge-preserving Gaussian weighted filter
        val1 : int, optional
            First filter argument, required for all filters
        val2 : float, optional
            Second filter argument, required for *Gaussian*, *Edge-preserving*, and *Bilateral* methods
        """
        # if self.noise_red_img:
        #     # Remove existing filters
        #     self.plot.removeItem(self.noise_red_img)

        # if self.grad_img:
        #     self.plot.removeItem(self.grad_img)

        # get data for current map
        field_type = self.parent.comboBoxColorByField.currentText()
        field = self.parent.comboBoxColorField.currentText()

        map_df = self.parent.data[self.parent.sample_id].get_map_data(field, field_type=field_type)
        array_size = self.parent.data[self.parent.sample_id].array_size
        aspect_ratio = self.parent.data[self.parent.sample_id].aspect_ratio

        # plot map
        self.array = np.reshape(map_df['array'].values, array_size, order=self.parent.data[self.parent.sample_id].order)

        match algorithm:
            case 'none':
                return
            case 'median':
                if val1 is None:
                    raise ValueError("val1 must be an odd integer greater than 1 for median")
                # Apply Median filter
                image = self.array.astype(np.float32)

                kernel_size = int(val1)
                if kernel_size % 2 == 0 or kernel_size < 1:
                    raise ValueError("Kernel size (val1) must be an odd integer greater than 1 for median")

                filtered_image = cv2.medianBlur(image, kernel_size)  # Kernel size is 5
            case 'gaussian':
                if val1 is None or val2 is None:
                    raise ValueError("val1 and val2 must be defined for gaussian")

                image = self.array.astype(np.float32)
                kernel_size = (int(val1), int(val1))

                if kernel_size[0] % 2 == 0 or kernel_size[1] % 2 == 0 or min(kernel_size) < 1:
                    raise ValueError("Kernel size must be a tuple of odd integers greater than 1")

                # Apply Median filter
                filtered_image = cv2.GaussianBlur(image, ksize = kernel_size, sigmaX=float(val2), sigmaY=float(val2))  # Kernel size is 5
            case 'wiener':
                if val1 is None:
                    raise ValueError("val1 must be an integer for wiener")
                # Apply Wiener filter
                # Wiener filter in scipy expects the image in double precision
                # Myopic deconvolution, kernel size set by spinBoxNoiseOption1
                filtered_image = wiener(self.array.astype(np.float64), (int(val1), int(val1)))
                filtered_image = filtered_image.astype(np.float32)  # Convert back to float32 to maintain consistency
            case 'edge-preserving':
                if val1 is None or val2 is None:
                    raise ValueError("val1 and val2 must be defined for edge-preserving")

                # Apply Edge-Preserving filter (RECURSIVE_FILTER or NORMCONV_FILTER)
                # Normalize the array to [0, 1]
                normalized_array = (self.array - np.nanmin(self.array)) / (np.nanmax(self.array) - np.nanmin(self.array))

                # Scale to [0, 255] and convert to uint8
                image = (normalized_array * 255).astype(np.uint8)
                filtered_image = cv2.edgePreservingFilter(image, flags=1, sigma_s=float(val1), sigma_r=float(val2))

                # convert back to original units
                filtered_image = (filtered_image.astype(np.float32) / 255) * (np.nanmax(self.array) - np.nanmin(self.array)) + np.nanmin(self.array)
                
            case 'bilateral':
                if val1 is None or val2 is None:
                    raise ValueError("val1 and val2 must be defined for edge-preserving")

                # Apply Bilateral filter
                # Parameters are placeholders, you might need to adjust them based on your data
                filtered_image = cv2.bilateralFilter(self.array.astype(np.float32), int(val1), float(val2), float(val2))

        # Update or create the image item for displaying the filtered image
        self.noise_red_array = filtered_image

        if self.parent.checkBoxGradient.isChecked() and self.parent.comboBoxPlotType.setCurrentText('gradient map'):
            self.plot_gradient()
            return
        else:
            if self.parent.comboBoxPlotType.currentText != 'field map':
                self.parent.plot_style.plot_type = 'field map'


        canvas = mplc.MplCanvas(parent=self.parent)

        norm = self.parent.plot_style.color_norm()
        cax = canvas.axes.imshow(filtered_image, cmap=self.parent.plot_style.get_colormap(),  aspect=aspect_ratio, interpolation='none', norm=norm)

        # set color limits
        self.parent.add_colorbar(canvas, cax)
        cax.set_clim(self.parent.plot_style.clim[0], self.parent.plot_style.clim[1])

        # use mask to create an alpha layer
        mask = self.parent.data[self.parent.sample_id].mask.astype(float)
        reshaped_mask = np.reshape(mask, array_size, order=self.parent.data[self.parent.sample_id].order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)

        # add scalebar
        self.parent.add_scalebar(canvas.axes)

        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        canvas.fig.tight_layout()

        field = self.parent.comboBoxColorField.currentText()
        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': self.parent.sample_id,
            'plot_name': field,
            'plot_type': 'field map',
            'field_type': self.parent.comboBoxColorByField.currentText(),
            'field': field,
            'figure': canvas,
            'style': self.parent.plot_style.style_dict[self.parent.plot_style.plot_type],
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }

        self.parent.canvas_widget.clear_layout(self.parent.widgetSingleView.layout())
        self.parent.widgetSingleView.layout().addWidget(canvas)

        self.parent.plot_tree.add_tree_item(self.plot_info)

    def plot_gradient(self):
        """
        Produces a gradient map with arrows showing gradient direction and colors indicating magnitude

        Executes only when ``MainWindow.comboBoxNoiseReductionMethod.currentText()`` is not ``none``,
        computes noise reduction and displays gradient map
        """
        # update plot type comboBox
        self.plot_flag = False
        self.plot_flat = True

        array_size = self.parent.data[self.parent.sample_id].array_size
        aspect_ratio = self.parent.data[self.parent.sample_id].aspect_ratio

        # Compute gradient
        grad_array = np.gradient(self.noise_red_array)
        # gradient magnitude
        self.grad_mag = np.sqrt(grad_array[0]**2 + grad_array[1]**2)

        dx = decimate(grad_array[0],10)
        dy = decimate(grad_array[1],10)

        x = np.arange((dx.T).shape[0])*10
        y = np.arange((dy.T).shape[1])*10
        X, Y = np.meshgrid(x, y)

        canvas = mplc.MplCanvas(parent=self.parent)

        q = np.quantile(self.grad_mag.flatten(), q=[0.025, 0.975])
        norm = colors.Normalize(q[0],q[1], clip=False)

        cax = canvas.axes.imshow(self.grad_mag, cmap=self.parent.plot_style.get_colormap(),  aspect=aspect_ratio, interpolation='none', norm=norm)
        canvas.axes.quiver(X,Y,dx,dy, color=self.parent.plot_style.overlay_color, linewidth=0.5)

        # set color limits
        #self.add_colorbar(canvas, cax, style)
        #cax.set_clim(style['Colors']['CLim'][0], style['Colors']['CLim'][1])

        # use mask to create an alpha layer
        mask = self.parent.data[self.parent.sample_id].mask.astype(float)
        reshaped_mask = np.reshape(mask, array_size, order=self.parent.data[self.parent.sample_id].order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)
        #cax = canvas.axes.imshow(self.array, alpha=alphas, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)
        #canvas.axes.set_facecolor('w')

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)

        # add scalebar
        self.parent.add_scalebar(canvas.axes)

        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        canvas.fig.tight_layout()

        field = self.parent.comboBoxColorField.currentText()
        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': self.parent.sample_id,
            'plot_name': field,
            'plot_type': 'field map',
            'field_type': self.parent.comboBoxColorByField.currentText(),
            'field': field,
            'figure': canvas,
            'style': self.parent.plot_style.style_dict[self.parent.plot_style.plot_type],
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }

        self.parent.canvas_widget.clear_layout(self.parent.widgetSingleView.layout())
        self.parent.widgetSingleView.layout().addWidget(canvas)

    def histogram_equalization(array):
        """Apply histogram equalization to an array.

        Transforms an array such that the histogram becomes uniform.  This is useful for
        equally distributing colors for maps.
        
        Parameters
        ----------
        array : np.ndarray
            Array to transform
        """
        sorted_vals = np.sort(array.ravel())
        cdf = np.searchsorted(sorted_vals, array.ravel(), side='right') / len(sorted_vals)

        return cdf.reshape(array.shape)


@auto_log_methods(logger_key='Image')
class ImageProcessingUI(ImageProcessing):
    def __init__(self, parent):
        super().__init__(self)
        self.logger_key = 'Image'

        self.ui = parent

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

    def connect_widgets(self):
        # noise reduction
        self.ui.comboBoxNoiseReductionMethod.clear()
        self.ui.comboBoxNoiseReductionMethod.addItems(self._noise_reduction_methods)
        self.ui.comboBoxNoiseReductionMethod.activated.connect(self.noise_reduction_method_callback)

        self.ui.spinBoxNoiseOption1.setEnabled(False)
        self.ui.labelNoiseOption1.setEnabled(False)
        self.ui.spinBoxNoiseOption1.valueChanged.connect(self.noise_reduction_option1_callback)

        self.ui.doubleSpinBoxNoiseOption2.setEnabled(False)
        self.ui.labelNoiseOption2.setEnabled(False)
        self.ui.doubleSpinBoxNoiseOption2.valueChanged.connect(self.noise_reduction_option2_callback)

        self.ui.checkBoxGradient.stateChanged.connect(self.gradient_checked_state_changed)
        self.ui.checkBoxGradient.stateChanged.connect(self.noise_reduction_method_callback)

    def connect_observer(self):
        """Connects properties to observer functions."""
        pass

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxNoiseReductionMethod.activated.connect(lambda: log(f"comboBoxNoiseReductionMethod value=[{self.ui.comboBoxNoiseReductionMethod.currentText()}]", prefix="UI"))
        self.ui.spinBoxNoiseOption1.valueChanged.connect(lambda: log(f"spinBoxNoiseOption1 value=[{self.ui.spinBoxNoiseOption1.value}]", prefix="UI"))
        self.ui.doubleSpinBoxNoiseOption2.valueChanged.connect(lambda: log(f"doubleSpinBoxNoiseOption2 value=[{self.ui.doubleSpinBoxNoiseOption2.value}]", prefix="UI"))
        self.ui.checkBoxApplyNoiseReduction.checkStateChanged.connect(lambda: log(f"checkBoxApplyNoiseReduction value=[{self.ui.checkBoxApplyNoiseReduction.isChecked()}]", prefix="UI"))
        self.ui.checkBoxGradient.checkStateChanged.connect(lambda: log(f"checkBoxGradient value=[{self.ui.checkBoxGradient.isChecked()}]", prefix="UI"))

    def update_noise_red_method_combobox(self, new_noise_red_method):
        self.ui.comboBoxNoiseReductionMethod.setCurrentText(new_noise_red_method)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample']:
            self.ui.plot_style.schedule_update()

    def update_noise_red_option1_spinbox(self, new_noise_red_option1):
        self.ui.spinBoxNoiseOption1.setValue(new_noise_red_option1)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample']:
            self.ui.plot_style.schedule_update()

    def update_noise_red_option2_spinbox(self, new_noise_red_option2):
        self.ui.doubleSpinBoxNoiseOption2.setValue(new_noise_red_option2)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample']:
            self.ui.plot_style.schedule_update()
    
    def update_gradient_flag_checkbox(self, new_gradient_flag):
        self.ui.checkBoxGradient.setChecked(new_gradient_flag)
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['sample']:
            self.ui.plot_style.schedule_update()

    def gradient_checked_state_changed(self):
        if self.parent.checkBoxGradient.isChecked():
            self.parent.plot_style.plot_type = 'gradient map'
        else:
            if self.parent.comboBoxPlotType.currentText != 'field map':
                self.parent.plot_style.plot_type = 'field map'

    def noise_reduction_method_callback(self):
        """Sets up noise reduction controls when noise reduction method is changed.

        Executes when ``MainWindow.comboBoxNoiseReductionMethod.currentText()`` is changed.
        Enables ``MainWindow.spinBoxNoiseOption1`` and ``MainWindow.doubleSpinBoxNoiseOption2`` (if applicable)
        and associated labels.  Constraints on the ranges are added to the spin boxes.

        After enabling options, it runs ``noise_reduction``.
        """
        algorithm = self.parent.comboBoxNoiseReductionMethod.currentText().lower()

        match algorithm:
            case 'none':
                # turn options off
                self.parent.labelNoiseOption1.setEnabled(False)
                self.parent.labelNoiseOption1.setText('')
                self.parent.spinBoxNoiseOption1.setEnabled(False)
                self.parent.labelNoiseOption2.setEnabled(False)
                self.parent.labelNoiseOption2.setText('')
                self.parent.doubleSpinBoxNoiseOption2.setEnabled(False)

                self.noise_reduction(algorithm)
                self.parent.comboBoxApplyNoiseReduction.setEnabled(False)
                self.parent.labelApplySmoothing.setEnabled(False)
                self.parent.checkBoxGradient.setEnabled(False)
                self.parent.labelGradient.setEnabled(False)

                self.parent.actionNoiseReduction.setEnabled(False)

                self.parent.plot_style.scheduler.schedule_update()
            case _:
                # set option 1
                self.parent.spinBoxNoiseOption1.blockSignals(True)
                self.parent.labelNoiseOption1.setEnabled(True)
                self.parent.labelNoiseOption1.setText(self.noise_red_options[algorithm]['label1'])
                self.parent.spinBoxNoiseOption1.setEnabled(True)
                match algorithm:
                    case 'median':
                        self.parent.spinBoxNoiseOption1.setRange(1,5)
                        self.parent.spinBoxNoiseOption1.setSingleStep(2)
                    case 'gaussian' | 'wiener':
                        self.parent.spinBoxNoiseOption1.setRange(1,199)
                        self.parent.spinBoxNoiseOption1.setSingleStep(2)
                    case 'edge-preserving':
                        self.parent.spinBoxNoiseOption1.setRange(0,200)
                        self.parent.spinBoxNoiseOption1.setSingleStep(5)
                    case _:
                        self.parent.spinBoxNoiseOption1.setRange(0,200)
                        self.parent.spinBoxNoiseOption1.setSingleStep(5)

                self.parent.spinBoxNoiseOption1.setValue(int(self.noise_red_options[algorithm]['value1']))
                self.parent.spinBoxNoiseOption1.blockSignals(False)
                #self.comboBoxApplyNoiseReduction.setEnabled(True)
                #self.labelApplySmoothing.setEnabled(True)
                self.parent.checkBoxGradient.setEnabled(True)
                self.parent.labelGradient.setEnabled(True)
                self.parent.actionNoiseReduction.setEnabled(True)

                val1 = self.parent.spinBoxNoiseOption1.value()

                # set option 2
                if self.noise_red_options[algorithm]['label2'] is None:
                    # no option 2
                    self.parent.labelNoiseOption2.setEnabled(False)
                    self.parent.labelNoiseOption2.setText('')
                    self.parent.doubleSpinBoxNoiseOption2.setEnabled(False)

                    self.noise_reduction(algorithm, val1)
                else:
                    # yes option 2
                    self.parent.doubleSpinBoxNoiseOption2.blockSignals(True)
                    self.parent.labelNoiseOption2.setEnabled(True)
                    self.parent.labelNoiseOption2.setText(self.noise_red_options[algorithm]['label2'])
                    self.parent.doubleSpinBoxNoiseOption2.setEnabled(True)
                    match algorithm:
                        case 'edge-preserving':
                            self.parent.doubleSpinBoxNoiseOption2.setRange(0,1)
                        case 'bilateral':
                            self.parent.doubleSpinBoxNoiseOption2.setRange(0,200)

                    self.parent.doubleSpinBoxNoiseOption2.setValue(self.noise_red_options[algorithm]['value2'])
                    self.parent.doubleSpinBoxNoiseOption2.blockSignals(False)

                    val2 = self.parent.doubleSpinBoxNoiseOption2.value()
                    self.noise_reduction(algorithm, val1, val2)

    def noise_reduction_option2_callback(self):
        """Callback executed when the second noise reduction option is changed

        Updates noise reduction applied to map(s) when ``MainWindow.spinBoxNoiseOption2.value()`` is changed by
        the user.  Note, not all noise reduction methods have a second option."""
        algorithm = self.parent.comboBoxNoiseReductionMethod.currentText().lower()

        val1 = self.parent.spinBoxNoiseOption1.value()
        val2 = self.parent.doubleSpinBoxNoiseOption2.value()
        self.noise_red_options[algorithm]['value2'] = val2
        self.noise_reduction(algorithm,val1,val2)

    def run_noise_reduction(self):
        """Gets parameters and runs noise reduction"""

        algorithm = self.parent.comboBoxNoiseReductionMethod.currentText().lower()
        if algorithm == 'none':
            return

        val1 = self.noise_red_options[algorithm]['value1']
        if self.noise_red_options[algorithm]['label2'] is None:
            self.noise_reduction(algorithm,val1)
        else:
            val2 = self.noise_red_options[algorithm]['value2']
            self.noise_reduction(algorithm,val1,val2)

    def noise_reduction_option1_callback(self):
        """Callback executed when the first noise reduction option is changed

        Updates noise reduction applied to map(s) when ``MainWindow.spinBoxNoiseOption1.value()`` is changed by
        the user."""
        algorithm = self.parent.comboBoxNoiseReductionMethod.currentText().lower()

        # get option 1
        val1 = self.parent.spinBoxNoiseOption1.value()
        match algorithm:
            case 'median' | 'gaussian' | 'wiener':
                # val1 must be odd
                if val1 % 2 != 1:
                    val1 = val1 + 1
        self.noise_red_options[algorithm]['value1'] = val1

        # add a second parameter (if required and run noise reduction)
        if self.noise_red_options[algorithm]['label2'] is None:
            self.noise_reduction(algorithm,val1)

        else:
            if algorithm == 'gaussian':
                val2 = self.gaussian_sigma(val1)
                self.parent.doubleSpinBoxNoiseOption2.blockSignals(True)
                self.parent.doubleSpinBoxNoiseOption2.setValue(val2)
                self.parent.doubleSpinBoxNoiseOption2.blockSignals(False)
                self.noise_red_options[algorithm]['value2'] = val2
            else:
                val2 = self.parent.doubleSpinBoxNoiseOption2.value()

            self.noise_reduction(algorithm,val1,val2)