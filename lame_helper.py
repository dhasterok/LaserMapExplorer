import os

# __file__ holds full path of current python file
basedir = os.path.dirname(__file__)
# Path to the icons directory
iconpath = os.path.join(basedir, 'resources', 'icons')
# Path to the stylesheet
sspath = os.path.join(basedir, 'resources', 'styles')

def load_stylesheet(filename):
    replacements = {
        '{icon_path}': iconpath.replace('\\', '/'),  # Ensure correct path format
    }
    with open(os.path.join(sspath,filename), "r") as file:
        stylesheet = file.read()
    for key, value in replacements.items():
        stylesheet = stylesheet.replace(key, value)
    return stylesheet 