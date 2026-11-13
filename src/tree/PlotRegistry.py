"""
Plot Registry System for Managing Plot Metadata and Canvas Lifecycle

This module provides centralized management for plot metadata and canvas instances,
separating plot data from Qt widgets to improve memory management and prevent crashes.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from collections import OrderedDict
from PyQt6.QtCore import QObject, pyqtSignal

from src.plotting.CustomMplCanvas import MplCanvas
from src.control.Logger import auto_log_methods, log


@auto_log_methods(logger_key='Registry')
def plot_key(plot_metadata: Dict[str, Any]) -> str:
    """A stable identity for a plot, from the metadata every plot carries.

    ``sample:plot_type:plot_name:field_type:field`` -- the same components
    `PlotRegistry._generate_plot_id` builds from, without the ``_1``/``_2``
    suffix it adds to avoid collisions with already-registered plots. That
    suffix is what makes the plot *id* unusable as a lookup key: it depends
    on registration order, so the same plot can be given a different id in
    a later session.

    Computed from the metadata rather than read from
    ``plot_info['plot_id']``, which only exists for plots saved to the tree
    (`PlotTree` is the one caller of `PlotRegistry.register_plot`).

    Parameters
    ----------
    plot_metadata : dict
        A ``plot_info``-shaped dict.

    Returns
    -------
    str
    """
    return ':'.join(str(plot_metadata.get(k, '')) for k in
                    ('sample_id', 'plot_type', 'plot_name', 'field_type', 'field'))


class PlotRegistry(QObject):
    """
    Central registry for plot metadata and canvas management.
    
    Manages plot metadata separately from Qt widgets and provides
    canvas caching with LRU eviction policy.
    """
    
    # Signals for plot lifecycle events
    plotRegistered = pyqtSignal(str)  # plot_id
    plotRemoved = pyqtSignal(str)  # plot_id
    canvasCreated = pyqtSignal(str)  # plot_id
    canvasEvicted = pyqtSignal(str)  # plot_id
    
    def __init__(self, app_data, max_cached_canvases=10):
        super().__init__()
        self.logger_key = 'Registry'
        
        self.app_data = app_data
        self.max_cached_canvases = max_cached_canvases
        
        # Core storage
        self.plots = {}  # plot_id -> plot_metadata
        self.tree_keys = {}  # tree_key -> plot_id mapping
        
        # Canvas cache (LRU)
        self.canvas_cache = OrderedDict()  # plot_id -> MplCanvas
        
    def register_plot(self, plot_metadata: Dict[str, Any]) -> str:
        """
        Register a new plot and return its unique ID.
        
        Parameters
        ----------
        plot_metadata : Dict[str, Any]
            Plot metadata dictionary containing sample_id, plot_type, etc.
            
        Returns
        -------
        str
            Unique plot ID generated for this plot
        """
        plot_id = self._generate_plot_id(plot_metadata)
        plot_metadata['plot_id'] = plot_id
        plot_metadata['registered_at'] = datetime.now()

        self.plots[plot_id] = plot_metadata.copy()

        # Cache the figure
        figure = plot_metadata.get('figure')
        if figure is not None and isinstance(figure, MplCanvas):
            if plot_id not in self.canvas_cache:
                self._cache_canvas(plot_id, figure)

        log(f"Registered plot: {plot_id}", "INFO")
        self.plotRegistered.emit(plot_id)

        return plot_id
    
    def get_plot_metadata(self, plot_id: str) -> Optional[Dict[str, Any]]:
        """Get plot metadata by ID."""
        return self.plots.get(plot_id)
    
    def remove_plot(self, plot_id: str) -> bool:
        """
        Remove plot and its associated canvas from registry.
        
        Parameters
        ----------
        plot_id : str
            Plot ID to remove
            
        Returns
        -------
        bool
            True if plot was removed, False if not found
        """
        if plot_id not in self.plots:
            return False
        
        # Remove from canvas cache if present
        if plot_id in self.canvas_cache:
            canvas = self.canvas_cache.pop(plot_id)
            self._cleanup_canvas(canvas)
        
        # Remove plot metadata
        del self.plots[plot_id]
        
        # Remove tree key mappings
        self.tree_keys = {k: v for k, v in self.tree_keys.items() if v != plot_id}
        
        log(f"Removed plot: {plot_id}", "INFO")
        self.plotRemoved.emit(plot_id)
        
        return True
    
    def link_to_tree(self, tree_key: str, plot_id: str):
        """Link a tree item location to a plot ID."""
        self.tree_keys[tree_key] = plot_id
    
    def get_plot_by_tree_key(self, tree_key: str) -> Optional[Dict[str, Any]]:
        """Get plot metadata using tree location key."""
        plot_id = self.tree_keys.get(tree_key)
        return self.plots.get(plot_id) if plot_id else None
    
    def get_or_create_canvas(self, plot_id: str) -> Optional[MplCanvas]:
        """
        Get existing canvas or create new one from plot metadata.
        
        Parameters
        ----------
        plot_id : str
            Plot ID to get canvas for
            
        Returns
        -------
        Optional[MplCanvas]
            Canvas instance or None if plot not found
        """
        if plot_id not in self.plots:
            log(f"Plot not found in registry: {plot_id}", "WARNING")
            return None
        
        # Check cache first
        if plot_id in self.canvas_cache:
            # Move to end (most recently used)
            canvas = self.canvas_cache.pop(plot_id)
            self.canvas_cache[plot_id] = canvas
            log(f"Retrieved canvas from cache: {plot_id}", "INFO")
            return canvas
        
        # Create new canvas
        plot_metadata = self.plots[plot_id]
        canvas = self._create_canvas(plot_id, plot_metadata)
        
        if canvas:
            self._cache_canvas(plot_id, canvas)
            log(f"Created new canvas: {plot_id}", "INFO")
            self.canvasCreated.emit(plot_id)
        
        return canvas
    
    def _create_canvas(self, plot_id: str, plot_metadata: Dict[str, Any]) -> Optional[MplCanvas]:
        """Create canvas from plot metadata."""
        try:
            # Get sample object for signal connections
            sample_id = plot_metadata['sample_id']
            sample_obj = self.app_data.data.get(sample_id)
            
            if not sample_obj:
                log(f"Sample object not found: {sample_id}", "WARNING")
                return None
            
            # Create canvas with registry integration parameters
            canvas = MplCanvas(
                parent=self.app_data.ui if hasattr(self.app_data, 'ui') else None,
                ui=self.app_data.ui if hasattr(self.app_data, 'ui') else None,
                plot_id=plot_id,
                sample_obj=sample_obj
            )
            
            # Set up plot-specific properties
            canvas.plot_name = plot_metadata.get('plot_name', '')
            
            # Set up data properties if available
            if 'field_type' in plot_metadata and plot_metadata['field_type'] in ['Analyte', 'Ratio']:
                canvas.map_flag = True
                
            # Copy other relevant properties from plot_metadata
            for key in ['dx', 'dy', 'array', 'color_units', 'distance_units']:
                if key in plot_metadata:
                    setattr(canvas, key, plot_metadata[key])
            
            return canvas
            
        except Exception as e:
            log(f"Failed to create canvas for {plot_id}: {e}", "ERROR")
            return None
    
    def _cache_canvas(self, plot_id: str, canvas: MplCanvas):
        """Add canvas to cache, evicting oldest if needed."""
        # Remove oldest if at capacity
        while len(self.canvas_cache) >= self.max_cached_canvases:
            oldest_id, oldest_canvas = self.canvas_cache.popitem(last=False)
            self._cleanup_canvas(oldest_canvas)
            log(f"Evicted canvas from cache: {oldest_id}", "INFO")
            self.canvasEvicted.emit(oldest_id)
        
        self.canvas_cache[plot_id] = canvas
    
    def _cleanup_canvas(self, canvas: MplCanvas):
        """Safely cleanup canvas resources."""
        try:
            # Check if canvas still exists (Qt may have deleted it)
            if not canvas or not hasattr(canvas, '__class__'):
                return
                
            # Disconnect from sample signals safely. The canvas does this
            # itself so it can drop *its own* slot: a bare
            # `signal.disconnect()` here would take every other listener
            # with it -- the other open canvases and the annotations table.
            if hasattr(canvas, 'disconnect_sample_signals'):
                try:
                    canvas.disconnect_sample_signals()
                except (RuntimeError, TypeError):
                    # Signal already disconnected or object deleted
                    pass
            
            # Clean up matplotlib resources safely
            if hasattr(canvas, 'figure') and canvas.figure:
                try:
                    canvas.figure.clear()
                except Exception:
                    pass
            
            # Clean up navigation toolbar safely
            if hasattr(canvas, 'mpl_toolbar') and canvas.mpl_toolbar:
                try:
                    canvas.mpl_toolbar.setParent(None)
                    canvas.mpl_toolbar.deleteLater()
                except (RuntimeError, AttributeError):
                    # Toolbar already deleted by Qt
                    pass
            
            # Set parent to None safely
            try:
                canvas.setParent(None)
            except RuntimeError:
                # Canvas already deleted by Qt
                pass
            
        except Exception as e:
            log(f"Error during canvas cleanup: {e}", "WARNING")
    
    def _generate_plot_id(self, plot_metadata: Dict[str, Any]) -> str:
        """Generate a unique plot ID.

        Unique, but *not* stable: the suffix below depends on what else is
        registered at the time. Anything that needs to find the same plot
        again later -- the per-plot annotations, for instance -- keys off
        `plot_key` instead.
        """
        base_id = plot_key(plot_metadata)

        # Ensure uniqueness by checking existing IDs
        plot_id = base_id
        counter = 1
        while plot_id in self.plots:
            plot_id = f"{base_id}_{counter}"
            counter += 1
            
        return plot_id
    
    def get_cached_canvas_ids(self) -> List[str]:
        """Get list of currently cached canvas IDs."""
        return list(self.canvas_cache.keys())
    
    def clear_cache(self):
        """Clear all cached canvases."""
        for plot_id, canvas in self.canvas_cache.items():
            self._cleanup_canvas(canvas)
            self.canvasEvicted.emit(plot_id)
        
        self.canvas_cache.clear()
        log("Cleared canvas cache", "INFO")
    
    def get_plots_for_sample(self, sample_id: str) -> List[Dict[str, Any]]:
        """Get all plots for a specific sample."""
        return [
            plot_metadata for plot_metadata in self.plots.values()
            if plot_metadata.get('sample_id') == sample_id
        ]
    
    def remove_plots_for_sample(self, sample_id: str) -> int:
        """Remove all plots for a sample. Returns number of plots removed."""
        plots_to_remove = [
            plot_id for plot_id, plot_metadata in self.plots.items()
            if plot_metadata.get('sample_id') == sample_id
        ]
        
        for plot_id in plots_to_remove:
            self.remove_plot(plot_id)
        
        log(f"Removed {len(plots_to_remove)} plots for sample: {sample_id}", "INFO")
        return len(plots_to_remove)