import os, re
import numexpr as ne
from src.app.config import BASEDIR
import numpy as np
import pandas as pd
from src.common.varfunc import partial_match
from src.app.UIControl import update_field_combobox

from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtWidgets import (
        QMainWindow, QTextEdit, QDockWidget, QWidget, QVBoxLayout, QMessageBox, QInputDialog, QLabel,
        QToolBar, QComboBox, QToolButton, QAction, QDialog, QCheckBox, QDialogButtonBox, QPushButton,
        QGroupBox, QGridLayout, QHBoxLayout
    )
from PyQt5.QtGui import QIcon

# -------------------------------
# Calculator
# -------------------------------
class CalculatorDock(QDockWidget):
    """Creates a CustomFieldCalculator with UI controls inside a dock widget that can be added to a QMainWindow

    Parameters
    ----------
    parent : QMainWindow, optional
        _description_, by default None
    filename : str, optional
        Filename for saving calculator functions, by default None
    debug : bool, optional
        When ``True``, will create verbose output, by default False

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    TypeError
        Parent must be an instance of QMainWindow.
    """        
    def __init__(self, parent=None, filename=None, debug=False):
        # super().__init__(self, parent=None)
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__("Calculator", parent)
        self.parent = parent

        # create an instance of CustomFieldCalculator for the heavy lifting
        self.cfc = CustomFieldCalculator(parent.data[parent.sample_id], debug)

        self.debug = debug

        if filename is None:
            self.calc_filename = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')

        self.calc_load_dict()
        self.add_formula = True
        self.precalculate_custom_fields = False

        # Create container
        container = QWidget()
        calculator_layout = QVBoxLayout()

        # Create toolbar
        toolbar = QToolBar("Calculator Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # calculate new field based on formula entered by user
        self.action_calculate = QAction()
        self.action_calculate.setIcon(QIcon(":resources/icons/icon-calculator-64.svg"))
        self.action_calculate.triggered.connect(self.calculate_new_field)
        self.action_calculate.setToolTip("Calculate field")
        self.toolbar.addAction(self.action_calculate)

        # save the current formula to a  dictionary
        self.action_save = QAction()
        self.action_save.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
        self.action_save.triggered.connect(lambda: self.calculate_new_field(save=True))
        self.action_save.setToolTip("Calculate and save field")
        self.toolbar.addAction(self.action_save)

        # clear the calculator screen
        self.action_clear = QAction()
        self.action_clear.setIcon(QIcon(":resources/icons/icon-reject-64.svg"))
        self.action_clear.triggered.connect(self.textEditCalcScreen.clear)
        self.action_clear.setToolTip("Clear current formula")
        self.toolbar.addAction(self.action_clear)

        # link the calculator to help
        self.action_help = QAction()
        self.action_help.setIcon(QIcon(':resources/icons/icon-help-64.svg'))
        self.action_help.triggered.connect(self.calc_help)
        self.action_help.setToolTip("Get help calculating fields")
        self.toolbar.addAction(self.action_help)

        calculator_layout.addWidget(toolbar)

        # calculator screen
        screen_group_box = QGroupBox()
        screen_group_box.setTitle("Enter Formula")
        screen_layout = QVBoxLayout()

        self.textEditCalcScreen = QTextEdit()
        self.textEditCalcScreen.textChanged.connect(self.calc_set_add_formula)
        screen_layout.addWidget(self.text_edit)

        # calculator status
        self.labelCalcMessage = QLabel()
        self.labelCalcMessage.setWordWrap(True)
        screen_layout.addWidget(self.labelCalcMessage)
        screen_group_box.setLayout(screen_layout)

        # Equations
        equation_select_layout = QHBoxLayout()
        self.comboBoxCalcFormula = QComboBox()
        self.comboBoxCalcFormula.activated.connect(self.calc_load_formula)

        self.toolButtonCalcDelete = QToolButton()
        delete_icon = QIcon(":resources/icons/icon-delete-64.svg")
        if not delete_icon.isNull():
            self.toolButtonCalcDelete.setIcon(delete_icon)
        else:
            self.toolButtonCalcDelete.setText("Delete")
        self.toolButtonCalcDelete.setToolTip("Delete selected equation")
        self.toolButtonCalcDelete.clicked.connect(self.calc_delete_formula)

        equation_select_layout.addWidget(self.comboBoxCalcFormula)
        equation_select_layout.addWidget(self.toolButtonCalcDelete)
        calculator_layout.addChildLayout(equation_select_layout)


        # Field Control
        self.comboBoxCalcFieldType = QComboBox()
        self.comboBoxCalcFieldType.setToolTip("Select field type")
        self.comboBoxCalcFieldType.showPopup(self.update_field_type_combobox)
        self.comboBoxCalcFieldType.activated(self.update_field_combobox)
        calculator_layout.addWidget(comboBoxCalcFieldType)

        field_layout = QHBoxLayout()
        self.comboBoxCalcField = QComboBox()
        self.comboBoxCalcField.setToolTip("Select field")

        self.toolButtonCalcAddField = QToolButton()
        add_icon = QIcon(":resources/icons/icon-accept-64.svg")
        if not add_icon.isNull():
            self.toolButtonCalcAddField.setIcon(add_icon)
        else:
            self.toolButtonCalcAddField.setText("Select a field to add it to the formula")
        self.toolButtonCalcAddField.clicked.connect(self.calc_add_field)

        field_layout.addWidget(self.comboBoxCalcField)
        field_layout.addWidget(self.toolButtonCalcAddField)
        calculator_layout.addChildLayout(field_layout)

        update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)


        # button_checkbox
        button_checkbox = QCheckBox()

        calculator_layout.addWidget(button_checkbox)

        # field/equation controls
        self.button_group = QGroupBox()
        button_layout = QGridLayout()

        # buttons
        buttons = [
                ('+', '+', 6,0, self.calc_insert_operator),
                (',', '-', 6,1, self.calc_insert_operator),
                ('*', '*', 6,2, self.calc_insert_operator),
                ('/', '/', 6,3, self.calc_insert_operator),
                ('x^y', '^()', 4,0, self.calc_insert_operator),
                ('x^2', '^2', 5,1, self.calc_insert_operator),
                ('x^-1', '^-1', 4.1, self.calc_insert_operator),
                ('10^x', '10^()', 4,2, self.calc_insert_operator),
                ('()', '()', 5,0, self.calc_insert_operator),
                ('sqrt()', 'sqrt', 5,2, self.calc_insert_function),
                ('exp()', 'exp', 5,3, self.calc_insert_function),
                ('ln()', 'ln', 4,3, self.calc_insert_function),
                ('log()', 'log', 3,3, self.calc_insert_function),
                ('abs()', 'abs', 2,3, self.calc_insert_function),
                ('case()', 'case', 0,0, self.calc_insert_function),
                ('otw()', 'otherwise', 0,1, self.calc_insert_function),
                ('grad()', 'grad', 0,2, self.calc_insert_function),
                ('area()', 'area', 0,3, self.calc_insert_function),
                ('<', ' < ', 2,0, self.calc_insert_operator),
                ('>', ' > ', 2,1, self.calc_insert_operator),
                ('<=', ' <= ', 3,0, self.calc_insert_operator),
                ('>=', ' >= ', 3,1, self.calc_insert_operator),
                ('==', ' == ', 2,2, self.calc_insert_operator),
                ('!=', ' != ', 3,2, self.calc_insert_operator),
                ('and', ' and ', 1,0, self.calc_insert_operator),
                ('or', ' or ', 1,1, self.calc_insert_operator),
                ('not', ' not ', 1,2, self.calc_insert_operator),
            ]
        
        def create_handler(handler, text=None):
            if text is not None:
                return lambda: handler(text)
            else:
                return handler

        for label, text, row, col, handler in buttons:
            button = QPushButton()
            button.setText(label)
            button_layout.addWidget(button, row, col)
            button.clicked.connect(create_handler(handler, text))
        
        self.button_group.setLayout(button_layout)
        calculator_layout.addWidget(self.button_goup)

        button_checkbox.changeEvent.connect(lambda: self.button_group.setVisible(button_checkbox.isChecked()))

        # Set layout to the container
        container.setLayout(calculator_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("LaME Calculator")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        parent.addDockWidget(Qt.RightDockWidgetArea, self)

    def update_field_type_combobox(self):
        self.parent.data[self.parent.sample_id].

    def calc_help(self):
        """Loads the help webpage associated with the calculator in the Help tab"""
        if self.debug:
            print("calc_help")

        filename = os.path.join(BASEDIR,"docs/build/html/custom_fields.html")

        self.lineEditBrowserLocation.setText(filename)

        if filename and hasattr(self.parent,'browser'):
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
        if self.debug:
            print(f"calc_insert_operator, operator {operator}")

        cursor = self.textEditCalcScreen.textCursor()
        cursor.insertText(operator)

   def calc_insert_function(self, func_name):
        """Inserts a func_name into the calculator

        When the user pushes a function button on the calculator, *operator* is inserted 
        into ``MainWindow.textEditCalcScreen``.  The ``case()`` function inserts ``(cond, expr)``
        as both a condition and expression are required to compute.  

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        if self.debug:
            print(f"calc_insert_function, function: {func_name}")

        cursor = self.textEditCalcScreen.textCursor()
        if cursor.hasSelection():
            cursor.insertText(f"{func_name}({cursor.selectedText()})")
            # add semicolon to end of case and otherwise functions
            if func_name in ['case', 'otherwise']:
                cursor.insertText(f"; ")
        else:
            # case should have conditional and expression
            if func_name == 'case':
                cursor.insertText(f"{func_name}(cond, expr); ")
            else:
                cursor.insertText(f"{func_name}()")
                # if otherwise add semicolon to end
                if func_name == 'otherwise':
                    cursor.insertText(f"; ")
    
    def calc_add_field(self):
        """Adds the selected field to the calculator

        Adds the selected field as ``{field_type.field}``.  If the field is normalized,
        a ``_N`` is added to the end of the field name, i.e., ``{field_type.field_N}``.
        """        
        if self.debug:
            print("calc_add_field")

        # get field type and name
        field_type = self.comboBoxCalcFieldType.currentText()
        field = self.comboBoxCalcField.currentText()

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
        cursor = self.textEditCalcScreen.textCursor()
        cursor.insertText(f"{{{fieldname}}}")

    #def calc_clear_text(self):
    #    self.textEditCalcScreen.clear()

    def calc_load_dict(self):
        """Loads saved calculated fields

        Loads the file saved in ``self.calc_filename``, unless the file is overridden by user preferences.  The file
        should be formatted as *name: expression*.  The expression may contain mulitple *case(cond, expr)* separated by a ``;``.
        """        
        if self.debug:
            print("calc_load_dict")

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
                self.comboBoxCalcFormula.clear()
                name_list = list(self.calc_dict.keys())
                self.comboBoxCalcFormula.addItems(name_list)
        except FileNotFoundError as e:
            # Return an empty dictionary if the file does not exist
            QMessageBox.warning(self,'Warning','Could not load custom calculated fields.\n Starting with empty custom field dictionary.')

    def calc_delete_formula(self):
        """Deletes a previously stored formula
        
        Removes the formula from ``MainWindow.comboBoxCalcFormula``, the file given by ``MainWindow.calc_filename`` and 
        ``parent.data[parent.sample_id].processed_data``.
        """
        if self.debug:
            print("calc_delete_formula")

        func = 'calc_delete_formula'

        # get name of formula
        name = self.comboBoxCalcFormula.currentText()

        # remove name from comboBoxCalcFormula
        self.comboBoxCalcFormula.removeItem(self.comboBoxCalcFormula.currentIndex())

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
        self.parent.data[self.parent.sample_id].delete_column(name)
    
    def calc_load_formula(self):
        """Loads a predefined formula to use in the calculator"""        
        if self.debug:
            print("calc_load_formula")

        name = self.comboBoxCalcFormula.currentText()

        self.textEditCalcScreen.clear()
        self.textEditCalcScreen.setText(self.calc_dict[name])

        self.add_formula = False
    
    def calc_set_add_formula(self):
        """Sets whether to add a new function

        Sets ``MainWindow.add_formula`` to ``True``, a flag used by ``MainWindow.calculate_new_field`` to determine
        whether to add an item to ``MainWindow.comboBoxCalcFormula``.
        """        
        if self.debug:
            print("calc_add_formula")

        self.add_formula = True

    def calc_parse(self, txt=None):
        """Prepares expression for calculating a custom field 

        Parses ``MainWindow.textEditCalcScreen`` to produce an expression that can be evaluated.
        """
        if self.debug:
            print(f"calc_parse, text: {txt}")

        func = 'calc_parse'

        # Get text 
        if txt is None:
            txt = self.textEditCalcScreen.toPlainText()
        print(txt)

        self.cfc.calc_parse(txt)

 

class CustomFieldCalculator():
    def __init__(self, data, debug=False):
        self.debug = debug
        self.data = data
        
    def calc_parse(self, txt=None):
        """Prepares expression for calculating a custom field 

        Parses ``MainWindow.textEditCalcScreen`` to produce an expression that can be evaluated.
        """
        if self.debug:
            print(f"calc_parse, text: {txt}")

        func = 'calc_parse'

        # Get text 
        if txt is None:
            txt = self.textEditCalcScreen.toPlainText()
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

            df = self.parent.data[self.parent.sample_id].get_map_data(field, field_type, ref_chem=self.parent.ref_chem)
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
        if self.debug:
            print(f"calculate_new_field, save: {save}")

        func = 'calculate_new_field'

        # open dialog to get new field
        if self.add_formula:
            new_field, ok = QInputDialog.getText(self, 'Save expression', 'Enter custon field name:')
            if ok:
                # check for valid field name
                if partial_match(['_N',':'],new_field)[0]:
                    err = "new field name cannot have an '_N' or ':' in the name"
                    self.calc_error(func, err, '')
                    ok = False
                    
            if not ok:
                return
        else:
            new_field = self.comboBoxCalcFormula.currentText()

        # parse the expression
        cond, expr = self.calc_parse()
        if cond is None:    # no conditionals
            result = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
            if result is None:
                return
            self.parent.data[self.parent.sample_id].add_columns('computed', new_field, result)
        elif expr is None:
            err = "expr returned 'None' could not evaluate formula. Check syntax."
            self.calc_error(func, err, '')
            return
        else:   # conditionals
            # start with empty dataFrame
            result = pd.DataFrame({new_field: np.nan*np.zeros_like(self.parent.data[self.parent.sample_id].processed_data.iloc[:,0])})

            # loop over cases (cond, expr)
            for i in range(0,len(cond),2):
                if (i == 0) and (cond[i] == 'any'):
                    try:
                        res = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
                    except Exception as e:
                        err = "could not evaluate otherwise expression. Check syntax."
                        self.calc_error(func, err, e)
                        return
                    self.parent.data[self.parent.sample_id].add_columns('computed', new_field, result)
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

            self.parent.data[self.parent.sample_id].add_columns('computed', new_field, result)

        # update comboBoxCalcFormula
        self.comboBoxCalcFormula.addItem(new_field)
        self.comboBoxCalcFormula.setCurrentText(new_field)

        # add new calculated field to self.treeView
        self.parent.plot_tree.add_calculated_leaf(new_field)

        if self.parent.comboBoxCalcFieldType.currentText == 'Calculated':
            self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)

        # get the formula and add to custom field dictionary
        formula = self.textEditCalcScreen.toPlainText()
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
        if self.debug:
            print(f"calc_evaluate_expr\n  expr: {expr}\n  val_dict: {val_dict}\n  keep: {keep}")

        func = 'calc_evaluate_expr'
        try:
            if val_dict is None:
                result = ne.evaluate(expr)
            else:
                result = ne.evaluate(expr, local_dict=val_dict)
            self.labelCalcMessage.setText("Success")
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
        if self.debug:
            print(f"calc_error\n  func: {func}\n  err: {err}\n  addinfo: {addinfo}")

        self.labelCalcMessage.setText(f"Error: {err}")
        QMessageBox.warning(self,'Calculation Error',f"Error: {err}\n\n({func}) {addinfo}")