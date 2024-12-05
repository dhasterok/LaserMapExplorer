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
conda install python=3.11 pyqt pyqtgraph PyQtWebEngine pandas matplotlib scikit-learn yopencv openpyxl numexpr
conda install conda-forge/label/cf201901::scikit-fuzzy
pip install darkdetect cmcrameri rst2pdf
pip install -U scikit-fuzzy
# Step 6: Run main.py on spyder or on terminal 

python3 main.py
