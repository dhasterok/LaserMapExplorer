import numpy as np

def get_hex_color(color):
    """Converts QColor to hex-rgb format

    Parameters
    ----------
    color : list of int
        RGB color triplet

    Returns
    -------
    str : 
        hex code for an RGB color triplet
    """
    if type(color) is tuple:
        color = np.round(255*np.array(color))
        color[color < 0] = 0
        color[color > 255] = 255
        return "#{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))
    else:
        return "#{:02x}{:02x}{:02x}".format(color.red(), color.green(), color.blue())

def get_rgb_color(color):
    """Convert from hex to RGB formatted color

    Parameters
    ----------
    color : str or list
        Converts a hex str to RGB colors.  If list, should be a list of hex str.

    Returns
    -------
    list of int or list of RGB tuples:
        RGB color triplets used to create colormaps.
    """        
    if not color:
        return []
    elif isinstance(color,str):
        color = color.lstrip('#').lower()
        return [int(color[0:2],16), int(color[2:4],16), int(color[4:6],16)]
    else:
        color_list = [None]*len(color)
        for i, hexcolor in enumerate(color):
            rgb = get_rgb_color(hexcolor)
            color_list[i] = tuple(float(c)/255 for c in rgb) + (1.0,)
        return color_list