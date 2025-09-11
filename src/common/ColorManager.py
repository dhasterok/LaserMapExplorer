#!/usr/bin/env python3
"""
Color Manager
Handles conversions between different color systems.

Created on Sat Aug 16 2025

@author: Derrick Hasterok
"""
import colorsys
import re
from typing import Union, Tuple, Optional, Any, List
from PyQt6.QtGui import QColor

# Add numpy support with graceful fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

def is_valid_hex_color(hex_str: str):
    """
    Validate if a string is a valid hex color in RGB (#RRGGBB) or RGBA (#RRGGBBAA) format.

    Parameters
    ----------
    hex_str : str
        The hex color string.

    Returns
    -------
    bool :
         True if valid, False otherwise.
    """
    if hex_str is None:
        return False

    pattern = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")
    return bool(pattern.match(hex_str))


class ColorConverter:
    """Unified color conversion system with explicit format specification."""
    
    # Supported color spaces
    SUPPORTED_FORMATS = {'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'}
    
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
    def _parse_to_rgba(color: Any, input_type: str, normalized: bool = True) -> Optional[Tuple[float, float, float, float]]:
        """
        Parse input color to normalized RGBA (0-1 range).
        
        Parameters
        ----------
        color : Any
            Input color
        input_type : str
            Color type ('rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor')
        normalized : bool
            Whether input values are normalized (0-1) or not
            
        Returns
        -------
        Optional[Tuple[float, float, float, float]]
            RGBA values in 0-1 range, or None if parsing fails
        """
        try:
            alpha = 1.0  # Default alpha
            
            if input_type == 'qcolor':
                if ColorConverter._is_array_like(color):
                    color_list = ColorConverter._to_list(color)
                    if len(color_list) == 1:
                        color = color_list[0]
                
                if not isinstance(color, QColor) or not color.isValid():
                    return None
                
                return color.redF(), color.greenF(), color.blueF(), color.alphaF()
            
            elif input_type == 'hex':
                if not isinstance(color, str):
                    return None
                
                hex_str = color.lstrip('#')
                
                # Validate hex format
                if not re.match(r"^([A-Fa-f0-9]{3}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$", hex_str):
                    return None
                
                # Expand short forms
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
                if not ColorConverter._is_array_like(color):
                    return None
                
                color_list = ColorConverter._to_list(color)
                
                # Check if all values are numeric
                if not all(ColorConverter._is_numeric(v) for v in color_list):
                    return None
                
                if input_type == 'rgb':
                    if len(color_list) < 3:
                        return None
                    
                    r, g, b = [ColorConverter._to_python_float(v) for v in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
                    # Normalize if needed
                    if not normalized:
                        r, g, b = r/255.0, g/255.0, b/255.0
                        if len(color_list) > 3:
                            alpha = alpha / 255.0
                    
                    return r, g, b, alpha
                
                elif input_type == 'hsv':
                    if len(color_list) < 3:
                        return None
                    
                    h, s, v = [ColorConverter._to_python_float(val) for val in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
                    # Normalize if needed
                    if not normalized:
                        h = h / 360.0 if h > 1 else h  # Handle both degree (0-360) and percentage (0-100) cases
                        s = s / 100.0 if s > 1 else s
                        v = v / 100.0 if v > 1 else v
                    
                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                    return r, g, b, alpha
                
                elif input_type == 'hsl':
                    if len(color_list) < 3:
                        return None
                    
                    h, s, l = [ColorConverter._to_python_float(val) for val in color_list[:3]]
                    alpha = ColorConverter._to_python_float(color_list[3]) if len(color_list) > 3 else 1.0
                    
                    # Normalize if needed
                    if not normalized:
                        h = h / 360.0 if h > 1 else h
                        s = s / 100.0 if s > 1 else s
                        l = l / 100.0 if l > 1 else l
                    
                    r, g, b = colorsys.hls_to_rgb(h, l, s)  # Note: HLS in colorsys
                    return r, g, b, alpha
                
                elif input_type == 'cmyk':
                    if len(color_list) < 4:
                        return None
                    
                    c, m, y, k = [ColorConverter._to_python_float(val) for val in color_list[:4]]
                    alpha = ColorConverter._to_python_float(color_list[4]) if len(color_list) > 4 else 1.0
                    
                    # Normalize if needed
                    if not normalized:
                        c, m, y, k = c/100.0, m/100.0, y/100.0, k/100.0
                    
                    # Convert CMYK to RGB
                    r = (1 - c) * (1 - k)
                    g = (1 - m) * (1 - k)
                    b = (1 - y) * (1 - k)
                    
                    return r, g, b, alpha
            
            return None
                
        except (ValueError, TypeError, IndexError, AttributeError):
            return None
    
    @staticmethod
    def _format_output(rgba: Tuple[float, float, float, float], 
                      output_type: str, 
                      normalized: bool = True, 
                      include_alpha: bool = None,
                      uppercase: bool = True) -> Any:
        """
        Format RGBA values to the specified output format.
        
        Parameters
        ----------
        rgba : Tuple[float, float, float, float]
            RGBA values in 0-1 range
        output_type : str
            Target format ('rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor')
        normalized : bool
            Whether to return normalized (0-1) or denormalized values
        include_alpha : bool, optional
            Whether to include alpha channel. If None, auto-detect based on alpha != 1.0
        uppercase : bool
            For hex output, whether to use uppercase letters
            
        Returns
        -------
        Any
            Formatted color in requested format
        """
        r, g, b, a = rgba
        
        # Auto-detect alpha inclusion if not specified
        if include_alpha is None:
            include_alpha = (a != 1.0)
        
        if output_type == 'rgb':
            if normalized:
                return (r, g, b, a) if include_alpha else (r, g, b)
            else:
                r_int, g_int, b_int = int(r * 255), int(g * 255), int(b * 255)
                a_int = int(a * 255)
                return (r_int, g_int, b_int, a_int) if include_alpha else (r_int, g_int, b_int)
        
        elif output_type == 'hsv':
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            if normalized:
                return (h, s, v, a) if include_alpha else (h, s, v)
            else:
                h_deg, s_pct, v_pct = h * 360.0, s * 100.0, v * 100.0
                return (h_deg, s_pct, v_pct, a) if include_alpha else (h_deg, s_pct, v_pct)
        
        elif output_type == 'hsl':
            h, l, s = colorsys.rgb_to_hls(r, g, b)  # Note: HLS in colorsys
            
            if normalized:
                return (h, s, l, a) if include_alpha else (h, s, l)
            else:
                h_deg, s_pct, l_pct = h * 360.0, s * 100.0, l * 100.0
                return (h_deg, s_pct, l_pct, a) if include_alpha else (h_deg, s_pct, l_pct)
        
        elif output_type == 'cmyk':
            # Convert RGB to CMYK
            k = 1 - max(r, g, b)
            
            if k == 1:  # Pure black
                c = m = y = 0
            else:
                c = (1 - r - k) / (1 - k)
                m = (1 - g - k) / (1 - k)
                y = (1 - b - k) / (1 - k)
            
            if normalized:
                return (c, m, y, k, a) if include_alpha else (c, m, y, k)
            else:
                c_pct, m_pct, y_pct, k_pct = c * 100.0, m * 100.0, y * 100.0, k * 100.0
                return (c_pct, m_pct, y_pct, k_pct, a) if include_alpha else (c_pct, m_pct, y_pct, k_pct)
        
        elif output_type == 'hex':
            # Convert to 0-255 range
            r_int = max(0, min(255, int(r * 255)))
            g_int = max(0, min(255, int(g * 255)))
            b_int = max(0, min(255, int(b * 255)))
            a_int = max(0, min(255, int(a * 255)))
            
            if include_alpha:
                hex_str = f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
            else:
                hex_str = f"#{r_int:02x}{g_int:02x}{b_int:02x}"
            
            return hex_str.upper() if uppercase else hex_str
        
        elif output_type == 'qcolor':
            qcolor = QColor()
            qcolor.setRgbF(r, g, b, a)
            return qcolor
        
        return None


def convert_color(color: Any, 
                 input_format: str, 
                 output_format: str,
                 norm_in: bool = True,
                 norm_out: bool = True, 
                 include_alpha: bool = None,
                 uppercase: bool = True) -> Any:
    """
    Convert color between different formats with explicit format specification.
    
    Parameters
    ----------
    color : Any
        Input color in the specified input format
    input_format : str
        Input format: 'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'
    output_format : str
        Output format: 'rgb', 'hsv', 'hsl', 'cmyk', 'hex', 'qcolor'
    norm_in : bool, default True
        Whether input values are normalized (0-1) or not (0-255 for RGB, 0-360/0-100 for HSV/HSL, etc.)
    norm_out : bool, default True
        Whether to return normalized (0-1) or denormalized values
    include_alpha : bool, optional
        Whether to include alpha channel. If None, auto-detect based on input
    uppercase : bool, default True
        For hex output, whether to use uppercase letters
        
    Returns
    -------
    Any
        Converted color in the specified output format, or None if conversion fails
        
    Examples
    --------
    >>> convert_color([255, 0, 0], 'rgb', 'hex', norm_in=False)
    '#FF0000'
    
    >>> convert_color('#FF0000', 'hex', 'hsv', norm_out=False)
    (0.0, 100.0, 100.0)
    
    >>> convert_color(np.array([1.0, 0.0, 0.0]), 'rgb', 'hsl')
    (0.0, 1.0, 0.5)
    
    >>> convert_color([360, 100, 50], 'hsv', 'rgb', norm_in=False, norm_out=False)
    (128, 0, 128)
    """
    # Validate formats
    if input_format not in ColorConverter.SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported input format: {input_format}. Supported: {ColorConverter.SUPPORTED_FORMATS}")
    
    if output_format not in ColorConverter.SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}. Supported: {ColorConverter.SUPPORTED_FORMATS}")
    
    # Parse input to normalized RGBA
    rgba = ColorConverter._parse_to_rgba(color, input_format, norm_in)
    if rgba is None:
        return None
    
    # Format output
    return ColorConverter._format_output(rgba, output_format, norm_out, include_alpha, uppercase)


def convert_color_list(colors: List[Any], 
                      input_format: str, 
                      output_format: str,
                      **kwargs) -> List[Any]:
    """
    Convert a list of colors between formats.
    
    Parameters
    ----------
    colors : List[Any]
        List of input colors
    input_format : str
        Input format for all colors
    output_format : str
        Output format for all colors
    **kwargs
        Additional arguments passed to convert_color
        
    Returns
    -------
    List[Any]
        List of converted colors (failed conversions are omitted)
    """
    converted = []
    for color in colors:
        result = convert_color(color, input_format, output_format, **kwargs)
        if result is not None:
            converted.append(result)
    return converted


# Example usage and testing
if __name__ == "__main__":
    print("=== Unified Color Converter Tests ===")
    
    # Test basic conversions
    print("\n--- Basic Conversions ---")
    red_rgb = [255, 0, 0]
    print(f"RGB {red_rgb} -> Hex: {convert_color(red_rgb, 'rgb', 'hex', norm_in=False)}")
    print(f"RGB {red_rgb} -> HSV: {convert_color(red_rgb, 'rgb', 'hsv', norm_in=False, norm_out=False)}")
    
    red_hex = '#FF0000'
    print(f"Hex {red_hex} -> RGB: {convert_color(red_hex, 'hex', 'rgb', norm_out=False)}")
    print(f"Hex {red_hex} -> HSL: {convert_color(red_hex, 'hex', 'hsl', norm_out=False)}")
    
    # Test normalized vs unnormalized
    print("\n--- Normalized vs Unnormalized ---")
    normalized_rgb = [1.0, 0.5, 0.0]
    print(f"Normalized RGB {normalized_rgb} -> HSV (normalized): {convert_color(normalized_rgb, 'rgb', 'hsv')}")
    print(f"Normalized RGB {normalized_rgb} -> HSV (degrees): {convert_color(normalized_rgb, 'rgb', 'hsv', norm_out=False)}")
    
    # Test with alpha
    print("\n--- Alpha Channel ---")
    rgba = [255, 128, 0, 128]
    print(f"RGBA {rgba} -> Hex: {convert_color(rgba, 'rgb', 'hex', norm_in=False, include_alpha=True)}")
    print(f"RGBA {rgba} -> HSV: {convert_color(rgba, 'rgb', 'hsv', norm_in=False, include_alpha=True)}")
    
    # Test NumPy support
    if HAS_NUMPY:
        print("\n--- NumPy Support ---")
        np_color = np.array([1.0, 0.0, 0.0])
        print(f"NumPy RGB {np_color} -> Hex: {convert_color(np_color, 'rgb', 'hex')}")
        
        np_tuple = (np.float64(0.0), np.float64(1.0), np.float64(0.0))
        print(f"NumPy tuple {np_tuple} -> HSV: {convert_color(np_tuple, 'rgb', 'hsv', norm_out=False)}")
    
    # Test batch conversion
    print("\n--- Batch Conversion ---")
    color_list = [
        [255, 0, 0],     # Red
        [0, 255, 0],     # Green
        [0, 0, 255],     # Blue
    ]
    hex_list = convert_color_list(color_list, 'rgb', 'hex', norm_in=False)
    print(f"RGB list -> Hex list: {hex_list}")
    
    # Test CMYK
    print("\n--- CMYK Conversion ---")
    cmyk = [0, 100, 100, 0]  # Red in CMYK percentage
    rgb_from_cmyk = convert_color(cmyk, 'cmyk', 'rgb', norm_in=False, norm_out=False)
    print(f"CMYK {cmyk} -> RGB: {rgb_from_cmyk}")
    
    # Test error handling
    print("\n--- Error Handling ---")
    result = convert_color("invalid", 'hex', 'rgb')
    print(f"Invalid hex -> RGB: {result}")
    
    try:
        convert_color([1, 0, 0], 'invalid_format', 'rgb')
    except ValueError as e:
        print(f"Invalid format error: {e}")
    
    print("\n=== Tests Complete ===")