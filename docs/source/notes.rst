Notes
*****

Text Formatting Guide
===================

Basic Formatting
--------------

Headers
^^^^^^^
Headers are created by underlining text with specific characters. The length of the underline must match the text length:

.. table::
   :widths: 40 60

   ================================  =======================
   Syntax                            Description
   ================================  =======================
   ``**********`` (asterisks)        Title header
   ``===========`` (equals)          Main section header
   ``-----------`` (hyphens)         Subsection header
   ``^^^^^^^^^^^`` (carets)          Sub-subsection header
   ``~~~~~~~~~~~`` (tildes)          Paragraph header
   ================================  =======================

Inline Text Styling
^^^^^^^^^^^^^^^^^
.. table::
   :widths: 40 60

   ================================  =======================
   Syntax                            Result
   ================================  =======================
   ``*italic*``                      *italic*
   ``**bold**``                      **bold**
   ````code````                      ``code``
   ``*LaME*``                        *LaME* (program name)
   ================================  =======================

Lists and Items
-------------

Bulleted Lists
^^^^^^^^^^^^^
Create bulleted lists using asterisks (*) or hyphens (-):
::

    * First item
    * Second item
        * Sub-item
        * Another sub-item
    * Third item

Numbered Lists
^^^^^^^^^^^^
Create numbered lists using numbers followed by periods (.):
::

    1. First step
    2. Second step
        a) Sub-step
        b) Another sub-step
    3. Third step

Links and References
------------------

External Links
^^^^^^^^^^^^
::

    `Link text <https://example.com>`_

Internal References
^^^^^^^^^^^^^^^^
::

    See :doc:`filtering`
    Refer to :ref:`section-name`

Citations and Notes
^^^^^^^^^^^^^^^^^
::

    Citation [Author2024]_
    Footnote [1]_

    .. [Author2024] Full citation text
    .. [1] Footnote text

Tables
------

Simple Tables
^^^^^^^^^^^
::

    ======  ======  ======
    Col 1   Col 2   Col 3
    ======  ======  ======
    Row 1   Data    Data
    Row 2   Data    Data
    ======  ======  ======

Grid Tables
^^^^^^^^^^
::

    +------------+------------+-----------+
    | Header 1   | Header 2   | Header 3  |
    +============+============+===========+
    | Cell 1     | Cell 2     | Cell 3    |
    +------------+------------+-----------+

Special Elements
--------------

Images and Figures
^^^^^^^^^^^^^^^^
::

    .. figure:: _static/image.png
        :align: center
        :width: 300
        :alt: Image description

        Figure caption text

