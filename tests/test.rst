=====
Title
=====

Subtitle
++++++++

Heading
*******

Subheading
~~~~~~~~~~

Subsubheading
-------------

word *emphasis* word
word **strong emphasis** word
word `interpreted text` word
word ``inline literal`` word

.. _Python: https://www.python.org/

This paragraph serves as a separator for testing purposes. It contains no special reStructuredText syntax and helps isolate the effects of individual highlight rules.

Internal cross-references, like example_.
.. _example:

:Field 1:
    Field text
    Field text

:Field 2: blah blah blah
:Field 3: blah blah blah

    A blockquote is indented text

A paragraph containing only two colons
indicates that the following indented
or quoted text is a literal block::
  
  This creates a literal block

This is an ordinary line

::

  Whitespace, newlines, blank lines, and
  all kinds of markup (like *this* or
  \this) is preserved by literal blocks.

  The paragraph containing only '::'
  will be omitted from the result.

.. code:: python

  def function():
    a = b
    return

Line block

| this is a line block
| it preserves indent
|    blah
|    blah

Complex table

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

Simple table

=======  =======
Header   Header2
=======  =======
value    value2

Definition

Term
  description of term

Term2
  description of term2

Bulleted lists

- This is item 1
- This is item 2
- Bullets are "-", "*" or "+".
  Continuing text must be aligned
  after the bullet and whitespace.

  * this is a sub bullet
  * this is a second sub bullet


Enumerated lists

1. This is the first item
2. This is the second item
3. Enumerators are arabic numbers,
   single letters, or roman numerals
#. This item is auto-enumerated

Directive, with options

.. figure:: _static/screenshots/LaME_Preprocess.png
    :align: center
    :alt: LaME interface: left toolbox, preprocessing tab
    :width: 315

    *Preprocessing* tab with tools for data enhancement and noise reduction.

word (round) () word
word [square] [] word
word {curly} {} word
word, word <word> <> word

In-line substitution

Autoscaling (|icon-autoscale|) addresses a common

directive with substitution

.. |icon-autoscale| image:: _static/icons/icon-autoscale-64.png
    :height: 2.5ex

Reference: [Smith2023]_

This paragraph serves as a separator for testing purposes. It contains no special reStructuredText syntax and helps isolate the effects of individual highlight rules.

Reference definition

.. [Smith2023] Some explanation

Comments

.. this is inline

words
..
  this is a multiline
  comment