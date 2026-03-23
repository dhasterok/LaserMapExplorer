"""
XRF Data Processor

This module provides functionality for processing XRF/EDS data from BCF files,
including element identification, peak deconvolution, and elemental mapping.

Author: LaserMapExplorer team
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
try:
    import hyperspy.api as hs
    HYPERSPY_AVAILABLE = True
except ImportError:
    HYPERSPY_AVAILABLE = False
    print("Warning: HyperSpy not available. Install with: pip install hyperspy[all]")


class XRFProcessor:
    """Process XRF/EDS data with element identification and quantification."""

    def __init__(self, filepath):
        """
        Initialize XRF processor with a BCF file.

        Parameters
        ----------
        filepath : str
            Path to the .bcf file
        """
        if not HYPERSPY_AVAILABLE:
            raise ImportError("HyperSpy is required for XRF processing")

        self.filepath = os.path.expanduser(filepath)
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        self.data = None
        self.model = None
        self.intensity_maps = {}
        self.elements = []

    def load(self):
        """Load the BCF file."""
        print(f"Loading {self.filepath}...")
        self.data = hs.load(self.filepath)
        print(f"✓ Loaded: shape={self.data.data.shape}, dtype={self.data.data.dtype}")
        return self

    def get_info(self):
        """Get information about the loaded data."""
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        info = {
            'shape': self.data.data.shape,
            'dtype': self.data.data.dtype,
            'metadata': self.data.metadata
        }

        if hasattr(self.data, 'axes_manager'):
            energy_axis = self.data.axes_manager.signal_axes[0]
            info['energy_range'] = (
                energy_axis.offset,
                energy_axis.offset + energy_axis.size * energy_axis.scale
            )
            info['energy_resolution'] = energy_axis.scale

        return info

    def set_elements(self, elements):
        """
        Set the elements to analyze.

        Parameters
        ----------
        elements : list of str
            List of element symbols (e.g., ['Si', 'Fe', 'Ca'])
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        self.elements = elements
        self.data.set_elements(elements)
        self.data.set_lines(elements)
        print(f"✓ Set elements: {elements}")
        print(f"  X-ray lines: {self.data.metadata.Sample.xray_lines}")
        return self

    def auto_identify_elements(self, threshold=0.5):
        """
        Automatically identify elements from peaks in the spectrum.

        Parameters
        ----------
        threshold : float
            Threshold for peak detection (0-1)

        Returns
        -------
        list
            Detected peak positions in keV
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        total = self.data.sum()
        peaks = total.find_peaks1D_ohaver(maxpeakn=50)
        print(f"✓ Found {len(peaks)} peaks")
        return peaks

    def create_model(self):
        """
        Create an XRF model with element components.

        Returns
        -------
        self
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        if not self.elements:
            raise ValueError("No elements set. Call set_elements() first.")

        print("Creating XRF model...")
        self.model = self.data.create_model()
        print(f"✓ Model created with {len(self.model)} components:")
        for component in self.model:
            print(f"  - {component.name}")
        return self

    def fit_model(self, navigation_mask=None):
        """
        Fit the model to the data.

        Parameters
        ----------
        navigation_mask : array-like, optional
            Boolean mask for spatial positions to fit

        Returns
        -------
        self
        """
        if self.model is None:
            raise ValueError("No model created. Call create_model() first.")

        print("Fitting model (this may take several minutes)...")
        if navigation_mask is not None:
            self.data.metadata.set_item('navigation_mask', navigation_mask)

        self.model.fit()
        print("✓ Model fitting complete")
        return self

    def get_element_maps(self):
        """
        Extract intensity maps for each element from the fitted model.

        Returns
        -------
        dict
            Dictionary mapping element lines to intensity maps
        """
        if self.model is None:
            raise ValueError("No model fitted. Call fit_model() first.")

        print("Extracting element intensity maps...")
        intensity_list = self.model.get_lines_intensity()

        self.intensity_maps = {}
        for element_line, intensity_map in intensity_list:
            self.intensity_maps[element_line] = intensity_map.data
            print(f"  - {element_line}: {intensity_map.data.shape}")

        print(f"✓ Extracted {len(self.intensity_maps)} element maps")
        return self.intensity_maps

    def plot_total_spectrum(self, background_subtracted=False, save_path=None):
        """
        Plot the total XRF spectrum.

        Parameters
        ----------
        background_subtracted : bool
            Whether to subtract background
        save_path : str, optional
            Path to save the figure
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        total = self.data.sum()

        if background_subtracted:
            # Make a copy and remove background
            total_bg = total.deepcopy()
            total_bg.remove_background()
            total_bg.plot()
            plt.title("Total XRF Spectrum (Background Removed)")
        else:
            total.plot()
            plt.title("Total XRF Spectrum")

        plt.xlabel("Energy (keV)")
        plt.ylabel("Counts")

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved spectrum to {save_path}")

        return plt.gcf()

    def plot_element_maps(self, figsize=(15, 10), cmap='viridis', save_path=None):
        """
        Plot all element intensity maps in a grid.

        Parameters
        ----------
        figsize : tuple
            Figure size (width, height)
        cmap : str
            Colormap name
        save_path : str, optional
            Path to save the figure
        """
        if not self.intensity_maps:
            raise ValueError("No intensity maps. Call get_element_maps() first.")

        n_elements = len(self.intensity_maps)
        n_cols = min(3, n_elements)
        n_rows = (n_elements + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        if n_elements == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        for i, (element_line, intensity_map) in enumerate(self.intensity_maps.items()):
            ax = axes[i]
            im = ax.imshow(intensity_map, cmap=cmap, origin='lower')
            ax.set_title(element_line, fontsize=12, fontweight='bold')
            plt.colorbar(im, ax=ax, label='Intensity')
            ax.axis('off')

        # Hide unused subplots
        for i in range(n_elements, len(axes)):
            axes[i].axis('off')

        plt.tight_layout()
        plt.suptitle("Element Intensity Maps", fontsize=14, y=1.001)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved element maps to {save_path}")

        return fig

    def plot_model_fit(self, save_path=None):
        """
        Plot the fitted model.

        Parameters
        ----------
        save_path : str, optional
            Path to save the figure
        """
        if self.model is None:
            raise ValueError("No model fitted. Call fit_model() first.")

        self.model.plot()
        plt.title("XRF Model Fit")

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved model fit to {save_path}")

        return plt.gcf()

    def export_element_maps(self, output_dir, format='tiff'):
        """
        Export element intensity maps to files.

        Parameters
        ----------
        output_dir : str
            Directory to save the maps
        format : str
            Output format ('tiff', 'png', 'hdf5')
        """
        if not self.intensity_maps:
            raise ValueError("No intensity maps. Call get_element_maps() first.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for element_line, intensity_map in self.intensity_maps.items():
            # Clean element name for filename
            clean_name = element_line.replace('_', '-')

            if format == 'tiff':
                from tifffile import imwrite
                filepath = output_path / f"{clean_name}.tif"
                imwrite(filepath, intensity_map.astype(np.float32))
            elif format == 'png':
                filepath = output_path / f"{clean_name}.png"
                plt.imsave(filepath, intensity_map, cmap='viridis')
            elif format == 'hdf5':
                import h5py
                filepath = output_path / f"{clean_name}.h5"
                with h5py.File(filepath, 'w') as f:
                    f.create_dataset('intensity', data=intensity_map)
                    f.attrs['element'] = element_line
            else:
                raise ValueError(f"Unsupported format: {format}")

            print(f"  ✓ Saved {element_line} to {filepath}")

        print(f"✓ Exported {len(self.intensity_maps)} maps to {output_dir}")

    def save_processed_data(self, output_path):
        """
        Save the processed data to HDF5 format.

        Parameters
        ----------
        output_path : str
            Path for output file
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load() first.")

        self.data.save(output_path, overwrite=True)
        print(f"✓ Saved processed data to {output_path}")


def process_xrf_file(filepath, elements, output_dir=None):
    """
    Convenience function to process an XRF file end-to-end.

    Parameters
    ----------
    filepath : str
        Path to BCF file
    elements : list of str
        List of element symbols to analyze
    output_dir : str, optional
        Directory to save outputs. If None, uses same directory as input file.

    Returns
    -------
    XRFProcessor
        Processor instance with fitted model and intensity maps
    """
    # Create processor
    processor = XRFProcessor(filepath)

    # Load and process
    processor.load()
    processor.set_elements(elements)
    processor.create_model()
    processor.fit_model()
    processor.get_element_maps()

    # Set output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(filepath), 'xrf_output')

    # Generate outputs
    os.makedirs(output_dir, exist_ok=True)
    processor.plot_total_spectrum(save_path=os.path.join(output_dir, 'total_spectrum.png'))
    processor.plot_element_maps(save_path=os.path.join(output_dir, 'element_maps.png'))
    processor.export_element_maps(output_dir, format='tiff')

    print(f"\n✓ Processing complete! Output saved to: {output_dir}")
    return processor


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python XRFProcessor.py <bcf_file> [element1 element2 ...]")
        print("\nExample:")
        print("  python XRFProcessor.py data.bcf Si Fe Ca Mg Al")
        sys.exit(1)

    bcf_file = sys.argv[1]
    elements = sys.argv[2:] if len(sys.argv) > 2 else ['Si', 'Fe', 'Ca', 'Mg', 'Al', 'Na', 'K']

    print(f"Processing {bcf_file}")
    print(f"Elements: {elements}\n")

    processor = process_xrf_file(bcf_file, elements)
