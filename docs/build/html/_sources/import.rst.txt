.. _`import formats`
Import Formats
**************

Import formats vary by data type, and can vary by machine manufacturer or depending on the program that is used to processes the data.  The formats for the various input files are described below.  If you have a file type that is not included, feel free to contact us (:doc:`contact`) to see if we can write a method to suit your particular needs.

At present, we only handle LA-ICP-MS data, though we have a number of additional data we plan to include in the comming months.

LA-ICP-MS
=========

Quadrupole
----------

For a single sample, the data are often stored in a collection of \*.csv or \*.xlsx files.  There are two formats.  *LaME* can read either, which it attempts to autodetect from the filename patterns.  While its ability to handle filename formats are limited, it will probably handle most reasonable naming schemes.  In both cases the collection of files should be stored in a directory given by the sample ID.  Once read in, the data are exported in a single file, common data format with a *.lame.csv* suffix and extension.

1. Files include all recorded analytes for a single scan line in each individual file.  This file format is typically used for raw data in CPS. Filenames for this format often include a sample number and a line number separated by a delimiter.  These can come in any order and a variety of delimeters may used.  *LaME* strips away these common elements to identify the line numbers.

Example filenames include:  

- RM03-3.csv
- RM05 - 10.csv
- TR3-06-1.csv
- M252-m1 - 6.csv
- 90-75B-PY-3.csv
- 121.csv

In all but the last two cases above, the line number came last.  However, the order doesn't matter as LaME will strip away the common patterns to reveal the line number, which it needs along with spot size to determine distance between lines.  This distance is defined as the *X*-direction.

Each file should include several metadata lines followed by a header and the table of values with results from each analyte in a separate column.  The first column is the time along the line.  The difference in times are the sweep time and should be constant from measurement to measurement.  The sweep time along with the rate of travel of the laser is used to determine the distance along the line.  This distance is the *Y*-direction.  A snippet is shown in the table below.

 .. csv-table:: Scan-line file from LA-ICP-MS quadrupole
    :file: _static/tables/la-icp-ms_line_snippet.csv
    :widths: 10 10 10 10 10 10 10 10 10 10 
    :header-rows: 4

*Note:* scan line data may include files with standards.  These standards will sit between scan lines of the sample resulting in non-sequential line numbers for the sample, which is accounted for by *LaME* when converting to distance.

2. An alternative format reports each analyte in a separate file as a matrix (map-form) and may be produced after calibration and/or processing in Iolite or XMapTools, generally used to report data in PPM, though they may still be in CPS.  The filenames are generally constructed from the sample name and the analyte and often include the units and matrix, though the only important component is the analyte, which is use to define the column in the output data.  The order of the mass and symbol can be either mass first or mass last conventions.

Example filenames:

- 23Na.csv
- RM03 Dy163_ppm matrix.csv
- B10B_SMALL_ppm K39_ppm matrix.csv
- 4337064_grt03 Ba137_CPS matrix.csv

Each file should include a matrix of data without headers, line numbers, distances, or times.  The default reads columns as the *X* coordinate and rows as the *Y*.  A snippet is shown in the table below.

 .. csv-table:: Analyte-matrix file from LA-ICP-MS quadrupole
    :file: _static/tables/la-icp-ms_matrix_snippet.csv
    :widths: 12 13 12 13 12 13 12 13 
    :header-rows: 0

TOF
---

HDF5 format files...to be added soon