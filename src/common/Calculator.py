import os, re
import numexpr as ne
from src.app.config import BASEDIR
import numpy as np
import pandas as pd
from src.common.varfunc import partial_match

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
        QMainWindow, QPlainTextEdit, QWidget, QVBoxLayout, QMessageBox, QInputDialog, QLabel,
        QToolBar, QComboBox, QCheckBox, QPushButton,
        QGroupBox, QGridLayout, QHBoxLayout, QFrame, QSizePolicy, QScrollArea
    )

from src.common.CustomWidgets import CustomComboBox, CustomDockWidget, CustomAction, CustomToolButton
from src.app.FieldLogic import FieldLogicUI
from src.common.Logger import LoggerConfig, auto_log_methods

def calc_error(parent, func, err, addinfo):
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
    parent.message_label.setText(f"Error: {err}")
    QMessageBox.warning(parent,"Calculation Error",f"Error: {err}\n\n({func}) {addinfo}",QMessageBox.StandardButton.Ok)

# -------------------------------
# Calculator
# -------------------------------
@auto_log_methods(logger_key='Calculator')
class CalculatorDock(CustomDockWidget, FieldLogicUI):
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
    def __init__(self, ui=None, filename=None):
        # super().__init__(self, parent=None)
        self.logger_key = 'Calculator'

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")
        
        super().__init__(ui)

        self.ui = ui
        if self.ui.app_data.sample_id == '':
            self.data = None
        else:
            self.data = self.ui.data[self.ui.app_data.sample_id].processed_data

        FieldLogicUI.__init__(self, self.data)

        # create an instance of CustomFieldCalculator for the heavy lifting
        if self.ui.app_data.sample_id != '':
            self.cfc = CustomFieldCalculator()

        if filename is None:
            self.calc_filename = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
        else:
            self.calc_filename = filename

        
        self.setupUI()
        self.connect_widgets()
        self.connect_logger()

        # update UI with pre-saved formulas
        self.calc_load_dict()
        self.add_formula = True
        self.precalculate_custom_fields = False

    def setupUI(self):
        # Create container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        calculator_layout = QVBoxLayout()

        # Create toolbar
        toolbar = QToolBar("Calculator Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # calculate new field based on formula entered by user
        self.calculate_action = CustomAction(
            text="Calculate",
            light_icon_unchecked="icon-run-64.svg"
        )
        self.calculate_action.setToolTip("Calculate field")

        # save the current formula to a  dictionary
        self.save_action = CustomAction(
            text="Save Equation",
            light_icon_unchecked="icon-save-file-64.svg"
        )
        self.save_action.setToolTip("Calculate and save field")

        # clear the calculator screen
        self.clear_action = CustomAction(
            text="Clear",
            light_icon_unchecked="icon-reject-64.svg",
        )
        self.clear_action.setToolTip("Clear current formula")

        # link the calculator to help
        self.help_action = CustomAction(
            text="Help",
            light_icon_unchecked="icon-info-64.svg",
        )
        self.help_action.setToolTip("Get help calculating fields")

        toolbar.addAction(self.calculate_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.clear_action)
        toolbar.addAction(self.help_action)
        calculator_layout.addWidget(toolbar)

        # calculator screen
        screen_group_box = QGroupBox()
        screen_group_box.setTitle("Enter Formula")
        screen_layout = QVBoxLayout()
        screen_layout.setContentsMargins(3,3,3,3)

        self.calc_text_edit = QPlainTextEdit()
        self.calc_text_edit.textChanged.connect(self.calc_set_add_formula)
        screen_layout.addWidget(self.calc_text_edit)

        # calculator status
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setFrameShape(QFrame.Shape.Box)
        self.message_label.setFrameShadow(QFrame.Shadow.Raised)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.message_label.setWordWrap(True)
        self.message_label.setText("Ready..")
        screen_layout.addWidget(self.message_label)
        screen_group_box.setLayout(screen_layout)
        calculator_layout.addWidget(screen_group_box)

        # Equations
        equation_select_layout = QHBoxLayout()
        self.comboBoxFormula = QComboBox()

        self.delete_formula_button = CustomToolButton(
            text="Delete",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
        )
        self.delete_formula_button.setToolTip("Delete selected equation")


        equation_select_layout.addWidget(self.comboBoxFormula)
        equation_select_layout.addWidget(self.delete_formula_button)
        calculator_layout.addLayout(equation_select_layout)

        # Field Control
        self.comboBoxFieldType = CustomComboBox()
        self.comboBoxFieldType.setToolTip("Select field type")
        self.comboBoxFieldType.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldType, self.comboBoxField))
        calculator_layout.addWidget(self.comboBoxFieldType)

        field_layout = QHBoxLayout()
        self.comboBoxField = CustomComboBox(popup_callback=lambda: self.update_field_combobox(self.comboBoxField))
        self.comboBoxField.setToolTip("Select field")

        self.add_formula_button = CustomToolButton(
            text="Add Formula",
            light_icon_unchecked="icon-accept-64.svg",
        )
        self.add_formula_button.setToolTip("Select a field to add it to the formula")

        field_layout.addWidget(self.comboBoxField)
        field_layout.addWidget(self.add_formula_button)
        calculator_layout.addLayout(field_layout)

        self.update_field_combobox(self.comboBoxFieldType, self.comboBoxField)

        # keypad_checkbox
        keypad_checkbox = QCheckBox()

        calculator_layout.addWidget(keypad_checkbox)

        # field/equation controls
        self.button_group = QGroupBox()
        self.button_group.setMinimumHeight(202)
        button_layout = QGridLayout()
        button_layout.setContentsMargins(3,3,3,3)
        button_layout.setHorizontalSpacing(3)
        button_layout.setVerticalSpacing(3)

        # buttons
        buttons = [
                ('+',      '+',         6,0, self.calc_insert_operator),
                ('-',      '-',         6,1, self.calc_insert_operator),
                ('*',      '*',         6,2, self.calc_insert_operator),
                ('/',      '/',         6,3, self.calc_insert_operator),
                ('x^y',    '^()',       4,0, self.calc_insert_operator),
                ('x^2',    '^2',        5,1, self.calc_insert_operator),
                ('x^-1',   '^-1',       4,1, self.calc_insert_operator),
                ('10^x',   '10^()',     4,2, self.calc_insert_operator),
                ('()',     '()',        5,0, self.calc_insert_operator),
                ('sqrt()', 'sqrt',      5,2, self.calc_insert_function),
                ('exp()',  'exp',       5,3, self.calc_insert_function),
                ('ln()',   'ln',        4,3, self.calc_insert_function),
                ('log()',  'log',       3,3, self.calc_insert_function),
                ('abs()',  'abs',       2,3, self.calc_insert_function),
                ('case()', 'case',      0,0, self.calc_insert_function),
                ('otw()',  'otherwise', 0,1, self.calc_insert_function),
                ('grad()', 'grad',      0,2, self.calc_insert_function),
                ('area()', 'area',      0,3, self.calc_insert_function),
                ('<',      ' < ',       2,0, self.calc_insert_operator),
                ('>',      ' > ',       2,1, self.calc_insert_operator),
                ('<=',     ' <= ',      3,0, self.calc_insert_operator),
                ('>=',     ' >= ',      3,1, self.calc_insert_operator),
                ('==',     ' == ',      2,2, self.calc_insert_operator),
                ('!=',     ' != ',      3,2, self.calc_insert_operator),
                ('and',    ' and ',     1,0, self.calc_insert_operator),
                ('or',     ' or ',      1,1, self.calc_insert_operator),
                ('not',    ' not ',     1,2, self.calc_insert_operator)
            ]
        
        def create_handler(handler, text=None):
            if text is not None:
                return lambda: handler(text)
            else:
                return handler

        for label, text, row, col, handler in buttons:
            button = QPushButton()
            button.setContentsMargins(0,0,0,0)
            button.setMinimumHeight(30)
            button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
            button.setText(label)
            button_layout.addWidget(button, row, col)
            button.clicked.connect(create_handler(handler, text))
        
        self.button_group.setLayout(button_layout)
        calculator_layout.addWidget(self.button_group)

        keypad_checkbox.setChecked(True)
        keypad_checkbox.stateChanged.connect(lambda: self.button_group.setVisible(keypad_checkbox.isChecked()))

        # Set layout to the container
        container.setLayout(calculator_layout)
        scroll_area.setWidget(container)

        self.setWidget(scroll_area)

        self.setFloating(True)
        self.setWindowTitle("LaME Calculator")

        self.ui.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)

    def connect_widgets(self):
        # connect actions to methods
        self.calculate_action.triggered.connect(self.calculate_new_field)
        self.save_action.triggered.connect(lambda: self.calculate_new_field(save=True))
        self.clear_action.triggered.connect(self.calc_text_edit.clear)
        self.clear_action.triggered.connect(lambda: self.message_label.setText("Ready..."))
        self.help_action.triggered.connect(self.calc_help)

        self.comboBoxFormula.activated.connect(self.calc_load_formula)
        self.delete_formula_button.clicked.connect(self.calc_delete_formula)
        self.add_formula_button.clicked.connect(self.calc_add_field)

    def connect_logger(self):
        pass

    def calc_help(self):
        """Loads the help webpage associated with the calculator in the Help tab"""
        try:
            if not hasattr(self.ui,"browser"):
                self.ui.open_browser()

            self.ui.browser.show()
            self.ui.browser.go_to_page('calculator')
        except Exception as e:
            print("Could not open browser to load calculator help page.")
        
    def calc_insert_operator(self, operator):
        """Inserts an operator into the calculator

        When the user pushes an operator button on the calculator, *operator* is inserted 
        into ``MainWindow.calc_text_edit``.

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        cursor = self.calc_text_edit.textCursor()
        cursor.insertText(operator)

    def calc_insert_function(self, func_name):
        """Inserts a func_name into the calculator

        When the user pushes a function button on the calculator, *operator* is inserted 
        into ``MainWindow.calc_text_edit``.  The ``case()`` function inserts ``(cond, expr)``
        as both a condition and expression are required to compute.  

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        cursor = self.calc_text_edit.textCursor()
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
        # get field type and name
        field_type = self.comboBoxFieldType.currentText()
        field = self.comboBoxField.currentText()

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
        cursor = self.calc_text_edit.textCursor()
        cursor.insertText(f"{{{fieldname}}}")

    #def calc_clear_text(self):
    #    self.calc_text_edit.clear()

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

                # update formula_combobox
                self.comboBoxFormula.clear()
                name_list = list(self.calc_dict.keys())
                self.comboBoxFormula.addItems(name_list)
        except FileNotFoundError as e:
            # Return an empty dictionary if the file does not exist
            QMessageBox.warning(self,'Warning','Could not load custom calculated fields.\n Starting with empty custom field dictionary.')

    def calc_delete_formula(self):
        """Deletes a previously stored formula
        
        Removes the formula from ``MainWindow.formula_combobox``, the file given by ``MainWindow.calc_filename`` and 
        ``parent.app_data.data[parent.app_data.sample_id].processed_data``.
        """
        func = 'calc_delete_formula'

        # get name of formula
        name = self.comboBoxFormula.currentText()

        # remove name from formula_combobox
        self.comboBoxFormula.removeItem(self.comboBoxFormula.currentIndex())

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
            calc_error(self, func, err, e)
            pass

        # remove field from Calculated dataframe
        self.ui.app_data.data[self.ui.app_data.sample_id].delete_column(name)

        self.message_label.setText("Formula, successfully deleted...")
    
    def calc_load_formula(self):
        """Loads a predefined formula to use in the calculator"""        
        name = self.comboBoxFormula.currentText()

        self.calc_text_edit.clear()
        self.calc_text_edit.setPlainText(self.calc_dict[name])

        self.add_formula = False
    
    def calc_set_add_formula(self):
        """Sets whether to add a new function

        Sets ``MainWindow.add_formula`` to ``True``, a flag used by ``MainWindow.calculate_new_field`` to determine
        whether to add an item to ``MainWindow.formula_combobox``.
        """        
        self.add_formula = True

    def calculate_new_field(self, save=False):
        """Calculates a new field from ``CalculatorDock.calc_text_edit`` and updates UI

        When ``CalculatorDock.toolButtonCalculate`` is clicked, ...

        If ``save == True``, the formula to ``resources/app_data/calculator.txt`` file so it can be recalled
        and used at a future time or in another sample.  Pushing ``CalculatorDock.toolButtonCalcSave``,
        opens a dialog prompting the user to input the name for the newly calculated field.

        Parameters
        ----------
        data : AttributeDataFrame
            Data used to compute custom field
        save : bool, optional
            Determines whether to save upon successful calculation, by default ``False``
        """
        func = 'CalculatorDock.calculate_new_field'
        # open dialog to get new field
        if self.add_formula:
            new_field, ok = QInputDialog.getText(self, 'Save expression', 'Enter custon field name:')
            if ok:
                # check for valid field name
                if partial_match(['_N',':'],new_field)[0]:
                    err = "new field name cannot have an '_N' or ':' in the name"
                    (func, err, '')
                    ok = False
                    
            if not ok:
                return
        else:
            new_field = self.comboBoxFormula.currentText()

        # Use CustomFieldCalculator to compute new field
        self.cfc.calculate_new_field(self.ui.app_data.data[self.ui.app_data.sample_id].processed_data, self.ui.ref_chem, new_field)

        # update formula_combobox
        self.comboBoxFormula.addItem(new_field)
        self.comboBoxFormula.setCurrentText(new_field)

        # add new calculated field to self.treeView
        self.ui.plot_tree.add_calculated_leaf(new_field)

        if self.ui.field_type_combobox.currentText == 'Calculated':
            self.update_field_combobox(self.comboBoxFieldType, self.comboBoxField)

        # get the formula and add to custom field dictionary
        formula = self.calc_text_edit.toPlainText()
        self.calc_dict.update({'field':new_field, 'expr':formula})

        # append calculator file
        if save:
            try:
                with open(self.calc_filename, 'a') as file:
                    file.write(f"{new_field}: {formula}\n")
            except Exception as e:
                # throw a warning that nam
                err = 'could not save expression, problem with write.'
                calc_error(self, func, err, e)
                return


@auto_log_methods(logger_key='Calculator')
class CustomFieldCalculator():
    def __init__(self):
        self.logger_key = 'Calculator'
        
    def calc_parse(self, data, ref_chem, txt=None):
        """Prepares expression for calculating a custom field 

        Parses ``MainWindow.calc_text_edit`` to produce an expression that can be evaluated.

        Parameters
        ----------
        data : AttributeDataFrame
            Data used to compute custom field
        ref_chem : pandas.DataFrame
            Reference chemistry used when normalization is required
        txt : str

        Returns
        -------
        str, str :
            returns the conditional (cond) and expression (expr)
        """
        func = 'CustomFieldCalculator.calc_parse'

        # remove whitespace
        if txt is None:
            return None, None

        txt = ''.join(txt.split())

        txt = txt.replace('^','**')
        txt = txt.replace('log(','log10(')
        txt = txt.replace('ln(','log(')
        txt = txt.replace('grad(','gradient(')

        if ('case' in txt) or ('otherwise' in txt):
            cases = txt.split(';')
            # if last case includes a ';', there will be an extra blank in cases list, remove it
            if cases[-1] == '':
                cases.pop()

            cond = []
            expr = []

            # deal with otherwise first as it will be used to set all the values and then cases will reset them
            otherwise_expr = None
            for i, c in enumerate(cases):
                if c.startswith('otherwise'):
                    try:
                        # extract expression after 'otherwise'
                        otherwise_expr = c[len('otherwise'):].strip()
                        _, expr_temp = self.calc_parse(data, ref_chem, txt=otherwise_expr)
                        cond.append('any')  # or None, depending on how you use it
                        expr.append(expr_temp)
                    except Exception as e:
                        calc_error(self, func, "Error parsing otherwise expression", e)
                        return None, None
                    cases.pop(i)
                    break  # only handle one 'otherwise'

            for c in cases:
                try:
                    # remove 'case' and trailing spaces
                    c = c[len('case'):].strip()
                    cond_txt, expr_txt = c.split(',', 1)
                    _, cond_temp = self.calc_parse(data, ref_chem, txt=cond_txt)
                    _, expr_temp = self.calc_parse(data, ref_chem, txt=expr_txt)
                    cond.append(cond_temp)
                    expr.append(expr_temp)
                except Exception as e:
                    err = "Each 'case' must be formatted as 'case condition, expression;'"
                    calc_error(self, func, err, e)
                    return None, None

                    return cond, expr
                else:
                    cond = None

        if txt.count('(') != txt.count(')'):
            err = 'mismatched parentheses in expr'
            calc_error(self, func, err, '')
            return None

        if txt.count('{') != txt.count('}'):
            err = 'mismatched braces in expr'
            calc_error(self, func, err, '')
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
                calc_error(self, func, err, e)
            if field[-2:] == '_N':
                field = field[:-2]
                if field_type in ['Analyte', 'Ratio']:
                    field_type = f"{field_type} (normalized)"

            if field in list(var.keys()):
                continue

            df = data.get_map_data(field, field_type, ref_chem=ref_chem)
            var.update({field: df['array']})

            txt = txt.replace(f"{{{field_str}}}", f"{field}")
        
        if len(var) == 0:
            var = None
        expr = [txt, var]

        print(expr)

        return cond, expr

    def calculate_new_field(self, data, ref_chem, new_field):
        """Calculates a new field from ``MainWindow.calc_text_edit``

        When ``MainWindow.toolButtonCalculate`` is clicked, ...

        If ``save == True``, the formula to ``resources/app_data/calculator.txt`` file so it can be recalled
        and used at a future time or in another sample.  Pushing ``MainWindow.toolButtonCalcSave``,
        opens a dialog prompting the user to input the name for the newly calculated field.

        Parameters
        ----------
        data : AttributeDataFrame
            Data used to compute custom field
        new_field : str
            Name of new field to be computed
        """
        func = 'calculate_new_field'

        # parse the expression
        cond, expr = self.calc_parse(data, ref_chem)
        if cond is None:    # no conditionals
            result = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
            if result is None:
                return
            data.add_columns('computed', new_field, result)
        elif expr is None:
            err = "expr returned 'None' could not evaluate formula. Check syntax."
            calc_error(self, func, err, '')
            return
        else:   # conditionals
            # start with empty dataFrame
            result = pd.DataFrame({new_field: np.nan*np.zeros_like(data.processed_data.iloc[:,0])})

            # loop over cases (cond, expr)
            for i in range(0,len(cond),2):
                if (i == 0) and (cond[i] == 'any'):
                    try:
                        res = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
                    except Exception as e:
                        err = "could not evaluate otherwise expression. Check syntax."
                        calc_error(self, func, err, e)
                        return
                    data.add_columns('computed', new_field, result)
                    continue

                # conditional yields boolean numpy.ndarray keep
                try:
                    keep = self.calc_evaluate_expr(cond[i], val_dict=cond[i+1])
                except Exception as e:
                    err = "could not evaluate conditional statement. Check syntax."
                    calc_error(self, func, err, e)
                    return

                # check for missing or incorrectly type for conditional
                if keep is None:
                    err = 'conditional did not return boolean result.'
                    calc_error(self, func, err, '')
                    return
                elif not isinstance(keep, np.ndarray):
                    if not np.issubdtype(keep.dtype, np.bool_):
                        err = 'conditional did not return boolean result.\n  Did you swap the conditional and expression?'
                        calc_error(self, func, err, '')
                        return

                # check for size error
                if keep.shape[0] != result.shape[0]:
                    err = 'the conditional size does not match the size of expected computed array.'
                    calc_error(self, func, err, '')
                    return

                # compute expression for indexes where keep==`True`
                try:
                    res = self.calc_evaluate_expr(expr[i], val_dict=expr[i+1], keep=keep)
                except Exception as e:
                    err = "could not evaluate expression. Check syntax."
                    calc_error(self, func, err, e)
                    return

                if res is None:
                    err = 'the expression failed to return an array of values.'
                    calc_error(self, func, err, '')
                    return

                result.loc[keep,new_field] = res

            data.add_columns('computed', new_field, result)


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
            self.message_label.setText("Success")
            if keep is None or result.ndim == 0:
                return result
            else:
                return result[keep]
        except Exception as e:
            err = 'unable to evaluate expression.'
            calc_error(self, func, err, e)
            return None
