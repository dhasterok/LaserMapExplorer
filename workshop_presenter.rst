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


Read this first: the handout is a superset, by design
=====================================================

**The handout is about five hours of material and you have 180 minutes, one of which
contains an installation.** That is deliberate. The overflow is there so that nobody
runs out of things to do, and so that attendees leave with a document that keeps working
after the room empties.

The budget, with nothing hidden:

.. list-table::
   :header-rows: 0
   :widths: 60 40

   * - 14:00–17:00
     - **180 min**
   * - less the catered coffee break at 15:00
     - −15
   * - less arrival, USB transfer and installation
     - −15
   * - less welcome and close
     - −3 *(the welcome is talked over the install)*
   * - **left for the seventeen handout sections**
     - **147 min**

Those seventeen sections cost about **282 minutes** at the pace a room actually moves.
So you can do a little over **half the handout**, and the timetable below picks which
half: **§1–6, §8–11 and §14 — eleven sections.** What it leaves out is §7, §12, §13 and
§15–17, all of which are self-contained.

.. important::

   **Say this during the install, and say it plainly:** *"Your handout has seventeen
   sections. We will get through about eleven of them. The rest is written so you can
   work through it on your own — the data is on your stick and nothing later depends on
   having been here for something earlier."*

   Thirty seconds, and it converts the thing that would otherwise read as running out of
   time into the thing it actually is. Without it, stopping at section 14 looks like
   failure; with it, it looks like a plan.

**The spine — reach these.** The timetable is built so that these four land:

#. **§1, the import.** The thing nobody can get from the documentation alone, and the
   reason several people are in the room.
#. **§9–10, clustering and using the clusters.** The most transferable skill of the day.
#. **§11, stoichiometry.** The mineral-formula chain is what LaME does that nothing else
   on their machine does.
#. **§14, notes.** Leaving with a record of their own work is worth more than one more
   plot type.

Everything between them is negotiable and every block carries a **Cut if behind** line.

**Eleven attendees changes two things.** Hands-on blocks move faster than the timings
below assume — those are sized for a room of twenty, so expect to gain a few minutes
every block, and bank them. And the arithmetic on helping someone individually changes:
two minutes spent on one person costs twenty person-minutes here, not fifty. A quick fix
is affordable where it would not be in a bigger room. Anything over about a minute still
goes on the triage sheet.

**Running ahead?** That is the good problem, and the ladder is in `Overflow blocks — if
you are ahead`_ at the end of this script. The TEC plot is first and it is only eight
minutes.

Timetable
=========

.. list-table::
   :header-rows: 1
   :widths: 5 8 5 10 36 36

   * - No.
     - Clock
     - Min
     - Handout
     - Block
     - Cut if behind
   * - 0
     - 14:00
     - **15**
     - —
     - **Arrival, USB transfer, install** — welcome talked over it
     - Cannot cut. This is also the afternoon's only slack
   * - 1
     - 14:15
     - **22**
     - §1
     - **Import RM01 from the iolite matrix files**; save the project
     - Never cut. Demote to a demo if the room cannot get it working
   * - 2
     - 14:37
     - 8
     - §2
     - Field maps; colour scaling
     - Three elements instead of six (−3)
   * - 3
     - 14:45
     - 6
     - §3
     - Correlation matrix
     - Drop the Spearman comparison (−4)
   * - 4
     - 14:51
     - 9
     - §4
     - Analyte grid, ratios, ratio map
     - Drop the second ratio (−4). Can finish after coffee
   * - —
     - 15:00
     - *15*
     - —
     - **Coffee** — fixed, catered, cannot slide
     - Not yours to move, and you should not want to
   * - 5
     - 15:15
     - 9
     - §5
     - Reference, then Eu\* in the Calculator
     - Demo rather than hands-on (−6)
   * - 6
     - 15:24
     - 14
     - §6
     - Scatter → heatmap → ternary → ternary map
     - Drop the heatmap tour (−6), then the scatter (−4)
   * - 7
     - 15:38
     - 12
     - §8
     - PCA: variance, basis vectors, score maps
     - Drop ``dimension scatter`` (−4)
   * - 8
     - 15:50
     - **22**
     - §9
     - k-means, fuzzy c-means, PCA preconditioning
     - Drop fuzzy c-means (−8). Never drop the PCA comparison
   * - 9
     - 16:12
     - 12
     - §10
     - Name clusters, cluster mask, replot the ternary
     - Nothing. Block 10 needs the region this creates
   * - 10
     - 16:24
     - **20**
     - §11
     - Stoichiometry; missing-Si lesson; ``Grt_Z`` on the whiteboard
     - Demo rather than hands-on (−8). Keep the two numbers
   * - 11
     - 16:44
     - **13**
     - §14
     - **Notes** — record, capture figures, Formatted Info
     - Two info blocks instead of four (−3). Protect the rest
   * - 12
     - 16:57
     - 3
     - —
     - Where the docs are; what you did not reach; close
     - Never cut

Contact time: 165 minutes — **60 before coffee (15 of them the install), 105 after**.
Break: 15. Total 14:00–17:00.

.. caution::

   **Three things about this slot specifically.**

   **The install is inside the session.** You have 5 sticks for 11 people, which is two
   or three per stick and genuinely quick — but the Windows unzip is 436 MB expanding to
   924 MB with Defender watching, and that is slow and silent. Block 0 tells you what
   each person actually needs to copy, which is about a third of the stick.

   **The break at 15:00 is only an hour in, and that is lucky.** It leaves a single
   unbroken 105-minute run for the entire spine. Do not try to move it later even if you
   could — a break at 15:45 would fall between clustering and stoichiometry, which is
   the one seam in the afternoon you cannot afford to open.

   **There is no buffer after 14:15.** Block 0 is the only slack, so every minute the
   install does not use is a minute you keep. If all eleven machines are running by
   14:10, start block 1 early.

.. important::

   **The single highest-value thing you can do before tomorrow is remove the install
   from the session.** Email the release link tonight with the Gatekeeper and SmartScreen
   steps spelled out, and ask people to install before they arrive. If even half of them
   do, block 0 shrinks to a few minutes of data copying and you get the TEC plot and a
   live TR1-07 back. Nothing else available to you tonight buys ten minutes.

Why the order is what it is
===========================

Worth knowing, because someone will ask.

**Dependency.** The sample must exist before fields can. Fields must exist before a plot
can use them. PCA scores must exist before clustering can precondition on them. Clusters
must exist before there is anything to mask with, or to scope stoichiometry to, or for
the *Cluster results* note block to insert. Import → fields → plots → reduce → cluster →
scope → formulae → report is the only order that never asks anyone to accept something
on faith.

**The import goes first.** Block 1 is an import, which means the riskiest twenty-two
minutes of the afternoon are also the first twenty-two after the install. That is a
deliberate trade: the import is what attendees cannot learn from the documentation,
their own data is sitting on their own laptops, and a room that has successfully
imported something believes the rest. The mitigation is the ``.lame.csv`` fallback — see
`Fallbacks`_ — not a reordering.

**Risk is spread, not stacked.** The two blocks most likely to behave unexpectedly are
the import at 14:15 and stoichiometry at 16:24 — the first and the second-to-last. The
import has an explicit fallback; stoichiometry runs after everyone has saved their
project three times. Neither can take the afternoon down with it.

**The break lands where it does least harm.** Coffee is fixed at 15:00, an hour in, and
that is awkward on paper — it splits the afternoon 60/105 rather than down the middle,
and it interrupts §4 rather than falling cleanly between sections. Take it anyway.

What it buys is a **single unbroken 105-minute run** that holds the entire spine: PCA,
clustering, masking, mineral formulae, notes. That matters for one specific reason —
the **PCA** tick box on the clustering page falls back to raw analytes silently if no
scores exist, so a coffee break between computing the scores and using them is exactly
how someone ends up comparing a PCA clustering against itself. A later break would fall
between clustering and stoichiometry, which is worse still: the ROI created in block 9
is what block 10 scopes itself to, and fifteen minutes is long enough for someone to
come back and start clicking elsewhere.

**Quarantine.** The unfinished features are named where they arise and collected in the
handout's limitations table, but no block in the timetable depends on one. Everything
purely demonstrative — the workflow designer most of all — has been moved out of the
timetable entirely and into `Overflow blocks — if you are ahead`_.


Room setup
==========

**Tomorrow, T-45 — presentation machine**

* Mirror displays, do not extend — you will lose track of which screen has the dialog.
* Set the LaME window to the size your checkpoint screenshots were taken at.
* Styling Toolbox → **Text and Scales** → raise **Font size**. Check legibility from the
  back row, not from your chair.
* Disable notifications, sleep and auto-update. Plug in power.
* **Import RM01 once and draw every plot type once.** This warms the lazy imports and
  matplotlib's first-figure cost so nothing stalls on stage. Then close the project and
  do the import again for real in block 1 — the second one is fast.
* **Only if you expect to reach the workflow overflow block:** have one already built
  in a second window. Building it live costs all four of its minutes.

**Tomorrow, T-20 — room**

* **The five sticks at the door, not at the front.** Hand them out as people arrive so
  copying starts before 14:00. Two or three people per stick.
* **Write the three import numbers on the whiteboard before anyone sits down** — spot
  16, sweep 0.279, speed 23.66. They need to be up for block 1 and they stay up all
  afternoon.
* Write ``SECTION: 1`` below them. Update it at every block boundary.
* Triage sheet out. Record every problem; do not fix them silently.
* **Know which attendees are on Windows.** Their unzip is the slowest step of block 0
  and it gives no progress indication worth watching. Ask as they come in.


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

.. important::

   **Gate one: ``RM01.lame.csv`` must be on the stick, beside the ``RM01/`` directory.**
   It is the only safety net block 1 has, and block 1 is an import — the riskiest
   twenty-two minutes of the afternoon, running before anyone has saved anything.

   It is on the stick as of the last check (95,676 px, 476 × 201, 28 analytes, identical
   to what the import produces). Open it once on the clean machine anyway — and confirm
   it is on **all five** sticks. Without it, anyone whose import does not work is locked
   out of everything from block 2 onward.

.. danger::

   **The workshop is tomorrow afternoon, so this checklist is tonight's work, not the
   morning's.** Items 1, 2 and 6 are the ones that can still change what you hand out;
   do those first, while there is time to re-cut a build or re-copy a stick.

   **And do item 3 first of all** — emailing the installer link tonight is the single
   highest-return action available to you, because it is the only thing that can give
   block 0's fifteen minutes back.

**Tonight**

#. **Confirm the Qt runtime is ≥ 6.11.2** (gate zero). Nothing below is worth checking
   until this passes.
#. **Open ``RM01.lame.csv`` from the stick** (gate one) and confirm 95,676 pixels.
#. **Email the release link to all eleven attendees tonight**, with the Gatekeeper and
   SmartScreen steps spelled out and a line saying *"please install before you arrive;
   it will save us fifteen minutes."* Even half of them doing it buys back the TEC plot
   and a live TR1-07.
#. Install following the attendee instructions **verbatim**, Gatekeeper and SmartScreen
   steps included. Use none of the shortcuts you know.
#. Launch. Note the cold-start time — say that number in your opening remarks so nobody
   thinks it has hung.
#. **Rehearse block 1 end to end on the clean machine.** Import
   ``data/LA-ICP-MS/RM01/`` with spot 16, sweep 0.279, speed 23.66. Confirm dX reads
   16 and dY reads 6.6 before you click Import, and confirm the loaded sample is
   **476 × 201 = 95,676 px with axes to ~3140 × 3220 µm**. Time it. This is the number
   you will quote when someone asks how long to wait.
#. **Save the project straight after that import and check what appears on disk** — the
   manifest, the notes file, and ``figures/``/``data/`` once you export a plot. Then
   leave it running past the autosave interval (ten minutes by default) and confirm the
   manifest's timestamp moves. The save step at the end of block 1 is the foundation of
   every later recovery, so verify it rather than assuming it.
#. **Rehearse the XRF import too**, in case you reach the overflow block: ``XRF`` / ``image`` on
   ``data/XRF/core 7/``, spot size 1, import ``row1``. It is a demo, so it has to work
   on *your* machine specifically.
#. Confirm the Stoichiometry **Mineral** dropdown is populated and not red. If it is
   empty, the mineral-config path fix did not make the build — block 10 cannot be
   hands-on and must become a demo on your machine.
#. Time one **scoped** stoichiometry run on RM01 and on TR1-07. Write the numbers down.
#. **Write down both ``Grt_Z`` values** — RM01's and TR1-07's. Block 10 closes on those
   two numbers from the whiteboard, and in this timetable you will not have time to
   compute TR1-07's live.
#. Set the reference to ``CI chondrite [AG89]`` and confirm **Eu\*** recomputes, and
   that the ``TEC`` plot draws with the ``REE`` preset.
#. Switch between all samples, including after a cluster mask is active. Blocks 10 and
   11 depend on this being clean, and so does the TR1-07 overflow block.
#. **Click every hazard once and write down the literal message** — see
   `Do not do these on the projector`_. You will be asked about at least one, and
   knowing the exact wording is the difference between authority and hand-waving.
#. Confirm **Help** opens a built page, and that the context-sensitive **Help** toggle
   jumps to the right page. Block 12 is three minutes long and entirely about this.
#. **Scan the survey QR with your own phone** and confirm it opens the form. It goes up
   on the projector at the close, and a QR nobody can scan is worse than no QR at all.
#. ``python main.py --selftest`` on each machine you will use.


Block 0 — Arrival, install and welcome (14:00, 15 min)
======================================================

*Not in the handout. Fifteen minutes you do not have but cannot avoid — so talk through
it rather than waiting it out.*

**The logistics, with 11 attendees and 5 sticks.** Two or three people per stick, in
parallel. Hand the sticks out at the door, not from the front.

What each person actually needs to start is **one installer plus about 90 MB of data**:

.. list-table::
   :header-rows: 1
   :widths: 34 16 50

   * - From the stick
     - Size
     - Needed
   * - ``program/LaME-macos-arm64.dmg`` **or** ``program/LaME-windows-x64.zip``
     - ~450 MB
     - One of the two. **Nobody needs both.** Say this out loud — it halves the copy.
   * - ``data/LA-ICP-MS/RM01/``
     - ~48 MB
     - Block 1 imports it
   * - ``data/LA-ICP-MS/RM01.lame.csv``
     - ~43 MB
     - The fallback if the import fails
   * - Everything else
     - ~550 MB
     - **Not today.** Copy it over coffee or at the end

**Tell them to copy the whole folder anyway if the stick is free** — they want the rest
for the take-home sections. But the critical path is the three rows above, and anyone
still copying the XRF data at 14:12 should stop and resume at coffee.

**Talk while they copy.** This block is the welcome, and none of it needs a screen:



* What LaME is for, in one sentence: element maps in, interpretation out.
* The four parts: one garnet end to end, two more garnets, a pyrite, a core scan.
* **It is beta.** Say this now, plainly, once. "You will see things that do not work.
  They are marked in your handout, and I will tell you what you would see. That is
  deliberate — I would rather you spend the afternoon on what works."
* The cold-start time you measured. "First launch takes about N seconds. It is
  unpacking, not hung."
* **Questions whenever.** Mean it. The timetable has slack for this and the handout
  says so.
* **The handout is bigger than the afternoon, on purpose.** Seventeen sections; we will
  not do all of them together; the rest is written to work through alone. Say it here,
  in one sentence — see the box at the top of this script for why it matters.

**Do not** demonstrate anything yet. The first thing anyone sees working should be on
their own screen, not yours.

**Watch for the Windows unzip.** 436 MB expands to about 924 MB and Defender scans it on
the way out. It is the slowest single step of the arrival and it is silent — check on
the Windows users specifically at the ten-minute mark.

**This block is also the afternoon's only buffer.** If everyone is running by 14:10,
start block 1 early and bank the five minutes; the first thing to spend them on is the
TEC plot, which is the top item in `Overflow blocks — if you are ahead`_.


Block 1 — Import RM01 (14:15, 22 min)
=====================================

*Handout §1. The highest-risk and highest-value block of the day.*

**The teaching point, and say it before they start:** the files contain no statement of
how big a pixel is. Everything else they will do today is downstream of three numbers
they type here.

**Drive it on the projector first, then let them do it.** This is the one block worth
doing twice. Twenty-two minutes is enough for a five-minute demonstration, a fourteen-minute
attempt and three minutes of recovery.

Numbers to put on the whiteboard, large, and leave there all afternoon:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Field
     - Value
     - Becomes
   * - Spot size (µm)
     - ``16``
     - dX = 16
   * - Sweep (s)
     - ``0.279``
     - —
   * - Speed (µm/s)
     - ``23.66``
     - dY = speed × sweep = 6.6

**Say while the dialog is open:**

* ``LA-ICP-MS`` / ``quadrupole``, then **Open directory** on ``data/LA-ICP-MS/`` — the
  parent, not the ``RM01`` folder. People will choose ``RM01/`` and get nothing.
* The dX/dY columns are **computed and not editable**. "Watch them while I type. If
  those two numbers are not 16 and 6.6, do not click Import."
* 28 files, one analyte each, no header and no coordinates. Show **Select files** for
  ten seconds so they see the filename-to-analyte parse, then close it.

**What will go wrong, in order of likelihood:**

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Symptom
     - Cause and fix
   * - Axes run 0–476 and 0–201
     - The three geometry fields were left blank; dX = dY = 1. Re-import.
   * - Map is a thin sliver
     - ``Swap XY`` is ticked. Untick, re-import.
   * - Nothing found in the directory
     - They opened ``RM01/`` rather than ``data/LA-ICP-MS/``.
   * - dY reads 6.59 or 6.61
     - They typed ``23.6`` or ``23.7``. Harmless — do not stop for it.
   * - Import appears to do nothing
     - Check the sample selector; it may have worked and not switched.

**Finish the block with a save, and spend thirty seconds on why.** *Save Project*, to
the Desktop, their own name. Two reasons, both worth saying out loud because neither is
visible:

* **It arms the autosave.** LaME autosaves every ten minutes, but an untitled project
  goes to a scratch location and stays untitled. Once it has a name, autosave writes
  back to it. From this point on, the worst case for anybody in the room is losing ten
  minutes.
* **It creates the project folder** that the notes file, ``figures/`` and ``data/`` all
  live in. Block 11 needs it to exist.

This is also what makes level 1 of `Fallbacks`_ available for the rest of the day, so it
is thirty seconds that buys back every later recovery.

**Hard stop at 14:37.** Anyone not loaded gets ``RM01.lame.csv`` and the triage sheet.
Do not debug an individual machine here — the whole room is waiting and the fallback
costs them nothing for the rest of the afternoon.

.. Figure placeholder PFIG-2  [presenter slide]
   WHAT: The three import numbers, large, on one slide: Spot size 16, Sweep 0.279,
   Speed 23.66, with an arrow to "dX 16 / dY 6.6 — check before importing".
   WHY: Leave it on screen for the whole block. It is the only thing they need to read.


Block 2 — Field maps (14:37, 8 min)
===================================

*Handout §2.*

**Say:** read the sample before analysing it. Ten minutes of stepping through elements
now saves an hour of plotting the wrong things later.

* Step the colour field through ``Mn55``, ``Ca43``, ``Fe57``, ``Mg24``, then ``Y89``.
* **Log scaling on Y89** is the moment to dwell on. Switch it linear and back. "Three
  orders of magnitude on a linear ramp is one colour."

**Hazard:** do not touch ``gradient map``, directly below ``field map`` on the
Preprocess page.

**Cut if behind:** step through three elements instead of six (−3). Keep the log-scaling
moment — it is the one thing in this block nobody works out for themselves.


Block 3 — Correlations (14:45, 6 min)
=====================================

*Handout §3.*

* ``correlation``. Pearson, then Spearman. Point at the REE block: "those twelve
  elements are telling you one thing, not twelve."

**This block justifies the next one.** Say so explicitly: the correlation matrix is why
you select analytes rather than clustering on everything, and why PCA helps after
coffee.

**Hazard:** mention from the handout that the correlation matrix ignores filters — say
it *now*, before anyone has a filter, so it does not later look like a discovery.

**Cut if behind:** the Spearman comparison (−4).


Block 4 — Analytes and ratios (14:51, 9 min)
============================================

*Handout §4.*

**The analyte grid is the block's hard part.** Diagonal = analyte, off-diagonal = ratio,
above versus below the diagonal inverts the ratio. Draw it on the whiteboard rather than
describing it. Everyone gets the inverted ratio wrong once.

* The eight analytes from the handout, then ``Y89 / Mn55``, then ``Mg24 / Fe57``.
* Note aloud that the grid's background colours are the correlation matrix they just
  looked at. It lands well and costs ten seconds.
* Map the ``Mg24 / Fe57`` ratio. "A boundary neither element shows on its own."

**Save again** at the end — it overwrites block 1's save with no dialog. Then say the
rule that makes the rest of the afternoon survivable: *if your screen stops matching
mine, reopen your own save rather than debugging.*

**Cut if behind:** the second ratio (−4). This block is the one that runs into coffee,
so finishing it is less important than starting it — the ratio map can wait until 15:15.


Coffee (15:00, 15 min)
======================

**Fixed at 15:00. Catered. It cannot slide.**

An hour in is early for a break, and in a three-hour session you might be tempted to
push it later. **Do not** — and not only because it is catered. Taking it at 15:00
leaves a single unbroken 105-minute run from 15:15 to 17:00, and the whole spine of the
afternoon — PCA, clustering, masking, mineral formulae, notes — needs 100 of those
minutes with nothing interrupting it. A break at 15:45 would split clustering from
stoichiometry, which is the one seam in the day you cannot afford to open.

Use it to fix anyone you noticed struggling, and to let the people who skipped the
optional data finish copying it.

**With 11 people you can actually do this.** Walk all eleven screens in fifteen minutes
— that is 80 seconds each, which is enough to see whether someone has a ratio map on
screen or a blank canvas.


Block 5 — Reference and Eu* (15:15, 9 min)
==========================================

*Handout §5.*

**The reference first, and say why the order matters:** ``CI chondrite [AG89]`` *before*
the Calculator, because ``Eu*`` uses ``_N`` normalised fields. If they calculate first
they get a number computed against bulk silicate Earth and nothing warns them.

* Calculator → saved formula ``Eu*`` → **Calculate** → plot from the ``Calculated``
  field type.
* Show the formula and the ``{FieldType.Field}`` syntax. One sentence. Resist the
  temptation to teach the Calculator properly; there is no time and it is in the docs.

**Hazard:** ``case()`` and ``otw()`` on the keypad. Do not click them. If asked, the
message is *"could not evaluate conditional statement"* — and tell them the Calculator
documentation's ``case()`` section describes syntax that has never existed.

**Cut if behind:** demonstrate it on the projector rather than hands-on (−6). It is a
Calculator feature, not a concept they need in their fingers.


Block 6 — Ternary and ternary map (15:24, 14 min)
=================================================

*Handout §6.*

* ``scatter``, Fe–Mn coloured by Ca. Then ``heatmap``, same axes. "95,000 points is a
  solid block; binning is not a cosmetic choice."
* Then fill **Z** with ``Mg24``. "There is no ternary plot type. A ternary is a scatter
  with a Z."
* Then ``ternary map``. **This is the best plot in LaME** — say that. Three elements,
  one map, no decision about which matters most.

**Say:** we come back to this one in block 9 with clusters as the colour. Flag it so the
repetition later reads as payoff rather than as filler.

**Hazard:** the ternary map ignores filters and masks, same as correlation. Nobody has
one yet, which is why this is the moment to say it.

**Cut if behind:** the heatmap statistic tour (−6), then the scatter, going straight from
the field maps to the ternary (−4).


Block 7 — PCA (15:38, 12 min)
=============================

*Handout §8.*

Four plot types in fourteen minutes. Name each one as you go; they will not remember
which plot gives what.

* ``variance`` — the scree plot. **Have them write the number down** where it flattens.
  They need it in block 8 and again if they redo anything.
* ``basis vectors`` — what the components are made of. "Here is the REE block from block
  3, quantified."
* ``dimension score map`` — and this is the one to dwell on. PCA has no idea these
  numbers came from a map. When PC1's score map comes out looking like growth zoning,
  that is the data saying the chemistry and the geometry are the same phenomenon.

**Cut if behind:** ``dimension scatter`` (−4). Keep variance and the score maps —
variance because block 8 needs its number, score maps because they are the block's one
genuinely surprising moment.


Block 8 — Clustering (15:50, 22 min)
====================================

*Handout §9. The most transferable skill of the day.*

* ``k-means``, 4 clusters, ``cluster map``.
* **Randomize the seed three times** and let the room watch. "If your zones survive
  several seeds they are real. If they reshuffle, they were not there." This is thirty
  seconds and it is the most important thing you will say about clustering.
* ``cluster performance`` once, to show there is an objective handle on *k*.
* ``fuzzy c-means`` next, then ``cluster score map`` — the membership as a continuous
  field. "k-means had to choose. This shows you how hard the boundary actually is."
* **Then the PCA comparison, which is the block's real content.** Dimensional Reduction
  once so scores exist, back to Clustering, tick **PCA**, set the basis count from block
  6, re-cluster.

  Say it plainly: PCA before clustering is usually presented as tidying. It is not
  neutral — it decides what variation the clustering is allowed to see. The honest move
  is to run it both ways, and it costs two minutes.

.. important::

   **The PCA tick box fails silently if no scores exist.** It falls back to raw analytes
   with no warning. If someone's "PCA clustering" looks identical to their raw
   clustering, this is why. Say it before they tick the box, not after.

**Hazards:** the **Distance** combobox does nothing — do not touch it on the projector,
it recomputes and returns an identical result and looks like you do not know your own
application. ``HDBSCAN`` + ``cluster performance`` silently does nothing.

**Cut if behind:** fuzzy c-means and the score map (−8). **Never** cut the PCA
comparison; it is the block.

**This is the longest block of the afternoon and it sits in the middle of a 105-minute
unbroken run.** If the room looks tired at 16:05, take a three-minute stretch here
rather than at the start of block 9 — the natural pause is after the seed-randomising,
before the PCA comparison.


Block 9 — Clusters as a filter (16:12, 12 min)
==============================================

*Handout §10.*

* Clusters tab → **rename them** — ``core``, ``mantle``, ``rim``, ``matrix``. Insist on
  this. The names propagate into every legend, the Notes report and the stoichiometry
  scope list, and "cluster 3" in a methods paragraph is worthless.
* **Create Cluster Mask** on the garnet clusters.
* **Create Region** on one cluster. Say loudly that block 10 cannot run without this.
* Then back to the ternary from block 6 with **Color** = ``Cluster``.

**This is the compounding block.** Say so: two plots they already know, now carrying
grouped information, in three clicks, because the clusters exist. One REE pattern per
zone is a figure a paper would carry.

**The TEC replot is not in this version of the timetable** — the TEC plot itself moved to
the overflow. If you did find time for it before coffee, add it back here: one REE
pattern per cluster is the best figure of the day.

**Cut if behind:** nothing. This block is already the minimum, and block 10 cannot start
without the region it creates.


Block 10 — Stoichiometry (16:24, 20 min)
========================================

*Handout §11. Never cut this.*

.. important::

   **Scope it first, in front of them, and say why.** The calculation runs pixel by pixel
   on the interface thread and re-runs on every settings change. Unscoped on 95,676
   pixels that is minutes of frozen window, several times over. Quote the time you
   measured at T-90.

* **Compute scope** first: the ROI from block 9, and tick **only** that region.
* Settings: ``Garnet``, ``ppm``, ``droop_1987``, BDL ``zero``. **Compare all redox
  methods off** — it triples the work.
* **Run.** Then ``Grt_dominant`` as a field map, with its swatch legend.

**Then the lesson, which is the point of using RM01 as the primary sample:** look at
``Grt_Z``. It should be 3.0, filled by Si. RM01 has no Si, so LaME filled the
tetrahedral site with Al and the end-member percentages are wrong.

Say the general version, slowly, because it is the most useful thing in the workshop:
**a missing major element does not produce an error. It produces a plausible-looking
answer that is incorrect.** Site totals are the sanity check, and they are the reason to
look at ``Grt_Z`` before quoting any end-member proportion.

**Hazard:** if the **Mineral** dropdown is empty and red, the build cannot find its
mineral configs. You will know this from T-90, not from here. If it happens anyway, this
block becomes a demonstration on your machine.

Close the loop with TR1-07, from the whiteboard
-----------------------------------------------

The block cannot end on *"and this answer is wrong"* — that is a cliffhanger, not a
lesson. The resolution is TR1-07, which has Si, and in this timetable there is no time to
switch samples and redo the whole sequence.

**So do it in ninety seconds with two numbers you measured last night.** Write RM01's
``Grt_Z`` beside TR1-07's on the whiteboard, say that the only difference between them is
that one sample measured silicon, and point at handout §13 for the steps. That is the
entire payoff, and it does not need a live run.

**Cut if behind:** run the calculation on the projector rather than hands-on (−8). The
lesson survives a demonstration; the block does not survive being dropped. Never cut the
two whiteboard numbers — they cost ninety seconds and they are the point of having used
RM01 all afternoon.


Block 11 — Notes (16:44, 13 min)
================================

*Handout §14. The last hands-on block of the day.*

**Say first, in one sentence:** *"Before we finish, let us write down what we just
found."* Thirteen minutes is enough for the recorder and four Formatted Info blocks, and
not much else.

* **Log** → **Notes** opens the reST Editor on a file inside their project — the folder
  they created by saving in block 1.
* **Record** on, then make two plots. They are captured automatically into ``figures/``
  beside the notes file.
* **Insert → Formatted Info** → *Sample info*, *List analytes used*, *Cluster results*,
  *Stoichiometry results*.

**Say:** this is the methods paragraph of a paper, assembled from what you actually did
rather than what you remember doing in six months. And the cluster names you set in
block 9 are why it reads as prose rather than as ``Cluster 3``.

Point at the handout's reStructuredText appendix rather than teaching the syntax. One
sentence about it: the notes are plain text you own, and ``reST Editor.app`` on the stick
opens them without LaME.

.. important::

   **This is the last hands-on block of the day, and it is the one they take home.**
   Protect its thirteen minutes. If you are behind at 16:44, take the time out of block
   10's whiteboard close rather than out of this — a methods record they wrote
   themselves outlasts everything else they did this afternoon.

**Cut if behind:** the hand-written heading and caption (−4), and insert two Formatted
Info blocks instead of four (−3). Keep *Cluster results* and *Stoichiometry results* —
they are the two that contain the afternoon's actual findings.


Block 12 — Documentation and close (16:57, 3 min)
=================================================

*Never cut. Three minutes, three things — and start the survey first so it is
collecting while you talk.*

#. **The context-sensitive help toggle.** Toggle **Help** in the toolbar, click
   something, land on its documentation page. Almost nobody discovers this
   independently, and it is the single most useful thing they can take away for working
   alone. Do it live — it takes fifteen seconds.
#. **The survey, up on the projector, first.** The QR is in the handout under *Tell us
   what you thought*, and the image itself is
   ``docs/source/_static/workshop_survey_qr.png`` if you want it full-screen. Put it up
   and leave it there for the whole three minutes — responses you collect in the room
   are worth several times what emailing the link afterwards gets you, because nobody
   fills in a workshop survey on Friday.
#. **Help → Report Bug.** What you want: what they were doing, what they expected, what
   happened. Say that everything in the handout's limitations table is already known, so
   anything else is genuinely new information.

**Name what you did not reach** — usually §15 pyrite and §16–17 the XRF core — and say
that those sections are complete, the data is on the stick, and nothing in them depends
on having been here.

**Close with the offer:** send raw data and get a ``.lame.csv`` back. It is the thing
most likely to turn an attendee into a user.


Overflow blocks — if you are ahead
==================================

These are **not in the timetable**. A three-hour session with an installation in it does
not contain them, and the handout tells attendees so in *How to read this handout*.

**Where the time would come from.** The arrival block is the only slack in the afternoon.
If all eleven machines are running by 14:10 you have five minutes; if people arrive
pre-installed because you emailed the installer the night before, you have closer to
twelve.

**Spend it in this order:**

#. **The TEC plot (§7), 8 minutes.** Top of the list, and the cheapest. It is the REE
   diagram petrologists actually publish, the Eu notch ties back to the Eu\* they
   calculated in block 5, and it gives block 9 a second plot to recolour by cluster. If
   you recover any time at all, spend it here.
#. **TR1-07 live (§13), 8 minutes.** Turns block 10's whiteboard close into a real
   demonstration.
#. **The workflow designer (§12), 4 minutes.** A look-ahead, nothing more.
#. **Pyrite (§15), 16 minutes.** Needs more time than this afternoon will ever recover,
   but it is the best block in the handout for working through alone — it is already
   written as *"your turn"* with fewer numbered steps.
#. **The XRF core scan (§16–17).** Entirely self-contained. Say its name in block 12 and
   leave it with them.

**Do not add material that is not in the handout.** Attendees cannot take notes on what
they cannot read later, and with three hours the handout is already doing most of the
teaching.


Overflow — TEC and radar (8 min)
================================

*Handout §7. Eight minutes. The first thing to add back if you recover time.*

* n-Dimensional page, ``TEC``, ``REE`` preset.
* Check the **Ref.** row still reads ``CI chondrite [AG89]`` — the plot is normalised, so
  the reference is doing real work.
* Point at the Eu notch and connect it back to the Eu\* from block 5.
* ``radar`` for ten seconds, so they know it exists and that it is the same data.

**If you get this far, also add the TEC replot to block 9** — **Color** field type
``Cluster`` gives one chondrite-normalised REE pattern per zone, on one plot, in three
clicks. It is the best single figure the afternoon can produce.


Overflow — Workflow designer (4 min)
====================================

*Handout §12. Demonstration only.*

Open the workflow you built at T-45. Do not build one live.

**Say:** this is the afternoon's analysis as a diagram you can save, share and re-run on
the next sample. The block vocabulary is the Control Toolbox vocabulary, so the diagram
reads as a record of the method.

**Then be straight about the state of it:** constructing works, running is not reliable
enough to put twenty people through, and **Capture** currently records only sample
changes. Point at the handout's limitations row rather than elaborating.

**Not in the timetable.** Four minutes, no hands-on, nothing downstream depends on it.


Overflow — TR1-07, live (8 min)
===============================

*Handout §13. Not in the timetable — block 10 closes the Si loop from the whiteboard
instead. This is what you do if you have eight minutes to do it properly.*

Switch sample on your machine and narrate four steps at pace: select analytes → cluster →
cluster mask and region → stoichiometry scoped to it.

**And now ``Grt_Z`` is near 3.0**, because TR1-07 has Si. **Put the two numbers side by
side on the whiteboard.** That contrast is the whole garnet thread of the afternoon, and
it is the resolution of the "this answer is wrong" that block 10 ended on. Do not skip it
— without it the stoichiometry block closes on a failure.

Flag the trap even though they are not doing it themselves: **the isotope names are
different.** ``Fe56``, ``Ti47``, ``Cr52``, not RM01's ``Fe57``, ``Ti49``, ``Cr53``.
Field selections do not carry across samples. Everyone hits this the first time they try
it alone, so it is worth thirty seconds now.

**Do not start WOS-02.** It is in the handout as optional and it will not happen.

**Cut if behind:** skip the demonstration entirely and just put the two ``Grt_Z`` numbers
on the whiteboard with one sentence (−5). The lesson survives; the clicking does not
matter.


Overflow — Pyrite (16 min)
==========================

*Handout §15. Attendee-driven.*

**Set up and get out of the way.** Two sentences, then let them work:

* Uncalibrated — CPS, not ppm. Maps, filters, clusters, biplots all fine. Mineral
  formulae and normalisation are not.
* The question: *does PCA preconditioning change the clustering, and is the pyrite
  uniform inside itself?*

**Walk the room.** Do not present. This is the block where they discover they can drive
it themselves, and narration from the front undermines that.

**Two things to have ready when asked:**

* The Fe–Cu biplot is the interesting one. Fe is the framework and barely varies; Cu
  does not substitute into pyrite, so where it appears it is something else — an
  inclusion, an overprint, a later generation.
* **Co and Ni do not separate the two pyrite clusters.** Several people will read this
  as having done it wrong. It is a real result: a few hundred thousand counts inside the
  sulfide against a few thousand outside, and essentially no difference between the two
  sulfide groups. The groups differ in ``Cu65`` and ``As75``. Have that answer ready —
  it is the best teaching moment in the block.

**Stop on your deadline, whatever state the room is in.** Do not let this block eat the
close; it is the one block whose value does not depend on finishing.

**Cut if behind:** set one question instead of two (−6). Drop the "is it uniform
inside" half and keep the PCA comparison.


Overflow — XRF core scan (9 min)
================================

*Handout §16–17. Demonstration only, and only if the time exists.*

Nine minutes, on your machine, no hands-on. Say that up front and say why: the handout
is complete, the data is on the stick, and they can work through it afterwards. If you
arrive here with twenty minutes rather than nine, make it hands-on instead — the import
is the part worth doing with their own hands.

**Four beats, roughly two minutes each:**

#. **The import.** ``XRF`` / ``image``, ``data/XRF/core 7/``, spot size 1. Five rows,
   26 PNGs each. "One image per element — the scanner's software exports pictures, and
   LaME reads brightness as relative intensity."
#. **What you have, and do not have.** Intensity, not concentration. And **each channel
   was scaled independently** before it became an 8-bit PNG, so Fe-here against
   Fe-there is valid and Fe against Ca is not.
#. **The Rh moment.** Show the mean intensities: ``Re`` and ``Rh`` are the two
   *brightest* channels in the scan, brighter than Fe in a rock. "That is not rhenium —
   those are tube anode materials, and what you are seeing is the X-ray source scattered
   off the sample." It is the best thirty seconds in the block. Check what your own
   instrument's tube is made of before interpreting any of them.
#. **The cluster map against the core photograph.** Cluster ``row1`` on the channels
   that carry signal, then put ``core7_Video Mosaic.png`` beside it. Chemistry
   recovering structure that is independently visible in a photograph is the most
   persuasive thing in Part IV.

**Mention in one sentence, do not demonstrate:** ROIs, polygons and crop are three more
ways to restrict a map, all covered in the handout, and crop is the one that makes a
long core strip manageable.

**Cut to 4 minutes if needed:** import one row, show the cluster map against the
photograph, stop. Beats 2 and 3 become one sentence each.


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
   * - Running a workflow
     - Unreliable. Build one, do not run one
   * - Data types other than LA-ICP-MS and XRF/image
     - Metadata table fills, then *"Not implemented"*

**Crop and Full Map are off this list.** They were broken in the previous build and are
fixed in this one — crop applies on a double-click inside the box or on Enter, and Full
Map restores the whole sample. The XRF overflow block mentions crop deliberately.
Rehearse it once tonight anyway.


Fallbacks
=========

**There are no checkpoint project files this time.** The previous version of this
workshop shipped four ``.lame_project.json`` files; this one does not, because the data
layout changed and stale project files are worse than none. Recovery has three levels
instead:

.. list-table::
   :header-rows: 1
   :widths: 10 34 56

   * - Level
     - Route
     - Covers
   * - 1
     - **Their own last save**, or the autosave. §1 ends with a save and every later
       section begins with one.
     - Anything after block 2. By far the most common case.
   * - 2
     - **The converted ``.lame.csv``** beside each directory we import.
     - A failed import — block 2, or the XRF overflow block. See gate one in the
       pre-flight.
   * - 3
     - **A two-click rebuild.** Most later blocks need *a* cluster or *an* ROI, not a
       particular one.
     - Blocks 8–12, where re-clustering from scratch takes under a minute.

.. caution::

   **Know the gap.** Level 1 does not exist until the save at the end of block 2,
   because until then there is nothing saved and autosave has nowhere of its own to
   write. For those eighteen minutes your only fallback is ``RM01.lame.csv``, which is
   why gate one is where it is in the pre-flight checklist.

.. important::

   **Never debug a lost attendee during contact time.** Hand them the fallback, write
   the symptom on the triage sheet, move on. One person's problem costs everyone else
   their attention. This is the rule that makes a hands-on workshop survivable, and it
   is the hardest one to keep.


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
* **The survey link**, to whoever did not scan it in the room. One reminder, same day —
  after that the response rate does not move.
* **A note naming the sections you did not reach**, and saying that they are complete and
  the data is on the stick. In a three-hour session that is usually §7, §12, §13 and
  §15–17. This is the difference between an unfinished workshop and a handout with
  homework in it.
* **A pointer to §15, pyrite, as the place to start.** It is written as an exercise
  rather than a walkthrough, so it is the section that works best unsupervised.

**File as issues**, from the triage sheet:

* Every symptom that is not already in the handout's limitations table.
* **Every import failure, with the directory and the numbers they typed.** Block 2 is
  the first unsupervised use of the new import path by people who did not write it, and
  that is information you cannot get any other way.
* Install failures by OS and chip. Intel Mac demand in particular — there is no build
  for it, and the count from today is the evidence for whether that matters.

**Fix list this workshop will have earned:**

* Make the dX/dY columns editable, or let a user enter pixel spacing directly. Working
  backwards from spot size, sweep and speed to a known pixel pitch is the wrong way
  round for anyone importing data they did not acquire themselves.
* Warn on import when the derived pixel spacing is 1 — it means the geometry fields were
  left blank, which is the single most likely import mistake and it is silent.
* Stoichiometry off the interface thread, with a progress indicator.
* A warning when a mineral's site-defining element is absent from the data — the RM01
  lesson, turned into something the software says itself.
* Remove or implement ``gradient map``, ``profile`` and ``polygon`` plot types; they are
  selectable and do nothing.
* Correct the Calculator documentation's ``case()`` section.
* Make the cluster **Distance** combobox work or remove it.
* Make clustering respect polygons, or say why it does not in the interface rather than
  only in the documentation.
* Keep the Qt runtime pinned. A GUI toolkit is not a dependency to float.
