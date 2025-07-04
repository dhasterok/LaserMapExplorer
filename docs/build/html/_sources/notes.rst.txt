Notes
*****

*LaME* incorporates note taking capabilities with tools for rapidly composing sample reports/supplmental information.  The file is auto saved as plain text (\*.rst) and reloaded when the sample is loaded.  Some tools are connected to the notes for quickly and easily formatting critical information/settings.

ReStructred Text (ReST)
=======================

The formatting tools take advantage of the ReStructred Text markup language.  ReST is a markup language used as a shorthand for producing html.  Within *LaME*, it is used to produce PDF reports, which can viewed using the PDF browser.  The notes toolbar contains a number of functions to quickly format test in ReST.  

Notes Toolbar
-------------

The toolbar functions can be used to add ReST markup elements to the text so that when compiled the text will appear properly formatted.  These can also be added manually ad described in the next section.  The toolbar also includes some functions to add preformatted information, saving the need for manual entry.

ReST Formatting Guide
---------------------

To write a paragraph in ReST, just typing starting from the left margin.  It is possible to add headings, bold and italicize the font, create formatted lists, tables, and add figures, citations, and links.  To add these some additional text markup is required.  As you'll see below, the markup elements quite simple. 

Headers
^^^^^^^
Headers are created by underlining text with specific characters. The length of the underline must match the text length:

.. table::
   :widths: 40 60

   ========================  =======================
   Syntax                    Description
   ========================  =======================
   ``********`` (asterisks)  Title header
   ``========`` (equals)     Main section header
   ``--------`` (hyphens)    Subsection header
   ``^^^^^^^^`` (carets)     Sub-subsection header
   ``~~~~~~~~`` (tildes)     Paragraph header
   ========================  =======================

Inline Text Styling
^^^^^^^^^^^^^^^^^^^
.. table::
   :widths: 40 60

   ========================  =======================
   Syntax                    Result
   ========================  =======================
   ``*italic*``              *italic*
   ``**bold**``              **bold**
   ````literal````              ``literal``
   ``*LaME*``                *LaME* (program name)
   ========================  =======================

Lists and Items
---------------

Bulleted Lists
^^^^^^^^^^^^^^
Create bulleted lists using asterisks (*) or hyphens (-):
::

    * First item
    * Second item
        * Sub-item
        * Another sub-item
    * Third item

Numbered Lists
^^^^^^^^^^^^^^
Create numbered lists using numbers followed by periods (.):
::

    1. First step
    2. Second step
        a) Sub-step
        b) Another sub-step
    3. Third step

Links and References
--------------------

External Links
^^^^^^^^^^^^^^
::

    `Link text <https://example.com>`_

Internal References
^^^^^^^^^^^^^^^^^^^
::

    See :doc:`filtering`
    Refer to :ref:`section-name`

Citations and Notes
^^^^^^^^^^^^^^^^^^^
::

    Citation [Author2024]_
    Footnote [1]_

    .. [Author2024] Full citation text
    .. [1] Footnote text

Tables
------

Simple Tables
^^^^^^^^^^^^^
::

    ======  ======  ======
    Col 1   Col 2   Col 3
    ======  ======  ======
    Row 1   Data    Data
    Row 2   Data    Data
    ======  ======  ======

Grid Tables
^^^^^^^^^^^
::

    +------------+------------+-----------+
    | Header 1   | Header 2   | Header 3  |
    +============+============+===========+
    | Cell 1     | Cell 2     | Cell 3    |
    +------------+------------+-----------+

Special Elements
----------------

Images and Figures
^^^^^^^^^^^^^^^^^^
::

    .. figure:: _static/image.png
        :align: center
        :width: 300
        :alt: Image description

        Figure caption text

