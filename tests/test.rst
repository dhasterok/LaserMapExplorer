*emphasis*
**strong emphasis**
`interpreted text`
``inline literal``
.. _Python: https://www.python.org/

Internal cross-references, like example_.
.. _example:

:Authors:
    Tony J. (Tibs) Ibbs,
    David Goodger
    (and sundry other good-natured folks)

:Version: 1.0 of 2001/08/08
:Dedication: To my father.

.. code::

A paragraph containing only two colons
indicates that the following indented
or quoted text is a literal block.

::

  Whitespace, newlines, blank lines, and
  all kinds of markup (like *this* or
  \this) is preserved by literal blocks.

  The paragraph containing only '::'
  will be omitted from the result.
.. code::
+------------+------------+-----------+
| Header 1   | Header 2   | Header 3  |
+============+============+===========+
| body row 1 | column 2   | column 3  |
+------------+------------+-----------+
| body row 2 | Cells may span columns.|
+------------+------------+-----------+
| body row 3 | Cells may  | - Cells   |
+------------+ span rows. | - contain |
| body row 4 |            | - blocks. |
+------------+------------+-----------+

=====
Title
=====

Subtitle
--------

- This is item 1
- This is item 2
- Bullets are "-", "*" or "+".
  Continuing text must be aligned
  after the bullet and whitespace.

1. This is the first item
2. This is the second item
3. Enumerators are arabic numbers,
   single letters, or roman numerals
4. List items should be sequentially
   numbered, but need not start at 1
   (although not all formatters will
   honour the first index).
#. This item is auto-enumerated