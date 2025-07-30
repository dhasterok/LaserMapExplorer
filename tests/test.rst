======================
ReST Test File (Title)
======================

Introduction
**********

This file is used to test syntax highlighting in reStructuredText (reST). Each of th lines below is used to test whether the rules for highlighting syntax work properly and whether the syntax checker correctly identifies errors to the docutils reST specifications (v.10184) which can be found on the `reStructedText Markup Specification`_ web-based documentation.

.. _reSTructuredText Markup Specification: https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html

Specific Tests
***+****=*****

Brackets
++++++++

While brackets do not necessarily have a special role in all cases, it is helpful to have them highlighted so that it is easy to make sure that they close.

* round (round), () word
* square [square], [] word
* curly {curly}, {} word
* angle <word> <> word
* pipe |word| || word

Headings
++++++++

Headings can be created with any non-numeric printing character, however, there are a subset that are recommended.  At the moment, the highlighting rules only allow for `= * - + ~ ^ ' "`.  The level of heading is assigned in order of use of the symbols, though no specific order of the symbols is required, i.e., the title level above could started with a `*` rather than an `=`.  ReST only allows for 6 heading levels (there are 8 checked here for syntax, though you could use `# % & [ }` if you desired).

Subheading test
~~~~~~~~~~~~~~~

Subsubheading test
------------------

Inline Markup
+++++++++++++

Text formatting can be applied to create *emphasis* (*italic*) or **strong emphasis** (**bold**).
test for *multiple words*
test for **multiple words**

Text can also be `interpreted` or ``literal``.
test for `multiple words`
test for ``multiple words``

Lists
+++++

Field Lists
~~~~~~~~~~~

:Field 1:
    Field text
    Field text

:Field 2: blah blah blah
:Field 3: blah blah blah

Definition lists
~~~~~~~~~~~~~~~~

Term
  description of term

Term2
  description of term2

Bulleted lists
~~~~~~~~~~~~~~

- This is item 1
- This is item 2
- Bullets are "-", "*" or "+".
  Continuing text must be aligned
  after the bullet and whitespace.

  * this is a sub bullet
  * this is a second sub bullet


Enumerated lists
~~~~~~~~~~~~~~~~

1. This is the first item
2. This is the second item
3. Enumerators are arabic numbers,
   single letters, or roman numerals
#. This item is auto-enumerated


Blocks
++++++

Blockquote
~~~~~~~~~~

    A blockquote is indented text

Literal block
~~~~~~~~~~~~~

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

Line block
~~~~~~~~~~

| this is a line block
| it preserves indent
|    blah
|    blah

Tables
~~~~~~

Complex table
--------------

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

Simple tables
-------------

====================  ==========  ==========
Header row, column 1  Header 2    Header 3
====================  ==========  ==========
body row 1, column 1  column 2    column 3
body row 2            Cells may span columns
====================  ======================

Directives
~~~~~~~~~~

Directives are a way to introduce specific formatting into reST compiled documents, including figures, images, LaTeX style math, code, unicode for special characters, and formatted tables to name a few of the potentially more features.  It is also possible to introduce raw text formatting and even construct your own specific directives, though they may not compile unless you have a custom compiler for parsing them.

A directive should be written in the following format

.. |substitution| keyword:: argument
    :option1: value1    
    :option2: value2    

    directive body text    

If syntax highlighting is working, the keyword in the description above should be identified as an error because there is no directive named keyword.  Only a few of the directives, (image, replacement text, unicode and date) have substitutions.

.. code:: python

  def function():
    a = b
    return

Directive, with options

.. figure:: _static/screenshots/LaME_Preprocess.png
    :align: center
    :alt: LaME interface: left toolbox, preprocessing tab
    :width: 315
    :invalid-option: this option should cause a syntax error

    *Preprocessing* tab with tools for data enhancement and noise reduction.

Some directives have substitutions.  These substitutions allow the user to insert something into the text.  It can be used to simplify common phrases, introduce images, etc.  The substitution can be defined before or after it's first use in the document.

This is an example of a substitution (|icon-autoscale|) where the text enclosed in `|` is replaced with the image below when compiled.

.. |icon-autoscale| image:: _static/icons/icon-autoscale-64.png
    :height: 2.5ex

Substitutions can also be done inline, though there are only a few directives that allow inline substitution (math, code, raw).  Example in-line substitution, :math:`\partial C / \partial t = D \nabla^2 C`.


Referencing
+++++++++++

Hyperlinks
~~~~~~~~~~

External
--------

This is a link python_ to `LaME program`_ word word

.. _Python: https://www.python.org/

.. _LaME program: https://github.com/dhasterok/LaserMapExplorer

This paragraph serves as a separator for testing purposes. It contains no special reStructuredText syntax and helps isolate the effects of individual highlight rules.

Internal
--------

Internal cross-references, like example_.
.. _example:

word _`internal target` word

Citation
~~~~~~~~

Reference: [HKGLH2026]_

This paragraph serves as a separator for testing purposes. It contains no special reStructuredText syntax and helps isolate the effects of individual highlight rules.

.. [HKGLH2026] Hasterok, D., et al., **2026**, Laser Map Explorer (LaME): a tool for interpreting
    and exploring and processing LA-ICP-MS map data.

Footnotes
~~~~~~~~~

Let's see if we can get footnotes[1]_ working

.. [1] This is a footnote
    that is longer than one line

Comments
++++++++

.. this is inline

words
..
  this is a multiline
  comment