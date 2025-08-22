import colorsys
import re
from typing import Union, Tuple, Optional, Any
from PyQt6.QtGui import QColor

# Add numpy support with graceful fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


class ColorConverter:
    """Unified color conversion system supporting multiple color formats, including numpy arrays."""
    
    @staticmethod
    def _is_numeric(value: Any) -> bool:
        """Check if value is numeric, including numpy numeric types."""
        if isinstance(value, (int, float)):
            return True
        if HAS_NUMPY and isinstance(value, np.number):
            return True
        return False
    
    @staticmethod
    def _to_python_float(value: Any) -> float:
        """Convert numeric value to Python float, handling numpy types."""
        if HAS_NUMPY and isinstance(value, np.number):
            return float(value)
        return float(value)
    
    @staticmethod
    def _is_array_like(obj: Any) -> bool:
        """Check if object is array-like (list, tuple, or numpy array)."""
        if isinstance(obj, (list, tuple)):
            return True
        if HAS_NUMPY and isinstance(obj, np.ndarray):
            return True
        return False
    
    @staticmethod
    def _to_list(obj: Any) -> list:
        """Convert array-like object to list."""
        if isinstance(obj, (list, tuple)):
            return list(obj)
        if HAS_NUMPY and isinstance(obj, np.ndarray):
            return obj.tolist()
        return [obj]
    
    @staticmethod
    def validate_color(color: Any) -> bool:
        """
        Validate if the input is a valid color in any supported format.
        
        Parameters
        ----------
        color : Any
            Input color to validate (supports numpy arrays and numpy numeric types)
            
        Returns
        -------
        bool
            True if color is valid, False otherwise
            
        Examples
        --------
        >>> ColorConverter.validate_color('#ff0000')
        True
        >>> ColorConverter.validate_color(np.array([1.0, 0.0, 0.0]))
        True
        >>> ColorConverter.validate_color((np.float64(1.0), np.float64(0.0), np.float64(0.0)))
        True
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
        """Validate RGB color values, including numpy arrays and numpy numeric types."""
        if not ColorConverter._is_array_like(color):
            return False
        
        try:
            color_list = ColorConverter._to_list(color)
            if len(color_list) < 3 or len(color_list) > 4:
                return False
            
            r, g, b = color_list[:3]
            alpha = color_list[3] if len(color_list) > 3 else None
            
            # Check if values are numeric (including numpy types)
            if not all(ColorConverter._is_numeric(v) for v in color_list[:3]):
                return False
            
            # Convert to Python floats for range checking
            r_f = ColorConverter._to_python_float(r)
            g_f = ColorConverter._to_python_float(g)
            b_f = ColorConverter._to_python_float(b)
            
            # Check ranges - support both 0-1 and 0-255
            if all(0 <= v <= 1 for v in [r_f, g_f, b_f]):
                # Normalized range (0-1)
                valid_rgb = True
            elif all(0 <= v <= 255 for v in [r_f, g_f, b_f]):
                # Integer range (0-255)
                valid_rgb = True
            else:
                valid_rgb = False
            
            # Validate alpha if present
            if alpha is not None:
                if not ColorConverter._is_numeric(alpha):
                    return False
                alpha_f = ColorConverter._to_python_float(alpha)
                # Alpha can be 0-1 or 0-255 depending on RGB range
                max_rgb = max(r_f, g_f, b_f)
                if max_rgb <= 1:
                    valid_alpha = 0 <= alpha_f <= 1
                else:
                    valid_alpha = 0 <= alpha_f <= 255
            else:
                valid_alpha = True
            
            return valid_rgb and valid_alpha
            
        except (TypeError, IndexError, ValueError):
            return False
    
    @staticmethod
    def _validate_hsv(color: Union[tuple, list]) -> bool:
        """Validate HSV color values, including numpy arrays and numpy numeric types."""
        if not ColorConverter._is_array_like(color):
            return False
        
        try:
            color_list = ColorConverter._to_list(color)
            if len(color_list) < 3 or len(color_list) > 4:
                return False
            
            h, s, v = color_list[:3]
            alpha = color_list[3] if len(color_list) > 3 else None
            
            # Check if values are numeric
            if not all(ColorConverter._is_numeric(val) for val in color_list[:3]):
                return False
            
            # Convert to Python floats
            h_f = ColorConverter._to_python_float(h)
            s_f = ColorConverter._to_python_float(s)
            v_f = ColorConverter._to_python_float(v)
            
            # Hue: 0-360 degrees or 0-1 normalized
            valid_h = (0 <= h_f <= 360) or (0 <= h_f <= 1)
            
            # Saturation and Value: 0-1 or 0-100
            valid_s = (0 <= s_f <= 1) or (0 <= s_f <= 100)
            valid_v = (0 <= v_f <= 1) or (0 <= v_f <= 100)
            
            # Validate alpha if present
            if alpha is not None:
                if not ColorConverter._is_numeric(alpha):
                    return False
                alpha_f = ColorConverter._to_python_float(alpha)
                valid_alpha = 0 <= alpha_f <= 1
            else:
                valid_alpha = True
            
            return valid_h and valid_s and valid_v and valid_alpha
            
        except (TypeError, IndexError, ValueError):
            return False
    
    @staticmethod
    def _validate_hsl(color: Union[tuple, list]) -> bool:
        """Validate HSL color values, including numpy arrays and numpy numeric types."""
        if not ColorConverter._is_array_like(color):
            return False
        
        try:
            color_list = ColorConverter._to_list(color)
            if len(color_list) < 3 or len(color_list) > 4:
                return False
            
            h, s, l = color_list[:3]
            alpha = color_list[3] if len(color_list) > 3 else None
            
            # Check if values are numeric
            if not all(ColorConverter._is_numeric(val) for val in color_list[:3]):
                return False
            
            # Convert to Python floats
            h_f = ColorConverter._to_python_float(h)
            s_f = ColorConverter._to_python_float(s)
            l_f = ColorConverter._to_python_float(l)
            
            # Hue: 0-360 degrees or 0-1 normalized
            valid_h = (0 <= h_f <= 360) or (0 <= h_f <= 1)
            
            # Saturation and Lightness: 0-1 or 0-100
            valid_s = (0 <= s_f <= 1) or (0 <= s_f <= 100)
            valid_l = (0 <= l_f <= 1) or (0 <= l_f <= 100)
            
            # Validate alpha if present
            if alpha is not None:
                if not ColorConverter._is_numeric(alpha):
                    return False
                alpha_f = ColorConverter._to_python_float(alpha)
                valid_alpha = 0 <= alpha_f <= 1
            else:
                valid_alpha = True
            
            return valid_h and valid_s and valid_l and valid_alpha
            
        except (TypeError, IndexError, ValueError):
            return False
    
    @staticmethod
    def _validate_cmyk(color: Union[tuple, list]) -> bool:
        """
        Validate CMYK color values, including numpy arrays and numpy numeric types.
        
        CMYK values are typically in 0-1 range (fractional) or 0-100 range (percentage).
        """
        if not ColorConverter._is_array_like(color):
            return False
        
        try:
            color_list = ColorConverter._to_list(color)
            if len(color_list) < 4 or len(color_list) > 5:
                return False
            
            c, m, y, k = color_list[:4]
            alpha = color_list[4] if len(color_list) > 4 else None
            
            # Check if values are numeric
            if not all(ColorConverter._is_numeric(val) for val in color_list[:4]):
                return False
            
            # Convert to Python floats
            cmyk_floats = [ColorConverter._to_python_float(val) for val in color_list[:4]]
            
            # CMYK values: 0-1 (fractional) or 0-100 (percentage)
            valid_cmyk = (all(0 <= val <= 1 for val in cmyk_floats) or 
                         all(0 <= val <= 100 for val in cmyk_floats))
            
            # Validate alpha if present
            if alpha is not None:
                if not ColorConverter._is_numeric(alpha):
                    return False
                alpha_f = ColorConverter._to_python_float(alpha)
                valid_alpha = 0 <= alpha_f <= 1
            else:
                valid_alpha = True
            
            return valid_cmyk and valid_alpha
            
        except (TypeError, IndexError, ValueError):
            return False
    
    @staticmethod
    def _detect_input_type(color: Any) -> Optional[str]:
        """
        Detect the input color type, including numpy arrays.
        
        Parameters
        ----------
        color : Any
            Input color in any supported format
            
        Returns
        -------
        Optional[str]
            Detected color type: 'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'
            Returns None if color format cannot be detected or is invalid
        """
        try:
            if isinstance(color, QColor):
                return 'qcolor' if color.isValid() else None
            
            elif isinstance(color, str):
                return 'hex' if ColorConverter._validate_hex(color) else None
            
            elif ColorConverter._is_array_like(color):
                color_list = ColorConverter._to_list(color)
                length = len(color_list)
                
                # Special handling for single QColor in a list/tuple/array
                if length == 1 and isinstance(color_list[0], QColor):
                    return 'qcolor' if color_list[0].isValid() else None
                
                # Check if it's a list/tuple/array of multiple QColor objects
                if length > 1 and all(isinstance(item, QColor) for item in color_list):
                    return None
                
                # Check if any element is a QColor (mixed types - not supported as single color)
                if any(isinstance(item, QColor) for item in color_list):
                    return None
                
                if length == 4 or (length == 5 and all(ColorConverter._is_numeric(v) for v in color_list)):
                    # Could be CMYK (4 values) or CMYKA (5 values)
                    if ColorConverter._validate_cmyk(color):
                        return 'cmyk'
                
                if length >= 3:
                    # Try to determine between RGB, HSV, HSL
                    if ColorConverter._validate_rgb(color):
                        # Check if it looks more like HSV
                        h, s, v = color_list[:3]
                        if (ColorConverter._is_numeric(h) and 
                            ColorConverter._to_python_float(h) > 1 and 
                            all(0 <= ColorConverter._to_python_float(val) <= 1 for val in color_list[1:3])):
                            if ColorConverter._validate_hsv(color):
                                return 'hsv'
                        return 'rgb'
                    
                    elif ColorConverter._validate_hsv(color):
                        return 'hsv'
                    
                    elif ColorConverter._validate_hsl(color):
                        return 'hsl'
            
            return None  # Cannot detect or invalid format
            
        except (TypeError, AttributeError, IndexError, ValueError):
            return None
    
    @staticmethod
    def _normalize_to_rgb(color: Any, input_type: str = None) -> Optional[Tuple[float, float, float, float]]:
        """
        Convert any color format to normalized RGBA (0-1 range), including numpy arrays.
        
        Parameters
        ----------
        color : Any
            Input color in any format (supports numpy arrays)
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
            
            # Handle special case of single QColor in a list/tuple/array
            if input_type == 'qcolor' and ColorConverter._is_array_like(color):
                color_list = ColorConverter._to_list(color)
                if len(color_list) == 1:
                    color = color_list[0]  # Extract the QColor from the container
            
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
            
            elif input_type in ['rgb', 'hsv', 'hsl', 'cmyk']:
                # Convert to list and handle numpy types
                color_list = ColorConverter._to_list(color)
                
                if input_type == 'rgb':
                    r, g, b = [ColorConverter._to_python_float(v) for v in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
                    # Normalize to 0-1 if values are in 0-255 range
                    if any(v > 1 for v in [r, g, b]):
                        r, g, b = r/255.0, g/255.0, b/255.0
                        if len(color_list) > 3 and ColorConverter._to_python_float(color_list[3]) > 1:
                            alpha = alpha / 255.0
                    
                    return r, g, b, alpha
                
                elif input_type == 'hsv':
                    h, s, v = [ColorConverter._to_python_float(val) for val in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
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
                    h, s, l = [ColorConverter._to_python_float(val) for val in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
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
                    c, m, y, k = [ColorConverter._to_python_float(val) for val in color_list[:4]]
                    alpha = ColorConverter._to_python_float(color_list[4]) if len(color_list) > 4 else 1.0
                    
                    # Normalize to 0-1 if values are in 0-100 range
                    if any(v > 1 for v in [c, m, y, k]):
                        c, m, y, k = c/100.0, m/100.0, y/100.0, k/100.0
                    
                    # Convert CMYK to RGB
                    r = (1 - c) * (1 - k)
                    g = (1 - m) * (1 - k)
                    b = (1 - y) * (1 - k)
                    
                    return r, g, b, alpha
            
            return None
                
        except (ValueError, TypeError, IndexError, AttributeError):
            return None


# Keep all the existing conversion functions with the same signatures
def color_to_rgb(color: Any, input_type: str = None, 
                 normalize: bool = True, include_alpha: bool = False) -> Optional[Union[Tuple[float, ...], Tuple[int, ...]]]:
    """
    Convert any color format to RGB, including numpy arrays and numpy numeric types.
    
    Parameters
    ----------
    color : Any
        Input color in any supported format (RGB, HSV, HSL, CMYK, hex, QColor, numpy arrays)
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
    >>> color_to_rgb(np.array([1.0, 0.0, 0.0]))
    (1.0, 0.0, 0.0)
    >>> color_to_rgb((np.float64(1.0), np.float64(0.0), np.float64(0.0)))
    (1.0, 0.0, 0.0)
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
    """Convert any color format to HSV, including numpy arrays and numpy numeric types."""
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
    """Convert any color format to HSL, including numpy arrays and numpy numeric types."""
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
    """Convert any color format to CMYK, including numpy arrays and numpy numeric types."""
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
    """Convert any color format to hex string, including numpy arrays and numpy numeric types."""
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
    """Convert any color format to QColor, including numpy arrays and numpy numeric types."""
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
    """Convert a list of colors to the specified output type, including numpy arrays."""
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
    # Test numpy support if available
    if HAS_NUMPY:
        print("=== NumPy Support Tests ===")
        
        # Test numpy array with regular tuples
        np_rgb = np.array([1.0, 0.0, 0.0])
        print(f"NumPy RGB array: {color_to_rgb(np_rgb)}")
        
        # Test tuple with numpy float64 values
        np_tuple_rgb = (np.float64(1.0), np.float64(0.0), np.float64(0.0))
        print(f"Tuple with numpy floats: {color_to_rgb(np_tuple_rgb)}")
        
        # Test validation
        print(f"NumPy array validation: {ColorConverter.validate_color(np_rgb)}")
        print(f"NumPy tuple validation: {ColorConverter.validate_color(np_tuple_rgb)}")
        
        # Test type detection
        print(f"NumPy array type detection: {ColorConverter._detect_input_type(np_rgb)}")
        print(f"NumPy tuple type detection: {ColorConverter._detect_input_type(np_tuple_rgb)}")
        
        # Test all conversions with numpy data
        print("\n=== NumPy Conversion Tests ===")
        test_np_color = np.array([0.8, 0.2, 0.6, 0.9])  # RGBA
        print(f"NumPy RGBA: {test_np_color}")
        print(f"  To RGB: {color_to_rgb(test_np_color)}")
        print(f"  To HSV: {color_to_hsv(test_np_color)}")
        print(f"  To HSL: {color_to_hsl(test_np_color)}")
        print(f"  To CMYK: {color_to_cmyk(test_np_color)}")
        print(f"  To Hex: {color_to_hex(test_np_color)}")
        
        # Test batch conversion with mixed numpy and regular data
        mixed_colors_with_np = [
            np.array([1.0, 0.0, 0.0]),
            (np.float64(0.0), np.float64(1.0), np.float64(0.0)),
            '#0000ff',
            (0.5, 0.5, 0.5)
        ]
        rgb_results_np = convert_color_list(mixed_colors_with_np, 'rgb', normalize=False)
        print(f"\nMixed colors with NumPy: {[str(c) for c in mixed_colors_with_np]}")
        print(f"RGB Results: {rgb_results_np}")
        
        # Test array of tuples with numpy floats (your specific case)
        print("\n=== Array of NumPy Float Tuples Test ===")
        color_tuples = np.array([
            (np.float64(1.0), np.float64(0.0), np.float64(0.0)),  # Red
            (np.float64(0.0), np.float64(1.0), np.float64(0.0)),  # Green
            (np.float64(0.0), np.float64(0.0), np.float64(1.0)),  # Blue
        ])
        
        print(f"Array of numpy float tuples shape: {color_tuples.shape}")
        print(f"Individual tuple type: {type(color_tuples[0])}")
        print(f"Individual value type: {type(color_tuples[0][0])}")
        
        # Test individual conversions
        for i, color_tuple in enumerate(color_tuples):
            converted = color_to_rgb(color_tuple)
            print(f"Color {i}: {color_tuple} -> {converted}")
            
        # Test batch conversion
        batch_converted = convert_color_list(color_tuples.tolist(), 'hex')
        print(f"Batch to hex: {batch_converted}")
    
    else:
        print("NumPy not available - skipping NumPy-specific tests")
    
    # Standard validation tests (same as before)
    print("\n=== Standard Color Validation Tests ===")
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