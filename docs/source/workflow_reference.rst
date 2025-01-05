Block Reference & Interface
***************************

Interface Components
====================
The WMD interface provides an intuitive environment for creating and managing workflows:

Block Palette
-------------
Located on the left side of the Workflow tab, contains all available blocks organized by category.

Workspace
---------
Central area where you assemble your workflow by connecting blocks. Blocks connect using specific symbols:

- < : Left connection
- > : Right connection
- v : Bottom connection
- ^ : Top connection
- x : Top and bottom connection
- o : Internal connection
- c : Loop connection
- \+ : External window connection

Preview Panel
-------------
Shows real-time feedback as you build and test your workflow.

Available Blocks
================

Global Settings
---------------
- Theme settings
- Notes configuration
- Filter settings
- Display figures (x) - Controls figure display with UI options [continue, stop, skip save]
- Add figures to plot selector (x)
- Batch samples for analysis (x)

File Operations
---------------
- Load Directory (v) - Opens file browser for directory selection
- Load Sample (x) - Opens file browser for sample selection
- Export Figure Data (<) - Text field for filename
- Loop Over Samples (c) - Batch processing
- Loop Over Fields (c) - Field type selection
- Global Analysis (c) - Batch processing for clustering, PCA
- Subsample Data (<) - Method selection and sample size

Sample and Fields
-----------------
- Analyte Select Tool (x) - Saved list selection with dialog
- Reference Value (x) - Reference chemistry selection
- Change Pixel Dimensions (<) - dx, dy text fields
- Swap XY (<) - Swap coordinate axes
- Outlier Method (x) - Methods and quantile bounds
- Negative Method (x) - Methods and bounds settings
- Field Select (<) - Field type and field selection
- Custom List (<) - Load and save field selections
- Custom Field Calculator (<) - Formula entry and field naming
- Compute Custom Field (<) - Use defined custom fields

Image Processing
----------------
- Noise Reduction (x) - Method selection and parameters
- Edge Detection (x) - Method selection
- Gradient Options - Additional processing capabilities

Plotting
--------
- Map (x) - Field selection with styling options
- Correlation (x) - Method selection and export options
- Histogram (x) - Type selection and styling
- Biplot (x) - Field selection with styling
- Ternary (x) - Three-field selection and styling
- Ternary Map (x) - Three-field visualization
- Compatibility Diagram (x) - N-dim selection
- Radar Plot (x) - N-dim visualization
- Basis Variance (x) - PCA visualization
- Basis Vectors Plot (x) - PCA components
- Cluster Performance (x) - Method selection and styling
- Regression (<) - Statistical analysis

Multidimensional Analysis
-------------------------
- Dimensional Reduction (x) - Method selection
- Clustering (x) - Method selection and options
- Seed (<) - Random number generation
- Cluster Options (<) - Advanced clustering settings
- PCA Preconditioning (<) - Basis vector settings

Filtering
---------
- Load Polygons (x) - Multiple polygon selection

Styling
-------
- Modify Style (<) - Dynamic styling options
- Axis Controls (<) - X, Y, Z, C axis properties
- Tick Direction (<) - Tick mark display options
- Aspect Ratio (<) - Plot dimensions
- Scale Settings (<) - Scale bar configuration
- Marker Properties (<) - Symbol and size settings
- Line Properties (<) - Line styling
- Color Select (<) - Color tool
- Color Field (<) - Field-based coloring
- Colormap (<) - Colormap selection and direction
- Ternary Colormap (<) - Specialized coloring
- Show Mass (<) - Mass display toggle
- Color by Cluster (<) - Cluster-based coloring

Block Connections
=================
Connection Rules:
- Vertical connections (v, ^) create sequences
- Horizontal connections (<, >) indicate data flow
- Internal connections (o) modify block behavior
- Loop connections (c) create iteration structures
- External windows (\+) manage pop-up interfaces

Color Coding:
- Each block type has a distinct color
- Compatible connections share colors
- Incompatible connections won't snap together

Best Practices:
- Start with File Operation blocks
- Build sequences top to bottom
- Use loops for batch processing
- Test connections before running