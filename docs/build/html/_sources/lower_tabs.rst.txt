Lower Tabs
**********

Notes
=====

The Notes tab allows you to take notes on a sample and keep them with the files. Notes are automatically saved every 5 minutes and when the sample is changed or the program is closed.  The saved file is stored in the same directory as the sample file with the extension *\*.rst*.  While in plain text, the notes can be compiled into a pdf or html.  The specific formatting language is called `reStructured Text`_ (*reST*).  This format was chosen due to its basic formatting that can be easily read without compiling and yet produces a clean, easy to read document with figures and tables.  In fact, this documentation is compiled from *reST*.  

A simple guide to *reST* is provided below and more complete documentation can be found online with a greater range of formatting operations.  *LaME* also includes several formatting tools to quickly add formatted information and figures.

.. _reStructured Text: https://www.sphinx-doc.org/en/master/usage/restructuredtext/

Intro to *reST*
---------------

==========================  =====================
text                        result
==========================  =====================
``*italics*``               *italics*
``**bold**``                **bold**
``reference_``              reference_
``[1]_``                    [1]_ footnote
``[Citation2024]_``         [Citation2004]_
==========================  =====================

.. [1] ``.. [1]`` will create a footnote

``.. _reference: http://www.this-is-an-external-hyperlink.org``

To use a phrase, rather than a word, to make a reference, enclose the words within backticks (`) and end with an underscore (_).

``.. _reference: this is an internal hyperlink``

.. [Citation2004] ``.. [Citation2004]`` will produce a journal-like citation (no spaces).

To display a special character, use a '\\'

Titles, sections and subsections can be created by including a line of \*, \=, and \-, the same length as the heading text.  The |icon-heading| button can be used to add the symbols for you.  Simply put the cursor on the line to make a heading and click the |icon-heading| button.

Profiling
=========

Profile plots are displayed in the *Profiles* tab.

.. |icon-heading| image:: _static/icons/icon-heading-64.png
    :height: 2ex