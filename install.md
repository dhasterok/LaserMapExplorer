# Installing LaME

## Prerequisites

- Python 3.11 or later
- git
- Node.js and npm (for the Blockly workflow editor)

---

## Step 1: Clone repositories

LaME requires several sibling packages. Clone them all into the same parent directory.

```bash
git clone https://github.com/dhasterok/LaserMapExplorer.git
git clone https://github.com/dhasterok/lame-core.git
git clone https://github.com/dhasterok/blueberry-colortools.git
git clone https://github.com/dhasterok/siesta-rest-editor.git
```

The result should look like:

```
GitHub/
├── LaserMapExplorer/
├── lame-core/
├── blueberry-colortools/
└── siesta-rest-editor/
```

---

## Step 2: Create a virtual environment

```bash
cd LaserMapExplorer
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

---

## Step 3: Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs the sibling packages in editable mode along with all other dependencies.

---

## Step 4: Build the Blockly workflow editor

```bash
cd blockly
npm install
npx webpack --config webpack.config.js
cd ..
```

---

## Step 5: Run LaME

```bash
python3 main.py
```
