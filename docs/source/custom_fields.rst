Custom Fields
*************

The calculator can be used to create custom fields in almost any plot.  The user can create custom fields by entering expressions either directly from the keyboard or by using the calculator buttons. These custom fields are saved for use with other samples or can be exported to a file for future sessions.

The calculator has a relatively simple language for developing expressions, including conditional cases.  The key thing to remember is that operations in *LaME* (by way of Python) uses PEMDAS order of operations: 

* parentheses (P)
* exponents and roots (E)
* multiplication and division (MD) 
* addition and subtraction (AS)

Operations on the same level e.g., multiplication and division or addition and subtraction are applied from left to right.  When in doubt, add parentheses ensure order.  

After arithmetic operations, the program evaluates comparison operators (<, <=, >, >=, ==, !=) and finally boolean operations in the following order (not, and, or).

Fields can be added by first selecting the appropriate *field_type*, then selecting the desired.  Fields may also be added manually by placing the field within braces ``{}`` and listing the field type followed by ``.`` and then the field name.  Note the field type may be different than that listed but the field name is always the same as the field, unless the field is normalized.  If the field is normalized, you will need to append ``_N`` to the field name.

Example use of fields in expressions:

- {Analyte.Sr88} for an unnormalized analyte
- {Analyte.La139_N} for a normalized analyte
- {Cluster Score.3} to choose the cluster score for the 3rd group

The ``case()`` function allows you to use conditional logic in your calculations. It requires two arguments separated by a comma:

1. A conditional argument that evaluates to ``True`` or ``False`` for each element.
2. An expression to be evaluated when the condition is true.

You can include multiple case statements to handle different conditions.

Example:
``case(condition1, expression1, condition2, expression2, ..., default_expression)``

This powerful feature enables you to create complex, condition-based custom fields for your analyses.
