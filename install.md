# Step 1: Install anaconda 

https://www.anaconda.com/download

# Step 2: Install git

windows: open anaconda prompt
mac/linux: open terminal

conda install git


# Step 3: Clone repository to local directory

git clone https://github.com/dhasterok/LaserMapExplorer.git
cd LaserMapExplorer


# Step 4: Install anaconda 

https://www.anaconda.com/download

# Step 5: Create virtual environment in anaconda 

conda create --name pyqt python=3.11 --file req.txt
conda activate pyqt

# if Step 5 fails, try:

conda create --name pyqt python=3.11
conda activate pyqt
conda install python=3.11 pyqt pyqtgraph PyQtWebEngine pandas matplotlib scikit-learn openpyxl numexpr
conda install conda-forge/label/cf201901::scikit-fuzzy
pip install darkdetect cmcrameri rst2pdf
pip install -U scikit-fuzzy
pip install opencv-python-headless
# Step 6: Run main.py on spyder or on terminal 

python3 main.py


# libraries needed
darkdetect
PyQt5
pyqtgraph
pandas
matplotlib
cmcrameri
scipy
numpy
scikit-learn
scikit-learn-extra
scikit-fuzzy
opencv-python
numexpr
rst2pdf
PyQtWebEngine
openpyxl

you'll also need blockly
so you'll need to install npm and Node.js and from the blockly directory, run

rm -rf node_modules
npm install
npx webpack --config webpack.config.js

