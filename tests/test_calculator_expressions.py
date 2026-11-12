"""Expression handling in ``src/common/Calculator.py``.

Two defects, both of which made the calculator look broken in ways that
blamed the user:

**Operator precedence.** ``&`` binds tighter than the comparisons in Python's
grammar, which numexpr borrows, so ``a>b & c>d`` parses as ``a > (b&c) > d``
-- a chained comparison. Chaining is implemented with ``and``, so numexpr
raised *"You can't use Python's standard boolean operators in NumExpr
expressions"* at someone who had carefully typed ``&``. ``calc_parse`` now
parenthesizes the operands, and accepts ``and``/``or``/``not`` as well, since
those read naturally to people who don't write code.

The word forms have to be substituted *before* ``calc_parse`` strips
whitespace -- afterwards ``a > 2 and b > 3`` is ``a>2andb>3`` and the word
boundaries are gone. Those boundaries matter in the other direction too:
``Grt_almandine`` and ``Grt_andradite`` both contain ``and``.

**Missing fields.** ``get_map_data`` raises a bare ``KeyError`` for a column
the sample doesn't have, and nothing caught it -- it escaped the dock
entirely, so no dialog, no log line, and no field appeared. Every other
calculator failure reports itself; this one looked like the button doing
nothing. Stoichiometry/PCA/cluster columns are per-sample, so referring to a
field computed on a *different* sample is the usual way in.
"""
import numpy as np
import pandas as pd
import pytest

from src.common.Calculator import (
    CustomFieldCalculator,
    apply_outside_braces,
    parenthesize_boolean_operands,
)
from src.data.DataHandling import LaserSampleObj

# garnet.yaml's end members, in the order that fixes {abbrev}_dominant's
# 1-indexed codes (see src/stoichiometry/dock.py's _write_results_to_sample).
MEMBERS = ['pyrope', 'almandine', 'spessartine', 'grossular', 'andradite',
           'uvarovite']
ALMANDINE_CODE = MEMBERS.index('almandine') + 1


@pytest.fixture
def garnet_sample(sample_factory, qapp):
    """``(sample, fractions)`` -- a sample carrying a stoichiometry run's output."""
    sample = LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore',
    )
    fractions = np.random.default_rng(1).random((len(sample.processed), len(MEMBERS))) * 100
    dominant = np.argmax(fractions, axis=1) + 1.0
    sample.add_columns(
        'Stoichiometry',
        [f'Grt_{m}' for m in MEMBERS] + ['Grt_dominant'],
        np.column_stack([fractions, dominant]),
    )
    return sample, fractions


@pytest.fixture
def ratio_sample(sample_factory, qapp):
    """A sample whose ``Ratio`` column is named with spaces: ``'Sr88 / Ca43'``.

    ``ref_chem`` has to be supplied explicitly -- ``LaserSampleObj`` stores
    the constructor argument raw, so the default ``None`` makes
    ``get_map_data``'s ``self.ref_chem.empty`` check raise for every
    Analyte/Ratio field. The app always passes ``AppData.ref_chem``.
    """
    return LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore',
        ref_chem=pd.Series(dtype=float),
    )


@pytest.fixture
def calc():
    return CustomFieldCalculator(parent=None)


# --- the rewrite itself -----------------------------------------------------

@pytest.mark.parametrize("expr,expected", [
    ('a>b&c>d', '(a>b)&(c>d)'),
    ('a>b|c>d', '(a>b)|(c>d)'),
    ('a>b&c>d&e>f', '(a>b)&(c>d)&(e>f)'),
    ('~a>b&c>d', '~(a>b)&(c>d)'),          # 'not' must negate the comparison
    ('(a>b)&(c>d)', '((a>b))&((c>d))'),    # already correct: still correct
    ('(a&b)>c', '(a&b)>c'),                # nested: not a top-level operator
    ('a+b*2', 'a+b*2'),                    # no boolean operator, no change
])
def test_boolean_operands_are_parenthesized(expr, expected):
    assert parenthesize_boolean_operands(expr) == expected


def test_malformed_input_is_left_for_the_existing_error_handling():
    """An empty operand means the expression is wrong; mangling it further
    would only produce a worse error message."""
    assert parenthesize_boolean_operands('a>b&') == 'a>b&'
    assert parenthesize_boolean_operands('&a>b') == '&a>b'


# --- end to end through the calculator --------------------------------------

def dominance_expression(joiner):
    """'is almandine the largest end member', spelled with `joiner`."""
    alm = '{Stoichiometry.Grt_almandine}'
    return joiner.join(
        f'{alm} > {{Stoichiometry.Grt_{m}}}' for m in MEMBERS if m != 'almandine'
    )


@pytest.mark.parametrize("joiner,label", [(' & ', 'bitwise'), (' and ', 'word')])
def test_almandine_dominance_agrees_with_argmax(garnet_sample, calc, joiner, label):
    """Both spellings must produce the field, and the same field -- which is
    also the field ``Grt_dominant`` already holds."""
    sample, fractions = garnet_sample

    assert calc.calculate_new_field(sample, None, f'alm_{label}', dominance_expression(joiner))

    expected = np.argmax(fractions, axis=1) == MEMBERS.index('almandine')
    assert np.array_equal(sample.processed[f'alm_{label}'].values.astype(bool), expected)
    assert np.array_equal(
        sample.processed['Grt_dominant'].values == ALMANDINE_CODE, expected
    )


def test_a_field_name_containing_and_survives_the_substitution(garnet_sample, calc):
    """``\\band\\b`` must not fire inside 'almandine' or 'andradite'."""
    sample, _ = garnet_sample
    _cond, expr = calc.calc_parse(sample, None, txt='{Stoichiometry.Grt_almandine}')
    assert 'Grt_almandine' in expr[1]

    _cond, expr = calc.calc_parse(
        sample, None,
        txt='{Stoichiometry.Grt_almandine} > {Stoichiometry.Grt_andradite}',
    )
    assert set(expr[1]) == {'Grt_almandine', 'Grt_andradite'}


@pytest.mark.parametrize("formula,expected", [
    ('{Stoichiometry.Grt_almandine} / 2 + 1', lambda f: f[:, 1] / 2 + 1),
    ('{Stoichiometry.Grt_almandine} ^ 2', lambda f: f[:, 1] ** 2),
    ('{Stoichiometry.Grt_almandine} - {Stoichiometry.Grt_pyrope}',
     lambda f: f[:, 1] - f[:, 0]),
])
def test_arithmetic_is_unaffected(garnet_sample, calc, formula, expected):
    """The rewrite only touches expressions containing & or |."""
    sample, fractions = garnet_sample
    assert calc.calculate_new_field(sample, None, 'arith', formula)
    assert np.allclose(sample.processed['arith'].values, expected(fractions))


def test_a_single_field_reference_is_a_valid_formula(garnet_sample, calc):
    """Copying a Stoichiometry column into a Calculated one: the only way to
    reach a mineral-formula output from the places that offer 'Calculated'."""
    sample, fractions = garnet_sample
    assert calc.calculate_new_field(sample, None, 'dom', '{Stoichiometry.Grt_dominant}')
    assert np.array_equal(
        sample.processed['dom'].values, np.argmax(fractions, axis=1) + 1.0
    )


# --- missing fields ---------------------------------------------------------

def test_a_missing_field_reports_instead_of_raising(garnet_sample, calc):
    sample, _ = garnet_sample
    assert calc.calculate_new_field(
        sample, None, 'nope', '{Stoichiometry.Grt_nosuchthing}') is False
    assert 'nope' not in sample.processed.columns


def test_a_missing_field_inside_a_larger_expression_reports_too(garnet_sample, calc):
    sample, _ = garnet_sample
    assert calc.calculate_new_field(
        sample, None, 'nope',
        '{Stoichiometry.Grt_almandine} + {Stoichiometry.Grt_nosuchthing}') is False
    assert 'nope' not in sample.processed.columns


# --- field names that are not identifiers (every ratio) ---------------------

def test_whitespace_is_stripped_only_outside_the_braces():
    collapse = lambda s: ''.join(s.split())
    assert apply_outside_braces('  {Ratio.Sr88 / Ca43}  * 2 ', collapse) == \
        '{Ratio.Sr88 / Ca43}*2'
    assert apply_outside_braces('a + b', collapse) == 'a+b'
    assert apply_outside_braces('{A.x}', collapse) == '{A.x}'


def test_the_operator_substitution_cannot_reach_inside_a_field_name():
    """Structural protection, rather than relying on ``\\b`` to keep 'and'
    out of 'almandine'."""
    assert apply_outside_braces(
        '{Stoichiometry.Grt_almandine} and {Stoichiometry.Grt_andradite}',
        lambda s: s.replace('and', '&'),
    ) == '{Stoichiometry.Grt_almandine} & {Stoichiometry.Grt_andradite}'


RATIO = '{Ratio.Sr88 / Ca43}'


def test_a_ratio_reference_keeps_its_spaces_and_resolves(ratio_sample, calc):
    """``'Sr88 / Ca43'`` is the real column name. Stripping it to
    ``'Sr88/Ca43'`` matched nothing -- and got as far as
    ``field.split(' / ')[1]`` raising IndexError inside get_map_data."""
    assert calc.calculate_new_field(ratio_sample, None, 'r2', f'{RATIO} * 2')
    assert np.allclose(ratio_sample.processed['r2'].values,
                       ratio_sample.processed['Sr88 / Ca43'].values * 2)


def test_a_ratio_is_handed_to_numexpr_under_a_valid_identifier(ratio_sample, calc):
    """numexpr parses names with Python's grammar, so 'Sr88 / Ca43' would be
    read as a division of two unknown names."""
    _cond, expr = calc.calc_parse(ratio_sample, None, txt=f'{RATIO} * 2')
    text, names = expr
    assert all(n.isidentifier() for n in names), names
    assert 'Sr88 / Ca43' not in text


def test_the_same_ratio_twice_resolves_once(ratio_sample, calc):
    assert calc.calculate_new_field(ratio_sample, None, 'rr', f'{RATIO} + {RATIO}')
    assert np.allclose(ratio_sample.processed['rr'].values,
                       ratio_sample.processed['Sr88 / Ca43'].values * 2)


def test_a_ratio_and_an_analyte_together(ratio_sample, calc):
    assert calc.calculate_new_field(
        ratio_sample, None, 'mixed', f'{RATIO} + {{Analyte.Sr88}}')
    assert np.allclose(
        ratio_sample.processed['mixed'].values,
        ratio_sample.processed['Sr88 / Ca43'].values + ratio_sample.processed['Sr88'].values,
    )


def test_a_ratio_in_a_comparison_with_the_word_operator(ratio_sample, calc):
    """The two fixes meeting: a non-identifier name inside an expression
    whose ``and`` has to become a parenthesized ``&``."""
    assert calc.calculate_new_field(
        ratio_sample, None, 'both',
        f'{RATIO} > 0.05 and {{Analyte.Sr88}} > 500')
    expected = ((ratio_sample.processed['Sr88 / Ca43'].values > 0.05)
                & (ratio_sample.processed['Sr88'].values > 500))
    assert np.array_equal(ratio_sample.processed['both'].values.astype(bool), expected)


def test_ordinary_names_are_still_used_verbatim(ratio_sample, calc):
    """Only names that are not identifiers get a placeholder, so expressions
    and the Calculator log stay readable."""
    _cond, expr = calc.calc_parse(ratio_sample, None, txt='{Analyte.Sr88} + 1')
    assert expr[0] == 'Sr88+1'
    assert list(expr[1]) == ['Sr88']
