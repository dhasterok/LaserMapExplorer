from pathlib import Path

# __file__ holds the full path to the current Python file
BASEDIR = Path(__file__).resolve().parent.parent.parent

# Path to the resources directory
RESOURCE_PATH = BASEDIR / 'resources'

# Path to app_data directory
APPDATA_PATH = RESOURCE_PATH / 'app_data'

# Path to the icons directory
ICONPATH = RESOURCE_PATH / 'icons'

# Path to the stylesheet directory
SSPATH = RESOURCE_PATH / 'styles'

def load_stylesheet(filename):
    replacements = {
        '{icon_path}': str(ICONPATH.as_posix()),  # Ensure forward slashes
    }
    with open(SSPATH / filename, "r", encoding="utf-8") as file:
        stylesheet = file.read()
    for key, value in replacements.items():
        stylesheet = stylesheet.replace(key, value)
    return stylesheet