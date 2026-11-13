Annotations Dock
****************

The *Annotations* dock lists the labels and distance measurements drawn on the
current plot, and lets you edit, move, hide or delete them.  Open it from the
*Annotations* button on the *Plot* page of the toolbar, or from *Tools >
Annotations*.

Annotations are made on the plot itself, with two tools on the canvas toolbar:

- |icon-annotate| *Annotate* places a text label where you click.
- |icon-distance| *Distance* measures between two clicked points and labels the
  line with the distance.

Where annotations live
======================

Annotations made on a **map** belong to the *sample*, not to the map that was on
screen when you made them.  Every map of a sample is drawn in the same stage
coordinates, so a label or a measurement is as true of one element map as of the
next, and *LaME* treats them as a layer of the sample in the same way as masks,
polygons and regions of interest.  Switch between element maps, or to a cluster,
score, ROI or ternary map, and the annotations come with you.

Annotations on a plot with **its own axes** — a scatter plot, histogram or
ternary diagram — are kept with that plot alone, since a point placed at a pair
of concentrations has no position anywhere else.  Return to the same plot and
they are still there.

The line above the table always says which of the two you are looking at, so you
can see how far *Remove* reaches before you use it.

Editing
=======

Every column except *Type* can be edited:

.. list-table::
    :header-rows: 1

    * - Column
      - Meaning
    * - Type
      - ``text`` for a label, ``line`` for a distance measurement.
    * - Text
      - The label drawn on the plot.  For a measurement this starts as the
        distance, and can be replaced with anything you like.
    * - X1, Y1
      - Position of the label, or the first end of a measurement.
    * - X2, Y2
      - The second end of a measurement; blank for a label.
    * - Size
      - Font size of the label.
    * - Width
      - Line width of a measurement; blank for a label.
    * - Color
      - Opens a colour picker.
    * - Visible
      - Whether it is drawn.

Editing a position moves the annotation, on every map that shows it.  There is no
dragging on the canvas yet.

Showing, hiding and removing
============================

To leave an annotation out of one particular figure, clear its *Visible*
checkbox before exporting and set it again afterwards.  The annotation itself is
kept, and exported figures contain exactly what is visible on screen.

The toolbar has three actions:

- *Select All* selects every row.
- *Show/Hide* flips the visibility of the selected annotations — hiding them if
  any are shown, otherwise showing them all.
- *Remove* deletes the selected annotations.  On a map this removes them from
  *every* map of the sample; hiding, not removing, is what leaves one out of a
  single figure.

Annotations are saved with the project and restored with the sample.

.. |icon-annotate| image:: _static/icons/icon-annotate-64.svg
    :height: 2.5ex

.. |icon-distance| image:: _static/icons/icon-distance-64.svg
    :height: 2.5ex
