# Step 1: Clone repository to local directory
git clone https://github.com/shavinkalu23/LaserMapExplorer.git
cd LaserMapExplorer

# Step 2: Install qt designer to make changes to the UI 

https://www.qt.io/download-qt-installer-oss?hsCtaTracking=99d9dd4f-5681-48d2-b096-470725510d34%7C074ddad0-fdef-4e53-8aa8-5e8a876d6ab4

# Step 3: Install anaconda 

https://www.anaconda.com/download

# Step 4: Create virtual environment in anaconda 

conda create --name pyqt python=3.9
conda activate pyqt

# Step 5: Install package list
conda install --file packagelist.txt

# Step 6: Run main.py on spyder or on terminal 

python3 main.py
