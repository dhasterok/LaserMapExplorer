==========================================
Laser Map Explorer (LaME) Workshop
==========================================

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/resources/icons/LaME-64.png
          :align: center
          :alt: Alternate text goes here
          :width: 25%

          Laser Map Explorer

:Duration: 14:00–17:00, with a coffee break at 15:00
:Build: ``LaME v0.9.0-workshop``
:Datasets: Three garnet maps, one pyrite map, one XRF core scan

.. note::

   Fill in your own date, venue and contact details above before printing.

.. contents:: On this page
   :depth: 2
   :local:


What today covers
=================

LaME turns element maps into something you can rapidly explore: import, filter, plot,
cluster, calculate, and get mineral formulae out the other end.

We work through the day the way you would work through a real dataset, rather than
feature by feature.

**Part I — RM01, start to finish.** One garnet, taken from the files the instrument
software produced all the way to a map of its mineral end-members. Everything else
today is a variation on this sequence.

**Part II — two more garnets.** The same analysis, faster, on samples that differ in
ways that matter. This is also where we keep a record of what we did.

**Part III — pyrite.** A different mineral system, uncalibrated, where you drive.

**Part IV — an XRF core scan.** A different instrument, a different import route, and
a million pixels of semi-quantitative data.

**Ask questions whenever you have them.** The schedule has slack in it for exactly
that, and if there is something you want to know how to do with your own data, we can
usually do it on the spot.

LaME is beta software and this handout is honest about that. Where something is
unfinished you will see a **Not in this build** box telling you what you would see and
what to do instead. Those boxes are not apologies — they are there so you do not waste
the workshop discovering them yourself. A consolidated list is in
`Known limitations in this build`_.

One part of the chain is not yet yours to drive: **going from raw counts to calibrated
concentrations inside LaME**. Where we need calibrated data, it was prepared beforehand
in iolite, and you will see how it is brought in. The presenter will demonstrate the
parts that are not ready rather than asking you to click through them.

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
   :widths: 50 50
   :header-rows: 0

   * - .. figure:: /Users/dhasterok/Documents/GitHub/siesta-rest-editor/src/siesta/icons/siesta2.png
          :align: center
          :alt: Alternate text goes here
          :width: 65%

          Siesta
     - .. figure:: /Users/dhasterok/Documents/GitHub/blueberry-colortools/resources/icons/blueberry_64.png
          :align: center
          :alt: Alternate text goes here
          :width: 65%

          Blüberry


Before you start
================

Copy the whole **LaME-Workshop** folder from the USB stick to your Desktop, then
install LaME from the copy you made. The important parts of the folder:

.. code-block:: text

   LaME-Workshop/
   ├── program/
   │   ├── LaME-macos-arm64.dmg       macOS installer (Apple Silicon)
   │   ├── LaME-windows-x64.zip       Windows — unzip and run LaME.exe
   │   └── reST Editor.app            Siesta, as a stand-alone macOS app
   └── data/
   │   ├── LA-ICP-MS/
   │   │   ├── RM01/                  28 iolite matrix files  <- we import this
   │   │   ├── RM01.lame.csv          the same data, already converted
   │   │   ├── WOS-02.lame.csv        garnet, already converted
   │   │   ├── TR1-07.lame.csv        garnet, already converted
   │   │   └── 71A-Py 12.lame.csv     pyrite, already converted
   │   └── XRF/
   │       └── core 7/
   │           ├── row1/ … row5/      26 element images each  <- we import these
   │           ├── core7_row1.lame.csv … row5    already converted
   │           └── core7_Video Mosaic.png        optical image of the core      
   └── workshop_figures/
   ├── workshop_plan.pdf   
   └── workshop_plan.rst

Two directories are the raw material for the import exercises — ``RM01/`` in Part I and
``row1/`` … ``row5/`` in Part IV. The ``.lame.csv`` files beside them are the same data
already converted, and they are your safety net: if an import does not come out right,
open the converted file and carry on.

.. warning::

   **Keep the folder structure.** Nothing in LaME depends on where you put the folder,
   but this handout refers to these paths throughout, and your own saved projects will
   remember where the data was when you loaded it.

.. admonition:: macOS first launch
   :class: tip

   The build is unsigned, so double-clicking it gets you *"LaME cannot be opened
   because the developer cannot be verified."* **Right-click the app → Open**, then
   confirm. You only do this once. Windows SmartScreen behaves similarly: **More
   info → Run anyway**.

First launch takes noticeably longer than later ones — it is unpacking itself, not
hung.


How to read this handout
========================

**Numbered steps are ordered procedures.** Do them in order; a few only work in one
order, and those are called out.

.. admonition:: Checkpoint
   :class: tip

   **Boxes like this are things you should see.** If your screen does not match, do not
   debug it — ask, or take the stated shortcut and carry on. Nothing later depends on
   you having done it the slow way.

.. admonition:: Not in this build
   :class: error

   **Boxes like this are known limitations.** They tell you what you would see if you
   tried, and what to do instead.

.. admonition:: Watch, do not click
   :class: note

   **Boxes like this are demonstrations.** The feature works, or works well enough to
   show, but not reliably enough for twenty people to drive at once.

*Try this* paragraphs at the end of a section are optional. They exist so that if you
finish early you have somewhere to go that does not put you ahead of the group.

**This handout is longer than the workshop, on purpose.** In three hours we will get
through roughly eleven of the seventeen sections. The rest are written to be worked
through on your own afterwards, and nothing in a later section depends on having been in
the room for an earlier one — the data is on your stick and the steps are all here.

The sections most likely to be left for you are **7** (REE patterns), **12** (the
workflow designer), **13** (the other two garnets), **15** (pyrite) and **16–17** (the
XRF core scan). Section 15 is the best one to start with: it is already written as an
exercise rather than a walkthrough.

**Save early and often.** Section 1 ends by saving your project, and each section after
that begins by suggesting you save again. Those saves are your recovery points — see
`If you fall behind`_.


The datasets
============

All real data, from four different instrument setups.

.. list-table::
   :header-rows: 1
   :widths: 14 14 10 62

   * - Sample
     - Pixels
     - Material
     - Notes
   * - ``RM01``
     - 95,676
     - Garnet
     - 476 × 201 px, 6.6 × 16 µm, 3.14 × 3.22 mm. A metamorphic garnet partly
       dissolved. 28 analytes: full REE suite plus Ca, Fe, Mg, Mn, Al, Ti, Cr, P, Li,
       Zr, Th, U, Pb. **Our primary sample**, and the one we import ourselves.
   * - ``WOS-02``
     - 123,256
     - Garnet
     - 33 analytes. Adds **Si**, Na, Sr, Ba and a second Pb isotope. The largest of the
       garnets.
   * - ``TR1-07``
     - 59,917
     - Garnet
     - 33 analytes, same suite as WOS-02. The smallest and quickest of the three.
   * - ``71A-Py 12``
     - 29,666
     - Pyrite
     - 91 scan lines × 326 px, 20 × 6.1 µm. 30 analytes: S, Fe and the chalcophile
       suite — **Co**, **Ni**, **Cu**, Zn, As, Se, Ag, Cd, Sn, Sb, Te, Au, Hg, Tl, Pb,
       Bi. Gold is below detection in most pixels, so the chalcophile story is in Cu
       and As.
   * - ``core 7``
     - ~997,000
     - Drill core
     - Five scanned segments, 1200 px long by 158–181 px wide, 26 element channels.
       X-ray fluorescence **intensity**, not concentration.

What these datasets **cannot** do — all five limits are properties of the data, not of
the software:

* **RM01 has no silicon.** Garnet is X\ :sub:`3`\ Y\ :sub:`2`\ Z\ :sub:`3`\ O\ :sub:`12`,
  and Si normally fills the tetrahedral Z site. Without it, LaME fills Z with aluminium
  instead. We use this deliberately in `11. Mineral formulae and the dominant phase`_ —
  it is the clearest demonstration you will get of what the stoichiometry calculation
  needs from your data.
* **None of them can do Lu–Hf dating.** That needs :sup:`176`\ Lu/:sup:`177`\ Hf and
  :sup:`176`\ Hf/:sup:`177`\ Hf. These maps have :sup:`175`\ Lu and at most one Hf
  isotope. The capability is real — you will see a result from a different sample — but
  no amount of clicking will produce an isochron from today's data.
* **The pyrite map is uncalibrated.** Values are counts per second, not ppm. Maps,
  filters, clusters and biplots are all valid on CPS. Mineral formulae and chondrite
  normalisation are **not**, so do not run the Stoichiometry dock on it.
* **The XRF core data is intensity, and each channel was scaled separately.** Patterns
  within one element across the core are meaningful; the ratio of one element's number
  to another's is not. Cluster it, map it, biplot it — but do not read the values as
  concentrations.
* **Isotope names differ between samples**, because the three garnets were run on
  different setups. RM01 has ``Fe57``, ``Ti49``, ``Cr53``; WOS-02 and TR1-07 have
  ``Fe56``, ``Ti47``, ``Cr52``. When a step names a field, check the sample you are
  actually on.


Part I — RM01, from files to formulae
=====================================

1. Importing RM01
-----------------

*Goal: turn 28 files of numbers into a loaded sample, and understand what LaME needed
from you to do it.*

The files in ``data/LA-ICP-MS/RM01/`` are **matrix exports from iolite**: one CSV per
analyte, each a bare rectangle of numbers with no header row and no coordinates —
``RM01 Fe57_ppm matrix.csv`` and 27 others. Every file is the same shape, and that shape
*is* the map.

What they do not contain is any statement of how big a pixel is. That is what you supply
in the import dialog, and it is the one part of importing you have to get right.

.. admonition:: Watch, do not click
   :class: note

   Calibrating raw counts to ppm is not yet something LaME will do for you. These files
   were calibrated in iolite first. The presenter will show where that step will live.

#. **Home** toolbar page → **Import Files**. The *Map Importer* dialog opens.
#. Set **Data type** to ``LA-ICP-MS`` and **Method** to ``quadrupole``.
#. Click **Open directory** and choose ``data/LA-ICP-MS/``. The metadata table fills
   with one row per sample it found — ``RM01`` among them.
#. Fill in these three columns on the ``RM01`` row:

   .. list-table::
      :header-rows: 1
      :widths: 24 16 60

      * - Column
        - Value
        - Why
      * - **Spot size (µm)**
        - ``16``
        - The laser spot, and so the spacing between adjacent scan lines. This becomes
          dX.
      * - **Sweep (s)**
        - ``0.279``
        - The mass spectrometer's cycle time — how long one pass through all 28 masses
          took.
      * - **Speed (µm/s)**
        - ``23.66``
        - How fast the stage moved under the beam. Speed × sweep is how far the spot
          travelled per reading, and so becomes dY.

#. Watch the **dX** and **dY** columns as you type. They are computed, not editable,
   and they should settle on **dX = 16** and **dY = 6.6**.
#. Leave **Swap XY**, **Reverse X** and **Reverse Y** unticked.
#. Click **Select files** on the ``RM01`` row to see what LaME thinks it has: 28 rows,
   one per file, each with the analyte it parsed out of the filename. Check a couple —
   ``RM01 Fe57_ppm matrix.csv`` → ``Fe57``. Close it.
#. Click **Import**.

.. admonition:: Checkpoint 1
   :class: tip

   ``RM01`` appears in the sample selector in the pinned toolbar, and a field map is on
   the canvas. The axes run to roughly **3140 µm in X and 3220 µm in Y**, and the map is
   very nearly square.

   *Axes in the thousands but the map a thin sliver?* dX and dY are the wrong way round
   — check that Swap XY is unticked.

   *Axes running 0–476 and 0–201?* Spot size, sweep and speed were left blank, so LaME
   fell back to one unit per pixel. Re-import with the three values above.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/import_la-icp-ms.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    The Map Importer dialog with data/LA-ICP-MS/ loaded. Data type on LA-ICP-MS,
    Method on quadrupole. The RM01 row visible with *spot size* 16, *sweep* 0.279, *speed*
    23.66 typed in and the derived dX=16 / dY=6.6 cells showing.

.. admonition:: Why this matters
   :class: note

   Nothing downstream warns you about wrong pixel dimensions. The map still draws, the
   clusters still cluster, the formulae still compute. What changes is the scale bar,
   the aspect ratio, and every distance you measure off the map — so a profile across a
   garnet rim comes back with the wrong width and nothing tells you.

   The arithmetic LaME uses is in the dialog: **dX = spot size**, and
   **dY = speed × sweep**. If you can reconstruct those three numbers for your own
   data, you can check it.

Save it before you do anything else
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. **Save Project** in the pinned toolbar. Put it on your Desktop, under your own name —
   not inside the workshop folder.

Do this now rather than later, for two reasons that are not obvious.

**It arms the autosave.** LaME autosaves every ten minutes, but an *untitled* project
has nowhere of its own to go — it is written to a scratch location and stays untitled.
Once the project has a name, autosave writes back to it, and the afternoon's work is
protected without you thinking about it again.

**It creates the project folder.** Saving establishes the directory that the rest of the
day writes into: your notes file lives there, and ``figures/`` and ``data/``
subdirectories appear beside it the first time you export a plot or a table. Section 14
depends on that folder existing.

*Try this:* re-import the same directory with ``Swap XY`` ticked and compare. It is
worth seeing once what a transposed map looks like, so that you recognise it later.

**What you just learned.** LaME reads a directory of per-analyte matrix files as one
sample. The geometry comes from you, not from the files. The derived dX/dY columns are
your check that it was understood correctly. Saving the project early is what makes
autosave and the project folder real.


2. First look at the maps
-------------------------

*Goal: read the sample before analysing it.*

#. Control Toolbox → **Field Viewer**, plot type ``field map``.
#. Step the **Color** field through the analytes. Start with ``Mn55``, ``Ca43``,
   ``Fe57``, ``Mg24`` — the major garnet cations — then ``Y89`` and a few REE.
#. In the Styling Toolbox on the right, open **Coloring** and try a different
   **Colormap**, then set **Scale** to ``log``. Trace elements spanning three orders of
   magnitude are unreadable on a linear colour ramp.

You should be able to see growth zoning, and the partial dissolution the sample is
named for.

Rather than look at individual maps, we can look at all of them rapidly using the 
**Quick View** canvas tab.  The user is able to create a custom sort of the maps in
this view.  The default is to arrange the maps by compatibility, often resulting in
a gradual visual changes from map to map that reflect processes within a mineral and
rapid changes that relate to different minerals.

When you are done examining the maps, select the **Single View** tab.

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/quick_view_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    **Quick View** of all analytes collected for the sample. This view is more for     
    reference than analysis, allowing the user to quickly assess the maps and consider    
    a preliminary plan for the data analysis.


.. admonition:: Not in this build
   :class: error

   The **Preprocess** page offers ``gradient map`` directly below ``field map``. It
   produces nothing in this build — either a warning about noise reduction, or silence
   with the previous plot left on screen. Everything today happens on pages whose plot
   lists contain no unfinished entries.

*Try this:* the **Multi View** tab above the canvas holds several plots side by side.
Add four element maps to it and compare them at once rather than in sequence.

**What you just learned.** The Control Toolbox page you are on determines which plot
types are offered. Colour scaling is a decision, not a default.


3. Correlations
---------------

*Goal: find out which elements are telling you the same thing before you choose what to
plot.*

#. Still on **Field Viewer**, set plot type to ``correlation``.
#. Set **Method** to ``Pearson``, then compare against ``Spearman``. Pearson assumes a
   linear relationship; Spearman only assumes a monotonic one, so a large gap between
   them is itself informative.
#. Tick **C²** to show correlation squared — the shared-variance view.

Look for the blocks. The REE should correlate strongly with each other, and Mn, Ca, Fe
and Mg should tell a different story — that is the growth-zoning signal separating
itself from the REE budget.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/correlation_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    The RM01 correlation matrix, Spearmann, with all 28 analytes.

.. admonition:: Not in this build
   :class: error

   The correlation matrix **ignores filters and masks**. Later today you will restrict
   the map; the correlation plot will not respond. The same applies to the ternary map.

   To see a filter's effect, use ``field map``, ``histogram`` or ``roi map``.

**What you just learned.** Correlation method choice is a real decision. The matrix is
the cheapest way to decide which analytes are worth carrying forward.


4. Choosing analytes and building ratios
----------------------------------------

*Goal: control which analytes are in play, and build ratio fields.*

Nothing in LaME plots an analyte you have not selected. That selection also drives what
the correlation matrix shows and what clustering and PCA use, so it is the first real
control you have.

#. Click **Analytes** in the pinned toolbar row. The *Select Analytes and Ratios*
   dialog opens on a square grid of your analytes.  The background colors are correlation   
   coefficients.  The matrix is symmetric across the diagonal, but there is a difference when   
   selecting above or below the diagonal as it inverts the ratio for the same two elements.
#. The **diagonal** cells are the analytes themselves. Click along it to select
   ``Mn55``, ``Y89``, ``Sm147``, ``Eu153``, ``Gd157``, ``Ca43``, ``Fe57``, ``Mg24``.
   Selected cells highlight.
#. The **off-diagonal** cells are ratios. Above the diagonal gives row ÷ column; below
   gives column ÷ row. Find the cell where ``Y89`` meets ``Mn55`` and click it once.
#. Add a second ratio that means something petrologically — ``Mg24`` over ``Fe57`` is
   the garnet one to have.
#. Your choices appear in the **Selected** list on the right, with columns *Field*,
   *Scaling* and *Normalized*. The ratios appear as ``Y89 / Mn55`` and ``Mg24 / Fe57``.
#. Click **Done**.

The background colours in that grid are the correlation matrix from section 3 — so the
dialog is already telling you which analytes co-vary while you pick them.


.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/analyte_selector_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    The Select Analytes and Ratios dialog, mid-selection. Several diagonal cells
    highlighted, and one off-diagonal cell highlighted in yellow.

Now put the ratios on the map:

#. **Field Viewer**, plot type ``field map``.
#. Set the colour **field type** to ``Ratio`` and the **field** to ``Mg24 / Fe57``.

A ratio map often shows a boundary that neither element shows on its own, because it
divides out whatever varied in both.

.. admonition:: Checkpoint 2
   :class: tip

   The Plot Tree on the right has a **Ratio** branch with two entries, and a ratio map
   is on the canvas.

#. **Save Project** again. It overwrites the save you made in section 1 — no dialog,
   no new file.

From here on, start each section by saving. You are building your own recovery points,
and they are the first thing to reach for if your screen stops matching everyone else's.

**What you just learned.** Field selection gates everything downstream. Ratios come
from the analyte grid, and they are fields in their own right — mappable, filterable,
clusterable.


5. A calculated field: Eu*
--------------------------

*Goal: build a field that is not in your data.*

Europium anomalies need the interpolated Eu you would *expect* from the neighbouring
REE. That is what the Calculator is for, and it is the general tool for any field you
can write as an expression.

First, the reference — do this before calculating anything normalised:

#. In the Control Toolbox, find the **Ref.** row and set it to a chondrite —
   ``CI chondrite [AG89]``.

Normalised fields divide by this reference, and the default is bulk silicate Earth,
which is not what you want for a REE anomaly.

#. **Analysis** toolbar page → **Calculator**.
#. In the saved-formula box, choose ``Eu*``. The formula appears:

   .. code-block:: text

      {Analyte.Eu153_N}/({Analyte.Sm147_N}*{Analyte.Gd157_N})^(1/2)

   Fields are written ``{FieldType.Field}``. The ``_N`` suffix means
   reference-normalised — which is why the reference had to be set first.
#. Click **Calculate**.
#. Plot it: **Field Viewer**, plot type ``field map``, colour field type ``Calculated``,
   field ``Eu*``.   
#. In the ``Styling Toolbox``, select the ``Colors`` tab.  Change the C limits to 0.05#.
   and 0.3.

Your canvas shows a smooth, low-contrast Eu* map — much flatter than a raw element map,
because you have divided out the overall REE level and are left with just the anomaly.

.. admonition:: Not in this build
   :class: error

   The Calculator's keypad offers ``case()`` and ``otw()`` buttons for conditional
   expressions. Conditionals do not work in this build — you will get *"could not
   evaluate conditional statement"*.

   The shipped Calculator documentation also describes a ``case(...)`` **function**.
   That syntax has never existed in any version. **Ignore the ``case()`` section of the
   Calculator docs.** Arithmetic, logs, powers and roots all work fine.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/Eu_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 150mm

    Canvas showing the Eu* field map on RM01.  Three things have been done to separate    
    docks on the right to display this map.

*Try this:* write your own. ``{Analyte.Y89}/{Analyte.Ho165}`` is a useful one — Y and Ho
have nearly the same ionic radius, so their ratio is sensitive to processes that
fractionate by something other than size.

**What you just learned.** Anything you can write as an expression over existing fields
becomes a field. Normalised fields depend on the reference being set first.


6. Biplot: Fe, Mn
-------------------------

*Goal: get three elements onto one plot, and then back onto the map.*

#. Control Toolbox → **Scatter and Heatmaps**. The axis rows now have labels **X**,
   **Y**, **Z** and **Color**.
#. Plot type ``scatter``. Set **X** = ``Fe57``, **Y** = ``Mn55``, leave **Z** empty, and
   set **Color** = ``Ca43``. That is your biplot; a third variable as colour is usually
   more informative than a third axis.   

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/biplot_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    Biplot of the entire map, Fe vs. Mn with Ca concentration used to color the pixels.    
    The result can be used to clearly identify the garnet as the generally higher Ca     
    points.

*Try this:* double-click any leaf in the Plot Tree. It restores that plot — type, fields
and styling together. The tree is a record of your session, not just a list.

**What you just learned.** Scatter and heatmap answer the same question at different
densities. Adding Z turns either into a ternary. The ternary map is how a three-element
relationship gets back onto the spatial map.


7. REE patterns: the TEC plot
-----------------------------

*Goal: look at all the rare earths at once, in the way petrologists expect to see them.*

A trace-element compatibility diagram — a spider plot — puts the REE in order of ionic
radius and normalises each to a reference. The shape is the information.

#. Control Toolbox → **n-Dimensional**. Plot type ``TEC``.
#. Set the analyte set to ``REE``. LaME ships preset element lists; ``REE`` is the one
   you want here.
#. Check the **Ref.** row still reads ``CI chondrite [AG89]``. The TEC plot is
   normalised, so the reference is doing real work.
#. Set **Color** to a field — start with ``Mn55``.

Because every one of your 95,676 pixels is a sample, this is not the handful of lines
you would get from spot analyses. What you are looking at is the envelope of REE
patterns across the whole map, and the Eu anomaly you calculated in section 5 should
now be visible as a notch in the middle of it.

#. Plot type ``radar``, same analyte set. The same data on polar axes. Which of the two
   reads better depends on how many groups you are comparing — radar is usually clearer
   for three or four, TEC for more.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/TEC_REE_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    The TEC plot of RM01 with the REE preset, chondrite-normalised. The Eu notch is visible.

We come back to this plot in section 10, once there are clusters to colour it by — which
is when it becomes a comparison rather than a description.

**What you just learned.** The n-Dimensional page takes an element *list*, not axes.
Preset lists save you rebuilding common suites. Normalisation is live, so the reference
setting matters here as much as in the Calculator.


8. Principal components
-----------------------

*Goal: find out how many independent things the data is actually doing.*

You have 28 analytes, and section 3 showed that many of them are telling you the same
story. PCA rewrites the data in terms of what varies, in order.

#. Control Toolbox → **Dimensional Reduction**. Opening the page runs PCA immediately
   with the current field selection.
#. Set **Method** to ``PCA: Principal component analysis``.
#. Plot type ``variance``. This is a scree plot: how much of the total variance each
   component carries. Usually three or four components carry nearly everything.

   **Note the number** where the curve flattens. You need it twice more today.
#. Plot type ``basis vectors``. This shows what each component is *made of* — which
   analytes load onto it. A component dominated by the REE and one dominated by Mn–Ca–Fe
   is the same split section 3 showed you, now quantified.
#. Plot type ``dimension scatter``. PC1 against PC2, every pixel. Set **Color** to
   ``Mn55`` and look for structure — separate clouds here mean separable populations.
#. Plot type ``dimension score map``. Each component mapped back onto the sample. PC1
   usually looks like the dominant zoning; the higher components are where the
   interesting and less obvious patterns live.

.. list-table::
   :widths: 50 50
   :header-rows: 0

   * - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/scree_RM01.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Principal component analysis scree plot.
     - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/basis_vectors_RM01.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Basis vectors resulting from principal component analysis.  Larger positive          
          and negative values have greater influence on the principal component score.          
   * - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/PC1_RM01.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Principal component 1.


     - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/PC2_RM01.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Principal component 2.

.. admonition:: Why this matters
   :class: note

   The score maps are worth dwelling on. A principal component is defined without any
   reference to position — PCA does not know these numbers came from a map. When a score
   map comes out looking like coherent growth zoning anyway, that is the data telling
   you the chemical variation and the spatial structure are the same phenomenon.

**What you just learned.** The variance plot tells you how many components to keep; the
basis vectors tell you what they mean; the score maps tell you where they are. You need
all three to use PCA honestly.


9. Clustering
-------------

*Goal: let the data propose its own zones, then test whether they are real.*

#. Control Toolbox → **Clustering**. Opening the page runs clustering immediately with
   the current settings and plots the result, so you will see groups before you have
   chosen anything.

k-means
~~~~~~~

#. Set **Method** to ``k-means`` and **No. clusters** to ``5``.
#. Plot type ``cluster map``.
#. Click **Randomize** beside the **Seed** box and watch the map. k-means starts from
   random centres; if your zones survive several seeds they are robust, and if they
   reshuffle they were not there.
#. Plot type ``cluster performance``. This sweeps the cluster count and scores each one,
   which is the closest thing to an objective answer to "how many clusters?". Set
   **No. clusters** to whatever it suggests, then go back to ``cluster map``.

fuzzy c-means
~~~~~~~~~~~~~

k-means assigns every pixel to exactly one cluster. Fuzzy c-means gives each pixel a
*membership* in every cluster, which is a better model of a boundary that is genuinely
gradational — like a diffusion profile, or a growth zone grading into the next.

#. Set **Method** to ``fuzzy c-means``. Same cluster count.
#. The **Exponent** box controls how fuzzy the result is. ``1.0`` would reproduce
   k-means; higher values blur the memberships. ``2.0`` is the conventional starting
   point.
#. Plot type ``cluster score map``. This is the one to look at — it maps the membership
   in a single cluster as a continuous field, so you can see the boundary *width*
   rather than just its position.   
#. Increase the number of clusters to 6 and 7 and compare the results with the initial 5
   clusters.

Compare it against the k-means map. Where the two agree, you have a real boundary.
Where fuzzy c-means smears something that k-means drew as a sharp line, the line was an
artefact of being forced to choose.


Clustering on principal components
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Much of what the clustering sees is the same signal repeated across correlated
analytes. Reducing first often gives cleaner groups.

#. Go back to **Dimensional Reduction** once, so the PCA scores exist.
#. Return to **Clustering**. Tick the **PCA** checkbox and set **No. basis** to the
   number you took from the variance plot in section 8.
#. Re-cluster, with the same method and cluster count as before.

.. important::

   Run PCA *before* ticking that box. If no PCA scores exist, LaME falls back to the raw
   analytes without telling you, and the comparison you were trying to make silently
   does not happen.

Compare against the raw-analyte clustering. The large boundaries usually survive; what
moves is the internal subdivision, because PCA has reweighted what counts as similar.

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/fcm_clusters_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    Clustered result using fuzzy c-means clustering for 6 clusters with an exponent of    
    2.1 using 7 PCA basis vectors as preconditioning.  The result highlights three    
    regions within the garnet.  This may be too many but it separates a core (Clusters,    
    5 and 6) from a rim (Cluster 1) of the garnet and identifies three additional phases.    

Now select plot type ``score map`` and examine how well each pixel corresponds to each
cluster.  This score can be used for filtering the data in addition to clustering to
restrict the data to the *best* results for additional analysis.  This filtering is 
important for producing high-quality geochronology results.

.. list-table::
   :widths: 33 33 33
   :header-rows: 0

   * - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/cluster5_RM02.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%          

          Fuzzy clustering scores for cluster 5, dominated by pixels in the central core.
     - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/cluster6_RM02.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Cluster 6 scores located predominantely in the core.

     - .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/cluster1_RM02.png
          :align: center
          :alt: Alternate text goes here
          :width: 95%

          Cluster 1 scores located largely on the rim.

.. admonition:: Why this matters
   :class: note

   PCA before clustering is often presented as a tidying step. It is not neutral — it
   decides which variation the clustering is allowed to see. Running it both ways on the
   same sample is the honest way to find out whether a result depends on that choice,
   and it takes two minutes.

.. admonition:: Not in this build
   :class: error

   The **Distance** combobox on this page has no effect — the distance-metric code is
   not active in this build. Changing it recomputes and gives an identical result.

   Also: ``HDBSCAN`` works as a method, but combining it with ``cluster performance``
   silently does nothing. HDBSCAN discovers its own cluster count, so there is no *k* to
   sweep. Use ``cluster performance`` with k-means or fuzzy c-means only.

Changing what clustering sees
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clustering uses exactly the fields you selected in section 4.

#. Click **Analytes** and add two or three light REE — ``La139``, ``Ce140``, ``Nd146``.
#. Click **Done**. Because you are on the Clustering page, it recomputes and replots
   automatically.

Adding light REE will usually sharpen a growth-zoning boundary, because those elements
partition strongly during garnet growth.

.. note::

   That automatic recompute only happens while you are on the **Clustering** or
   **Dimensional Reduction** page. From anywhere else, change the selection and then
   press **Update Plot**.

**What you just learned.** Clustering reads your field selection, so curating it is the
main lever you have. k-means draws hard boundaries; fuzzy c-means tells you how hard
they really are. PCA first changes the answer, which is why you run it both ways.


10. Filtering by cluster, and replotting
----------------------------------------

*Goal: use the clusters as a selection tool, then look at everything again through it.*

A cluster map is a picture. The Clusters tab turns it into a filter.

Naming and masking
~~~~~~~~~~~~~~~~~~

#. Masking Toolbox at the bottom → **Clusters** tab. The table lists your clusters with
   *Name*, *Link*, *Color*, *% Total* and *% Filtered*.
#. Rename them in place — ``core``, ``mantle``, ``rim``, ``matrix``. These names follow
   through into every legend, the Notes report and the stoichiometry scope list, so it
   is worth doing now rather than later.
#. Recolour one by clicking its *Color* cell.
#. If two clusters are clearly the same zone, tick both and click **Link Clusters** —
   they then behave as one class.
#. Tick the clusters that are **garnet** and press **Create Cluster Mask**.

Everything outside those clusters is now masked, and every plot that follows uses garnet
pixels only. No bounds to choose, because the clustering already found the boundary.

#. Tick one cluster and click **Create Region** instead. It becomes an ROI — which is
   what the stoichiometry calculation in section 11 needs to scope itself to.

Replotting through the clusters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now go back and redo two plots with the clusters as the colour field. This is where the
day's work starts compounding.

#. **Scatter and Heatmaps**, plot type ``scatter``, **X** = ``Fe57``, **Y** = ``Mn55``,
   **Z** = ``Mg24`` — your ternary from section 6 — and set **Color** field type to
   ``Cluster``.
#. From the Cluster Table, select cluster 1.  This should be the garnet.
#. Now let's look at a ternary system, plot type ``scatter``, **X** = ``Dy163``,
   **Y** = ``Er165``, **Z** = ``Lu175`` and set **Color** to ``Mn55``

   The ternary is now a map of which zone sits where in composition space. If your
   clusters are real, they occupy distinct regions of the triangle. If they overlap
   completely, the clustering found something the ternary does not resolve.   
#. Change the plot type to ``heatmap``, same X, Y, and Z. With 95,000 points, overplotting hides the
   structure and binning reveals it. In the **Biplot and Ternary** group, try the
   *Heatmaps* statistic — ``counts``, then ``median``.
#. Now change the plot type to ``ternary map``, same three fields.
#. In the **Ternary Map** group, either pick a **Colormap** or set the four colour
   swatches — one per vertex plus one for the centre.
#. Click **Ternary map**.

Each pixel is now coloured by where it sits in the ternary. This is the single most
useful plot in LaME for seeing compositional zoning, because it puts three elements on
one map without you choosing which matters most.

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/ternary_clustered_RM01.png
   :align: center
   :alt: Alternate text goes here   
   :width: 150mm

   Trace element compatibility diagram with REE data for each cluster.  The garnet      
   core is clusters 5 and 6 and the rim is cluster 1.

#. **n-Dimensional**, plot type ``TEC``, analyte set ``REE``, **Color** field type
   ``Cluster``.

   One REE pattern per cluster, chondrite-normalised, on one plot. This is the figure a
   paper would carry — and it took you three clicks because the clusters already exist.
   Look at whether the Eu anomaly differs between core and rim.   

   .. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/TEC_REE_clustered_RM01.png
      :align: center
      :alt: Alternate text goes here
      :width: 150mm

      Trace element compatibility diagram with REE data for each cluster.  The garnet      
      core is clusters 5 and 6 and the rim is cluster 1.


#. Try ``radar`` as well.


.. admonition:: Checkpoint 4
   :class: tip

   A cluster map with named, recoloured clusters; a cluster mask restricting the map to
   the garnet; and both the ternary and the TEC plot coloured by cluster with a legend
   showing your names.

*Try this:* turn the cluster mask off with the **Cluster Mask** toolbar toggle and
redraw the ternary. Watch the matrix pixels flood back in. It is a concrete
demonstration of why masking was not optional.

**What you just learned.** Clusters are a masking and grouping tool, not just a
picture. Naming them early pays off everywhere downstream. Any plot gains a grouped
version for free once clusters exist.


11. Mineral formulae and the dominant phase
-------------------------------------------

*Goal: get apfu, site occupancies and end-member proportions, and map them.*

LaME can convert composition into a mineral formula — site by site, with iron split
between Fe²⁺ and Fe³⁺ by charge balance. The chemistry behind this is the most heavily
validated part of LaME, cross-checked against published mineral-recalculation workbooks
for garnet, feldspar, olivine and pyroxene.

.. important::

   **Scope it to one region before you touch anything else.** The calculation runs pixel
   by pixel.   Across a whole 95,000-pixel map that is minutes of frozen window, several times over.
   Scoped to one cluster it is seconds.

#. **Analysis** toolbar page → **Stoichiometry**. The *Stoichiometric Calculator* opens.
#. **First**, in the **Compute scope** group: set *Filter* to the ROI you made from a
   cluster in section 10, and tick **only that region** in the list below. New regions
   start unticked deliberately — leave the others alone.
#. Now the **Settings** group: *Mineral* = ``Garnet``, *Input basis* = ``ppm``,
   *Redox method* = ``droop_1987``, *BDL treatment* = ``zero``.
#. Leave **Compare all redox methods** switched **off**. It triples the work.
#. Click **Run**.#.



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/stoichiometry_calculator.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    Stoichiometry calculations for the k-means, cluster 1 (all of the garnet).  The    
    results show a dominant pyrope composition for this garnet with lesser andradite and    
    spessartine components. Approximately Alm0-Pyr73-Sps10-Adr15-Grs1-Uv1.


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



.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/workshop_figures/stoichiometry_dominant_RM01.png
    :align: center
    :alt: Alternate text goes here
    :width: 100%

    Dominant garnet phase calculated using the stoichiometry calculator.


What happens without silicon
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now look at ``Grt_Z``. It should be close to 3.0, filled by silicon. **On RM01 it is
not** — RM01 has no Si, so LaME has filled the tetrahedral site with aluminium instead,
following the fallback order in the garnet configuration. The end-member percentages
that come out are correspondingly wrong.

This is worth seeing rather than being told. The stoichiometry calculation is only as
good as the elements you measured, and a missing major element does not produce an
error — it produces a plausible-looking answer that is incorrect. We fix this in section
13 by moving to a sample that has Si.

.. admonition:: Not in this build
   :class: error

   If the **Mineral** dropdown is empty and outlined in red, the application cannot find
   its mineral configuration files. Tell the presenter — there is a workaround.

.. admonition:: Checkpoint 5
   :class: tip

   The Plot Tree has a **Stoichiometry** branch, and a ``Grt_dominant`` map with a
   swatch legend is on the canvas. ``Grt_Z`` is visibly not 3.0.

*Try this:* the **Region summary** table at the bottom of the dock gives per-region
statistics. Switch *Region source* between ``ROI`` and a cluster column to compare
formulae between the zones you named in section 10.

**What you just learned.** Scope first, always. Site totals are your sanity check on
whether the calculation had the elements it needed. ``Grt_dominant`` maps mineral
classification back onto the sample.


12. The workflow designer
-------------------------

*Goal: see where this is going.*

.. admonition:: Watch, do not click
   :class: note

   The Workflow designer is a drag-and-drop block canvas — the analysis you just did by
   hand, as a diagram you can save, share and re-run on the next sample.

   **Constructing** a workflow works, and the presenter will build one in front of you
   so you can see the blocks and how they connect. **Running** one is not reliable
   enough in this build to put twenty people through, so we will not.

   Worth seeing anyway: the block vocabulary is the same vocabulary as the Control
   Toolbox pages, so a workflow diagram reads as a record of the method.

.. admonition:: Not in this build
   :class: error

   The **Capture** toggle, which would record your clicks into a workflow, currently
   records only sample changes. Hand-built workflows in the designer do run; recorded
   ones do not yet exist. Use the Notes recorder in section 14 for a record of what you
   did.

.. Figure placeholder FIG-12.1
   WHAT: The Workflow designer with a small hand-built workflow on the canvas — load
   sample, select analytes, cluster, plot — with the block palette visible on the left.
   WHY: Attendees will not build one themselves, so the figure is the whole of their
   record of this feature.
   SIZE: two-thirds page width.


Part II — Two more garnets
==========================

13. The other two garnets
-------------------------

*Goal: repeat the core of Part I quickly on two samples that differ in ways that matter,
and get the stoichiometry right this time.*

We are not redoing all twelve sections. Four steps, on each of ``TR1-07`` and
``WOS-02``, with the big one being the one RM01 could not do.

#. Switch sample using the selector in the pinned toolbar: choose ``TR1-07``.

   ``TR1-07`` and ``WOS-02`` are already converted, so they load from
   ``.lame.csv`` directly — no import step. They also have **different isotope names**:
   ``Fe56``, ``Ti47``, ``Cr52`` rather than RM01's ``Fe57``, ``Ti49``, ``Cr53``.
   Your field selection does not carry across, so re-select on each sample.

#. **Cluster it.** Clustering page, k-means, 3 or 4 clusters. Pick a field selection
   first — the major cations plus two or three REE is enough.
#. **Filter to the garnet.** Clusters tab → name the clusters → tick the garnet ones →
   **Create Cluster Mask**. Then tick one and **Create Region** for the next step.
#. **Run the stoichiometry**, scoped to that region, exactly as in section 11.

   Now compare ``Grt_Z`` with what RM01 gave you. **With ``Si29`` present it should sit
   near 3.0**, and the end-member proportions are meaningful for the first time today.

#. **Map the dominant phase** — ``field map``, field type ``Stoichiometry``, field
   ``Grt_dominant``.
#. **Make a ternary map**, two ways:

   * on the chemistry — ``Fe56``, ``Mn55``, ``Mg24``, as in section 6;
   * on the **stoichiometry** — put three end-member proportions on the axes instead,
     ``Grt_almandine``, ``Grt_spessartine``, ``Grt_pyrope``.

   The second is the more interpretable plot: the axes are now mineralogical quantities
   rather than raw element levels, so a position on the triangle is a composition you
   could quote in a paper.

#. Repeat on ``WOS-02`` if time allows. It is the largest of the three, so keep the
   region small.

.. Figure placeholder FIG-13.1
   WHAT: Three Grt_dominant maps side by side — RM01, TR1-07, WOS-02 — each with its
   swatch legend visible. Underneath each, the Grt_Z value from the region summary
   table, so the ~3.0 (TR1-07, WOS-02) versus wrong (RM01) contrast is explicit.
   WHY: This is the payoff figure of the whole garnet thread and the Si lesson in one
   image.
   SIZE: full page width.

.. Figure placeholder FIG-13.2
   WHAT: Two ternary maps of TR1-07 side by side — left on chemistry (Fe56-Mn55-Mg24),
   right on stoichiometry (almandine-spessartine-pyrope). Same colour scheme.
   WHY: Shows that stoichiometric fields are ordinary fields, usable anywhere a chemical
   field is, and makes the interpretability difference visible.
   SIZE: full page width.

.. admonition:: Checkpoint 6
   :class: tip

   At least two garnets have ``Grt_*`` fields. ``Grt_Z`` is near 3.0 for TR1-07 and
   clearly not for RM01. You have a ternary map built on end-member proportions.

**What you just learned.** The whole sequence transfers to a new sample in a few
minutes once you know it. Field names do not transfer. Stoichiometric outputs are
first-class fields — mappable, plottable, filterable.


14. Notes, figures and tables
-----------------------------

*Goal: leave with a record of what you did, not just the plots.*

#. **Log** toolbar page → **Notes**. An editor window opens — titled *reST Editor* —
   holding a notes file tied to this sample inside your project folder.
#. Click **Record** in the same toolbar page. The status-bar *Notes* light turns red.
#. Now make a plot — anything. It is captured into the notes automatically as a figure,
   written into the ``figures/`` folder beside the notes file and referenced from it.
   This is the project folder you created by saving back in section 1; exported tables
   land in ``data/`` in the same place.
#. Make two or three more. Every plot you produce while recording is captured, so turn
   it off when you are exploring and on when you are producing.

Automated data blocks
~~~~~~~~~~~~~~~~~~~~~

#. In the Notes toolbar, open the **Insert** page and use **Formatted Info**. It offers:

   * Sample info
   * List analytes used
   * Current plot details
   * Filter table
   * PCA results
   * Cluster results
   * Diffusion results
   * Stoichiometry results

#. Insert **Sample info**, **List analytes used**, **Cluster results** and
   **Stoichiometry results**. Each writes a formatted block pulled from your live
   session — the actual analytes, the actual clusters, the actual formulae.

That is the methods section of a paper, assembled from what you really did rather than
from what you remember doing a month later. The cluster names you set in section 10 are
why it reads as prose rather than as ``Cluster 3``.

Writing around it
~~~~~~~~~~~~~~~~~

The notes are **reStructuredText** — plain text with light markup. You need about eight
pieces of syntax to write a usable set of notes, and they are in
`Appendix B: reStructuredText in one page`_. The editor's toolbar will insert most of
them for you, but knowing the syntax means you can read and fix what it inserts.

#. Add a heading above your figures and a sentence of interpretation under each one.
#. Export from the Notes toolbar to see it typeset.

.. Figure placeholder FIG-14.1
   WHAT: The reST Editor window with a recorded figure, a hand-written heading and
   caption, and at least two inserted Formatted Info blocks visible (analytes used, and
   the cluster results as a formatted table). The Formatted Info menu can be shown open
   if it fits.
   WHY: Shows all three halves of the feature at once — automatic figure capture, the
   live-data info blocks, and the fact that you can type around them.
   SIZE: full page width.

.. admonition:: Checkpoint 7
   :class: tip

   Your notes file contains at least two captured figures, two Formatted Info blocks
   with real numbers in them, and a heading you typed yourself.

*Try this:* ``reST Editor.app`` on the USB stick is the same editor as a stand-alone
application. Open your notes file in it after the workshop — it is just a text file, and
it will outlive any particular version of LaME.

**What you just learned.** Notes are per-sample and live inside the project. Record
captures figures as you go. Formatted Info blocks pull real state, so the record stays
honest. The output is plain text you own.


Part III — Pyrite
=================

15. Pyrite — your turn
----------------------

*Goal: apply what you have done to a different mineral system, with less guidance, and
see what preconditioning does to a clustering.*

This section has fewer numbered steps on purpose. You have the tools now; the questions
are new.

**The questions.** ``71A-Py 12`` is a pyrite-bearing sample. Two things to find out.
Does clustering change when you precondition the data with PCA first? And once you have
the pyrite on its own, is it chemically uniform, or are there distinct populations
within it?

Remember this map is **uncalibrated**: counts per second, not ppm. Relative patterns are
fine; absolute values and mineral formulae are not.

#. Add ``data/LA-ICP-MS/71A-Py 12.lame.csv`` using **Open** on the Home toolbar page, or
   simply drag the file onto the window.

#. **Find the pyrite.** Field maps of ``Fe57`` and ``S34``. Pyrite is FeS₂, so it should
   stand out sharply against the silicate matrix in both. Something like 40% of this map
   is sulfide, so it is not a small target.

#. **Cluster the whole map, on the analytes.** Clustering page, ``k-means``, 4 clusters.
   Choose a sensible set of analytes first (``Fe57``, ``S34``, ``Cu65``, ``Co59``,
   ``Ni60``, ``As75`` is a good start). Look at the ``cluster map``: two of the four
   groups should land on the sulfide and two on everything else.

   Note which clusters are the pyrite, and roughly what fraction of the map they cover.

#. **Now precondition with PCA and cluster again.** Visit the Dimensional Reduction page
   first so the scores exist, then return to Clustering, tick **PCA** and set
   **No. basis** to 3. Re-cluster.

   Compare the two cluster maps. The sulfide/matrix split survives — that boundary is
   not in doubt — but the way the pyrite is divided *within* itself changes, and so do
   the cluster proportions. Neither answer is the "right" one: PCA has reweighted what
   counts as similar, by dropping the directions in which the data varies least.

#. **Filter to the pyrite with the Cluster tool.** Masking Toolbox → **Clusters** tab.
   Tick the clusters that are the pyrite, then press **Create Cluster Mask**.

   Everything outside those clusters is now masked, so every plot that follows uses
   pyrite pixels only.

#. **Fe against Cu.** Scatter and Heatmaps page, plot type ``scatter``: **X** =
   ``Fe57``, **Y** = ``Cu65``, **Color** = your cluster field.

   Fe is the pyrite's own framework and barely varies; Cu does not substitute into
   pyrite in any quantity, so where it appears it is telling you about something else —
   an inclusion, a later overprint, or a different generation of growth. Watch for the
   points that climb away from the main Fe population.

#. **A histogram per cluster.** Field Viewer page, plot type ``histogram``, **X** =
   ``Co59``, with **Show KDE** on and ``log-scaling`` set. Then step through your
   clusters and compare.

   Expect a dramatic separation between the sulfide clusters and the matrix — Co runs a
   few hundred thousand counts inside the pyrite against a few thousand outside. What
   you will probably *not* see is much difference between the two pyrite clusters
   themselves: Co (and Ni, which behaves the same way) is substituting for Fe fairly
   uniformly through the sulfide.

   That is a real result, not a failed exercise. It says the populations your clustering
   found are not Co–Ni populations. Go back to the biplot: ``Cu65`` and ``As75`` are
   where those two groups actually differ.

.. Figure placeholder FIG-15.1
   WHAT: Two cluster maps of 71A-Py 12 side by side at the same scale — left, k-means on
   the raw analytes; right, k-means after PCA with 3 components. Same number of
   clusters, same colours where they correspond. Annotate the sulfide/matrix boundary as
   unchanged and circle one area where the division *within* the pyrite differs.
   WHY: The whole point of the first half of this section. Attendees need to see that
   preconditioning moved an internal boundary while leaving the obvious one alone.
   SIZE: full page width.

.. Figure placeholder FIG-15.2
   WHAT: The Fe57 vs Cu65 biplot on the masked pyrite, points coloured by cluster,
   legend visible. Frame it so the Cu-enriched population is clearly separated from the
   main Fe cloud.
   WHY: The scientific punchline of the pyrite thread, and the figure attendees are most
   likely to want to reproduce on their own data.
   SIZE: two-thirds page width.

.. Figure placeholder FIG-15.3
   WHAT: Co59 histograms for each cluster, log-scaled, ideally overlaid or in a small
   column so they can be compared directly. The two sulfide clusters should sit on top
   of one another, far to the right of the matrix clusters.
   WHY: Supports the point that a strong element contrast between pyrite and matrix says
   nothing about structure *within* the pyrite.
   SIZE: half page width.

.. admonition:: Checkpoint 8
   :class: tip

   Two cluster maps of the same sample (with and without PCA), a cluster mask
   restricting the map to the sulfide, an Fe–Cu biplot coloured by cluster, and a Co
   histogram you have compared across clusters.

**What you just learned.** Clustering is a choice, not a measurement: preconditioning
changes the answer, and the way to know how much is to run it both ways. And a huge
contrast in one element between two materials tells you nothing about structure inside
either of them.


Part IV — An XRF core scan
==========================

16. Importing the core 7 scan
-----------------------------

*Goal: import from a completely different instrument, and understand what you have.*

``data/XRF/core 7/`` holds a scanned drill core, cut into five segments. Each of
``row1/`` … ``row5/`` contains **26 PNG images**, one per element — ``Fe.png``,
``Ca.png``, ``Rh.png`` and so on. The scanner's software exports element maps as
pictures, and LaME reads the pixel brightness as a relative intensity.

#. **Home** toolbar page → **Import Files**.
#. Set **Data type** to ``XRF`` and **Method** to ``image``.
#. Click **Open directory** and choose ``data/XRF/core 7/``. Five rows appear in the
   metadata table — ``row1`` through ``row5``.
#. Set **Spot size (µm)** to the scanner's pixel pitch if you know it. If you do not,
   leave it at ``1``: dX and dY both become 1 and the map axes read in **pixels**
   instead of microns. Everything except absolute distance works the same way.
#. Import ``row1`` to start with. It is 1200 × 181 px — about 217,000 pixels, more than
   twice RM01.

.. admonition:: Checkpoint 9
   :class: tip

   ``row1`` is in the sample selector and a field map draws as a long thin strip. 26
   fields are available, named by element symbol alone — ``Fe``, ``Ca``, ``Si`` — with
   no isotope numbers, because XRF measures elements, not isotopes.

.. Figure placeholder FIG-16.1
   WHAT: The Map Importer dialog with Data type on XRF, Method on image, and the five
   row1-row5 sample rows populated. Beside it or below it, the resulting Fe field map of
   row1 as a long thin strip.
   WHY: The second import route, and the figure that shows how different the same dialog
   looks for a different data type.
   SIZE: full page width.

.. admonition:: Why this matters
   :class: note

   Two things about this data that the numbers will not tell you.

   **It is intensity, not concentration.** There is no calibration behind these values,
   so ``Fe = 55`` does not mean 55 of anything.

   **Each element image was scaled independently** by the scanner software before it was
   written to a PNG, and then clipped to the 0–255 range of an 8-bit image. So
   comparing Fe to Ca pixel-for-pixel is meaningless, and the brightest pixels in any
   channel may be saturated. Comparing *Fe here* to *Fe there* is fine, and that is
   what makes maps, clusters and zoning valid on this data.

.. admonition:: Not in this build
   :class: error

   Only ``LA-ICP-MS`` and ``XRF`` → ``image`` import in this build. The other data types
   populate the metadata table and then stop with a *"Not implemented"* message, so the
   table filling in is not a sign that it will work.

**What you just learned.** The import dialog adapts to the data type. Images are a
legitimate data source. What you cannot do with the result is a property of how it was
produced, not of LaME.


17. Exploring the core
----------------------

*Goal: find the chemical zones in a core without any concentrations at all.*

#. **Look at it.** Field maps of ``Fe``, ``Ca``, ``S``, ``K``, ``Si``. Open
   ``core7_Video Mosaic.png`` alongside — the optical image of the core — and compare.
   You should be able to match chemical boundaries to things you can see.

#. **Find the channels worth using.** Plot type ``histogram`` and step through the
   elements. Several are almost entirely zero — ``Mg``, ``Na``, ``Cu`` and ``Ni`` are
   above 90% zeros in this core — and they will only add noise to a clustering.

   .. admonition:: Why this matters
      :class: note

      Look at the mean intensities and you will find ``Re`` and ``Rh`` are the two
      *brightest* channels in the scan — brighter than Fe, in a rock. That is not
      rhenium.

      **Rh, Pd and Pt are common X-ray tube anode materials**, and what those channels
      mostly record is the tube's own characteristic radiation scattered off the sample.
      Check what your instrument's tube is made of before you interpret any of them as
      sample chemistry. Leave them out of the clustering.

#. **Correlations.** Plot type ``correlation``, Spearman. With independently-scaled
   channels, the rank-based method is the more defensible of the two here.

#. **Biplots.** Scatter and Heatmaps, ``heatmap`` rather than ``scatter`` — at 217,000
   points the scatter is a solid block. ``Ca`` against ``Fe`` is a good first pair.

#. **Radar.** n-Dimensional page, plot type ``radar``. Build an element list from the
   channels that carry real signal. This is the plot that will compare your zones once
   you have them.

#. **Cluster it to find the zones.** Clustering page, k-means, start with 4 clusters and
   use ``cluster performance`` to check. Use only the channels you kept.

   The clusters are lithological and alteration zones down the core. This is the result
   that matters: you have mapped chemical domains in a core with no calibration, no
   standards, and no concentrations.

#. **Name them and compare them.** Clusters tab → name the clusters → then back to the
   radar plot with **Color** field type ``Cluster``. One pattern per zone.

Refining by hand
~~~~~~~~~~~~~~~~

Clustering finds domains by composition. Sometimes you want a region because of where
it is — a single band, or everything outside a crack.

#. **Processing** toolbar page → **Filters**. In the **ROI** table click **Add ROI**,
   name it, and **leave the row selected**. Then in **Filter Settings** set a field and
   a range and click **Add filter**.

   Filters live *inside* regions of interest: an ROI is a named definition, a filter is
   one rule inside it. Select the ROI row first. If you add a filter with no ROI
   selected, LaME quietly creates one — convenient once, confusing the second time.

#. Plot type ``roi map`` on the Field Viewer page. Excluded pixels draw grey. This is
   the plot to use whenever you want to check what a filter actually did.

#. **Polygons** tab. Flip the toggle switch at the left of its toolbar to enter polygon
   mode, click **Create a new polygon**, then click round a feature on the core.

   The *In/out* column controls whether the polygon keeps or removes what is inside it.
   Use **Move a control point**, **Add a vertex** and **Remove a vertex** to adjust.

#. **Crop** on the toolbar restricts the map to a rectangle. Click it, drag a box over
   the map, adjust the handles, then **double-click inside the box** to apply — or press
   **Enter**, which works once you have clicked on the canvas. **Full Map**, beside it
   on the toolbar, puts the whole sample back.

   Crop is only enabled while a map is on screen; it greys out on a histogram or a
   biplot, because there is nothing spatial to cut.

   Cropping a long core strip down to the interval you care about makes everything
   downstream faster, and the clustering no longer has to account for pixels you were
   never going to use.

.. admonition:: Not in this build
   :class: error

   Polygons are deliberately **excluded from clustering**. Drawing a polygon around a
   band and re-clustering will not restrict the clustering to it. To scope an analysis,
   use an ROI, a cluster mask, or a crop.

   **Save filter** is also unavailable in the packaged build — it tries to write inside
   the application bundle. Your filters are saved in your *project*, which is what
   matters.

.. Figure placeholder FIG-17.1
   WHAT: The core 7 row1 cluster map above the matching strip of core7_Video Mosaic.png,
   aligned so the chemical zones and the visible layers line up. Cluster legend with
   your names visible.
   WHY: The single most persuasive figure in Part IV — chemistry recovering structure
   that is independently visible in a photograph.
   SIZE: full page width.

.. Figure placeholder FIG-17.2
   WHAT: The radar plot of core 7, coloured by cluster, one pattern per zone, using only
   the channels that carry signal.
   WHY: Shows the n-dimensional plots working on a completely different data type, and
   is the quantitative companion to FIG-17.1.
   SIZE: two-thirds page width.

.. admonition:: Checkpoint 10
   :class: tip

   A cluster map of ``row1`` with named zones, a radar plot comparing them, and at least
   one ROI or polygon you drew yourself.

*Try this:* import ``row2`` as well and cluster it with the same settings. Do the zone
boundaries continue across the gap between segments? That is a real question about the
core, and you can answer it in about five minutes.

**What you just learned.** The whole toolkit works on uncalibrated intensity data.
Knowing which channels are instrument artefacts is part of the analysis. ROIs,
polygons, cluster masks and crop are four different ways to restrict a map, and they
are not interchangeable.


Wrapping up
===========

#. **Save Project**.
#. Close the project — **File → Close Project**.
#. Reopen it. Your fields, ratios, calculated fields, ROIs, filters, polygons, clusters,
   stoichiometry and notes all come back.

That round trip is the thing to trust: the project file is the unit of work, and it
survives being moved between machines because it stores paths relative to itself.

Finding the documentation
-------------------------

**In the application.** **Help** menu → *User Guide* or *Tutorials*. The whole user
guide ships inside the application, so it works offline.

**Context-sensitive help.** Toggle **Help** in the toolbar, then click any part of the
interface. It jumps straight to the documentation for whatever you clicked. This is the
fastest route to an answer and almost nobody discovers it on their own.

.. admonition:: Checkpoint 11
   :class: tip

   You have used context-sensitive help at least once to look up something you used
   today.


Tell us what you thought
------------------------

Please fill in the survey before you leave. It takes a couple of minutes, and it is what
shapes the next version of both the software and this workshop — including which of the
sections below stop being limitations.

.. figure:: /Users/dhasterok/Documents/GitHub/LaserMapExplorer/docs/source/_static/workshop_survey_qr.png
    :align: center
    :alt: QR code linking to the LaME user survey
    :width: 40mm

    LaME user survey

If you would rather type it in:

    https://docs.google.com/forms/d/e/1FAIpQLScv996yHMq34L7ySHEt5TgXEISj8zuRctdF1lmQcs4LMdSXGw/viewform

Known limitations in this build
===============================

Everything from the boxes above, in one place.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Feature
     - What you will see
     - What to do instead
   * - Raw → calibrated data
     - Not available to drive yourself
     - Calibrate in iolite and import the matrix files, as in section 1
   * - ``gradient map`` plot type
     - A warning about noise reduction, or nothing at all
     - Not available; use ``field map``
   * - Calculator conditionals
     - *"could not evaluate conditional statement"*
     - Arithmetic only. **Ignore the ``case()`` section of the Calculator docs** — that
       syntax never existed
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
     - Scope with an ROI, a cluster mask or a crop instead
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
   * - Workflow **Capture**, and running a workflow
     - Capture records only sample changes; running is unreliable
     - Build one to see the design; use Notes for a record of what you did
   * - Thermometry / Barometry tabs
     - Empty method dropdowns
     - Not implemented


If you fall behind
==================

Do not spend the workshop debugging. In order of preference:

#. **Reopen your own last save.** **File → Open Project**. This is why section 1 ends by
   saving and every section after it begins by saving — and why autosave has somewhere
   to write. At worst you lose ten minutes.
#. **Skip the import.** Every sample we import has a converted ``.lame.csv`` beside it.
   If section 1 or section 16 does not come out right, open the converted file and
   carry straight on — you lose nothing that any later section needs.

   .. list-table::
      :header-rows: 1
      :widths: 30 70

      * - Instead of importing
        - Open
      * - ``data/LA-ICP-MS/RM01/``
        - ``data/LA-ICP-MS/RM01.lame.csv``
      * - ``data/XRF/core 7/row1/``
        - ``data/XRF/core 7/core7_row1.lame.csv``

#. **Ask.** Several sections depend on a cluster or an ROI existing rather than on it
   being any particular one, so there is usually a two-click way back in.


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
#. Click **Create new profile and set control points**, then click along the map — for a
   garnet, rim through core to the far rim.
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
   WHY: Shows the control points on the map and the output together, which is what makes
   the workflow make sense.
   SIZE: full page width.


Appendix B: reStructuredText in one page
========================================

LaME's notes are reStructuredText — plain text that typesets. This is everything you
need for a set of workshop notes. **Blank lines matter**: they separate blocks, and most
mistakes are a missing one.

**Headings.** Underline with punctuation, at least as long as the text. The character
you use first becomes level 1, the next new character level 2, and so on — so be
consistent.

.. code-block:: rest

   Sample RM01
   ===========

   Clustering
   ----------

**Emphasis and code.**

.. code-block:: rest

   *italic*, **bold**, and ``literal text`` for field names like ``Mn55``.

**Lists.** Blank line before and after. Indent continuation lines to line up.

.. code-block:: rest

   * four clusters, k-means
   * PCA with three components
   * cluster 2 is the garnet rim

   #. auto-numbered
   #. second item

**Field lists**, for metadata at the top of a document:

.. code-block:: rest

   :Sample: RM01
   :Date: 2026-11-14
   :Analyst: your name

**Figures.** The path is relative to the notes file. Everything indented under the
directive belongs to it, and the last indented paragraph is the caption.

.. code-block:: rest

   .. figure:: figures/cluster_map.png
      :width: 80%
      :align: center

      k-means clustering of RM01 on four components.

**Tables.** The simple form needs only ``=`` rules and aligned columns:

.. code-block:: rest

   ======  =========  =======
   Zone    Grt_Z      Dominant
   ======  =========  =======
   core    2.98       almandine
   rim     2.95       spessartine
   ======  =========  =======

**Admonitions**, for anything you want to stand out:

.. code-block:: rest

   .. note::

      Fe57 is noisy below 100 ppm in this sample.

   .. warning::

      Grt_Z is wrong here -- no Si in the data.

**Comments** — a line starting ``..`` with nothing the parser recognises is ignored:

.. code-block:: rest

   .. check this against the spot data before using it

That is enough to write notes anyone can read, including you in six months. The full
specification is at `docutils.org <https://docutils.sourceforge.io/rst.html>`_, and the
*reST Editor* toolbar will insert most of these for you.


Appendix C: Getting your own data in
====================================

Sections 1 and 16 covered the two routes we use today. The Import tool handles several
more.

#. **Home** toolbar page → **Import Files**.
#. Choose a **Data type** and **Method** — ``LA-ICP-MS`` with ``quadrupole``, ``TOF`` or
   ``SF``, or ``XRF`` with ``image``.
#. Point it at your directory. The metadata table fills with one row per sample.
#. Fill in the geometry. For quadrupole and SF, that is spot size, sweep time and stage
   speed, and LaME derives dX and dY from them — **dX = spot size**,
   **dY = speed × sweep**. For TOF, you give the raster's physical length and width
   instead, and the per-pixel spacing is derived from the file's own grid.
#. Use the per-sample **Select files** button to check which files map to which analytes,
   and to exclude standards from a line-scan directory.
#. **Import**.

Three layouts are recognised, and LaME works out which it is looking at:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Layout
     - What it looks like
   * - Matrix per analyte
     - One file per analyte, each a bare rectangle of numbers. Section 1's RM01, and
       XMapTools exports.
   * - Line scans
     - One file per laser traverse, all analytes in columns, with a time column.
       Agilent "Intensity Vs Time" exports. LaME reads the line number out of the
       filename, sorts the lines, and drops the ``Printed:`` footer.
   * - Images
     - One image per element. Section 16's XRF core scan.

If a conversion gives you trouble, send the presenter a raw export and you will get a
``.lame.csv`` back.


Getting help
============

**In the application.** **Help** menu → *User Guide* or *Tutorials*, and the
context-sensitive **Help** toolbar toggle described in `Finding the documentation`_.

**Video walkthroughs.**

* `Introduction to LaME <https://www.youtube.com/watch?v=wPuP3z1NJXA>`_ — interface,
  navigation, view modes
* `Loading Data and Selecting Samples <https://www.youtube.com/watch?v=DWJTAN3SPS8>`_ —
  import formats and analyte selection
* `Visualization Fundamentals <https://www.youtube.com/watch?v=j6oNE7QN5Ak>`_ —
  correlation, spatial patterns
* `Working with Notes <https://www.youtube.com/watch?v=5Xe5hjQQcMc>`_

**The survey.** Please fill it in before you leave — see
`Tell us what you thought`_. It is the most direct route your opinion has into the next
release.

**Reporting a problem.** **Help** menu → *Report Bug*. Please include what you were
doing, what you expected, and what happened. Everything in
`Known limitations in this build`_ is already known — anything else is worth telling us
about, and today is exactly the sort of session that surfaces new ones.

References
==========

.. _GitHub: https://github.com/dhasterok
