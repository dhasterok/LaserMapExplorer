import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.image as mpimg

class CropTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Crop Tool')
        self.setGeometry(100, 100, 800, 600)

        self.image_path = 'image.jpg'
        self.image = mpimg.imread(self.image_path)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.imshow(self.image)
        self.canvas.draw()

        self.label = QLabel(self)
        self.label.setText("Click and drag to select region of interest. Then click 'Crop'.")
        self.label.setGeometry(10, 10, 500, 20)

        self.crop_button = QPushButton('Crop', self)
        self.crop_button.setGeometry(10, 40, 100, 30)
        self.crop_button.clicked.connect(self.crop_image)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.rectangle = None
        self.start = None
        self.end = None

        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        if event.button == 1:
            self.start = (event.xdata, event.ydata)

    def on_motion(self, event):
        if event.button == 1 and self.start:
            if self.rectangle:
                self.rectangle.remove()
            x0, y0 = self.start
            x1, y1 = event.xdata, event.ydata
            width = x1 - x0
            height = y1 - y0
            self.rectangle = Rectangle((x0, y0), width, height, linewidth=1, edgecolor='r', facecolor='none')
            self.ax.add_patch(self.rectangle)
            self.canvas.draw()

    def on_release(self, event):
        if event.button == 1:
            self.end = (event.xdata, event.ydata)

    def crop_image(self):
        if self.start and self.end:
            x0, y0 = min(self.start[0], self.end[0]), min(self.start[1], self.end[1])
            x1, y1 = max(self.start[0], self.end[0]), max(self.start[1], self.end[1])
            cropped_image = self.image[int(y0):int(y1), int(x0):int(x1)]
            mpimg.imsave('cropped_image.jpg', cropped_image)
            print("Image cropped and saved as 'cropped_image.jpg'.")
        else:
            print("Please select a region of interest first.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = CropTool()
    mainWindow.show()
    sys.exit(app.exec_())