================================================
LaME Workshop — Presenter Script
================================================

:Audience: Presenter only — do not distribute
:Companion: ``workshop_plan.rst`` (the participant handout)
:Build: ``LaME v0.9.0-workshop``

.. note::

   Print landscape, one block per spread if you can. The handout tells attendees *what*
   to do; this tells you *what to say*, *what will go wrong*, and *what to cut*.

.. contents:: Contents
   :depth: 1
   :local:


Timetable
=========

.. list-table::
   :header-rows: 1
   :widths: 6 10 6 44 34

   * - No.
     - Clock
     - Min
     - Block
     - Cut if behind
   * - 0
     - 08:40
     - *20*
     - Doors open — install triage
     - Not contact time. Do not start late to accommodate it
   * - 1
     - 09:00
     - 8
     - Welcome and scope
     - Trim to 5. Keep the honesty framing
   * - 2
     - 09:08
     - **10**
     - **First win** — open project, map + histogram
     - Never cut. This is the whole morning's foundation
   * - 3
     - 09:18
     - 22
     - Fields: analytes, ratio, reference, Eu\*
     - Drop the ratio step (−4)
   * - 4
     - 09:40
     - 18
     - Histogram, correlation
     - Drop Spearman/Kendall comparison (−4)
   * - 5
     - 09:58
     - 22
     - Scatter → heatmap → ternary → ternary map
     - Drop the heatmap statistic tour (−6)
   * - C1
     - 10:20
     - 8
     - **Resync buffer**
     - This is slack. Spend it here, not on content
   * - —
     - 10:28
     - 20
     - **Break**
     - Do not shorten. People need to fix things
   * - 6
     - 10:48
     - 30
     - Regions and filters; polygons
     - Drop polygons (−10). Keep ROI + filters + ``roi map``
   * - 7
     - 11:18
     - 26
     - Clustering; change analytes; PCA
     - Drop cluster naming/linking (−6)
   * - 8
     - 11:44
     - 26
     - Stoichiometry across three garnets
     - Do RM02 + TR1-07 only, skip WOS-02 (−8)
   * - C2
     - 12:10
     - 6
     - **Resync buffer**
     - —
   * - 9
     - 12:16
     - 24
     - **Pyrite — attendee-driven**
     - Drop the per-cluster histogram (−8). Keep the PCA comparison
   * - 10
     - 12:40
     - 10
     - Notes → methods report
     - Drop Formatted Info, keep Record (−5)
   * - 11
     - 12:50
     - 6
     - Look-ahead: Lu–Hf, import, Blockly, profiles
     - First thing to cut entirely (−6)
   * - 12
     - 12:56
     - 4
     - Q&A, feedback, bug reporting
     - Keep 2 min minimum
   * - **Total**
     -
     - **220**
     - + 20 min break
     -

**Hard decision points.**

* **10:20** — if more than a quarter of the room is not at Checkpoint 2, spend the whole
  buffer resyncing and plan to cut polygons from block 6.
* **11:44** — if you are more than 10 minutes late here, do two garnets, not three. The
  Si lesson needs exactly two samples to land; the third is reinforcement.
* **12:16** — the pyrite block is the one attendees will remember, because it is the one
  they drive. Protect it. Cut blocks 10 and 11 before you cut it.


Why the order is what it is
===========================

Worth knowing, because someone will ask why filtering comes after plotting.

**Dependency.** Fields must exist before a plot can use them. A plot must exist before a
filter has anywhere to show its effect. Filters and clusters must exist before
stoichiometry can be scoped to one. Clusters must exist before the *Cluster results*
note block has anything to insert. Data → fields → plots → masks → clusters → report is
the only order that never asks anyone to accept something on faith.

**Risk.** Every block before the break is on the reliable list. First contact with
filtering — the roughest area — is at 10:48, after 80 minutes of unbroken success and
after everyone has saved their own project. If filtering goes badly the workshop has
already delivered its value. Doing filtering early "while everyone is fresh" risks
poisoning the first hour instead.

**Attention.** "Filters live inside ROIs" is the most confusing concept in the
application. It gets the post-break slot, not 12:30.

**Quarantine.** Every unfinished feature is in block 11, labelled. Sprinkling "and this
bit isn't ready" through the morning erodes confidence cumulatively; one clearly-framed
roadmap block at the end reads as candour.


Room setup
==========

**T-45, presentation machine**

* Mirror displays, do not extend — you will lose track of which screen has the dialog.
* Set the LaME window to the size your checkpoint screenshots were taken at.
* Styling Toolbox → **Text and Scales** → raise **Font size**. Check legibility from the
  back row, not from your chair.
* Disable notifications, sleep and auto-update. Plug in power.
* **Open the project once and draw all five plots once.** This warms the lazy imports and
  matplotlib's first-figure cost so nothing stalls on stage.
* Pre-load the block 11 demo states in a second window, or have screenshots ready.

**T-20, room**

* USB sticks at the end of each row of tables.
* Write ``CHECKPOINT: 0`` on the whiteboard. Update it at every checkpoint — latecomers
  and stuck attendees then self-rescue without interrupting.
* Triage sheet out. Record every problem; do not fix them silently.


Pre-flight checklist
====================

Run this on a **clean machine**, not your development machine, which hides the
packaging problems.

.. danger::

   **Gate zero: the build must carry Qt 6.11.2 or newer.** Qt 6.11.0 and 6.11.1 segfault
   at random on macOS 26 and later — a dangling ``CGColorSpaceRef`` in
   ``QImage::toCGImage()`` (QTBUG-147602, fixed in 6.11.2). Every image Qt converts is
   exposed, so it surfaces as the app vanishing with no error, typically on a sample
   switch or a redraw. If the release you hand out was built before ``requirements.txt``
   pinned ``PyQt6-Qt6>=6.11.2``, **re-cut it**: otherwise a quarter of the room loses
   their work at unpredictable moments and there is nothing you can say from the front
   that helps. Check it from a terminal against the packaged interpreter::

      python -c "from PyQt6.QtCore import qVersion; print(qVersion())"

   ``qVersion()`` is the number that matters — ``QT_VERSION_STR`` reports what the
   bindings were compiled against (still 6.11.0) and will mislead you.

**T-90**

#. **Confirm the Qt runtime is ≥ 6.11.2** (see above). Nothing below is worth checking
   until this passes.
#. Download the release assets **fresh over the venue wifi** and time it. Over five
   minutes means the USB route is mandatory, not a backup.
#. Install following the attendee instructions **verbatim**, Gatekeeper and SmartScreen
   steps included. Use none of the shortcuts you know.
#. Launch. Note the cold-start time — say that number in your opening remarks so nobody
   thinks it has hung.
#. Unzip ``LaME-workshop.zip`` to the Desktop. Open ``00-open.lame_project.json``.
   Confirm the relative sample path resolved and the field map draws.
#. **Open every checkpoint project in turn and verify its condition** — above all that
   the clustering one restores its groups *without recomputing*. **This is the most
   important item on this list.** If a checkpoint does not restore, your entire
   desynchronisation strategy is gone, and you need to know now rather than at 10:20.
#. Confirm the Stoichiometry **Mineral** dropdown is populated and not red. If it is
   empty, the mineral-config path fix did not make the build — block 8 cannot be
   hands-on and must become a demo on your machine.
#. Time one **scoped** stoichiometry run on each garnet. Write the numbers down; you
   will be asked how long to wait.
#. Set the reference to ``CI chondrite [AG89]`` and confirm **Eu\*** recomputes.
#. Switch between all four samples. Block 8 depends on this being clean.
#. **Click every hazard once and write down the literal message** — see
   `Do not do these on the projector`_. You will be asked about at least one, and
   knowing the exact wording is the difference between authority and hand-waving.
#. Confirm **Help** opens a built page.
#. ``python main.py --selftest`` on each machine you will use.


Block 1 — Welcome (09:00, 8 min)
================================

.. Figure placeholder PFIG-1  [presenter slide]
   WHAT: One title slide. "Laser Map Explorer" + version + your name/affiliation +
   the date. Bottom third: four small thumbnails in a row -- an RM02 ternary map, a
   four-cluster cluster map, a Grt_dominant swatch map, an As-Au biplot. These are
   the four things the room will have made by 13:00.
   WHY: Projected during block 1 while you talk. The thumbnails are the promise;
   referring back to them ("that one, by lunch") is worth more than a bullet list.
   SIZE: full slide.

**Say.** What LaME is for: you have a map with tens of thousands of pixels and thirty
analytes, and the question is never "what is the mean" — it is "which parts of this
grain are chemically distinct, and what are they". Today is about answering that.

**Set the expectation about beta software early and once.** Something like: *"This is
beta. There are things in the interface that do not work yet, and rather than hope you
do not find them, the handout lists them with what to do instead. If you hit something
not on that list, tell me — that is genuinely useful."*

Doing this at 09:00 converts every later limitation from an embarrassment into a
confirmation that you were straight with them.

**Do not** demo anything in this block. Talking over a live app at minute three invites
a question you have not laid groundwork for.


Block 2 — First win (09:08, 10 min)
===================================

*Handout section 1.*

**Transition.** "Before anything else, let us all get to the same screen."

**Click path.** Home toolbar page → **Open Project** → ``Desktop/LaME-workshop/`` →
``00-open.lame_project.json``.

**Say while it loads.** Why a project and not the CSV: a project carries the sample, the
field selection and the window state together. That makes it a reliable starting point —
and, more usefully today, a reliable *recovery* point. Point at the whiteboard.

**The payoff to name out loud.** One action produced both a map and a histogram. That
pairing is the Preprocess page's doing, and it is the cheapest useful thing in the app.

**Then spend the gradient-map warning, once.** While everyone is looking at the Plot
box: the entry one line below ``field map`` does nothing in this build. Then move
everyone to **Field Viewer** and say you are not coming back to this page. Every
subsequent block runs on pages whose plot lists contain no unfinished entries.

**Planted question.** *"Why did we not just open the CSV?"* — Because then all 25 of you
would be in slightly different default states and no checkpoint photograph would match.
Also because you will need Open Project for catch-up in about forty minutes, so you may
as well learn it now.

**If X then Y.**

* *Project will not open / sample not found* → their folder is not on the Desktop, or
  they moved files out of it. Relative paths. Have them re-unzip.
* *Window is tiny or off-screen* → their display is smaller than the authoring machine.
  Resize manually; note it on the triage sheet.
* *Nothing in the canvas* → check the Control Toolbox is on Preprocess and a sample is
  selected in the pinned combobox.

**Checkpoint 0.** Title bar ``LaME - 00-open``, Preprocess page, RM02 field map plus
histogram. Update the whiteboard to ``0``.


Block 3 — Fields (09:18, 22 min)
================================

*Handout section 2.*

**Transition.** "LaME will not plot an analyte you have not asked for. That selection is
the first real control you have, and it reaches further than you would expect."

**Click path.** Pinned **Analytes** → diagonal cells for Mn55, Y89, Sm147, Eu153,
Gd157, Ca43, Fe57, Mg24 → the off-diagonal Y89 × Mn55 cell → **Done**. Then the **Ref.**
row → ``CI chondrite [AG89]``. Then Analysis page → **Calculator** → saved formula
``Eu*`` → **Calculate**.

**The one thing to labour.** Diagonal versus off-diagonal. Say it, then show it, then
say it again. It is the least discoverable thing in that dialog. Mention that the
background colours *are* the correlation matrix — the dialog is already telling them
which analytes co-vary.

**Order matters here and the handout says so.** Reference **before** Eu\*. The shipped
formula uses ``_N`` normalised fields, and the default reference is bulk silicate Earth,
not a chondrite. If someone computes Eu\* first they get a number that looks fine and is
normalised to the wrong thing — the worst kind of wrong.

**Planted question.** *"Why is Eu\* a formula rather than a button?"* — Because the
interpolation you want depends on which neighbours you trust. Sm–Gd is conventional, but
it is a choice, and making it explicit in a formula you can read is better than burying
it.

**If X then Y.**

* *"could not evaluate"* → they typed a conditional, or opened the Calculator
  documentation and copied the ``case()`` example. That syntax does not exist in any
  version. Point them at the limitations table.
* *Eu\* map looks like a raw element map* → reference not set. Set it, recalculate.
* *Field not in the Calculator's field list* → not selected in the Analytes dialog.

**What to cut.** The ratio step (−4 min). Eu\* is the one that matters; it is the first
moment LaME does something they could not do in a spreadsheet.

**Checkpoint 1.** ``Eu*`` under the Plot Tree's Calculated branch, smooth low-contrast
map. Then have everyone **Save Project** under their own name. Whiteboard ``1``.


Block 4 — One field (09:40, 18 min)
===================================

*Handout section 3.*

**Transition.** "Before comparing elements, read one properly."

**Click path.** Field Viewer → ``histogram`` → X = ``Mn55`` → PDF, **Show KDE** →
``log-scaling``. Then ``correlation`` → Method ``Pearson``, then ``Spearman`` → **C²**.

**The teaching point on log-scaling.** Trace elements are usually closer to log-normal
than normal. The shape change when they toggle it is the diagnostic, and it determines
which colour scaling their maps should use for the rest of the day.

**The teaching point on method.** Pearson assumes linear; Spearman only monotonic. A big
gap between them means a real but non-linear relationship — which is common in zoned
minerals and easy to miss if you only ever look at one.

**Say once, now, because it will bite later.** The correlation matrix **ignores filters**.
So does the ternary map. When they filter in forty minutes and the correlation does not
move, that is why. Pre-empting this here costs ten seconds and saves a confused question
at 11:00.

**If X then Y.**

* *Histogram empty or one bar* → a constant or near-constant field. Switch field.
* *Correlation matrix missing analytes* → they were not selected in block 3.

**What to cut.** The Spearman/Kendall comparison (−4 min).


Block 5 — Two then three fields (09:58, 22 min)
===============================================

*Handout section 4.*

**Transition.** "Now relationships, and then back onto the map."

**Click path.** Scatter and Heatmaps page → ``scatter``, X = ``Mn55``, Y = ``Y89``,
Color = ``Ca43`` → ``heatmap``, try *Heatmaps* = ``counts`` then ``median`` → back to
``scatter``, set Z = ``Fe57`` → ``ternary map``, set colours → **Ternary map** button.

**The thing to point out explicitly.** There is no "ternary" entry in the plot-type list.
A ternary appears when you fill in Z. Nobody discovers this unaided.

**Why heatmap after scatter.** With 78,000 points the scatter is a solid blob.
Overplotting hides structure; binning reveals it. Make them see the blob first so the
heatmap has something to fix.

**The ternary map is the money shot of the morning.** Say what it is doing: each pixel
coloured by its position in the ternary, so three elements land on one map without you
deciding which matters most. For a zoned garnet the core/rim contrast should be obvious.
Pause here and let them look at it.

**Planted question.** *"How do I know which three elements to use?"* — Start with the
major cations that define the end members. For garnet, Mn–Ca–Fe gets you spessartine
versus grossular versus almandine. Then follow the correlation matrix.

**If X then Y.**

* *Nothing happens on scatter* → X and Y are the same field, or one is blank. Silent
  no-op by design.
* *Ternary blank* → two of the three fields are identical.
* *Ternary map unchanged after picking colours* → they did not press **Ternary map**.

**What to cut.** The heatmap statistic tour (−6 min).

**Checkpoint 2.** Five plots in the tree, ternary map on screen with visible zoning.
Whiteboard ``2``. **This is the resync point before the break** — if a quarter of the
room is not here, use the buffer and plan to cut polygons.


Block 6 — Regions and filters (10:48, 30 min)
=============================================

*Handout section 5.* **The highest-risk block of the day. Do not improvise.**

**Transition.** "Everything so far used every pixel. Now we choose which pixels."

.. Figure placeholder PFIG-2  [presenter slide -- the one diagram worth projecting]
   WHAT: A diagram, not a screenshot. A box labelled "ROI: garnet" containing two
   stacked rows labelled "filter: Mn55 > x  (and)" and "filter: Ca43 < y". Beside
   it a second box "ROI: rim" with one filter inside. An arrow from both boxes to a
   small map thumbnail with grey excluded areas, labelled "roi map".
   WHY: "Filters live inside ROIs" is the sentence that loses the room. The
   containment is obvious in a drawing and invisible in the interface, where
   Filter Settings sits to the LEFT of the ROI table it belongs to.
   SIZE: half slide, large type.

**Say the structure before anyone clicks.** An ROI is a named saved region; a filter is
one rule inside it. You select the ROI first, then add filters to it. Say it in that
order, and show the ROI table *before* the Filter Settings panel, even though Filter
Settings is on the left and reads first.

**Why this matters.** With zero ROIs, the first **Add filter** silently creates one. The
blocking dialog — *"Select a single region of interest…"* — only appears on the
**second** filter. So the natural discovery path teaches the wrong model first and then
contradicts it. Script it:

**Click path.** Processing page → **Filters** → Masking Toolbox opens on Filters tab →
in the **ROI table at the bottom**, **Add ROI** → rename to ``garnet`` → **leave it
selected** → Filter Settings: Field type ``Analyte``, Field ``Mn55``, narrow Min/Max via
the percentile spin boxes, Operator ``and`` → **Add filter** → add a second on ``Ca43``.

Then: Field Viewer → ``roi map``. **This is the plot that shows what a filter did.** Grey
is excluded. Use it every time.

**Polygons, if time.** Polygons tab → toggle switch → **Create a new polygon** → click
around a feature. Mention the *In/out* column.

**Two things not to say.** Do not say "now let us re-cluster inside this polygon" —
clustering ignores polygons by design. And do not reach for **Crop** or **Full Map**;
crop is incomplete and the button that would undo it raises an error.

**Planted question.** *"Why are filters inside regions rather than global?"* — Because
real samples need different rules in different places. One grain's rim and another
grain's core are different populations, and a global filter cannot express that.

**If X then Y.**

* *"Select a single region of interest…"* → no ROI row selected, or two are. Click one
  row. This will happen to several people; it is the expected failure, not a bug.
* *Map did not change after Add filter* → **Use** checkbox unticked, or the ROI mask
  toggle is off in the Processing toolbar page.
* *"could not save filter table"* → they pressed **Save filter**. Unavailable in the
  packaged build. Filters live in the project; that is enough.
* *Correlation did not change after filtering* → expected. Already flagged in block 4.
* *Lost in polygon mode* → flip the toggle off. That is the whole fix; do not
  troubleshoot further.
* *ROI work collapsed entirely* → **there is no forward-safe checkpoint for this block**
  (see `Fallbacks`_). Pair them with a neighbour and tell them 11:44 puts the whole room
  back in sync. Do not hand them ``04-clusters`` now — it starts at block 8 and would
  skip clustering as well.

**What to cut.** Polygons entirely (−10 min). ROI + filters + ``roi map`` is the part
that everything downstream depends on.

**Checkpoint 3.** ROI named ``garnet`` with non-zero % Filtered; ``roi map`` showing a
grey rim. Whiteboard ``3``.


Block 7 — Clustering (11:18, 26 min)
====================================

*Handout section 6.*

**Transition.** "So far you have told LaME what to look at. Now let it propose the
zones itself."

**Click path.** Clustering page (runs on open) → Method ``k-means``, No. clusters ``4``
→ ``cluster map`` → **Randomize** the seed two or three times → **Analytes**, add
``La139``, ``Ce140``, ``Nd146`` → **Done** (auto-recomputes on this page) → Dimensional
Reduction page, look at ``variance`` → back to Clustering, tick **PCA**, set
**No. basis** → re-cluster → Masking Toolbox **Clusters** tab, rename, link, **Create
Region**.

**The seed demonstration is the most valuable thirty seconds in this block.** k-means
starts from random centres. Zones that survive several seeds are robust; zones that
reshuffle were never there. Most people have never seen this done and it changes how
they read a cluster map permanently.

**Order matters: PCA before the checkbox.** If no PCA scores exist, LaME falls back to
raw analytes silently, and the comparison they are trying to make does not happen. Run
the Dimensional Reduction page first.

**Two inert controls to steer around.** The **Distance** combobox has no effect in this
build. And HDBSCAN works, but combined with ``cluster performance`` it silently does
nothing — HDBSCAN finds its own cluster count, so there is no *k* to sweep.

**Planted question.** *"How do I choose the number of clusters?"* — ``cluster
performance`` with k-means gives you inertia and silhouette against *k*. But the honest
answer is that you choose it from the petrology: if you expect core, mantle and rim, try
three and see whether the map agrees.

**If X then Y.**

* *Clusters did not change after adding analytes* → not on the Clustering page when they
  pressed Done. Press **Update Plot**.
* *PCA tick did nothing* → PCA never ran. Visit Dimensional Reduction.
* *Dimensional Reduction page sluggish* → expected on 78,000 pixels; PCA recomputes on
  each update there. Say so rather than letting them think it has hung.
* *``cluster performance`` blank* → HDBSCAN selected.

**What to cut.** Cluster naming and linking (−6 min). But **keep Create Region** — block
8 needs an ROI.

**Checkpoint 4.** Four named clusters, PCA ticked, at least one cluster turned into an
ROI. Whiteboard ``4``.


Block 8 — Stoichiometry (11:44, 26 min)
=======================================

*Handout section 7.* **Read the warning below before you start.**

.. warning::

   **Scope before anything else.** The calculation runs pixel by pixel on the interface
   thread and re-runs on every settings change. Unscoped on RM02 that is 78,228
   iterations of frozen window — and again each time someone nudges a combobox. Set the
   scope to one cluster or ROI *first*, tick only that region, and leave **Compare all
   redox methods** off.

**Transition.** "Composition is one thing. What mineral is it, site by site, is another."

**Click path.** Analysis page → **Stoichiometry** → **Compute scope**: *Filter* = your
ROI, tick **only** that region → **Settings**: Mineral ``Garnet``, Input basis ``ppm``,
Redox ``droop_1987``, BDL ``zero``, Compare redox **off** → **Run**. Then ``field map``,
field type ``Stoichiometry``, field ``Grt_dominant``.

**Then the Si lesson, which is the point of the block.** Look at ``Grt_Z``. It should be
near 3.0, filled by silicon. On RM02 it is not — RM02 has no Si, so aluminium has filled
the tetrahedral site following the configuration's fallback order, and the end-member
percentages are wrong.

.. Figure placeholder PFIG-3  [presenter slide -- prepare in advance, do not build live]
   WHAT: Side by side. LEFT: RM02's Grt_Z histogram or value readout, centred well
   away from 3.0, annotated "no Si measured -> Al fills the Z site". RIGHT: TR1-07's
   Grt_Z, sitting at ~3.0, annotated "Si29 present". Below each, that sample's
   end-member percentages.
   WHY: The single most transferable lesson of the day. Building this comparison
   live costs minutes you will not have at 11:44, and if a run misbehaves the lesson
   is lost. Have it on a slide and let the live runs confirm it.
   SIZE: full slide.

**Say this plainly:** the calculation is only as good as the elements you measured, and a
missing major element does not raise an error. It produces a plausible, incorrect answer.
That is the single most transferable thing in this workshop.

Then switch to ``TR1-07``, make a quick ROI, run again, and compare ``Grt_Z``. With
``Si29`` present it sits near 3.0 and the end members mean something.

**Credibility note worth making.** The chemistry here is the most heavily validated code
in LaME — cross-checked against published recalculation workbooks for garnet, feldspar,
olivine and pyroxene. What is missing is a background thread in the interface, not
correctness in the mathematics. Say that; it reframes the slowness accurately.

**Planted question.** *"Could it warn me that Si is missing?"* — It should, and that is
going on the list. Today it is on you to check the site totals. Which is a reasonable
habit anyway.

**If X then Y.**

* *Mineral dropdown empty and red* → the config-path fix is not in this build. Abandon
  hands-on, demo from your machine, and note it.
* *Frozen window* → they ran unscoped. Wait it out; force-quitting loses their session.
  Then re-scope. Prevention is the whole point of the warning.
* *All results blank / "No matching element columns"* → wrong Input basis, or the
  sample genuinely lacks the elements.
* *``Grt_dominant`` draws as a colour bar instead of swatches* → note it and move on.

**What to cut.** WOS-02 (−8 min). Two samples is enough for the contrast.

**Checkpoint 5.** Two garnets with ``Grt_*`` fields, a ``Grt_dominant`` swatch map,
``Grt_Z`` near 3.0 on TR1-07 and clearly not on RM02. Whiteboard ``5``.


Block 9 — Pyrite, attendee-driven (12:16, 24 min)
=================================================

*Handout section 8.* **Protect this block. It is the one they will remember.**

**Transition.** "Everything you have used so far works on any mineral system. Here is a
different one, and two real questions. You drive; I will circulate."

**Pose the questions, do not answer them.** Does clustering change if you precondition
with PCA first? And once the pyrite is on its own, what actually separates the
populations inside it? Sample is ``71A-Py 12`` — 91 lines, 29,666 pixels, roughly 40%
of it sulfide.

**Deliberately give fewer steps.** They have done clustering, PCA and biplots once each.
Doing it again unassisted, on unfamiliar data and with a question attached, is the
consolidation — the only part of the day that tests whether anything stuck. Resist the
urge to drive.

**Prompts, if the room stalls** — in this order, one at a time:

#. "How would you find the pyrite in the first place?" → field map on Fe57 and S34.
#. "Cluster the whole map first — which clusters are the sulfide?" → k-means, 4 groups,
   on Fe57/S34/Cu65/Co59/Ni60/As75. Two land on sulfide, two on everything else.
#. "Now do it again with PCA on. What moved?" → Dimensional Reduction page first, then
   PCA ticked, No. basis 3.
#. "How do you keep just the pyrite, without choosing any filter bounds?" → Clusters
   tab, tick the sulfide clusters, **Create Cluster Mask**.
#. "Fe against Cu — what are the outliers?" → scatter, X ``Fe57``, Y ``Cu65``,
   Color = cluster.
#. "Is Co telling you about the zoning?" → histogram of ``Co59``, log-scaled, per
   cluster.

**The PCA comparison is the teaching point, so make sure it lands.** Both clusterings
put the sulfide/matrix boundary in the same place — that boundary is not in doubt. What
changes is how the pyrite is divided *within* itself, and the cluster proportions along
with it. Say plainly that neither is the right answer: PCA reweights what counts as
similar by discarding the directions of least variance, and running it both ways is how
you find out whether a result depends on that choice.

**Know the answer to the histogram step before they get there.** Co and Ni are close to
*uniform* through this pyrite — the two sulfide clusters sit almost on top of each other,
while both sit two to three orders of magnitude above the matrix. Attendees will read
that as having done it wrong. It is the opposite: a huge contrast between two materials
says nothing about structure inside either one. What separates their two pyrite clusters
is **Cu** (roughly tenfold) and **As**, which is exactly what the Fe–Cu biplot shows.
Have that sentence ready; it turns an apparent dead end into the result.

**Say once.** This map is uncalibrated — counts per second, not ppm. Patterns are fine;
absolute values and mineral formulae are not. Nobody should run the Stoichiometry dock
on it.

**Don't send them after gold on this sample.** Au197 is below detection in about
four-fifths of these pixels. The arsenian-pyrite gold story is a good one, but this is
not the map for it — Cu and As carry the chalcophile signal here.

**The extension worth saving for the end.** Have someone turn the cluster mask off with
the **Cluster Mask** toolbar toggle and redraw the Fe–Cu biplot on the whole map. The
silicate matrix swamps the pyrite entirely. That is the most concrete argument for
masking anyone will see today, and it lands better as a discovery than as an assertion.

**If X then Y.**

* *Both clusterings look identical* → PCA never ran; they skipped the Dimensional
  Reduction page, so it silently fell back to raw analytes. Same trap as block 7.
* *Cluster mask greys out everything* → they ticked the matrix clusters, not the
  sulfide. Check against the Fe57 map.
* *Biplot is a blob* → the mask is off, or they are plotting the whole map. That is the
  lesson; let them find it.
* *Co histogram looks the same for every cluster* → expected for the two pyrite
  clusters, and the point. Make sure they also see the matrix clusters, which are
  dramatically lower.
* *Cannot find pyrite on the map* → try S34 rather than Fe57; sulfur has less background
  in silicates.

**What to cut.** Drop the histogram step (−8 min) and keep the PCA comparison and the
Fe–Cu biplot; the comparison is the part that is genuinely new to them. Do not cut the
block.

**Checkpoint 6.** Two cluster maps of the same sample with and without PCA, a cluster
mask restricting the view to the sulfide, an Fe–Cu biplot coloured by cluster, and a
Co histogram compared across clusters. Whiteboard ``6``.

Block 10 — Notes (12:40, 10 min)
================================

*Handout section 9.*

**Transition.** "You have results. Now leave with a record of how you got them."

**Click path.** Log page → **Notes** → **Record** (status light goes red) → make any
plot → Notes toolbar **Insert** page → **Formatted Info** → insert *List analytes used*,
*Filter table*, *Cluster results*.

**The point to make.** Those blocks pull live session state — the actual analytes, the
actual filters, the actual clusters. It is the methods paragraph of a paper, assembled
from what they really did rather than what they remember a month later.

**Frame Capture honestly.** There is a Workflow designer with a block canvas, and a
Capture toggle. Capture currently records only sample changes as blocks, so describe it
as a **methods-report generator** — which it does well — rather than as a way to record
clicks into a re-runnable workflow. Hand-built workflows do run; recording them does not
yet. Said plainly this is fine. Oversold, it is the thing that costs you trust.

**What to cut.** Formatted Info (−5 min). Keep Record and the automatic figure capture.


Block 11 — Look-ahead (12:50, 6 min)
====================================

Hands down. You drive. Label the block as roadmap before you start.

.. Figure placeholder PFIG-4  [presenter slide -- YOUR data, not distributed]
   WHAT: One slide from olary2 or AH5C-1. A per-pixel date map on the left; a
   per-cluster isochron with its Monte Carlo uncertainty envelope on the right.
   Caption the isotope pair used and the decay constant source.
   WHY: Block 11's whole credibility. The feature is real and this is the proof,
   but today's four samples cannot produce it. A result on screen converts "not
   today" from a shortfall into an invitation.
   NOTE: unpublished -- slide only. Not in the attendee bundle, not in the handout.
   SIZE: full slide.

**Lu–Hf dating — one slide, no demo.** The implementation is real: decay constants from
Söderlund et al. 2004, per-pixel date maps, per-cluster isochrons with Monte Carlo
uncertainty. It needs :sup:`176`\ Lu/:sup:`177`\ Hf and :sup:`176`\ Hf/:sup:`177`\ Hf.
Today's samples have :sup:`175`\ Lu and at most one Hf isotope, so no sequence of clicks
produces an isochron. Show your own result from olary2 or AH5C-1, say "bring me a map
with Hf isotopes and we will run it", and move on. **Do not open the empty dock** — it
invites a question with no satisfying answer.

.. Figure placeholder PFIG-5  [presenter slide -- reuse from docs/source/_static/screenshots/]
   WHAT: Two or three Import tool screenshots in sequence: the file list with a raw
   export loaded, the column-mapping table with analyte names resolved, and the
   confirmation. Existing docs screenshots are fine here; nothing needs to match
   attendee screens.
   WHY: 90 seconds of narration over stills beats a live run that 25 people would
   then try to repeat on their own exports.
   SIZE: full slide.

**Import tool — 90 seconds, screenshots.** Handout Appendix B covers it. Offer the
conversion service: send a raw export, get a ``.lame.csv`` back. That offer is worth more
to them than a live demo.

**Blockly — 3 minutes, your machine only.** Show the canvas and a small hand-built
stack. **Do not touch the plot-correlation block** — it emits a field map in this build.
Presenter-only because the bundle ships in the packaged build but is absent from a source
clone, so it works for some of the room and not others.

**Profiles — 4 minutes, if time.** Handout Appendix A has full steps. Make the entry
point explicit: the **Profiles dock**, never the ``profile`` plot type, which draws
nothing.

**Cut this entire block first if you are behind.** Everything in it is in the handout.


Do not do these on the projector
================================

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Do not touch
     - What the room would see
   * - ``gradient map`` plot type
     - A noise-reduction warning, or silence with the old plot still up
   * - Calculator ``case()`` / ``otw()``
     - *"could not evaluate conditional statement. Check syntax."*
   * - **Crop**
     - Incomplete; leaves no way back
   * - **Full Map**
     - Dialog appears, then an ``AttributeError`` and nothing happens
   * - Cluster **Distance** combobox
     - Recomputes, identical result. Looks like you do not know your own app
   * - HDBSCAN + ``cluster performance``
     - Blank or stale canvas, no message
   * - ``profile`` / ``polygon`` plot types
     - Blank canvas, no error
   * - Blockly plot-correlation block
     - Draws a field map
   * - **Save filter** preset
     - *"could not save filter table."* in the packaged build
   * - Stoichiometry unscoped
     - Minutes of frozen window on a projector
   * - Thermometry / Barometry tabs
     - Empty dropdowns, nothing behind them
   * - Correlation or ternary map after filtering
     - No change, and you have just implied filtering is broken


Fallbacks
=========

.. list-table::
   :header-rows: 1
   :widths: 14 30 14 42

   * - Ckpt
     - File
     - Resumes
     - Recovers
   * - 0
     - ``00-open.lame_project.json``
     - block 2
     - RM02 loaded, nothing else
   * - 2
     - ``02-plots.lame_project.json``
     - block 5
     - Fields, ratio, Eu\*
   * - 4
     - ``04-clusters.lame_project.json``
     - block 8
     - ROI and clusters, restored without recomputing
   * - 6
     - ``06-pyrite.lame_project.json``
     - block 9
     - Pyrite sample loaded

Three keystrokes: **File → Open Project**, pick the file, done.

.. caution::

   **Know the gap before the day.** The four files resume at blocks 2, 5, 8 and 9. There
   is nothing that resumes at block 6 or 7, so an attendee whose ROI or clustering work
   collapses cannot be caught up until 11:44 — handing them ``04-clusters`` earlier skips
   both blocks. If you find an hour before the workshop, author a fifth file after the
   filters block (``03-filters``, resuming at block 7) and add it to the handout's
   catch-up table. It covers the two riskiest blocks of the day and is the single highest-value
   piece of remaining prep.

.. important::

   **Never debug a lost attendee during contact time.** Hand them the checkpoint, write
   the symptom on the triage sheet, move on. One person's problem costs twenty-four
   people their attention. This is the rule that makes a hands-on workshop survivable,
   and it is the hardest one to keep.


Triage sheet
============

Keep this on paper at the front. It is the workshop's real research output — a list of
what breaks for real users on real machines, which no amount of testing on your own
machine will give you.

.. list-table::
   :header-rows: 1
   :widths: 16 14 12 34 24

   * - Name
     - OS / chip
     - Block
     - Symptom
     - Resolution
   * -
     -
     -
     -
     -
   * -
     -
     -
     -
     -
   * -
     -
     -
     -
     -


After the workshop
==================

**Send attendees**, same day if you can:

* The handout PDF, in case they annotated a paper copy.
* Their own saved projects if anything was lost.
* A link to file issues, and an explicit invitation to send raw data for conversion.

**File as issues**, from the triage sheet:

* Every symptom that is not already in the handout's limitations table.
* Install failures by OS and chip. Intel Mac demand in particular — there is no build
  for it, and the count from today is the evidence for whether that matters.

**Fix list this workshop will have earned:**

* Mineral-config paths anchored to ``BASEDIR`` rather than the working directory.
* Stoichiometry off the interface thread, with a progress indicator.
* A warning when a mineral's site-defining element is absent from the data — the RM02
  lesson, turned into something the software says itself.
* Remove or implement ``gradient map``, ``profile`` and ``polygon`` plot types; they are
  selectable and do nothing.
* Correct the Calculator documentation's ``case()`` section.
* Make the cluster **Distance** combobox work or remove it.
* Keep the Qt runtime pinned. ``requirements.txt`` left ``PyQt6`` unpinned, so the build
  silently picked up the one Qt patch release in years that corrupts image rendering on
  macOS. A GUI toolkit is not a dependency to float.
