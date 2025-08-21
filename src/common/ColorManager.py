import colorsys
import re
from typing import Union, Tuple, Optional, Any
from PyQt6.QtGui import QColor


class ColorConverter:
    """Unified color conversion system supporting multiple color formats."""
    
    @staticmethod
    def validate_color(color: Any) -> bool:
        """
        Validate if the input is a valid color in any supported format.
        
        Parameters
        ----------
        color : Any
            Input color to validate
            
        Returns
        -------
        bool
            True if color is valid, False otherwise
            
        Examples
        --------
        >>> ColorConverter.validate_color('#ff0000')
        True
        >>> ColorConverter.validate_color('#xyz123')
        False
        >>> ColorConverter.validate_color((255, 0, 0))
        True
        >>> ColorConverter.validate_color((300, 0, 0))  # Invalid RGB
        False
        """
        try:
            detected_type = ColorConverter._detect_input_type(color)
            return ColorConverter._validate_by_type(color, detected_type)
        except (ValueError, TypeError, AttributeError):
            return False
    
    @staticmethod
    def _validate_by_type(color: Any, color_type: str) -> bool:
        """
        Validate color based on its detected type.
        
        Parameters
        ----------
        color : Any
            Input color
        color_type : str
            Detected color type
            
        Returns
        -------
        bool
            True if valid for the detected type
        """
        if color_type == 'qcolor':
            return isinstance(color, QColor) and color.isValid()
        
        elif color_type == 'hex':
            return ColorConverter._validate_hex(color)
        
        elif color_type == 'rgb':
            return ColorConverter._validate_rgb(color)
        
        elif color_type == 'hsv':
            return ColorConverter._validate_hsv(color)
        
        elif color_type == 'hsl':
            return ColorConverter._validate_hsl(color)
        
        elif color_type == 'cmyk':
            return ColorConverter._validate_cmyk(color)
        
        return False
    
    @staticmethod
    def _validate_hex(hex_str: str) -> bool:
        """Validate hex color string."""
        if hex_str is None or not isinstance(hex_str, str):
            return False
        
        # Remove leading # if present
        hex_str = hex_str.lstrip('#')
        
        # Valid patterns: 3, 4, 6, or 8 hex digits
        pattern = re.compile(r"^([A-Fa-f0-9]{3}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")
        return bool(pattern.match(hex_str))
    
    @staticmethod
    def _validate_rgb(color: Union[tuple, list]) -> bool:
        """Validate RGB color values."""
        if not isinstance(color, (tuple, list)) or len(color) < 3 or len(color) > 4:
            return False
        
        try:
            r, g, b = color[:3]
            alpha = color[3] if len(color) > 3 else None
            
            # Check if values are numeric
            if not all(isinstance(v, (int, float)) for v in color[:3]):
                return False
            
            # Check ranges - support both 0-1 and 0-255
            if all(0 <= v <= 1 for v in color[:3]):
                # Normalized range (0-1)
                valid_rgb = True
            elif all(0 <= v <= 255 for v in color[:3]):
                # Integer range (0-255)
                valid_rgb = True
            else:
                valid_rgb = False
            
            # Validate alpha if present
            if alpha is not None:
                if not isinstance(alpha, (int, float)):
                    return False
                # Alpha can be 0-1 or 0-255 depending on RGB range
                max_rgb = max(color[:3])
                if max_rgb <= 1:
                    valid_alpha = 0 <= alpha <= 1
                else:
                    valid_alpha = 0 <= alpha <= 255
            else:
                valid_alpha = True
            
            return valid_rgb and valid_alpha
            
        except (TypeError, IndexError):
            return False
    
    @staticmethod
    def _validate_hsv(color: Union[tuple, list]) -> bool:
        """Validate HSV color values."""
        if not isinstance(color, (tuple, list)) or len(color) < 3 or len(color) > 4:
            return False
        
        try:
            h, s, v = color[:3]
            alpha = color[3] if len(color) > 3 else None
            
            # Check if values are numeric
            if not all(isinstance(val, (int, float)) for val in color[:3]):
                return False
            
            # Hue: 0-360 degrees or 0-1 normalized
            valid_h = (0 <= h <= 360) or (0 <= h <= 1)
            
            # Saturation and Value: 0-1 or 0-100
            valid_s = (0 <= s <= 1) or (0 <= s <= 100)
            valid_v = (0 <= v <= 1) or (0 <= v <= 100)
            
            # Validate alpha if present
            if alpha is not None:
                if not isinstance(alpha, (int, float)):
                    return False
                valid_alpha = 0 <= alpha <= 1
            else:
                valid_alpha = True
            
            return valid_h and valid_s and valid_v and valid_alpha
            
        except (TypeError, IndexError):
            return False
    
    @staticmethod
    def _validate_hsl(color: Union[tuple, list]) -> bool:
        """Validate HSL color values."""
        if not isinstance(color, (tuple, list)) or len(color) < 3 or len(color) > 4:
            return False
        
        try:
            h, s, l = color[:3]
            alpha = color[3] if len(color) > 3 else None
            
            # Check if values are numeric
            if not all(isinstance(val, (int, float)) for val in color[:3]):
                return False
            
            # Hue: 0-360 degrees or 0-1 normalized
            valid_h = (0 <= h <= 360) or (0 <= h <= 1)
            
            # Saturation and Lightness: 0-1 or 0-100
            valid_s = (0 <= s <= 1) or (0 <= s <= 100)
            valid_l = (0 <= l <= 1) or (0 <= l <= 100)
            
            # Validate alpha if present
            if alpha is not None:
                if not isinstance(alpha, (int, float)):
                    return False
                valid_alpha = 0 <= alpha <= 1
            else:
                valid_alpha = True
            
            return valid_h and valid_s and valid_l and valid_alpha
            
        except (TypeError, IndexError):
            return False
    
    @staticmethod
    def _validate_cmyk(color: Union[tuple, list]) -> bool:
        """
        Validate CMYK color values.
        
        CMYK values are typically in 0-1 range (fractional) or 0-100 range (percentage).
        """
        if not isinstance(color, (tuple, list)) or len(color) < 4 or len(color) > 5:
            return False
        
        try:
            c, m, y, k = color[:4]
            alpha = color[4] if len(color) > 4 else None
            
            # Check if values are numeric
            if not all(isinstance(val, (int, float)) for val in color[:4]):
                return False
            
            # CMYK values: 0-1 (fractional) or 0-100 (percentage)
            valid_cmyk = (all(0 <= val <= 1 for val in color[:4]) or 
                         all(0 <= val <= 100 for val in color[:4]))
            
            # Validate alpha if present
            if alpha is not None:
                if not isinstance(alpha, (int, float)):
                    return False
                valid_alpha = 0 <= alpha <= 1
            else:
                valid_alpha = True
            
            return valid_cmyk and valid_alpha
            
        except (TypeError, IndexError):
            return False
    
    @staticmethod
    def _detect_input_type(color: Any) -> Optional[str]:
        """
        Detect the input color type.
        
        Parameters
        ----------
        color : Any
            Input color in any supported format
            
        Returns
        -------
        Optional[str]
            Detected color type: 'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'
            Returns None if color format cannot be detected or is invalid
            
        Examples
        --------
        >>> ColorConverter._detect_input_type('#ff0000')
        'hex'
        >>> ColorConverter._detect_input_type((255, 0, 0))
        'rgb'
        >>> ColorConverter._detect_input_type('invalid')
        None
        """
        try:
            if isinstance(color, QColor):
                return 'qcolor' if color.isValid() else None
            
            elif isinstance(color, str):
                return 'hex' if ColorConverter._validate_hex(color) else None
            
            elif isinstance(color, (tuple, list)):
                length = len(color)
                
                # Special handling for single QColor in a list/tuple
                if length == 1 and isinstance(color[0], QColor):
                    # This is a single QColor wrapped in a list/tuple
                    # We should treat this as the QColor itself for conversion
                    return 'qcolor' if color[0].isValid() else None
                
                # Check if it's a list/tuple of multiple QColor objects (not a single color)
                if length > 1 and all(isinstance(item, QColor) for item in color):
                    # This is a list of multiple QColor objects, not a single color
                    return None
                
                # Check if any element is a QColor (mixed types - not supported as single color)
                if any(isinstance(item, QColor) for item in color):
                    return None
                
                if length == 4 or (length == 5 and all(isinstance(v, (int, float)) for v in color)):
                    # Could be CMYK (4 values) or CMYKA (5 values)
                    if ColorConverter._validate_cmyk(color):
                        return 'cmyk'
                
                if length >= 3:
                    # Try to determine between RGB, HSV, HSL
                    if ColorConverter._validate_rgb(color):
                        # Check if it looks more like HSV
                        h, s, v = color[:3]
                        if isinstance(h, (int, float)) and h > 1 and all(0 <= val <= 1 for val in color[1:3]):
                            if ColorConverter._validate_hsv(color):
                                return 'hsv'
                        return 'rgb'
                    
                    elif ColorConverter._validate_hsv(color):
                        return 'hsv'
                    
                    elif ColorConverter._validate_hsl(color):
                        return 'hsl'
            
            return None  # Cannot detect or invalid format
            
        except (TypeError, AttributeError, IndexError):
            return None
    
    @staticmethod
    def _normalize_to_rgb(color: Any, input_type: str = None) -> Optional[Tuple[float, float, float, float]]:
        """
        Convert any color format to normalized RGBA (0-1 range).
        
        Parameters
        ----------
        color : Any
            Input color in any format
        input_type : str, optional
            Explicit input type, by default None (auto-detect)
            
        Returns
        -------
        Optional[Tuple[float, float, float, float]]
            RGBA values in 0-1 range, or None if conversion fails
        """
        try:
            if input_type is None:
                input_type = ColorConverter._detect_input_type(color)
                if input_type is None:
                    return None
            
            # Handle special case of single QColor in a list/tuple
            if input_type == 'qcolor' and isinstance(color, (list, tuple)) and len(color) == 1:
                color = color[0]  # Extract the QColor from the container
            
            # Validate the color for the detected/specified type
            if not ColorConverter._validate_by_type(color, input_type):
                return None
            
            alpha = 1.0  # Default alpha
            
            if input_type == 'qcolor':
                return color.redF(), color.greenF(), color.blueF(), color.alphaF()
            
            elif input_type == 'hex':
                # Handle hex strings
                hex_str = color.lstrip('#')
                if len(hex_str) == 3:
                    hex_str = ''.join([c*2 for c in hex_str])
                elif len(hex_str) == 4:
                    hex_str = ''.join([c*2 for c in hex_str])
                
                if len(hex_str) == 6:
                    r = int(hex_str[0:2], 16) / 255.0
                    g = int(hex_str[2:4], 16) / 255.0
                    b = int(hex_str[4:6], 16) / 255.0
                elif len(hex_str) == 8:
                    r = int(hex_str[0:2], 16) / 255.0
                    g = int(hex_str[2:4], 16) / 255.0
                    b = int(hex_str[4:6], 16) / 255.0
                    alpha = int(hex_str[6:8], 16) / 255.0
                else:
                    return None
                
                return r, g, b, alpha
            
            elif input_type == 'rgb':
                r, g, b = color[:3]
                alpha = color[3] if len(color) > 3 else 1.0
                
                # Normalize to 0-1 if values are in 0-255 range
                if any(v > 1 for v in color[:3]):
                    r, g, b = r/255.0, g/255.0, b/255.0
                    if len(color) > 3 and color[3] > 1:
                        alpha = alpha / 255.0
                
                return r, g, b, alpha
            
            elif input_type == 'hsv':
                h, s, v = color[:3]
                alpha = color[3] if len(color) > 3 else 1.0
                
                # Normalize values to 0-1 range
                if h > 1:
                    h = h / 360.0
                if s > 1:
                    s = s / 100.0
                if v > 1:
                    v = v / 100.0
                
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                return r, g, b, alpha
            
            elif input_type == 'hsl':
                h, s, l = color[:3]
                alpha = color[3] if len(color) > 3 else 1.0
                
                # Normalize values to 0-1 range
                if h > 1:
                    h = h / 360.0
                if s > 1:
                    s = s / 100.0
                if l > 1:
                    l = l / 100.0
                
                r, g, b = colorsys.hls_to_rgb(h, l, s)  # Note: HLS in colorsys
                return r, g, b, alpha
            
            elif input_type == 'cmyk':
                c, m, y, k = color[:4]
                alpha = color[4] if len(color) > 4 else 1.0
                
                # Normalize to 0-1 if values are in 0-100 range
                if any(v > 1 for v in color[:4]):
                    c, m, y, k = c/100.0, m/100.0, y/100.0, k/100.0
                
                # Convert CMYK to RGB
                r = (1 - c) * (1 - k)
                g = (1 - m) * (1 - k)
                b = (1 - y) * (1 - k)
                
                return r, g, b, alpha
            
            else:
                return None
                
        except (ValueError, TypeError, IndexError, AttributeError):
            return None


def color_to_rgb(color: Any, input_type: str = None, 
                 normalize: bool = True, include_alpha: bool = False) -> Optional[Union[Tuple[float, ...], Tuple[int, ...]]]:
    """
    Convert any color format to RGB.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format (RGB, HSV, HSL, CMYK, hex, QColor)
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
    normalize : bool, optional
        If True, return values in 0-1 range, else 0-255 range, by default True
    include_alpha : bool, optional
        If True, include alpha channel in output, by default False
        
    Returns
    -------
    Optional[Union[Tuple[float, ...], Tuple[int, ...]]]
        RGB or RGBA values, or None if conversion fails
        
    Examples
    --------
    >>> color_to_rgb('#ff0000')
    (1.0, 0.0, 0.0)
    >>> color_to_rgb((255, 0, 0), normalize=False)
    (255, 0, 0)
    >>> color_to_rgb((0, 1, 1), input_type='hsv')
    (1.0, 0.0, 0.0)
    >>> color_to_rgb('invalid_color')
    None
    """
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    
    if not normalize:
        r, g, b, a = int(r * 255), int(g * 255), int(b * 255), int(a * 255)
    
    if include_alpha:
        return (r, g, b, a)
    else:
        return (r, g, b)


def color_to_hsv(color: Any, input_type: str = None, 
                 degrees: bool = True, include_alpha: bool = False) -> Optional[Tuple[float, ...]]:
    """
    Convert any color format to HSV.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
    degrees : bool, optional
        If True, return hue in 0-360 range, else 0-1 range, by default True
    include_alpha : bool, optional
        If True, include alpha channel in output, by default False
        
    Returns
    -------
    Optional[Tuple[float, ...]]
        HSV or HSVA values, or None if conversion fails
        
    Examples
    --------
    >>> color_to_hsv('#ff0000')
    (0.0, 1.0, 1.0)
    >>> color_to_hsv((1, 0, 0), degrees=False)
    (0.0, 1.0, 1.0)
    >>> color_to_hsv('invalid_color')
    None
    """
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    
    if degrees:
        h = h * 360.0
    
    if include_alpha:
        return (h, s, v, a)
    else:
        return (h, s, v)


def color_to_hsl(color: Any, input_type: str = None, 
                 degrees: bool = True, include_alpha: bool = False) -> Optional[Tuple[float, ...]]:
    """
    Convert any color format to HSL.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
    degrees : bool, optional
        If True, return hue in 0-360 range, else 0-1 range, by default True
    include_alpha : bool, optional
        If True, include alpha channel in output, by default False
        
    Returns
    -------
    Optional[Tuple[float, ...]]
        HSL or HSLA values, or None if conversion fails
        
    Examples
    --------
    >>> color_to_hsl('#ff0000')
    (0.0, 1.0, 0.5)
    >>> color_to_hsl((255, 0, 0), normalize=False)
    (0.0, 1.0, 0.5)
    >>> color_to_hsl('invalid_color')
    None
    """
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    h, l, s = colorsys.rgb_to_hls(r, g, b)  # Note: HLS in colorsys
    
    if degrees:
        h = h * 360.0
    
    if include_alpha:
        return (h, s, l, a)
    else:
        return (h, s, l)


def color_to_cmyk(color: Any, input_type: str = None, 
                  include_alpha: bool = False) -> Optional[Tuple[float, ...]]:
    """
    Convert any color format to CMYK.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
    include_alpha : bool, optional
        If True, include alpha channel in output, by default False
        
    Returns
    -------
    Optional[Tuple[float, ...]]
        CMYK or CMYKA values (0-1 range), or None if conversion fails
        
    Examples
    --------
    >>> color_to_cmyk('#ff0000')
    (0.0, 1.0, 1.0, 0.0)
    >>> color_to_cmyk((255, 255, 0), input_type='rgb')
    (0.0, 0.0, 1.0, 0.0)
    >>> color_to_cmyk('invalid_color')
    None
    """
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    
    # Convert RGB to CMYK
    k = 1 - max(r, g, b)
    
    if k == 1:  # Pure black
        c = m = y = 0
    else:
        c = (1 - r - k) / (1 - k)
        m = (1 - g - k) / (1 - k)
        y = (1 - b - k) / (1 - k)
    
    if include_alpha:
        return (c, m, y, k, a)
    else:
        return (c, m, y, k)


def color_to_hex(color: Any, input_type: str = None, 
                 include_alpha: bool = False, uppercase: bool = True) -> Optional[str]:
    """
    Convert any color format to hex string.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
    include_alpha : bool, optional
        If True, include alpha channel in hex output, by default False
    uppercase : bool, optional
        If True, return uppercase hex, by default True
        
    Returns
    -------
    Optional[str]
        Hex color string (e.g., '#FF0000' or '#FF0000FF'), or None if conversion fails
        
    Examples
    --------
    >>> color_to_hex((1, 0, 0))
    '#FF0000'
    >>> color_to_hex((255, 0, 0, 128), include_alpha=True, normalize=False)
    '#FF000080'
    >>> color_to_hex('invalid_color')
    None
    """
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    
    # Convert to 0-255 range
    r_int = int(r * 255)
    g_int = int(g * 255)
    b_int = int(b * 255)
    a_int = int(a * 255)
    
    if include_alpha:
        hex_str = f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
    else:
        hex_str = f"#{r_int:02x}{g_int:02x}{b_int:02x}"
    
    return hex_str.upper() if uppercase else hex_str


def color_to_qcolor(color: Any, input_type: str = None) -> Optional[QColor]:
    """
    Convert any color format to QColor.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format
    input_type : str, optional
        Explicit input type to skip auto-detection, by default None
        
    Returns
    -------
    Optional[QColor]
        Qt QColor object, or None if conversion fails
        
    Examples
    --------
    >>> qcolor = color_to_qcolor('#ff0000')
    >>> qcolor = color_to_qcolor((0, 1, 1), input_type='hsv')
    >>> qcolor = color_to_qcolor((0, 100, 100, 0), input_type='cmyk')
    >>> qcolor = color_to_qcolor('invalid_color')
    >>> qcolor is None
    True
    """
    if input_type == 'qcolor' or isinstance(color, QColor):
        return QColor(color) if (isinstance(color, QColor) and color.isValid()) else None
    
    result = ColorConverter._normalize_to_rgb(color, input_type)
    if result is None:
        return None
    
    r, g, b, a = result
    
    # QColor expects 0-255 range for setRgbF uses 0-1 range
    qcolor = QColor()
    qcolor.setRgbF(r, g, b, a)
    return qcolor


def convert_color_list(colors: list, output_type: str, **kwargs) -> list:
    """
    Convert a list of colors to the specified output type.
    
    Parameters
    ----------
    colors : list
        List of colors in any supported format
    output_type : str
        Target format: 'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'
    **kwargs
        Additional arguments passed to the conversion function
        
    Returns
    -------
    list
        List of converted colors (invalid colors are filtered out)
        
    Examples
    --------
    >>> colors = ['#ff0000', '#00ff00', '#0000ff', 'invalid']
    >>> convert_color_list(colors, 'rgb')
    [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    """
    conversion_funcs = {
        'rgb': color_to_rgb,
        'hsv': color_to_hsv,
        'hsl': color_to_hsl,
        'cmyk': color_to_cmyk,
        'hex': color_to_hex,
        'qcolor': color_to_qcolor
    }
    
    if output_type not in conversion_funcs:
        raise ValueError(f"Unsupported output type: {output_type}")
    
    func = conversion_funcs[output_type]
    converted = []
    
    for color in colors:
        result = func(color, **kwargs)
        if result is not None:
            converted.append(result)
    
    return converted


# Example usage and testing
if __name__ == "__main__":
    # Test validation
    print("=== Color Validation Tests ===")
    test_colors = [
        '#ff0000',      # Valid hex
        '#xyz123',      # Invalid hex
        (255, 0, 0),    # Valid RGB
        (300, 0, 0),    # Invalid RGB (out of range)
        (0, 1, 1),      # Valid HSV
        (0.0, 1.0, 0.5, 0.8),  # Valid HSLA
        (50, 75, 100, 25),     # Valid CMYK percentage
        'invalid'       # Invalid
    ]
    
    for color in test_colors:
        is_valid = ColorConverter.validate_color(color)
        detected_type = ColorConverter._detect_input_type(color)
        print(f"{str(color):20} -> Valid: {is_valid:5}, Type: {detected_type}")
    
    # Test QColor in list/tuple
    print("\n=== QColor in List Tests ===")
    qcolor_red = QColor(255, 0, 0)
    qcolor_list = [qcolor_red]
    qcolor_tuple = (qcolor_red,)
    
    print(f"Single QColor: {color_to_rgb(qcolor_red)}")
    print(f"QColor in list: {color_to_rgb(qcolor_list)}")
    print(f"QColor in tuple: {color_to_rgb(qcolor_tuple)}")
    
    # Test multiple QColors in list (should return None for individual conversion)
    qcolor_green = QColor(0, 255, 0)
    multiple_qcolors = [qcolor_red, qcolor_green]
    print(f"Multiple QColors in list: {color_to_rgb(multiple_qcolors)}")
    
    # Test conversions with validation
    print("\n=== Color Conversion Tests ===")
    valid_color = "#ff0000"
    invalid_color = "invalid_color"
    
    print(f"Valid color '{valid_color}':")
    print(f"  RGB: {color_to_rgb(valid_color)}")
    print(f"  HSV: {color_to_hsv(valid_color)}")
    print(f"  HSL: {color_to_hsl(valid_color)}")
    print(f"  CMYK: {color_to_cmyk(valid_color)}")
    print(f"  Hex: {color_to_hex(valid_color)}")
    print(f"  QColor valid: {color_to_qcolor(valid_color) is not None}")
    
    print(f"\nInvalid color '{invalid_color}':")
    print(f"  RGB: {color_to_rgb(invalid_color)}")
    print(f"  HSV: {color_to_hsv(invalid_color)}")
    print(f"  HSL: {color_to_hsl(invalid_color)}")
    print(f"  CMYK: {color_to_cmyk(invalid_color)}")
    print(f"  Hex: {color_to_hex(invalid_color)}")
    print(f"  QColor: {color_to_qcolor(invalid_color)}")
    
    # Test batch conversion with mixed valid/invalid colors
    print("\n=== Batch Conversion Test ===")
    mixed_colors = ['#ff0000', '#00ff00', 'invalid', (0, 255, 0)]
    rgb_results = convert_color_list(mixed_colors, 'rgb', normalize=False)
    print(f"Input: {mixed_colors}")
    print(f"RGB Results (invalid filtered out): {rgb_results}")
    
    # Test batch conversion with QColors
    print("\n=== Batch QColor Conversion Test ===")
    qcolor_mixed = [qcolor_red, qcolor_green, '#0000ff']
    rgb_qcolor_results = convert_color_list(qcolor_mixed, 'rgb', normalize=False)
    print(f"Input QColors + Hex: {[str(c) for c in qcolor_mixed]}")
    print(f"RGB Results: {rgb_qcolor_results}")