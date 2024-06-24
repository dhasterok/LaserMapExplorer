Filter
======

There are three types of filters than can be applied to exclude data from analyses and geochemical plots.  These include filters by value ( |icon-filter2| ), polygon masking ( |icon-polygon-new| ), and cluster masking ( |icon-mask-dark| ).  Filter by value and polygon masking are both created from the *Filter* tab whereas the cluster mask is set from *Styling\>Clusters* in the right toolbox.  It is possible to use any combination of these filters and masks and turn them on or off as required.  All filters and masks can be turned off by clicking the |icon-map| button.

.. figure:: _static/screenshots/LaME_Filter.png
    :align: center
    :alt: LaME interface: left toolbox, filter tab
    :width: 315

    The *Filter* tab contains tools for filtering by value creating polygons.  It also contains an edge detection algorithm, useful for creating polygons.

Filter by value |icon-filter2|
--------------------------------

To set a filter, use the two drop down menus to select the type of field (lower) and the desired field (upper).  It is possible to filter by value using element/isotopes, ratios, custom fields, principal component score, or cluster score.  Once selected, the ranges for the field will be automatically displayed in the min and max boxes.  Change the values to set the bounds explicitly using the (left boxes) or implicitly by setting the quantile bounds (right boxes).  Once the bounds are set, click the |icon-filter2| button to add the filter to the list.

Multiple filters may be combined to produce more complex filters.  The filters include a boolean operations (*and* and *or*, set in the *Filter Table* in the :doc:`lower_tabs`) to assist with precisely defining filters to capture the desired regions for analysis and plotting.  In many cases, the overlap between values may make it difficult to separate phases.  In these cases, we suggest targeting specific regions with a polygon or cluster mask.

Polygon Masking |icon-polygon-new|
----------------------------------

to create a polygon for filtering, select a map from the plot selector and then click the |icon-polygon-new| button.  Move the mouse over the map and left-click to add vertices.  You will notice a zoom tool appears that shows a small region of the map where the mouse is located.  Once you have added enough points, right-click on the map to end digitizing.  A polygon will appear in the *polygon table*, where a name can be added.  Once created, polygons can be edited.  Move a point by clicking the |icon-move-point| button, then left-click on the map near the point to be moved and then left-click again for the new location.  Add a vertex by clicking the button |icon-add-point| and selecting the line segment where you wish to add a point.  Then click where you would like the new point.  To remove points, click the button |icon-remove-point| and then click the point you wish to remove.

It is possible to create multiple polygons.  These polygons can be analyzed as separate regions or linked by selecting multiple polygons in the *Polygon Table* and clicking the |icon-link| button.  To delink the polygons, select the polygon in the table and then click the |icon-unlink| button.  The use of individual polygons in analyses can be toggled by clicking the associated checkbox in the *Polygon Table*.

The polygons within the table can be stored by clicking the |icon-save| button and recolled using the |icon-open-file| button.  See a description of `file specifications`_ for more information.

Cluster Masking |icon-mask-light|
--------------------------------

Cluster masks can be turned on or off from the *Filter* tab, but cannot be set here.  To set a cluster mask, you will need to 

#. compute clusters first from the *Cluster* pane in the *Control Toolbox*
#. from the *Styling* tab on the right pane, select the *Clusters* sub-tab and choose the type of clustering from the point grouping drop down
#. select the cluster(s) that you wish to mask and click the |icon-mask-dark| button to set the cluster mask or
#. alternatively, select the clusters you wish to use for analysis and click the |icon-mask-light| button to set the other groups as the mask.

Edge-detection
--------------
To aid with the identification of mineral boundaries, you can turn on edge detection by clicking the |icon-edge-detection| button. There are multiple edge detection methods available (Sobel, Canny, zero-cross) which you can select using the dropdown menu.  Edge-detection is useful for locating the boundaries of polygons.  The use of edge detection does not affect analyses.

.. |icon-mask-light| image:: _static/icons/icon-mask-light-64.png
    :height: 2.5ex

.. |icon-mask-dark| image:: _static/icons/icon-mask-dark-64.png
    :height: 2.5ex

.. |icon-polygon-new| image:: _static/icons/icon-polygon-new-64.png
    :height: 2.5ex

.. |icon-polygon-off| image:: _static/icons/icon-polygon-off-64.png
    :height: 2.5ex