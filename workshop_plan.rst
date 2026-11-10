==========================================
Laser Map Explorer (LaME) Workshop
==========================================

:Duration: Half day (09:00–13:00)
:Build: ``LaME v0.9.0-workshop``
:Datasets: Three garnet maps, one pyrite map

.. note::

   Fill in your own date, venue and contact details above before printing.

.. contents:: On this page
   :depth: 1
   :local:





    


What today covers
=================

LaME turns LA-ICP-MS element maps into something you can rapidly explore: filter, plot,
cluster, calculate, and get mineral formulae out the other end.

We work through two threads.

**Garnet — the quantitative thread.** One sample to learn on, then the same analysis
across three garnets, ending with mineral formulae and a map of the end-member
distribution.

**Pyrite — the qualitative thread.** A completely different mineral system, where you
drive. Cluster it with and without PCA preconditioning, mask to the sulfide using the
clusters themselves, and ask what separates the populations inside it.

**Core – XRF.** Use many of the same tools to investigate XRF intensity maps.  Turn
semi-quantitative data into something that you can interpret rapidly and with
confidence.

LaME is beta software and this handout is honest about that. Where something is
unfinished you will see a **Not in this build** box telling you what you would see and
what to do instead. Those boxes are not apologies — they are there so you do not waste
the workshop discovering them yourself. A consolidated list is in
`Known limitations in this build`_.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/docs/source/_static/screenshots/LaME_Initial_Window.png
    :align: center
    :alt: Alternate text goes here
    :width: 150mm

    The LaME main window immediately after opening.  There are four main areas in the window:
    (1) Control Toolbox, left; (2) plot canvas, center; (3) Styling Toolbox and Plot Tree,    
    right; (4) bottom tabs; (5) the toolbar.


Where to find LaME
==================

LaME is built around five separate GitHub repositories.  They can all be found by visiting: `GitHub`_

- **LaserMapExplorer**, the main application machinery and GUI components

- **lame-core**, core utilities required by *LaME* and the other repositories 

- **siesta-rest-editor**, used to produce reSTructured text notes within *LaME*.  Siesta can 
  also be used as a stand-alone application for viewing, editing, and printing documents.  

- **blueberry-color-tools** is used within LaME to create and modify colormaps and select colors.
  Like Siesta, Blũberry can be used as a stand-alone application.

- **global-geochemistry**, utilities for producing various geochemical plots displayed within 
  LaME and much more.  It was originally written to process large geochemical datasets and has  
  some mapping capabilities, geophysical property estimation, and interfaces with tectonic  
  shapefiles and a metamorphic conditions dataset.
      
.. list-table::
   :widths: 33 33 33
   :header-rows: 0

   * - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/resources/icons/LaME-64.png
          :align: center
          :alt: Alternate text goes here
          :width: 93%

          Laser Map Explorer
        
          
     - .. figure:: /Users/dhasterok/Documents/GitHub/siesta-rest-editor/src/siesta/icons/siesta2.png
          :align: center
          :alt: Alternate text goes here
          :width: 85%

          Siesta
     - .. figure:: /Users/dhasterok/Documents/GitHub/blueberry-colortools/resources/icons/blueberry_64.png
          :align: center
          :alt: Alternate text goes here
          :width: 85%

          Blüberry

Before you start
================

You need two things, both of which should already be on your machine:

#. **LaME installed** — the ``.dmg`` (macOS) or ``.zip`` (Windows) from the release
   link you were emailed.
#. **The workshop folder**, unzipped **to your Desktop with its structure intact**:

   .. code-block:: text

      LaME-workshop/
      ├── data/
      │   ├── RM02.lame.csv          garnet, 78,228 px
      │   ├── WOS-02.lame.csv        garnet, 123,255 px
      │   ├── TR1-07.lame.csv        garnet, 59,916 px
      │   └── 71A-Py 12.lame.csv     pyrite, 29,666 px
      ├── 00-open.lame_project.json      + 00-open/
      ├── 02-plots.lame_project.json     + 02-plots/
      ├── 04-clusters.lame_project.json  + 04-clusters/
      ├── 06-pyrite.lame_project.json    + 06-pyrite/
      └── handout.pdf

.. warning::

   Do not move files out of that folder or rename the directories beside each
   ``.lame_project.json``. Project files find their data by **relative** path, so the
   structure is what makes them work on your machine rather than only on the
   presenter's.


How to read this handout
========================

**Numbered steps** are things you do. Do them in order — a few of them only work in
one order, and those are called out.

.. admonition:: Checkpoint
   :class: tip

   **Grey boxes like this are things you should see.** If your screen does not match,
   do not debug it: open the project file named in the box and carry on. You will lose
   nothing that later sections need.

.. admonition:: Not in this build
   :class: error

   **Boxes like this are known limitations.** They tell you what you would see if you
   tried, and what to do instead.

*Try this* paragraphs at the end of a section are optional. They exist so that if you
finish early you have somewhere to go that does not put you ahead of the group.


The datasets
============

Three garnets and a pyrite, all real data.

.. list-table::
   :header-rows: 1
   :widths: 14 12 10 64

   * - Sample
     - Pixels
     - Mineral
     - Notes
   * - ``RM02``
     - 78,228
     - Garnet
     - Garnet–chlorite schist, Walter–Outalpa Shear Zone, South Australia.
       28 analytes: full REE suite plus Ca, Fe, Mg, Mn, Al, Ti, Cr, P, Li, Zr, Th, U, Pb.
   * - ``WOS-02``
     - 123,255
     - Garnet
     - 33 analytes. Adds **Si**, Na, Sr, Ba and a second Pb isotope.
   * - ``TR1-07``
     - 59,916
     - Garnet
     - 33 analytes, same suite as WOS-02. The smallest and quickest of the three.
   * - ``71A-Py 12``
     - 29,666
     - Pyrite
     - 91 scan lines × 326 pixels, 20 × 6.1 µm. 30 analytes: S, Fe and the chalcophile
       suite — **Co**, **Ni**, **Cu**, Zn, As, Se, Ag, Cd, Sn, Sb, Te, Au, Hg, Tl, Pb, Bi.
       Gold is below detection in most pixels here, so the chalcophile story is in Cu
       and As.

What these datasets **cannot** do — worth knowing up front, because all three are properties of the data rather than of the software:

* **RM02 has no silicon.** Garnet is X\ :sub:`3`\ Y\ :sub:`2`\ Z\ :sub:`3`\ O\ :sub:`12`,
  and Si normally fills the tetrahedral Z site. Without it, LaME fills Z with aluminium instead. We use this deliberately in `7. Mineral formulae across three garnets`_ — it is the clearest demonstration you will get of what the stoichiometry calculation needs from your data.
* **None of them can do Lu–Hf dating.** That needs
  :sup:`176`\ Lu/:sup:`177`\ Hf and :sup:`176`\ Hf/:sup:`177`\ Hf. These maps have :sup:`175`\ Lu and at most one Hf isotope. The capability is real — you will see a result from a different sample — but no amount of clicking will produce an isochron from today's data.
* **The pyrite map is uncalibrated.** Values are counts per second, not ppm. Everything
  we do with it — maps, filters, clusters, biplots — is valid on CPS. Mineral formulae
  and chondrite normalisation are **not**, so do not run the Stoichiometry dock on it.

One practical wrinkle: the three garnets were run on different setups, so **isotope
names differ between samples**. RM02 has ``Fe57``, ``Ti49``, ``Cr53``; WOS-02 and
TR1-07 have ``Fe56``, ``Ti47``, ``Cr52``. When a step names a field, check the sample
you are actually on.


1. Opening the project
======================

*Goal: get a map on screen in under two minutes, with everyone seeing the same thing.*

#. Launch LaME. First launch takes a little while — it is unpacking, not hung.
#. **Home** toolbar page → **Open Project**.
#. Navigate to ``Desktop/LaME-workshop/`` and choose ``00-open.lame_project.json``.

That is all. You did not open the CSV directly, and you will not need to today — a
project file carries the sample, the selected fields and the window state together,
which is why it makes a reliable starting point and a reliable *recovery* point.

.. admonition:: Checkpoint 0
   :class: tip

   The title bar reads **LaME - 00-open**. The Control Toolbox on the left is on its
   **Preprocess** page. There is a field map of RM02 in the centre and a small
   histogram of the same field beside it.

   *Not matching?* You are at the first step; just try the open again.

.. Figure placeholder FIG-1.1  [CHECKPOINT — must match attendee screens exactly]
   WHAT: Full window at Checkpoint 0. Title bar visible showing "LaME - 00-open".
   Control Toolbox on the Preprocess page. RM02 field map in the canvas with its
   companion histogram. Take this at the same window size you will tell attendees to
   use (1280x800 is a safe laptop size).
   WHY: This is the reference photograph for the first checkpoint. It must be
   pixel-faithful, not illustrative — attendees compare their screen against it.
   SIZE: full page width.

.. admonition:: Not in this build
   :class: error

   Look at the **Plot** box at the top of the Control Toolbox. It reads ``field map``.
   The entry directly below it, ``gradient map``, produces nothing in this build —
   either a warning about noise reduction, or silence and the previous plot left on
   screen.

   We now leave this page and do not come back. Everything else today happens on pages
   whose plot lists contain no unfinished entries.

#. In the Control Toolbox, switch from **Preprocess** to **Field Viewer**.

**What you just learned.** Projects, not CSVs, are how you save and resume work in
LaME. The Control Toolbox page you are on determines which plot types are offered.


2. Choosing fields
==================

*Goal: control which analytes are in play, build a ratio, and calculate a new field.*

Nothing in LaME plots an analyte you have not selected. That selection also drives what
the correlation matrix shows and what clustering uses, so it is the first real control
you have.

Selecting analytes and a ratio
------------------------------

#. Click **Analytes** in the pinned toolbar row. The *Select Analytes and Ratios*
   dialog opens on a square grid of your analytes.
#. The **diagonal** cells are the analytes themselves. Click along it to select
   ``Mn55``, ``Y89``, ``Sm147``, ``Eu153``, ``Gd157``, ``Ca43``, ``Fe57``, ``Mg24``.
   Selected cells highlight.
#. The **off-diagonal** cells are ratios. Above the diagonal gives row ÷ column; below
   gives column ÷ row. Find the cell where ``Y89`` meets ``Mn55`` and click it once.
#. Your choices appear in the **Selected** list on the right, with columns *Field*,
   *Scaling* and *Normalized*. The ratio appears as ``Y89 / Mn55``.
#. Click **Done**.

.. Figure placeholder FIG-2.1
   WHAT: The Select Analytes and Ratios dialog, mid-selection. Several diagonal cells
   highlighted, and one off-diagonal cell (Y89 x Mn55) highlighted. The Selected list
   on the right visible with both analytes and the "Y89 / Mn55" ratio row showing.
   Annotate with two short arrows: "diagonal = analyte", "off-diagonal = ratio".
   WHY: The diagonal/off-diagonal distinction is the single least obvious thing in this
   dialog and the thing people get wrong.
   SIZE: two-thirds page width.

The background colours in that grid are the correlation matrix — so the dialog is
already telling you which analytes co-vary before you plot anything.

Setting the reference
---------------------

#. Back in the Control Toolbox, find the **Ref.** row and set it to a chondrite —
   ``CI chondrite [AG89]``.

Do this **before** the next part. Normalised fields divide by this reference, and the
default is bulk silicate Earth, which is not what you want for a REE anomaly.

Calculating Eu*
---------------

Europium anomalies need a field that is not in your data: the interpolated Eu you would
expect from its neighbours. That is what the Calculator is for.

#. **Analysis** toolbar page → **Calculator**.
#. In the saved-formula box, choose ``Eu*``. The formula appears:

   .. code-block:: text

      {Analyte.Eu153_N}/({Analyte.Sm147_N}*{Analyte.Gd157_N})^(1/2)

   Fields are written ``{FieldType.Field}``. The ``_N`` suffix means
   reference-normalised — which is why the reference had to be set first.
#. Click **Calculate**.
#. Plot it: Control Toolbox **Field Viewer**, plot type ``field map``, then set the
   colour field type to ``Calculated`` and the field to ``Eu*``.

.. admonition:: Not in this build
   :class: error

   The Calculator's keypad offers ``case()`` and ``otw()`` buttons for conditional
   expressions. Conditionals do not work in this build — you will get *"could not
   evaluate conditional statement"*.

   The shipped Calculator documentation also describes a ``case(...)`` **function**.
   That syntax has never existed in any version. **Ignore the ``case()`` section of the
   Calculator docs.** Arithmetic, logs, powers and roots all work fine.

.. admonition:: Checkpoint 1
   :class: tip

   The Plot Tree on the right has a **Calculated** branch containing ``Eu*``. Your
   canvas shows a smooth, low-contrast Eu* map — much flatter than a raw element map,
   because you have divided out the overall REE level.

   *Not matching?* Open ``02-plots.lame_project.json`` — it has the fields, the ratio
   and Eu* already built.

.. Figure placeholder FIG-2.2  [CHECKPOINT]
   WHAT: Canvas showing the Eu* field map on RM02, with the Plot Tree visible on the
   right expanded to show the Calculated branch containing Eu*.
   WHY: Checkpoint reference. Also shows where calculated fields live in the tree,
   which is how attendees find them again later.
   SIZE: full page width.

#. **Save Project** in the pinned toolbar. Save it next to the workshop folder under
   your own name.

From here on, start each section by saving. You are building your own recovery points
alongside the ones we supply.

**What you just learned.** Field selection gates everything downstream. Ratios come
from the analyte grid; anything more complex comes from the Calculator. Normalised
fields depend on the reference material being set first.


3. One field at a time
======================

*Goal: read a single element's distribution properly before comparing elements.*

Histograms
----------

#. Control Toolbox **Field Viewer**, plot type ``histogram``.
#. Set the **X** field to ``Mn55``.
#. In the **Histogram** group, set *Histogram type* to ``PDF`` and tick **Show KDE**.
#. Try ``log-scaling``. Trace-element distributions are usually closer to log-normal
   than normal, and the shape change tells you whether yours is.
#. Set the colour field type to ``Cluster`` or ``ROI`` later in the day and this same
   histogram splits by group — a quick way to see whether two zones really differ.

.. Figure placeholder FIG-3.1
   WHAT: Mn55 histogram on RM02 with the KDE overlay switched on, log-scaling enabled.
   The Histogram control group visible in the Control Toolbox so the Bin width,
   No. Bins, Histogram type and Show KDE controls can be seen.
   WHY: Pairs the output with the controls that produced it.
   SIZE: two-thirds page width.

Correlations
------------

#. Plot type ``correlation``.
#. Set **Method** to ``Pearson``, then compare against ``Spearman``. Pearson assumes a
   linear relationship; Spearman only assumes monotonic, so a large gap between them is
   itself informative.
#. Tick **C²** to show correlation squared — the shared-variance view.

The matrix covers exactly the analytes you selected in section 2. Change the selection
and the matrix changes with it.

.. admonition:: Not in this build
   :class: error

   The correlation matrix **ignores filters**. Later today you will filter the map; the
   correlation plot will not respond. The same applies to the ternary map.

   To see a filter's effect, use ``field map``, ``histogram`` or ``roi map``.

**What you just learned.** Histogram shape tells you which scaling to use. Correlation
method choice is a real decision, not a default. Both read from your field selection.


4. Two fields, then three
=========================

*Goal: move from distributions to relationships, and back onto the map.*

#. Control Toolbox → **Scatter and Heatmaps**. The axis rows now have labels: **X**,
   **Y**, **Z** and **Color**.

Biplot
------

#. Plot type ``scatter``. Set **X** to ``Mn55`` and **Y** to ``Y89``. Leave **Z** empty.
#. Set **Color** to ``Ca43``. A third variable as colour is usually more informative
   than a third axis.

Heatmap
-------

#. Plot type ``heatmap``, same X and Y. With 78,000 points, overplotting hides the
   structure; binning reveals it.
#. In the **Biplot and Ternary** group, try the *Heatmaps* statistic — ``counts``,
   then ``median``. ``counts`` shows where the data is; ``median`` shows what a third
   variable does there.

Ternary
-------

There is no separate "ternary" plot type. A ternary appears when you fill in Z.

#. Plot type ``scatter``, then set **Z** to ``Fe57``. X, Y and Z must be three
   different fields.
#. With X = ``Mn55``, Y = ``Ca43``, Z = ``Fe57`` you have a compositional ternary of
   the three major garnet cations.

Ternary map
-----------

#. Plot type ``ternary map``, same three fields.
#. In the **Ternary Map** group, either pick a **Colormap** or set the four colour
   swatches — one per vertex plus one for the centre.
#. Click **Ternary map**.

Each pixel is now coloured by where it sits in the ternary. This is the single most
useful plot in LaME for seeing compositional zoning, because it puts three elements on
one map without you choosing which matters most.

.. Figure placeholder FIG-4.1
   WHAT: Side by side if the layout allows: the Mn55-Ca43-Fe57 ternary scatter on the
   left, and the corresponding ternary map on the right, using the same colour scheme
   so vertices are visually matched between the two.
   WHY: The link between position-in-ternary and colour-on-map is the whole idea, and
   it is much easier to see as a pair than as two separate figures.
   SIZE: full page width.

.. admonition:: Checkpoint 2
   :class: tip

   Your Plot Tree contains five plots: a field map, a histogram, a correlation, a
   scatter and a ternary map. The canvas shows the ternary map with clear zoning —
   the garnet core should be a visibly different colour from its rim.

   *Not matching?* Open ``02-plots.lame_project.json``.

*Try this:* double-click any leaf in the Plot Tree. It restores that plot — type, fields
and styling together. The tree is a record of your session, not just a list.

**What you just learned.** Scatter and heatmap answer the same question at different
densities. Adding Z turns either into a ternary. The ternary map is how you get a
three-element relationship back onto the spatial map.


5. Regions and filters
======================

*Goal: restrict the analysis to the material you actually care about.*

This is the part of LaME with the most moving parts, so read step 1 before clicking.

**Filters live inside regions of interest.** An ROI is a named, saved definition; a
filter is one rule inside it. You select the ROI first, then add filters to it. If you
add a filter with no ROI defined, LaME quietly creates one for you — which is
convenient once and confusing the second time, when it starts asking which region you
meant.

Your first ROI and filter
-------------------------

#. **Processing** toolbar page → **Filters**. The Masking Toolbox opens at the bottom
   on its **Filters** tab.
#. In the **ROI** table at the bottom of that tab, click **Add ROI**. A new row appears.
   Double-click its *Name* and call it ``garnet``. **Leave this row selected.**
#. Now in **Filter Settings** on the left: set *Field type* to ``Analyte`` and *Field*
   to ``Mn55``. The Min and Max boxes fill with that field's range.
#. Narrow it. Either type values, or use the percentile spin boxes beside them — the
   percentile route is usually faster for a first pass.
#. Set *Operator* to ``and``.
#. Click **Add filter**.

The filter appears as a row in the table on the right, with a **Use** checkbox, and the
map updates.

#. Add a second filter the same way on a different element — ``Ca43``, say. Because the
   ``garnet`` row is still selected, it joins the same region.

.. Figure placeholder FIG-5.1
   WHAT: The Masking Toolbox Filters tab, fully populated: Filter Settings on the left
   with Field/Min/Max/Operator filled in, the filter table on the right showing two
   rows with Use ticked, and the ROI table at the bottom with the "garnet" row
   selected and showing non-zero % Total and % Filtered.
   WHY: This is the most structurally confusing panel in the app. One annotated figure
   showing all three tables populated at once is worth several paragraphs.
   SIZE: full page width. Annotate the ROI table with "select this row FIRST".

Seeing what you removed
-----------------------

#. Control Toolbox **Field Viewer** → plot type ``roi map``.

Excluded pixels are drawn grey. This is the plot to use whenever you want to check what
a filter actually did — it shows you the mask itself rather than its effect on a value.

Polygons
--------

Filters cut by composition. Polygons cut by location.

#. Masking Toolbox → **Polygons** tab.
#. Flip the toggle switch at the left of its toolbar to enter polygon mode. The plot
   type collapses to ``field map`` only while you are drawing.
#. Click **Create a new polygon**, then click round a feature on the map to place
   vertices.
#. The *In/out* column on each row controls whether the polygon keeps or removes what
   is inside it.
#. Use **Move a control point**, **Add a vertex** and **Remove a vertex** to adjust.

.. admonition:: Not in this build
   :class: error

   Polygons are deliberately **excluded from clustering**. Drawing a polygon around a
   grain and re-clustering will not restrict the clustering to that grain.

   To scope an analysis spatially, use an ROI. That is what the clustering and
   stoichiometry sections do.

.. admonition:: Not in this build
   :class: error

   Two toolbar buttons to avoid: **Crop** and **Full Map**. Cropping is incomplete in
   this build, and the *Full Map* button that would undo it raises an error instead.
   Nothing today needs either; if you crop by accident, reopen your saved project.

   **Save filter** is also unavailable in the packaged build — it tries to write inside
   the application bundle. Your filters are saved in your *project*, which is what
   matters.

.. admonition:: Checkpoint 3
   :class: tip

   The ROI table has one row named ``garnet`` with a non-zero **% Filtered**. The
   ``roi map`` shows your garnet in colour with a grey excluded rim.

   *Not matching?* Open ``04-clusters.lame_project.json``, which has the ROI already
   built — it also has clusters, which you are about to need anyway.

**What you just learned.** ROI first, then filters into it. ``roi map`` is how you
verify a mask. Polygons are spatial, filters are compositional, and only filters and
ROIs scope downstream analysis.


6. Clustering
=============

*Goal: let the data propose its own zones, then test whether they are real.*

#. Control Toolbox → **Clustering**. Opening the page runs clustering immediately with
   the current settings and plots the result, so you will see groups before you have
   chosen anything.

k-means
-------

#. Set **Method** to ``k-means`` and **No. clusters** to ``4``.
#. Plot type ``cluster map``.
#. Click **Randomize** beside the **Seed** box and watch the map. k-means starts from
   random centres; if your zones survive several seeds they are robust, and if they
   reshuffle they were not there.

.. admonition:: Not in this build
   :class: error

   The **Distance** combobox on this page has no effect — the distance-metric code is
   not active in this build. Changing it recomputes and gives an identical result.

   Also: ``HDBSCAN`` works as a method, but combining it with the ``cluster
   performance`` plot type silently does nothing. HDBSCAN discovers its own cluster
   count, so there is no *k* to sweep. Use ``cluster performance`` with k-means or
   fuzzy c-means only.

Changing what clustering sees
-----------------------------

Clustering uses exactly the fields you selected in section 2 — so changing that
selection changes the clusters.

#. Click **Analytes** and add two or three REE you had left out — ``La139``, ``Ce140``,
   ``Nd146``.
#. Click **Done**. Because you are on the Clustering page, it recomputes and replots
   automatically.
#. Compare against what you had. Adding light REE will usually sharpen a growth-zoning
   boundary, because those elements partition strongly during garnet growth.

.. note::

   That automatic recompute only happens while you are on the **Clustering** or
   **Dimensional Reduction** page. From anywhere else, change the selection and then
   press **Update Plot**.

Clustering on principal components
----------------------------------

With 11 correlated analytes, much of what k-means sees is the same signal repeated.
Reducing first often gives cleaner groups.

#. Control Toolbox → **Dimensional Reduction**. Opening the page runs PCA.
#. Set **Method** to ``PCA: Principal component analysis``. Look at the ``variance``
   plot to see how many components you actually need — usually three or four carry
   nearly everything.
#. Go back to **Clustering**. Tick the **PCA** checkbox and set **No. basis** to the
   number you just decided on.
#. Re-cluster.

Run PCA *before* ticking that box. If no PCA scores exist, LaME falls back to the raw
analytes without telling you, and the comparison you were trying to make silently
does not happen.

.. Figure placeholder FIG-6.1
   WHAT: Two cluster maps of RM02 side by side, both k-means with 4 clusters and the
   same seed: left = raw analytes, right = PCA-preconditioned. Use the same cluster
   colours in both if possible.
   WHY: The whole point of the PCA step is that the boundaries get cleaner. Shown as a
   pair this is obvious; described in prose it is not.
   SIZE: full page width.

Naming and reusing clusters
---------------------------

#. Masking Toolbox → **Clusters** tab. The table lists your clusters with *Name*,
   *Link*, *Color*, *% Total* and *% Filtered*.
#. Rename a cluster in place — ``core``, ``rim``, ``inclusion``. These names follow
   through into the legend, the Notes report and the stoichiometry scope list.
#. Recolour one by clicking its *Color* cell.
#. Tick two clusters that you think are the same zone and click **Link Clusters** —
   they then behave as one class.
#. Tick the cluster you want to work on and click **Create Region**. It becomes an ROI,
   which is how you will scope the next section.

.. admonition:: Checkpoint 4
   :class: tip

   A ``cluster map`` with four k-means groups, the **PCA** box ticked, and a Clusters
   table with four named rows. At least one cluster has been turned into an ROI, so the
   ROI table in the Filters tab now has a second row.

   *Not matching?* Open ``04-clusters.lame_project.json``. Its clusters restore from
   disk without recomputing, so it loads quickly.

**What you just learned.** Clustering reads your field selection, so curating that
selection is the main lever you have. PCA first usually improves it. Clusters become
ROIs, and ROIs are how you scope everything downstream.


7. Mineral formulae across three garnets
========================================

*Goal: get apfu, site occupancies and end-member proportions, and map them.*

LaME can convert composition into a mineral formula — site by site, with iron split
between Fe²⁺ and Fe³⁺ by charge balance. The chemistry behind this is the most heavily
validated part of LaME, cross-checked against published mineral-recalculation workbooks
for garnet, feldspar, olivine and pyroxene.

.. important::

   **Scope it to one region before you touch anything else.** The calculation runs
   pixel by pixel, on the interface thread, and it re-runs every time you change any
   setting. Across a whole 78,000-pixel map that is minutes of frozen window, several
   times over. Scoped to one cluster it is seconds.

RM02 — and what happens without silicon
---------------------------------------

#. **Analysis** toolbar page → **Stoichiometry**. The *Stoichiometric Calculator* opens.
#. **First**, in the **Compute scope** group: set *Filter* to the ROI you made from a
   cluster, and tick **only that region** in the list below. New regions start
   unticked deliberately — leave the others alone.
#. Now the **Settings** group: *Mineral* = ``Garnet``, *Input basis* = ``ppm``,
   *Redox method* = ``droop_1987``, *BDL treatment* = ``zero``.
#. Leave **Compare all redox methods** switched **off**. It triples the work.
#. Click **Run**.

New fields appear under field type ``Stoichiometry``:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Field
     - Meaning
   * - ``Grt_Z``, ``Grt_Y``, ``Grt_X``
     - Cations per formula unit on each site — tetrahedral, octahedral, dodecahedral
   * - ``Grt_pyrope`` … ``Grt_uvarovite``
     - End-member proportions: pyrope, almandine, spessartine, grossular, andradite,
       uvarovite
   * - ``Grt_dominant``
     - Which end member dominates at each pixel — a categorical field

#. Plot it: ``field map``, colour field type ``Stoichiometry``, field ``Grt_dominant``.
   It draws with a labelled swatch legend rather than a colour bar, because the values
   are categories rather than amounts.

Now look at ``Grt_Z``. It should be close to 3.0, filled by silicon. **On RM02 it is
not** — RM02 has no Si, so LaME has filled the tetrahedral site with aluminium instead,
following the fallback order in the garnet configuration. The end-member percentages
that come out are correspondingly wrong.

This is worth seeing rather than being told. The stoichiometry calculation is only as
good as the elements you measured, and a missing major element does not produce an
error — it produces a plausible-looking answer that is incorrect.

The same garnet, with silicon
-----------------------------

#. Switch sample using the selector in the pinned toolbar: choose ``TR1-07``.
#. Make a quick ROI on it — one filter on ``Mn55`` is enough; you do not need to
   re-cluster.
#. Scope the Stoichiometry dock to that ROI and **Run** again.
#. Compare ``Grt_Z`` with what RM02 gave you. With ``Si29`` present it should sit near
   3.0, and the end-member proportions are now meaningful.
#. Repeat on ``WOS-02`` if time allows. It is the largest of the three, so keep the
   region small.

.. Figure placeholder FIG-7.1
   WHAT: Three Grt_dominant maps side by side — RM02, TR1-07, WOS-02 — each with its
   swatch legend visible. Underneath each, the Grt_Z value from the region summary
   table, so the ~3.0 (TR1-07, WOS-02) versus wrong (RM02) contrast is explicit.
   WHY: This is the payoff figure of the whole garnet thread and the Si lesson in one
   image.
   SIZE: full page width.

.. admonition:: Checkpoint 5
   :class: tip

   At least two garnets have ``Grt_*`` fields, and you have a ``Grt_dominant`` map with
   a swatch legend on screen. ``Grt_Z`` is near 3.0 for TR1-07 and clearly not for RM02.

.. admonition:: Not in this build
   :class: error

   If the **Mineral** dropdown is empty and outlined in red, the application cannot
   find its mineral configuration files. Tell the presenter — there is a workaround.

*Try this:* the **Region summary** table at the bottom of the dock gives per-region
statistics. Switch *Region source* between ``ROI`` and a cluster column to compare
formulae between zones you identified in section 6.

**What you just learned.** Scope first, always. Site totals are your sanity check on
whether the calculation had the elements it needed. ``Grt_dominant`` maps mineral
classification back onto the map.


8. Pyrite — your turn
=====================

*Goal: apply what you have done to a different mineral system, with less guidance, and
see what preconditioning does to a clustering.*

This section has fewer numbered steps on purpose. You have the tools now; the questions
are new.

**The questions.** ``71A-Py 12`` is a pyrite-bearing sample. Two things to find out.
Does clustering change when you precondition the data with PCA first? And once you have
the pyrite on its own, is it chemically uniform, or are there distinct populations
within it?

Remember this map is **uncalibrated**: counts per second, not ppm. Relative patterns
are fine; absolute values and mineral formulae are not.

#. Open ``06-pyrite.lame_project.json``, or add ``data/71A-Py 12.lame.csv`` yourself.

#. **Find the pyrite.** Field maps of ``Fe57`` and ``S34``. Pyrite is FeS₂, so it
   should stand out sharply against the silicate matrix in both. Something like 40% of
   this map is sulfide, so it is not a small target.

#. **Cluster the whole map, on the analytes.** Clustering page, ``k-means``, 4 clusters.
   Choose a sensible set of analytes first (``Fe57``, ``S34``, ``Cu65``, ``Co59``,
   ``Ni60``, ``As75`` is a good start). Look at the ``cluster map``: two of the four
   groups should land on the sulfide and two on everything else.

   Note which clusters are the pyrite, and roughly what fraction of the map they cover.

#. **Now precondition with PCA and cluster again.** Visit the Dimensional Reduction
   page first so the scores exist, then return to Clustering, tick **PCA** and set
   **No. basis** to 3. Re-cluster.

   Compare the two cluster maps. The sulfide/matrix split survives — that boundary is
   not in doubt — but the way the pyrite is divided *within* itself changes, and so do
   the cluster proportions. Neither answer is the "right" one: PCA has reweighted what
   counts as similar, by dropping the directions in which the data varies least.

.. admonition:: Why this matters
   :class: note

   PCA before clustering is often presented as a tidying step. It is not neutral. It
   decides which variation the clustering is allowed to see. Comparing the two maps on
   the same sample, as you just did, is the honest way to find out whether a result
   depends on that choice — and it takes two minutes.

#. **Filter to the pyrite with the Cluster tool.** Masking Toolbox → **Clusters** tab.
   Tick the clusters that are the pyrite, then press **Create Cluster Mask**.

   Everything outside those clusters is now masked, so every plot that follows uses
   pyrite pixels only. This is the cluster-based route to the same place section 5
   reached with an ROI and field filters — no bounds to choose, because the clustering
   has already found the boundary for you.

#. **Fe against Cu.** Scatter and Heatmaps page, plot type ``scatter``: **X** =
   ``Fe57``, **Y** = ``Cu65``, **Color** = your cluster field.

   Fe is the pyrite's own framework and barely varies; Cu does not substitute into
   pyrite in any quantity, so where it appears it is telling you about something else —
   an inclusion, a later overprint, or a different generation of growth. Watch for the
   points that climb away from the main Fe population.

#. **A histogram per cluster.** Field Viewer page, plot type ``histogram``, **X** =
   ``Co59``, with **Show KDE** on and ``log-scaling`` set. Then step through your
   clusters and compare.

   Expect a dramatic separation between the sulfide clusters and the matrix — Co runs
   a few hundred thousand counts inside the pyrite against a few thousand outside. What
   you will probably *not* see is much difference between the two pyrite clusters
   themselves: Co (and Ni, which behaves the same way) is substituting for Fe fairly
   uniformly through the sulfide.

   That is a real result, not a failed exercise. It says the populations your clustering
   found are not Co–Ni populations. Go back to the biplot: ``Cu65``, and ``As75``, are
   where those two groups actually differ.

.. Figure placeholder FIG-8.1
   WHAT: Two cluster maps of 71A-Py 12 side by side at the same scale — left, k-means
   on the raw analytes; right, k-means after PCA with 3 components. Same number of
   clusters, same colours where they correspond. Annotate the sulfide/matrix boundary
   as unchanged and circle one area where the division *within* the pyrite differs.
   WHY: The whole point of the first half of this section. Attendees need to see that
   preconditioning moved an internal boundary while leaving the obvious one alone.
   SIZE: full page width.

.. Figure placeholder FIG-8.2
   WHAT: The Fe57 vs Cu65 biplot on the masked pyrite, points coloured by cluster,
   legend visible. Frame it so the Cu-enriched population is clearly separated from
   the main Fe cloud.
   WHY: The scientific punchline of the pyrite thread, and the figure attendees are
   most likely to want to reproduce on their own data.
   SIZE: two-thirds page width.

.. Figure placeholder FIG-8.3
   WHAT: Co59 histograms for each cluster, log-scaled, ideally overlaid or in a small
   column so they can be compared directly. The two sulfide clusters should sit on top
   of one another, far to the right of the matrix clusters.
   WHY: Supports the point that a strong element contrast between pyrite and matrix
   says nothing about structure *within* the pyrite.
   SIZE: half page width.

.. admonition:: Checkpoint 6
   :class: tip

   Two cluster maps of the same sample (with and without PCA), a cluster mask
   restricting the map to the sulfide, an Fe–Cu biplot coloured by cluster, and a
   Co histogram you have compared across clusters.

*Try this:* turn the cluster mask off with the **Cluster Mask** toolbar toggle and redraw
the Fe–Cu biplot on the whole map. The silicate matrix swamps the pyrite entirely — a
concrete demonstration of why the masking step was not optional.

**What you just learned.** Clustering is a choice, not a measurement: preconditioning
changes the answer, and the way to know how much is to run it both ways. Clusters are a
masking tool in their own right, not just a picture. And a huge contrast in one element
between two materials tells you nothing about structure inside either of them.

9. Notes and the methods report
===============================

*Goal: leave with a record of what you did, not just the plots.*

#. **Log** toolbar page → **Notes**. An editor window opens — titled *reST Editor* —
   holding a notes file tied to this sample inside your project folder.
#. Click **Record** in the same toolbar page. The status-bar *Notes* light turns red.
#. Now make a plot — anything. It is captured into the notes automatically as a figure.
#. In the Notes toolbar, open the **Insert** page and use **Formatted Info**. It offers:

   * Sample info
   * List analytes used
   * Current plot details
   * Filter table
   * PCA results
   * Cluster results
   * Diffusion results
   * Stoichiometry results

   Insert **List analytes used**, **Filter table** and **Cluster results**. Each writes
   a formatted block pulled from your live session — the actual analytes, the actual
   filters, the actual clusters.

That is the methods paragraph of a paper, assembled from what you really did rather
than from what you remember doing a month later.

.. Figure placeholder FIG-9.1
   WHAT: The reST Editor window with a recorded figure and at least two inserted
   Formatted Info blocks visible (analytes used, and the filter table as a formatted
   table). The Formatted Info menu can be shown open if it fits.
   WHY: Shows both halves of the feature — automatic figure capture and the
   live-data info blocks.
   SIZE: two-thirds page width.

.. admonition:: Not in this build
   :class: error

   There is also a **Capture** toggle, and a Workflow designer with a drag-and-drop
   block canvas. Capture currently records only sample changes as reusable blocks —
   so treat it as a **methods report generator**, which it does well, rather than as a
   way to record your clicks into a re-runnable workflow. Hand-built workflows in the
   designer do run; recording them does not yet.

**What you just learned.** Notes are per-sample and live inside the project. Record
captures figures as you go. Formatted Info blocks pull real state, so the record stays
honest.


10. Take it home
================

#. **Save Project**.
#. Close the project — **File → Close Project**.
#. Reopen it. Your fields, ratios, calculated fields, ROIs, filters, polygons, clusters
   and notes all come back.

That round trip is the thing to trust: the project file is the unit of work, and it
survives being moved between machines because it stores paths relative to itself.


Known limitations in this build
===============================

Everything from the boxes above, in one place.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Feature
     - What you will see
     - What to do instead
   * - ``gradient map`` plot type
     - A warning about noise reduction, or nothing at all
     - Not available; use ``field map``
   * - Calculator conditionals
     - *"could not evaluate conditional statement"*
     - Arithmetic only. **Ignore the ``case()`` section of the Calculator docs** — that
       syntax never existed
   * - **Crop** / **Full Map**
     - Crop is incomplete; *Full Map* raises an error instead of undoing it
     - Avoid both. Reopen your project if you crop by accident
   * - ``profile`` and ``polygon`` plot types
     - Blank canvas, no error
     - Drive profiles from the **Profiles** dock (Appendix A)
   * - Correlation and ternary map
     - Both ignore filters and masks entirely
     - Check filter effects on ``field map``, ``histogram`` or ``roi map``
   * - Adding a filter with no ROI selected
     - First one silently creates an ROI; the second asks which region you meant
     - Create and select the ROI row first
   * - Polygons + clustering
     - Clustering ignores polygons by design
     - Scope with an ROI instead
   * - Cluster **Distance** combobox
     - No effect on the result
     - Leave it alone
   * - HDBSCAN + ``cluster performance``
     - Silently does nothing
     - Use k-means or fuzzy c-means for that plot
   * - **Save filter** preset
     - *"could not save filter table"* in the packaged build
     - Your filters are saved in the project, which is what matters
   * - Stoichiometry on a whole map
     - Minutes of frozen window
     - Scope to one ROI or cluster first
   * - Lu–Hf dating
     - Needs ¹⁷⁶Lu/¹⁷⁷Hf and ¹⁷⁶Hf/¹⁷⁷Hf, absent from today's data
     - Implemented, but not demonstrable on these samples
   * - Workflow **Capture**
     - Records only sample changes as blocks
     - Use it as a methods-report generator
   * - Thermometry / Barometry tabs
     - Empty method dropdowns
     - Not implemented


If you fall behind
==================

Open the nearest project file and carry on. You lose nothing that later sections need.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - File
     - Picks up at
   * - ``00-open.lame_project.json``
     - Section 1 — RM02 loaded, nothing else done
   * - ``02-plots.lame_project.json``
     - Section 4 — fields, ratio and Eu* built
   * - ``04-clusters.lame_project.json``
     - Section 7 — ROI and clusters ready
   * - ``06-pyrite.lame_project.json``
     - Section 8 — pyrite sample loaded

**File → Open Project**, pick the file, carry on. Do not spend the workshop debugging.


Appendix A: Profiles
====================

Profiles extract a transect across a map — the standard way to show garnet zoning as a
function of radius. It works, but the route to it is not the obvious one.

.. admonition:: Not in this build
   :class: error

   Do **not** select ``profile`` from the plot-type list. It produces a blank canvas.
   Profiles are driven entirely from the Profiles dock.

#. Get a ``field map`` on screen.
#. **Analysis** toolbar page → **Profiles**.
#. Flip the toggle switch at the left of the dock's toolbar. Plot type collapses to
   ``field map`` while profiling is active.
#. Click **Create new profile and set control points**, then click along the map — for
   a garnet, rim through core to the far rim.
#. Set **Point radius** (how much to average around each point), **Interp. distance**
   (spacing along the transect) and **Point type** (``median + IQR`` is the robust
   choice).
#. In **Axis Options**, set **No. subplots**, then for each subplot pick a field and
   click the add button. Several elements stacked against distance is how zoning is
   normally presented.
#. Use **Edit mode** to click out any point sitting on a crack or inclusion.
#. Save with the export button. Profiles are stored per sample in your project.

.. Figure placeholder FIG-A.1
   WHAT: The Profiles dock beside a field map with a rim-core-rim transect drawn on it,
   plus the resulting multi-subplot profile showing two or three elements against
   distance.
   WHY: Shows the control points on the map and the output together, which is what
   makes the workflow make sense.
   SIZE: full page width.


Appendix B: Getting your own data in
====================================

Today's samples were already converted to LaME's ``.lame.csv`` format. For your own
data, the Import tool handles raw exports.

#. **Home** toolbar page → **Import Files**.
#. Choose a **Data type** and **Method** — ``LA-ICP-MS`` with ``quadrupole``, ``TOF`` or
   ``SF``, or ``XRF`` with ``image``.
#. Point it at your directory. The metadata table fills with one row per sample.
#. Set spot size, sweep time and stage speed; LaME derives pixel spacing from them.
#. Use the per-sample **Select files** button to check which files map to which
   analytes, then **Import**.

.. admonition:: Not in this build
   :class: error

   Only ``LA-ICP-MS`` and ``XRF`` → ``image`` import in this build. The other data
   types populate the metadata table and then stop with a *"Not implemented"* message,
   so the table filling in is not a sign that it will work.

.. Figure placeholder FIG-B.1
   WHAT: The Map Import dialog with the metadata table populated for two or three
   samples, Data type on LA-ICP-MS and Method on quadrupole, with the spot
   size/sweep/speed columns filled and the derived dX/dY columns visible.
   WHY: Attendees will do this unsupervised later; the figure is their reference for
   which columns they must fill in themselves.
   SIZE: full page width.

If a conversion gives you trouble, send the presenter a raw export and you will get a
``.lame.csv`` back.


Getting help
============

**In the application.** **Help** menu → *User Guide* or *Tutorials*. There is also a
context-sensitive mode: toggle **Help** in the toolbar, then click any part of the
interface to jump to its documentation.

**Video walkthroughs.**

* `Introduction to LaME <https://www.youtube.com/watch?v=wPuP3z1NJXA>`_ — interface,
  navigation, view modes
* `Loading Data and Selecting Samples <https://www.youtube.com/watch?v=DWJTAN3SPS8>`_ —
  import formats and analyte selection
* `Visualization Fundamentals <https://www.youtube.com/watch?v=j6oNE7QN5Ak>`_ —
  correlation, spatial patterns
* `Working with Notes <https://www.youtube.com/watch?v=5Xe5hjQQcMc>`_

**Reporting a problem.** **Help** menu → *Report Bug*. Please include what you were
doing, what you expected, and what happened. Everything in
`Known limitations in this build`_ is already known — anything else is worth telling us
about, and today is exactly the sort of session that surfaces new ones.

References
==========

.. _GitHub: https://github.com/dhasterok
