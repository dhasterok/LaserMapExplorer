Creating Custom Fields
**********************

The calculator can be used to create custom fields that can be used in almost any plot.  The user can enter the expression from the keyboard or use the calculator buttons to help build an expresion for evaluation.  These custom fields are saved for use with other samples or can be saved to a file for any future session.

The calculator has a relatively simple language to develop expressions including cases.  The key thing to remember is that operations in LaME (by way of python) uses PEMDAS order of operations: parentheses (P), exponents and roots (E), multiplication and division (MD), and addition and subtraction (AS).  Operations on the same level e.g., multiplication and division or addition and subtraction are applied from left to right.  When in doubt, add parentheses ensure order.  After arithmetic operations, the program evaluates comparison operators (<, <=, >, >=, ==, !=) and finally boolean operations in the following order (not, and, or).

Fields can be added by first selecting the appropriate *field_type* that contains the field from the *field type combobox*, then selecting the desired *field* from the *field combobox*.  Fields may also be added manually by placing the field within braces ``{}`` and listing the field type followed by ``.`` and then the field name.  Note the field type may be different than that listed in the *field type combobox*.  The field name is always the same as the field, unless the field is normalized.  If the field is normalized, you will need to append ``_N`` to the field name.

Example use of fields in expressions:
- {Analyte.Sr88} for an unnormalized analyte
- {Analyte.La139_N} for a normalized analyte
- {Cluster Score.3} to choose the cluster score for the 3rd group

At times, you may wish to use one or more cases for calculations depending on the range of a field or combination of fields.  To do so, use the ``case()`` function.  To use the case function, you will need to include two arguments, a conditional and an expression, separated by a ``,``.  The first argument should be a conditional argument that evaluates to ``True`` or ``False`` for each element.  The expression can be any mathematical expression.