import os

# __file__ holds full path of current python file
BASEDIR = os.path.dirname(__file__)
# Path to the icons directory
ICONPATH = os.path.join(BASEDIR, 'resources', 'icons')
# Path to the stylesheet
SSPATH = os.path.join(BASEDIR, 'resources', 'styles')

def load_stylesheet(filename):
    replacements = {
        '{icon_path}': ICONPATH.replace('\\', '/'),  # Ensure correct path format
    }
    with open(os.path.join(SSPATH,filename), "r") as file:
        stylesheet = file.read()
    for key, value in replacements.items():
        stylesheet = stylesheet.replace(key, value)
    return stylesheet 