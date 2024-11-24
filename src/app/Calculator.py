import os, re
import numexpr as ne
from src.app.config import BASEDIR, DEBUG_CALCULATOR
import numpy as np

from PyQt5.QtCore import ( QUrl)
from PyQt5.QtWidgets import ( QMessageBox, QInputDialog )

# -------------------------------
# Calculator
# -------------------------------
class CustomFieldCalculator():
    def __init__(self, parent=None):
        # super().__init__(self, parent=None)

        self.parent = parent

        self.calc_filename = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
        self.calc_load_dict()
        self.add_formula = True
        self.precalculate_custom_fields = False
        self.parent.labelCalcMessage.setWordWrap(True)
        self.parent.textEditCalcScreen.textChanged.connect(self.calc_set_add_formula)
        buttons = [
                ('+', self.parent.pushButtonAdd, self.calc_insert_operator),
                ('-', self.parent.pushButtonSubtract, self.calc_insert_operator),
                ('*', self.parent.pushButtonMultiply, self.calc_insert_operator),
                ('/', self.parent.pushButtonDivide, self.calc_insert_operator),
                ('^()', self.parent.pushButtonPower, self.calc_insert_operator),
                ('^2', self.parent.pushButtonSquare, self.calc_insert_operator),
                ('^-1', self.parent.pushButtonInverse, self.calc_insert_operator),
                ('10^()', self.parent.pushButtonPower10, self.calc_insert_operator),
                ('()', self.parent.pushButtonBrackets, self.calc_insert_operator),
                ('sqrt', self.parent.pushButtonSqrt, self.calc_insert_function),
                ('exp', self.parent.pushButtonExp, self.calc_insert_function),
                ('ln', self.parent.pushButtonLn, self.calc_insert_function),
                ('log', self.parent.pushButtonLog, self.calc_insert_function),
                ('abs', self.parent.pushButtonAbs, self.calc_insert_function),
                ('case', self.parent.pushButtonCase, self.calc_insert_function),
                ('otherwise', self.parent.pushButtonOtherwise, self.calc_insert_function),
                ('grad', self.parent.pushButtonCalcGrad, self.calc_insert_function),
                ('area', self.parent.pushButtonCalcArea, self.calc_insert_function),
                (' < ', self.parent.pushButtonLessThan, self.calc_insert_operator),
                (' > ', self.parent.pushButtonGreaterThan, self.calc_insert_operator),
                (' <= ', self.parent.pushButtonLessThanEqualTo, self.calc_insert_operator),
                (' >= ', self.parent.pushButtonGreaterThanEqualTo, self.calc_insert_operator),
                (' == ', self.parent.pushButtonEqualTo, self.calc_insert_operator),
                (' != ', self.parent.pushButtonNotEqualTo, self.calc_insert_operator),
                (' and ', self.parent.pushButtonAnd, self.calc_insert_operator),
                (' or ', self.parent.pushButtonOr, self.calc_insert_operator),
                (' not ', self.parent.pushButtonNot, self.calc_insert_operator),
                (None, self.parent.toolButtonCalcHelp, self.calc_help),
                (None, self.parent.toolButtonCalcAddField, self.calc_add_field),
                (None, self.parent.toolButtonCalcDelete, self.calc_delete_formula),
                (None, self.parent.toolButtonCalculate, self.calculate_new_field)
            ]
        
        def create_handler(handler, text=None):
            if text is not None:
                return lambda: handler(text)
            else:
                return handler

        for text, button, handler in buttons:
            button.clicked.connect(create_handler(handler, text))

        self.parent.toolButtonCalcSave.clicked.connect(lambda: self.calculate_new_field(save=True))
        self.parent.comboBoxCalcFormula.activated.connect(self.calc_load_formula)
        self.parent.comboBoxCalcFieldType.currentIndexChanged.connect(lambda: self.parent.update_field_combobox(self.parent.comboBoxCalcFieldType, self.parent.comboBoxCalcField))
        self.parent.toolButtonCalcClear.clicked.connect(self.parent.textEditCalcScreen.clear)
        self.parent.update_field_combobox(self.parent.comboBoxCalcFieldType, self.parent.comboBoxCalcField)

    def calc_set_add_formula(self):
        """Sets whether to add a new function

        Sets ``MainWindow.add_formula`` to ``True``, a flag used by ``MainWindow.calculate_new_field`` to determine
        whether to add an item to ``MainWindow.comboBoxCalcFormula``.
        """        
        self.add_formula = True

    def calc_help(self):
        """Loads the help webpage associated with the calculator in the Help tab"""
        filename = os.path.join(BASEDIR,"docs/build/html/custom_fields.html")

        self.parent.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.parent.browser.setUrl(QUrl.fromLocalFile(filename))
        
    def calc_insert_operator(self, operator):
        """Inserts an operator into the calculator

        When the user pushes an operator button on the calculator, *operator* is inserted 
        into ``MainWindow.textEditCalcScreen``.

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        print('calc_insert_operator')
        cursor = self.parent.textEditCalcScreen.textCursor()
        cursor.insertText(operator)
    
    def calc_insert_function(self, function):
        """Inserts a function into the calculator

        When the user pushes a function button on the calculator, *operator* is inserted 
        into ``MainWindow.textEditCalcScreen``.  The ``case()`` function inserts ``(cond, expr)``
        as both a condition and expression are required to compute.  

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        print('calc_insert_function')
        cursor = self.parent.textEditCalcScreen.textCursor()
        if cursor.hasSelection():
            cursor.insertText(f"{function}({cursor.selectedText()})")
            # add semicolon to end of case and otherwise functions
            if function in ['case', 'otherwise']:
                cursor.insertText(f"; ")
        else:
            # case should have conditional and expression
            if function == 'case':
                cursor.insertText(f"{function}(cond, expr); ")
            else:
                cursor.insertText(f"{function}()")
                # if otherwise add semicolon to end
                if function == 'otherwise':
                    cursor.insertText(f"; ")
    
    def calc_add_field(self):
        """Adds the selected field to the calculator

        Adds the selected field as ``{field_type.field}``.  If the field is normalized,
        a ``_N`` is added to the end of the field name, i.e., ``{field_type.field_N}``.
        """        
        # get field type and name
        field_type = self.parent.comboBoxCalcFieldType.currentText()
        field = self.parent.comboBoxCalcField.currentText()

        # combine name in calculator style
        match field_type:
            case 'Analyte (normalized)':
                fieldname = f'Analyte.{field}_N'
            case 'Ratio (normalized)':
                fieldname = f'Ratio.{field}_N'
            case 'Calculated':
                fieldname = f'Calculated.{field}'
            case _:
                if field != '':
                    fieldname = f'{field_type}.{field}'

        # add to calculation screen
        cursor = self.parent.textEditCalcScreen.textCursor()
        cursor.insertText(f"{{{fieldname}}}")

    #def calc_clear_text(self):
    #    self.textEditCalcScreen.clear()

    def calc_load_dict(self):
        """Loads saved calculated fields

        Loads the file saved in ``self.calc_filename``, unless the file is overridden by user preferences.  The file
        should be formatted as *name: expression*.  The expression may contain mulitple *case(cond, expr)* separated by a ``;``.
        """        
        self.calc_dict = {}
        try:
            with open(self.calc_filename, 'r') as file:
                # read file with name: expression
                for line in file:
                    line = line.strip()  # Remove leading/trailing whitespace, including newline characters
                    if ':' in line:  # Check if the line contains a ':'
                        name, expression = line.split(':', 1)  # Split only on the first ':'
                        name = name.strip()  # Remove any leading/trailing whitespace from name
                        expression = expression.strip()  # Remove any leading/trailing whitespace from expression
                        self.calc_dict[name] = expression

                # update comboBoxCalcFormula
                self.parent.comboBoxCalcFormula.clear()
                name_list = list(self.calc_dict.keys())
                self.parent.comboBoxCalcFormula.addItems(name_list)
        except FileNotFoundError as e:
            # Return an empty dictionary if the file does not exist
            QMessageBox.warning(self.parent,'Warning','Could not load custom calculated fields.\n Starting with empty custom field dictionary.')

    def calc_delete_formula(self):
        """Deletes a previously stored formula
        
        Removes the formula from ``MainWindow.comboBoxCalcFormula``, the file given by ``MainWindow.calc_filename`` and 
        ``MainWindow.data[MainWindow.sample_id]['computed_data']['Calculated']``.
        """
        func = 'calc_delete_formula'

        # get name of formula
        name = self.parent.comboBoxCalcFormula.currentText()

        # remove name from comboBoxCalcFormula
        self.parent.comboBoxCalcFormula.removeItem(self.parent.comboBoxCalcFormula.currentIndex())

        # remove line with name from calculator formula file
        try:
            # Read all lines from the file
            with open(self.calc_filename, 'r') as file:
                lines = file.readlines()

            # Filter out the lines that contain the name_to_remove
            lines_to_keep = [line for line in lines if not line.startswith(f'{name}:')]

            # Write the remaining lines back to the file
            with open(self.calc_filename, 'w') as file:
                file.writelines(lines_to_keep)

        except FileNotFoundError as e:
            err = 'could not find file'
            self.calc_error(func, err, e)
            pass

        # remove field from Calculated dataframe
        self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].drop([name], axis=1, inplace=True)
    
    def calc_load_formula(self):
        """Loads a predefined formula to use in the calculator"""        
        name = self.parent.comboBoxCalcFormula.currentText()

        self.parent.textEditCalcScreen.clear()
        self.parent.textEditCalcScreen.setText(self.calc_dict[name])

        self.add_formula = False
        
    def calc_parse(self, txt=None):
        """Prepares expression for calculating a custom field 

        Parses ``MainWindow.textEditCalcScreen`` to produce an expression that can be evaluated.
        """
        func = 'calc_parse'

        # Get text 
        if txt is None:
            txt = self.parent.textEditCalcScreen.toPlainText()
            txt = ''.join(txt.split())
        print(txt)

        txt = txt.replace('^','**')
        txt = txt.replace('log(','log10(')
        txt = txt.replace('ln(','log(')
        txt = txt.replace('grad(','gradient(')

        cond = []
        expr = []
        if ('case' in txt) or ('otherwise' in txt):
            cases = txt.split(';')
            # if last case includes a ';', there will be an extra blank in cases list, remove it
            if cases[-1] == '':
                cases.pop()

            # deal with otherwise first as it will be used to set all the values and then cases will reset them
            idx = [i for i, j in enumerate(['foo', 'bar', 'baz']) if j == 'bar']
            if idx is not None:
                cond[0] = 'any'
                expr[0] = cases.index(idx)[10:-1]
                cases.pop(idx)

            for c in cases:
                c = c[5:-1]
                # separate conditional from expression
                try:
                    cond_temp, expr_temp = c.split(',')
                except Exception as e:
                    err = "a case statement must include a conditional and an expression separated by a comma, ',' and end with a ';'."
                    self.calc_error(func, err, e)
                    return None, None

                # parse conditional and expression
                _, cond_temp = self.calc_parse(txt=cond_temp)
                _, expr_temp = self.calc_parse(txt=expr_temp)

                # append list
                cond = cond + cond_temp
                expr = expr + expr_temp

            return cond, expr
        else:
            cond = None

        if txt.count('(') != txt.count(')'):
            'mismatched parentheses in expr'
            self.calc_error(func, err, '')
            return None

        if txt.count('{') != txt.count('}'):
            'mismatched braces in expr'
            self.calc_error(func, err, '')
            return None
        
        field_list = re.findall(r'\{.*?\}', txt)
        print(field_list)
        var = {}
        for field_str in field_list:
            field_str = field_str.replace('{','')
            field_str = field_str.replace('}','')
            try:
                field_type, field = field_str.split('.')
            except Exception as e:
                err = "field type and field must be separated by a '.'"
                self.calc_error(func, err, e)
            if field[-2:] == '_N':
                field = field[:-2]
                if field_type in ['Analyte', 'Ratio']:
                    field_type = f"{field_type} (normalized)"

            if field in list(var.keys()):
                continue

            df = self.parent.get_map_data(self.parent.sample_id, field, field_type, scale_data=False)
            var.update({field: df['array']})

            txt = txt.replace(f"{{{field_str}}}", f"{field}")
        
        if len(var) == 0:
            var = None
        expr = [txt, var]

        print(expr)

        return cond, expr

    def calculate_new_field(self, save=False):
        """Calculates a new field from ``MainWindow.textEditCalcScreen``

        When ``MainWindow.toolButtonCalculate`` is clicked, ...

        If ``save == True``, the formula to ``resources/app_data/calculator.txt`` file so it can be recalled
        and used at a future time or in another sample.  Pushing ``MainWindow.toolButtonCalcSave``,
        opens a dialog prompting the user to input the name for the newly calculated field.

        Parameters
        ----------
        save: bool, optional
            Determines whether to save upon successful calculation, by default ``False``
        """
        func = 'calculate_new_field'

        # open dialog to get new field
        if self.add_formula:
            new_field, ok = QInputDialog.getText(self.parent, 'Save expression', 'Enter custon field name:')
            if ok:
                # check for valid field name
                if self.partial_match_in_list(['_N',':'],new_field):
                    err = "new field name cannot have an '_N' or ':' in the name"
                    self.calc_error(func, err, '')
                    ok = False
                    
            if not ok:
                return
        else:
            new_field = self.parent.comboBoxCalcFormula.currentText()

        # parse the expression
        cond, expr = self.calc_parse()
        if cond is None:    # no conditionals
            result = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
            if result is None:
                return
            self.parent.data[self.parent.sample_id]['computed_data']['Calculated'][new_field] = result
        elif expr is None:
            err = "expr returned 'None' could not evaluate formula. Check syntax."
            self.calc_error(func, err, '')
            return
        else:   # conditionals
            # start with empty dataFrame
            result = pd.DataFrame({new_field: np.nan*np.zeros_like(self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].iloc[:,0])})

            # loop over cases (cond, expr)
            for i in range(0,len(cond),2):
                if (i == 0) and (cond[i] == 'any'):
                    try:
                        res = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
                    except Exception as e:
                        err = "could not evaluate otherwise expression. Check syntax."
                        self.calc_error(func, err, e)
                        return
                    self.parent.data[self.parent.sample_id]['computed_data']['Calculated'][new_field] = result
                    continue

                # conditional yields boolean numpy.ndarray keep
                try:
                    keep = self.calc_evaluate_expr(cond[i], val_dict=cond[i+1])
                except Exception as e:
                    err = "could not evaluate conditional statement. Check syntax."
                    self.calc_error(func, err, e)
                    return

                # check for missing or incorrectly type for conditional
                if keep is None:
                    err = 'conditional did not return boolean result.'
                    self.calc_error(func, err, '')
                    return
                elif not isinstance(keep, np.ndarray):
                    if not np.issubdtype(keep.dtype, np.bool_):
                        err = 'conditional did not return boolean result.\n  Did you swap the conditional and expression?'
                        self.calc_error(func, err, '')
                        return

                # check for size error
                if keep.shape[0] != result.shape[0]:
                    err = 'the conditional size does not match the size of expected computed array.'
                    self.calc_error(func, err, '')
                    return

                # compute expression for indexes where keep==`True`
                try:
                    res = self.calc_evaluate_expr(expr[i], val_dict=expr[i+1], keep=keep)
                except Exception as e:
                    err = "could not evaluate expression. Check syntax."
                    self.calc_error(func, err, e)
                    return

                if res is None:
                    err = 'the expression failed to return an array of values.'
                    self.calc_error(func, err, '')
                    return

                result.loc[keep,new_field] = res

            self.parent.data[self.parent.sample_id]['computed_data']['Calculated'][new_field] = result

        # update comboBoxCalcFormula
        self.parent.comboBoxCalcFormula.addItem(new_field)
        self.parent.comboBoxCalcFormula.setCurrentText(new_field)

        if self.parent.comboBoxCalcFieldType.currentText == 'Calculated':
            self.parent.update_field_combobox(self.parent.comboBoxCalcFieldType, self.parent.comboBoxCalcField)

        # get the formula and add to custom field dictionary
        formula = self.parent.textEditCalcScreen.toPlainText()
        self.calc_dict.update({'field':new_field, 'expr':formula})

        # append calculator file
        if save:
            try:
                with open(self.calc_filename, 'a') as file:
                    file.write(f"{new_field}: {formula}\n")
            except Exception as e:
                # throw a warning that nam
                err = 'could not save expression, problem with write.'
                self.calc_error(func, err, e)
                return

    def calc_evaluate_expr(self, expr, val_dict=None, keep=None):
        """Evaluates an expression and returns the result

        Parameters
        ----------
        expr : string
            Expression to be evaluated.  The expression can be a conditional expression, which results
            in returning a np.ndarray of bool, otherwise, generally np.ndarray of float
        val_dict : dict
            Dictionary with variable names as the key and values taken from the data, generally np.ndarray, by default ``None``
        keep : np.ndarray of bool or None, optional
            An array of True/False values that are used to evaluate the expression of limited values,
            i.e., generally when cases are involved.

        Returns
        -------
        np.ndarray of float or bool
            Result of evaluated expression.
        """        
        func = 'calc_evaluate_expr'
        try:
            if val_dict is None:
                result = ne.evaluate(expr)
            else:
                result = ne.evaluate(expr, local_dict=val_dict)
            self.parent.labelCalcMessage.setText("Success")
            if keep is None or result.ndim == 0:
                return result
            else:
                return result[keep]
        except Exception as e:
            err = 'unable to evaluate expression.'
            self.calc_error(func, err, e)
            return None

    def calc_error(self, func, err, addinfo):
        """Raise a calculator-related error

        Parameters
        ----------
        func : str
            Function that threw the error
        err : str
            Error string
        addinfo : str
            Additional info (generally exception raised)
        """        
        self.parent.labelCalcMessage.setText(f"Error: {err}")
        QMessageBox.warning(self.parent,'Calculation Error',f"Error: {err}\n\n({func}) {addinfo}")