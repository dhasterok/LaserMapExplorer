Lower Tabs
**********

The Lower Tabs provide additional functionality for note-taking and profile visualization, enhancing your analysis workflow。

.. figure:: _static/screenshots/LaME_Lower_Tab.png
    :align: center
    :alt: LaME interface: lower tab
    :width: 600

    The Lower Tabs section of the *LaME* interface, providing access to Notes and Profiles features.


Notes Tab
=========

The Notes tab allows you to take and store notes on a sample, keeping them alongside your analysis files. This integrated note-taking capability is one of LaME's novel features, enabling rapid production of report-style documentation for your samples or analyses.

The Notes tab is a powerful tool for documenting observations and analyses directly within *LaME*. This integrated note-taking capability allows users to store notes on a sample alongside their analysis files. It enables the rapid production of report-style documentation for samples or analyses. The Notes tab supports reStructured Text (reST) formatting, providing a flexible and powerful way to create well-structured notes and allows user to export the note as PDF documents. 

Intro to reStructured Text (reST)
---------------------------------
reST is a simple yet powerful markup language. Here are some basic formatting options:

==========================  =====================
Text                        Result
==========================  =====================
``*italics*``               *italics*
``**bold**``                **bold**
``reference_``              reference_
``[1]_``                    [1]_ footnote
``[Citation2024]_``         [Citation2024]_
==========================  =====================

.. [1] ``.. [1]`` will create a footnote

``.. _reference: http://www.this-is-an-external-hyperlink.org``

To use a phrase as a reference, enclose the words within backticks (`) and end with an underscore (_).

.. [Citation2024] ``.. [Citation2024]`` will produce a journal-like citation (no spaces).

To display a special character, use a '\\'

Titles, sections, and subsections can be created by including a line of \*, \=, and \- characters, the same length as the heading text. Use the |icon-heading| button to quickly add these symbols.

Filters Tab
===========

Profiles Tab
=============

The Profiles tab allows for the visualization of data trends across specific sections of a sample.  Users can create and view profile plots to analyze how various parameters change along a particular path or cross-section of their sample.  For detailed information on how to create profiles, please refer to the :doc:`left_toolbox` section.

.. |icon-heading| image:: _static/icons/icon-heading-64.png
    :height: 2ex

Plot Info Tab
=============

Workflow Tab
============

Help Tab
========

The help tab includes an integrated web browser that allows you to navigate and search *LaME*'s documentation.