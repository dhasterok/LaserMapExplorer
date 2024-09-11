Lower Tabs
**********

The Lower Tabs provide additional functionality for note-taking and profile visualization, enhancing your analysis workflow in LaME.

Notes
=====

The Notes tab allows you to take and store notes on a sample, keeping them alongside your analysis files. This integrated note-taking capability is one of LaME's novel features, enabling rapid production of report-style documentation for your samples or analyses.

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

``.. _reference: this is an internal hyperlink``

.. [Citation2024] ``.. [Citation2024]`` will produce a journal-like citation (no spaces).

To display a special character, use a '\\'

Titles, sections, and subsections can be created by including a line of \*, \=, and \- characters, the same length as the heading text. Use the |icon-heading| button to quickly add these symbols.

Profiling
=========

Profile plots are displayed in the Profiles tab of the Lower Tabs section. This feature allows you to visualize data trends across specific sections of your sample.

.. |icon-heading| image:: _static/icons/icon-heading-64.png
    :height: 2ex