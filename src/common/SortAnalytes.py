import re, os
import pandas as pd
from lame_core.config import BASEDIR

def sort_analytes(method, analytes, order = 'd'):
    """Sort the analyte list

    Sorting the analyte list can make data selection easier, or improve the pattern of correlations and PCA vectors.

    Parameters
    ----------
    method : str
        Method used for sorting.  Options include ``'alphabetical'``, ``'atomic number'``, ``'mass'``, ``'compatibility'``, and ``'radius'``.
    analytes : list
        List of analytes to sort
    order : str, optional
        Sets order as ascending (``'a'``) or decending (``'d'``), by default 'd'

    Returns
    -------
    list
        Sorted analyte list. Entries with no parseable mass number (e.g. "Pb", "Pb_tot")
        are returned exactly as given; only true "{symbol}{mass}" isotope names (e.g.
        "Ca43") are reconstructed from their parsed parts.
    """
    if not analytes:
        return []

    # Extract element symbols and any mass numbers if present, keeping the original
    # string alongside so mass-less / non-isotope names can be returned losslessly.
    parsed_analytes = []
    for analyte in analytes:
        # Extracts the element symbol and mass if available (e.g., "Al27" -> ("Al", 27))
        match = re.match(r"([A-Za-z]+)(\d*)", analyte)
        element_symbol = match.group(1) if match else analyte
        mass_number = int(match.group(2)) if match and match.group(2) else None
        parsed_analytes.append((analyte, element_symbol, mass_number))

    # Convert to DataFrame for easier manipulation
    df_analytes = pd.DataFrame(parsed_analytes, columns=['analyte', 'element_symbol', 'mass'])

    sort_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/element_info.xlsx'))

    # Merge with sort_data for additional information
    df_analytes = df_analytes.merge(sort_data, on='element_symbol', how='left')

    # Sort based on the selected method
    match method:
        case 'alphabetical':
            df_analytes.sort_values(by='element_symbol', ascending=True, inplace=True)
        case 'atomic number':
            df_analytes.sort_values(by='atomic_number', ascending=True, inplace=True)
        case 'mass':
            # Use provided mass or average mass if not available, for ordering only.
            df_analytes['computed_mass'] = df_analytes['mass'].fillna(df_analytes['average_mass'])
            df_analytes.sort_values(by='computed_mass', ascending=True, inplace=True)
        case 'compatibility':
            df_analytes.sort_values(by='order', ascending=False, inplace=True)
        case 'radius':
            df_analytes.sort_values(by='radius1', ascending=True, inplace=True)

    def _reconstruct(row):
        # Only rebuild "{symbol}{mass}" when a mass was parsed AND it exactly reproduces
        # the original string; otherwise return the original name untouched (covers
        # "Pb", "Pb_tot", and any other non-isotope field, without corrupting the dtype
        # of the whole 'mass' column into affecting valid isotopes like "Ca43").
        if pd.notna(row['mass']):
            candidate = f"{row['element_symbol']}{int(row['mass'])}"
            if candidate == row['analyte']:
                return candidate
        return row['analyte']

    return df_analytes.apply(_reconstruct, axis=1).to_list()


def resolve_element_tokens(tokens, analytes_list):
    """Resolves element/analyte tokens (bare symbols like ``'Sr'`` or full isotope
    names like ``'Sr88'``) to real analyte columns in ``analytes_list``.

    An exact (case-insensitive) match against a real column name is used when
    available -- this preserves specificity for a token that's already a full
    isotope name, e.g. resolving exactly ``'Sr88'`` rather than any isotope of Sr.
    Otherwise, falls back to matching by element symbol alone (stripping mass
    numbers from both sides), taking only the *first* matching isotope column --
    multi-isotope elements (e.g. Sr86/Sr87/Sr88, common in isotope geochemistry
    datasets) would otherwise all be resolved for a single bare-symbol token like
    ``'Sr'``, inflating one element into several duplicate entries wherever this
    list is used (e.g. TEC/spider plots), and shifting the position of every
    element that follows.

    Parameters
    ----------
    tokens : list of str
        Element symbols or analyte names to resolve (e.g. from a TEC preset or a
        user-picked field).
    analytes_list : list of str
        Real analyte column names available in the current sample.

    Returns
    -------
    list
        Resolved analyte column names, one per token that found a match, in
        token order, with duplicates removed.
    """
    resolved = []
    for token in tokens:
        token_lower = token.lower()
        match = next((col for col in analytes_list if col.lower() == token_lower), None)
        if match is None:
            stripped_token = re.sub(r'\d', '', token_lower)
            match = next((col for col in analytes_list if re.sub(r'\d', '', col).lower() == stripped_token), None)
        if match is not None:
            resolved.append(match)

    return list(dict.fromkeys(resolved))